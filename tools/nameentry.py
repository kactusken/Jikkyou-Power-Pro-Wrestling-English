#!/usr/bin/env python3
"""English name entry for the created wrestler (Max Voltage mode).

The entry screen ($8D:DC36) looks up the code to add from a 15-column table per mode:
hiragana $85:F358, katakana $85:F448, kanji $85:F538 (row*15 + column; rows 0-5 letters, 6-7 the buttons). The grids on
screen are script strings ($90:FAAE / FB8C / FC6A) drawn separately. Here the hiragana page
becomes capitals, the katakana page small letters (both with digits and signs); the kanji button
(a kana-to-kanji converter, lists at $85:F60A) does nothing ($8D:D6AF hook), with matching grid strings
(each cell a dictionary chunk: the letter centred in 12 px with 1-2 px spacers, so the letters
sit where the cursor box goes). The name buffer ($1FD2, 8 words) gets two letters per word:
$8D:DC63 (store the code, move on) now joins a letter to a lone letter before it (hook
`namepack` in tools/hooks.py), so a name can have 16 letters.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import script  # noqa: E402

TABLES = (0x85F358, 0x85F448)
GRIDS = (0x90FAAE, 0x90FB8C)
UPPER = ['ABCDEFGHIJKLMNO', 'PQRSTUVWXYZ.-\'&', '0123456789!?,"/', ':;()+*#$%=@', '', '']
LOWER = ['abcdefghijklmno', 'pqrstuvwxyz.-\'&', '0123456789!?,"/', ':;()+*#$%=@', '', '']
PAGES = (UPPER, LOWER)
CELL_TYPES = 0x8EF669      # per cell (15x8, both letter pages): bit 7 = part of a wider key; the
                           # doubled や/よ and わ/を/ん cells (rows 2 and 4, columns 5-9) made the
                           # cursor skip 6 and 8 - plain cells now (row 5 Spc and the buttons stay)
SPACE_KEY = 'Spc'          # the last row's 空白 key (columns 10-14 enter a space)
FULL_SPACE = 0x25E9        # the game's 12 px blank


def cell(ch):
    """A letter centred in 12 px: \\x01/\\x02 spacers either side."""
    L = script.Letters()
    w = L.width[ch]
    left = (12 - w) // 2
    right = 12 - w - left

    def pad(n):
        return '\x02' * (n // 2) + '\x01' * (n % 2)
    return pad(left) + ch + pad(right)


def chunks():
    """The dictionary chunks the grids need (set into script.EXTRA_CHUNKS before the script)."""
    out = {cell(ch) for page in PAGES for row in page for ch in row}
    out.add(SPACE_KEY)
    return sorted(out)


def apply(rom, chunker):
    L = script.Letters()
    off = rom.to_file(CELL_TYPES)
    for r in (2, 4):
        rom.data[off + 15 * r:off + 15 * r + 15] = bytes(15)
    for page, table, grid in zip(PAGES, TABLES, GRIDS):
        # codes: a lone letter each ($A000 + index*128 + $7F); blank cells enter a space. Rows 6-7
        # are the buttons (function codes 4 5 0 / 1 2 3: next, back, done / the three pages): kept.
        off = rom.to_file(table)
        for r in range(6):
            row = page[r] if r < len(page) else ''
            for c in range(15):
                ch = row[c] if c < len(row) else ' '
                code = L.pair(ch)
                rom.data[off + 2 * (r * 15 + c):off + 2 * (r * 15 + c) + 2] = code.to_bytes(2, 'little')
        # the grid string, word for word in the original's layout
        segs = dict(script.segments(rom, grid >> 16))
        words = segs[grid]
        out = [words[0]]                               # {at 24,92}
        for r in range(6):
            if r:
                out += [3, (24) | (92 + 16 * r) << 8]
            row = page[r]
            for g in range(3):
                if r == 5 and g == 2:
                    out.append(chunker.code[SPACE_KEY])
                    out.append(chunker.code[''])
                    break
                for c in range(5 * g, 5 * g + 5):
                    ch = row[c] if c < len(row) else None
                    out.append(chunker.code[cell(ch)] if ch else FULL_SPACE)
                if g < 2:
                    out.append(FULL_SPACE)
        out.append(words[-1])
        if len(out) > len(words):
            raise SystemExit(f'nameentry: grid ${grid:06X} needs {len(out)} words, has {len(words)}')
        out[-1:-1] = [chunker.code['']] * (len(words) - len(out))
        o = rom.to_file(grid)
        rom.data[o:o + 2 * len(out)] = b''.join(w.to_bytes(2, 'little') for w in out)
    return f'name entry: {len(PAGES)} letter pages'
