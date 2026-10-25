#!/usr/bin/env python3
"""Build step for the English text: font, script streams and code hooks (standard library only).

  english.py check        build into memory and print what went where (nothing written)

1. Font: the packed text font ($FA:9280, unpacked to $7F:2000 by the descriptor at $82:8556) gets
   the English letters of tools/font12.py at hooks.FONT_BASE + 12*i (over glyphs only translated
   text used - move names and interview answers in $B3-$B5 use the font's tail), repacked
   with tools/kpack.py, in place when it fits, else in free ROM with the descriptor repointed.
2. Script: tools/script.py insert - the English over the Japanese, as letter chunks (tools/hooks.py).
3. Hooks: tools/hooks.py, with the glyph, width and stream tables.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import font12  # noqa: E402
import hooks  # noqa: E402
import kpack  # noqa: E402
import nameentry  # noqa: E402
import paths  # noqa: E402
import script  # noqa: E402
import snes  # noqa: E402

FONT_BLOCK = 0xFA9280
FONT_DESC_PTR = 0x828559          # 3-byte source pointer in the descriptor
FONT_LOAD = 0x7F2000
HOOK_END = 0xB4E000           # $B4:E000-$B4:FFFF: relocated graphics (tools/artlabels.py)


CONVERTER_LISTS = (0x85F60A, 0x868000)     # the kana-to-kanji converter's candidate lists


def converter_only_glyphs(rom):
    """Glyph codes only the (disabled) kanji converter shows: in its lists, in no string."""
    o = rom.to_file(CONVERTER_LISTS[0])
    conv = {rom.data[o + i] | rom.data[o + i + 1] << 8 for i in range(0, CONVERTER_LISTS[1] - CONVERTER_LISTS[0], 2)}
    used = set()
    for bank in script.BANKS:
        for addr, words in script.segments(rom, bank):
            used.update(words)
    for a, b in script.PROTECTED:
        o = rom.to_file(a)
        used.update(rom.data[o + i] | rom.data[o + i + 1] << 8 for i in range(0, b - a, 2))
    # font bytes that used glyphs draw from (odd = 24 bytes at code-1, even = 12 bytes at code): a
    # 12 px kanji shares its bytes with two 6 px glyphs (the digits at $200C+ sit under $2001/$2019)
    busy = set()
    for c in used:
        if 0x2000 <= c < 0xA000:
            busy.update(range(c - 1, c + 23) if c & 1 else range(c, c + 12))
    return {c for c in conv if 0x2000 <= c < 0xA000 and c & 1 and c not in used
            and busy.isdisjoint(range(c - 1, c + 23))}


def build_font(rom):
    off = rom.to_file(FONT_BLOCK)
    font, packed_len = kpack.unpack(rom.data, off)
    font = bytearray(font)
    # clear the kanji only the disabled name converter showed: the font then packs into its old room
    for code in converter_only_glyphs(rom):
        at = code - 1 - (FONT_LOAD & 0xffff)
        font[at:at + 24] = bytes(24)
    g = font12.parse()
    widths = []
    for i, ch in enumerate(font12.CHARS):
        data, adv = font12.glyph(ch, g)
        at = hooks.FONT_BASE + 12 * i - (FONT_LOAD & 0xffff)
        font[at:at + 12] = data
        widths.append(adv)
    if hooks.FONT_BASE + 12 * len(font12.CHARS) - (FONT_LOAD & 0xffff) > len(font):
        raise SystemExit('english: the English letters run past the end of the font')
    packed = kpack.pack(bytes(font))
    if len(packed) <= packed_len:
        rom.data[off:off + len(packed)] = packed
        where = FONT_BLOCK
    else:
        raise SystemExit(f'english: packed font {len(packed)} bytes > original {packed_len}; needs a new home')
    return widths, len(packed), where


def place_dictionary(rom, dictionary):
    """Write each chunk (length byte + letter indices) into hooks.DICT_FREE; [addresses], bytes."""
    ranges = [list(r) for r in hooks.DICT_FREE]
    addrs, used = [], 0
    for entry in dictionary:
        data = bytes([len(entry)]) + bytes(entry)
        r = next((r for r in ranges if r[1] - r[0] >= len(data)), None)
        if r is None:
            raise SystemExit(f'english: no room for dictionary chunk {len(addrs)} ({used} bytes placed)')
        off = rom.to_file(r[0])
        rom.data[off:off + len(data)] = data
        addrs.append(r[0])
        r[0] += len(data)
        used += len(data)
    return addrs, used


# The created wrestler's default name: two 4-word fields (family, given) at $8F:8082, copied
# straight into the name buffer ($8D:DCBB) and compared with it ($91:A3F6). Letter pairs only
# (fixed codes, no dictionary), each field ended by 0000.
DEFAULT_NAME = (0x8F8082, 'Otori', 'Rekka')


# Glyph words the game reads straight from protected tables: replaced by letters.
# $8F:C76A 秒, $8F:C76C 分 (the match time on the results screen, after the numbers).
TABLE_WORDS = [(0x8FC76A, 's'), (0x8FC76C, 'm'),
               (0x8FBDFE, '/'), (0x8FBE02, '')]   # 年 月 in the digit strip: the save slot line (91:AE2C)
SLOT_WORDS = ['', ' y', 'r']                      # hooks slotw: after the year, after the career year


def table_words(rom):
    L = script.Letters()
    for addr, letters in TABLE_WORDS:
        off = rom.to_file(addr)
        code = L.pair(letters) if letters else hooks.DICT_BASE    # '' = the empty dictionary chunk
        rom.data[off:off + 2] = code.to_bytes(2, 'little')


def default_name(rom):
    L = script.Letters()
    addr, family, given = DEFAULT_NAME
    words = []
    for name in (family, given):
        w = [L.pair(name[i:i + 2]) for i in range(0, len(name), 2)]
        if len(w) > 3:
            raise SystemExit(f'english: default name {name!r} is too long (5 letters at most)')
        words += w + [0] * (4 - len(w))
    off = rom.to_file(addr)
    rom.data[off:off + 16] = b''.join(x.to_bytes(2, 'little') for x in words)


def apply(rom, strict=True):
    """Everything above, into the Rom object; returns a one-line summary."""
    widths, flen, where = build_font(rom)
    script.EXTRA_CHUNKS[:] = nameentry.chunks()
    stats, dictionary, errors = script.insert(rom, strict)
    default_name(rom)
    table_words(rom)
    ne = nameentry.apply(rom, script.insert.chunker)
    for e in errors[:20]:
        print('  not inserted: ' + e)
    addrs, dbytes = place_dictionary(rom, dictionary)
    code, labels = hooks.assemble(widths, addrs, script.insert.chunker.last_blank())
    if hooks.HOOK_ORG + len(code) > HOOK_END:
        raise SystemExit(f'english: hooks and tables run past ${HOOK_END:06X}')
    off = rom.to_file(hooks.HOOK_ORG)
    rom.data[off:off + len(code)] = code
    L = script.Letters()
    o = rom.to_file(labels['slotw'])
    for k, letters in enumerate(SLOT_WORDS):
        w = L.pair(letters) if letters else hooks.DICT_BASE
        rom.data[o + 2 * k:o + 2 * k + 2] = w.to_bytes(2, 'little')
    for addr, old, new, what in hooks.patches(labels):
        o = rom.to_file(addr)
        if bytes(rom.data[o:o + len(old)]) != old:
            raise SystemExit(f'english: unexpected code at ${addr:06X}: {bytes(rom.data[o:o + len(old)]).hex()}')
        rom.data[o:o + len(new)] = new
    return (f'{stats["parts"]} strings in English, {stats["dict"]} dictionary chunks ({dbytes} bytes), '
            f'font {flen} bytes packed at ${where:06X}, hooks {len(code)} bytes'
            + (f', {stats["errors"]} strings too long (left Japanese)' if stats['errors'] else '') + '; ' + ne)


def main(argv=None):
    a = sys.argv[1:] if argv is None else argv
    if a == ['check']:
        rom = snes.Rom(bytearray(paths.ROM.read_bytes()))
        print(apply(rom))
        return 0
    print(__doc__)
    return 1


if __name__ == '__main__':
    sys.exit(main())
