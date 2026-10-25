#!/usr/bin/env python3
"""The game's text in banks $8F and $90: parse, dump to block files, encode the English.

  script.py dump [ROM]          write translation/script/bank_8F.txt and bank_90.txt (keeps the
                                EN lines of existing files)
  script.py check FILE          report EN that does not fit (budget, line widths)

Format (docs/TECHNICAL.md "Text"): a string is 16-bit words read through $8D:B801 - glyph codes
(addresses in the font at $7F:2000; odd = 12 px, even = 6 px), controls below $2B, ended by 0000
(end) or 0001 (end of a part; callers often go on with the next part). Many strings start with a
position word (x, y in pixels). The parts are cut at every 0000/0001; each is one block, its id is
the CPU address of its first word.

Codes in the files:
  {at X,Y}     the position word at the start of a string (pixels, decimal) - keep it
  {pos X,Y}    control 03 + position: go to x, y
  {end}        0001 (the block ends with it; not written in the EN lines)
  {skip}       0002, ignored by the renderer
  {name1} {name2}   08/09: a wrestler name the game inserts
  {cNN}        any other control (hex), e.g. {c13} month, {c14} day - kept as they are
  {wXXXX}      a word that is neither: data, kept as it is
Text characters come from translation/tables/font.tsv (code -> character, machine-read and partly
checked by eye). Japanese half-width katakana and full-width letters are separate characters.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import blocks  # noqa: E402
import paths  # noqa: E402
import snes  # noqa: E402

BANKS = (0x8F, 0x90, 0xB3, 0xB4, 0xB5)
# where the text is in each bank (the rest of $B3-$B5 is code and graphics)
REGIONS = {0x8F: (0x8000, 0x10000), 0x90: (0x8000, 0x10000), 0xB3: (0xA100, 0xADFE),
           0xB4: (0x8000, 0xB148), 0xB5: (0x83A8, 0xFE0A)}
FONT_TSV = paths.TRANSLATION / 'tables' / 'font.tsv'
CTRL_MAX = 0x2B
NAMES = {1: 'end', 2: 'skip', 8: 'name1', 9: 'name2'}


def font_table(path=FONT_TSV):
    t = {}
    for line in Path(path).read_text(encoding='utf-8').splitlines():
        if not line or line.startswith('#'):
            continue
        f = line.split('\t')
        t[int(f[0], 16)] = f[1]       # '' = a piece of a picture, shown as {wXXXX}
    return t


def bank_words(rom, bank):
    lo, hi = REGIONS[bank]
    o = rom.to_file(bank << 16 | lo)
    d = rom.data[o:o + hi - lo]
    return [d[i] | d[i + 1] << 8 for i in range(0, hi - lo, 2)]


def segments(rom, bank):
    """[(cpu address, [words incl. the terminator])], cut after every 0000 and 0001.
    after_end(segs, i) tells whether part i starts a whole string."""
    w = bank_words(rom, bank)
    out, start, i = [], 0, 0
    # a table read directly by the game ends where the next string starts (no 0000 between)
    base = REGIONS[bank][0]
    cuts = {((b & 0xffff) - base) // 2 for a, b in PROTECTED if a >> 16 == bank}
    while i < len(w):
        if i in cuts and i > start:
            out.append(((bank << 16) | (base + 2 * start), w[start:i]))
            start = i
        if w[i] == 3 and i + 1 < len(w):      # 03 takes a position word, which may look like anything
            i += 2
            continue
        if w[i] == 0x0E and i + 2 < len(w):   # 0E (a choice) takes two words: ?, the address to jump to
            i += 3
            continue
        if w[i] in (0, 1):
            out.append(((bank << 16) | (base + 2 * start), w[start:i + 1]))
            start = i + 1
        i += 1
    if start < len(w):
        out.append(((bank << 16) | (base + 2 * start), w[start:]))
    return out


def after_end(segs, k):
    return k == 0 or segs[k - 1][1][-1] == 0


def is_glyph(code, font):
    return code in font


def has_text(words, font):
    return any(is_glyph(x, font) and font[x] not in (' ', '　') for x in words)


def char_class(ch):
    if not ch:
        return None
    if ch == ' ' or ('!' <= ch <= '~'):
        return 'latin'
    if '\uff61' <= ch <= '\uff9f':
        return 'kana'
    return 'other'


def has_header(words, font, after_end=True):
    """True if the part starts with a position word: not a glyph or control, or - at the start
    of a whole string (after 0000) - a half-width (even) glyph code that the next glyph does not
    go on from (headers have even x and y, full-width codes are odd; text like WWK, 1P, ﾃﾞｽﾏｯﾁ
    starts with a half-width letter followed by another of its kind)."""
    x = words[0] if words else 0
    if x < CTRL_MAX or x in (0, 1):
        return False
    if not is_glyph(x, font):
        return True
    if not after_end or x & 1:
        return False
    nxt = words[1] if len(words) > 1 else 0
    a, b = char_class(font[x]), char_class(font.get(nxt))
    return not (a in ('latin', 'kana') and a == b)


def decode(words, font, after_end=True):
    """Text form of a part (without its terminator)."""
    out = []
    i = 0
    body = words[:-1] if words and words[-1] in (0, 1) else words
    hdr = has_header(body, font, after_end)
    while i < len(body):
        x = body[i]
        if i == 1 and hdr and len(body) > 2 and body[2] == 2:
            out.append(f'{{w{x:04x}}}')       # a record: position, address of the next record, page
        elif i == 0 and hdr:
            out.append(f'{{at {x & 0xff},{x >> 8}}}')
        elif x == 3 and i + 1 < len(body):
            p = body[i + 1]
            out.append(f'{{pos {p & 0xff},{p >> 8}}}')
            i += 1
        elif x == 0x0E and i + 2 < len(body):
            out.append(f'{{c0e}}{{w{body[i + 1]:04x}}}{{w{body[i + 2]:04x}}}')
            i += 2
        elif x in NAMES and x != 1:
            out.append('{' + NAMES[x] + '}')
        elif x < CTRL_MAX:
            out.append(f'{{c{x:02x}}}')
        elif is_glyph(x, font):
            ch = font[x]
            out.append(ch if ch and ch not in '{}' else f'{{w{x:04x}}}')
        else:
            out.append(f'{{w{x:04x}}}')
        i += 1
    s = ''.join(out)
    if words and words[-1] == 1:
        s += '{end}'
    return s


def dump(rom_path=None):
    rom = snes.Rom(Path(rom_path or paths.ROM).read_bytes())
    font = font_table()
    for bank in BANKS:
        path = paths.TRANSLATION / 'script' / f'bank_{bank:02X}.txt'
        old = {b.id: b for b in blocks.BlockFile(path).blocks} if path.exists() else {}
        lines = [f'# Text of bank ${bank:02X} (tools/script.py; codes and limits: docs/TRANSLATION.md).',
                 '# One block per string part; @ id = CPU address. EN lines replace the part; no EN = unchanged.',
                 '# Keep every {code} (positions, names, numbers). {end} parts: the game draws the next part after.',
                 '']
        n = 0
        segs = segments(rom, bank)
        for k, (addr, words) in enumerate(segs):
            if not has_text(words, font):
                continue
            ident = f'{addr:06X}'
            jp = decode(words, font, after_end(segs, k))
            lines.append(f'@ {ident} words={len(words)}')
            lines.append('JP ' + jp)
            ob = old.get(ident)
            if ob:
                for k, t in ob.lines:
                    if k == blocks.EN:
                        lines.append('EN ' + t)
                    elif k == '#':
                        lines.append(t)
            lines.append('')
            n += 1
        path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
        print(f'{paths.show(path)}: {n} blocks')


# Read directly by the game's code as data (not as text): never changed.
PROTECTED = [(0x8F807E, 0x8F8092), (0x8F82C2, 0x8F82C6), (0x8FB508, 0x8FB516), (0x8FBDEA, 0x8FBE04),
             (0x8FC76A, 0x8FC76E)]
TOKEN = re.compile(r'\{([^}]*)\}|(.)', re.S)


def protected(addr, words):
    end = addr + 2 * len(words)
    return any(a < end and addr < b for a, b in PROTECTED)


class Letters:
    """The English letters (tools/font12.py) and their chunk codes (tools/hooks.py)."""

    def __init__(self):
        import font12
        import hooks
        self.hooks = hooks
        self.chars = font12.CHARS
        self.index = {ch: i for i, ch in enumerate(self.chars)}
        g = font12.parse()
        self.width = {ch: font12.glyph(ch, g)[1] for ch in self.chars}

    def px(self, s):
        return sum(self.width[c] for c in s)

    def pairable(self, s):
        """A pair word holds its first letter only below PAIR_FIRST (higher codes are dictionary chunks)."""
        return self.index[s[0]] < PAIR_FIRST

    def pair(self, s):
        a = self.index[s[0]]
        if a >= PAIR_FIRST:
            raise ValueError(f'letter {s[0]!r} (index {a}) cannot start a pair word')
        b = self.index[s[1]] if len(s) > 1 else self.hooks.SINGLE
        return self.hooks.PAIR_BASE + a * 128 + b


def items(text, where, font):
    """An EN text as a list of ('w', word) for fixed words and ('t', letters) for letter runs."""
    jp = {}
    for code, ch in font.items():
        if ch:
            jp.setdefault(ch, code)
    out, run = [], ''
    letters = Letters()

    def flush():
        nonlocal run
        if run:
            out.append(('t', run))
            run = ''
    for m in TOKEN.finditer(text):
        code, ch = m.group(1), m.group(2)
        if code is None:
            if ch in letters.index:
                run += ch
            elif ch in jp:
                flush()
                out.append(('w', jp[ch]))
            else:
                raise SystemExit(f'{where}: no glyph for {ch!r}')
            continue
        flush()
        c = code.strip()
        if c.startswith('at ') or c.startswith('pos '):
            x, y = (int(v) for v in c.split(None, 1)[1].split(','))
            if c.startswith('pos'):
                out.append(('line', None))
                out.append(('w', 3))
            out.append(('w', x | y << 8))
        elif c in ('end', 'skip', 'name1', 'name2'):
            out.append(('w', {'end': 1, 'skip': 2, 'name1': 8, 'name2': 9}[c]))
        elif re.fullmatch(r'c[0-9a-f]{2}', c):
            out.append(('w', int(c[1:], 16)))
        elif re.fullmatch(r'[wj][0-9a-f]{4}', c):
            out.append(('w', int(c[1:], 16)))
        elif re.fullmatch(r'x \d+', c):
            out.append(('x', int(c[2:])))
        else:
            raise SystemExit(f'{where}: unknown code {{{code}}}')
    flush()
    return out


PAIR_FIRST = 96     # $A000 + a*128 + b stays below DICT_BASE $D000 only for a < 96: letters from 96 up
                    # (♥ ♪ and the 1-2 px spacers) are written as one-letter dictionary chunks
EXTRA_CHUNKS = []    # chunks other build steps need in the dictionary (tools/nameentry.py)


def pad_chunks():
    """Blank runs for line padding (pad_letters) as dictionary chunks: one word clears up to 40 px."""
    L = Letters()
    out = set()
    for n in range(11):
        for tail in ('', '\x01 ', '\x02 ', '\x02\x01 '):
            c = ' ' * n + tail
            if len(c) >= 3 and L.px(c) <= 40:
                out.add(c)
    return sorted(out)


def is_blank(chunk):
    """A chunk that draws nothing: spaces and the 1-2 px spacers."""
    return all(c in ' \x01\x02' for c in chunk)


class Chunker:
    """Cuts letter runs into chunks: letter pairs, or dictionary chunks of 3+ letters up to
    hooks.MAX_CHUNK_PX wide (the dictionary is built from the whole script, most useful first)."""

    def __init__(self, runs, forced=()):
        self.L = Letters()
        maxpx = self.L.hooks.MAX_CHUNK_PX
        from collections import Counter
        count = Counter()
        for r in runs:
            for n in range(3, 13):
                for i in range(len(r) - n + 1):
                    s = r[i:i + n]
                    if self.L.px(s) <= maxpx:
                        count[s] += 1
        # a chunk of n letters saves about n/2 - 1 pair words each time it is used
        scored = sorted(((c * ((len(s) + 1) // 2 - 1), s) for s, c in count.items() if c >= 1), reverse=True)
        spaces = [' ' * k for k in range(2, maxpx // self.L.width[' '] + 1)]
        high = [c for c in self.L.chars if not self.L.pairable(c)]
        forced = list(dict.fromkeys(forced))
        # blank chunks (spaces, line padding) come first, one range the name-length hook can test
        blanks = spaces + [f for f in forced if is_blank(f) and f not in spaces]
        base = blanks + high
        self.dict = [''] + base + [f for f in forced if f not in base]
        # generous before pruning (prune() keeps only what the strings use; the build checks the room)
        room = 4 * self.L.hooks.DICT_BYTES - sum(len(e) + 1 for e in self.dict)
        for sc, s in scored:
            if len(self.dict) >= 4 * self.L.hooks.DICT_MAX:
                break
            if sc <= 0 or not s.strip() or len(s) + 1 > room:
                continue
            self.dict.append(s)
            room -= len(s) + 1
        self.code = {s: self.L.hooks.DICT_BASE + i for i, s in enumerate(self.dict)}
        self.maxlen = max((len(s) for s in self.dict), default=2)

    def cut(self, run):
        """Fewest chunks for a letter run: list of strings."""
        n = len(run)
        best = [0] + [None] * n
        back = [None] * (n + 1)
        for i in range(n):
            if best[i] is None:
                continue
            for ln in range(1, min(self.maxlen, n - i) + 1):
                s = run[i:i + ln]
                if (ln > 2 or not self.L.pairable(s)) and s not in self.code:
                    continue
                if ln == 2 and self.L.px(s) > self.L.hooks.MAX_CHUNK_PX:
                    continue
                if best[i + ln] is None or best[i] + 1 < best[i + ln]:
                    best[i + ln] = best[i] + 1
                    back[i + ln] = i
        out, j = [], n
        while j:
            out.append(run[back[j]:j])
            j = back[j]
        return out[::-1]

    def prune(self):
        """Drop the dictionary chunks no string used (the empty chunk stays first)."""
        keep = [''] + [s for s in self.dict[1:] if s in self.used or s in EXTRA_CHUNKS]
        if len(keep) > self.L.hooks.DICT_MAX or sum(len(e) + 1 for e in keep) > self.L.hooks.DICT_BYTES:
            raise SystemExit(f'script: dictionary of {len(keep)} chunks does not fit the ROM room')
        self.dict = keep
        self.code = {s: self.L.hooks.DICT_BASE + i for i, s in enumerate(self.dict)}
        self.used = None

    def last_blank(self):
        """The code of the last chunk of the leading blank range (the empty chunk is the first)."""
        n = 0
        while n < len(self.dict) and is_blank(self.dict[n]):
            n += 1
        assert not any(is_blank(e) for e in self.dict[n:]), 'script: a blank chunk outside the blank range'
        return self.L.hooks.DICT_BASE + n - 1

    def word(self, chunk):
        if chunk in self.code:
            if getattr(self, 'used', None) is not None:
                self.used.add(chunk)
            return self.code[chunk]
        if not 1 <= len(chunk) <= 2:
            raise ValueError(f'chunk {chunk!r} is neither a pair nor in the dictionary')
        return self.L.pair(chunk)


def pad_letters(L, x, goal):
    """Blank letters from x to goal. Each letter is drawn as a 6 px cell that clears its pixels,
    so none may start after goal - 6 (past that it writes outside the original text: at a bitmap's
    right edge, into the font - the name slots of the 4-player setup did that to the digits);
    1-2 px spacers put the last space exactly at goal - 6."""
    out, last = '', goal - 6
    while x + L.px(' ') <= last:
        out += ' '
        x += L.px(' ')
    if x >= goal:
        return out
    if x > last:            # already inside the last cell's reach: the letter before cleared it
        return out
    d = last - x
    out += '\x02' * (d // 2) + '\x01' * (d % 2) + ' '
    return out


def encode(seq, n, term, chunker, where, targets=(), keys=(), widest=None):
    """Words for an item list (items()) that must fill exactly n words, the last one `term`
    (None: no terminator). Lines whose original ended in blanks (targets: px per line, 0 = no)
    are padded with spaces to that width or to the widest English line at the same position
    (keys: (x, y) per line), to wipe what was drawn there before. Room left over makes the
    chunks smaller (smoother typing in the dialogue box), then is filled with empty chunks."""
    L = chunker.L
    seq = resolve_x(seq, L)
    fixed = sum(1 for k, v in seq if k == 'w') + (1 if term is not None else 0)
    budget = n - fixed
    runs = [chunker.cut(v) if k == 't' else None for k, v in seq]
    used = sum(len(r) for r in runs if r)
    if used > budget:
        raise SystemExit(f'{where}: too long - {used} chunks for {budget} words '
                         f'(shorten by about {used - budget} chunk(s) of 2-3 letters)')
    spare = budget - used
    # line ends: index of the item after which a line's padding goes
    ends, width, widths = [], 0, []
    for i, (k, v) in enumerate(seq):
        if k == 'line':
            ends.append(i - 1)
            widths.append(width)
            width = 0
        elif k == 't':
            width += L.px(v)
        elif k == 'w' and v >= CTRL_MAX and i and seq[i - 1] != ('w', 3):
            width += 12 if v & 1 else 6
    ends.append(len(seq) - 1)
    widths.append(width)
    after = {}
    for ln, (at, w) in enumerate(zip(ends, widths)):
        if ln < len(targets) and targets[ln]:
            goal = max(targets[ln], (widest or {}).get(keys[ln] if ln < len(keys) else None, 0))
            pad = pad_letters(L, w, goal)
            while pad and spare > 0:
                cut = next((k for k in range(len(pad), 0, -1) if pad[:k] in chunker.code
                            or (k <= 2 and L.pairable(pad[:k]))), 1)
                after.setdefault(at, []).append(pad[:cut])
                pad = pad[cut:]
                spare -= 1

    def split_once():
        """Cut one chunk into two or more valid ones (a pair + the rest cut again); returns the
        number of words added, 0 if nothing can be cut within the room left."""
        for size in (3, 2):
            for r in runs:
                for j, c in enumerate(r or ()):
                    if len(c) < size:
                        continue
                    pieces = [c[0], c[1:]] if len(c) == 2 else [c[:2]] + chunker.cut(c[2:])
                    added = len(pieces) - 1
                    if 0 < added <= spare:
                        r[j:j + 1] = pieces
                        return added
        return 0

    while spare > 0:
        added = split_once()
        if not added:
            break
        spare -= added
    out = []
    for c in after.get(-1, []):
        out.append(chunker.word(c))
    for i, (k, v) in enumerate(seq):
        if k == 'w':
            out.append(v)
        elif k == 't':
            out += [chunker.word(c) for c in runs[i]]
        for c in after.get(i, []):
            out.append(chunker.word(c))
    out += [chunker.code['']] * spare
    if term is not None:
        out.append(term)
    if len(out) != n:
        raise SystemExit(f'{where}: internal error, {len(out)} words for {n}')
    return out


def resolve_x(seq, L):
    """{x N} -> spaces from the current pixel position in the line to N (at least one)."""
    out, width = [], 0
    for i, (k, v) in enumerate(seq):
        if k == 'x':
            n = max(1, -(-(v - width) // L.width[' ']))
            out.append(('t', ' ' * n))
            width += n * L.width[' ']
            continue
        out.append((k, v))
        if k == 'line':
            width = 0
        elif k == 't':
            width += L.px(v)
        elif k == 'w' and v >= CTRL_MAX and i and seq[i - 1] != ('w', 3):
            width += 12 if v & 1 else 6
    return out


def line_widths(seq, L):
    """Pixel width of each line of an item list (parameter words of 03 and 0E are not glyphs)."""
    seq = resolve_x(seq, L)
    out, width, params = [], 0, 0
    for i, (k, v) in enumerate(seq):
        if k == 'line':
            out.append(width)
            width = 0
        elif k == 't':
            width += L.px(v)
        elif k == 'w':
            if params:
                params -= 1
            elif v in (3, 0x0E):
                params = 1 if v == 3 else 2
            elif v >= CTRL_MAX and i:
                width += 12 if v & 1 else 6
    out.append(width)
    return out


def jp_line_widths(words, font):
    """Pixel width of each line ({pos}) of an original part."""
    out, width = [], 0
    body = words[:-1] if words and words[-1] in (0, 1) else words
    i = 0
    while i < len(body):
        x = body[i]
        if x == 3 and i + 1 < len(body):
            out.append(width)
            width = 0
            i += 2
            continue
        if x >= CTRL_MAX and not (i == 0 and has_header(body, font)):
            width += 12 if x & 1 else 6
        i += 1
    out.append(width)
    return out


DIALOGUE_PX = 180          # the dialogue box wraps after 30 half-width columns
PAGE_PX = {0xB4: 204, 0xB5: 204}   # interview answers: 17 full-width glyphs from x 16


def page_items(text, where, font):
    """Items of one line block of a dialogue page: a trailing {end} is the block's own
    terminator; an {end} inside starts another line (0001) - lines may move between blocks."""
    return items(re.sub(r'\{end\}\s*$', '', text), where, font)


def page_line_widths(seq, L):
    out, cur = [], []
    for it in seq:
        if it in (('w', 1), ('w', 2)):
            out += line_widths(cur, L)
            cur = []
        else:
            cur.append(it)
    return out + line_widths(cur, L)


def encode_part(text, words, font, chunker, where, widest=None):
    """A menu-type part: every line after a {pos} keeps its original word offset (the game has
    tables pointing at line starts - wrestler names in the roster lists, for example), so each
    line is encoded into its own words. Falls back to one budget when the lines don't match."""
    term = words[-1] if words[-1] in (0, 1) else None
    seq = items(text.replace('{end}', ''), where, font)
    targets, keys = Encoder_padded(words, font), line_keys_of(text)
    body = words[:-1] if term is not None else words
    pos, i = [], 0                   # word index of each 03 in the original
    while i < len(body):
        if body[i] == 3 and i + 1 < len(body):
            pos.append(i)
            i += 2
            continue
        i += 3 if body[i] == 0x0E and i + 2 < len(body) else 1
    lines = [[]]
    for k, v in seq:
        if k == 'line':
            lines.append([])
        else:
            lines[-1].append((k, v))
    if not pos or len(lines) != len(pos) + 1 or any(ln[:1] != [('w', 3)] or len(ln) < 2 for ln in lines[1:]):
        return encode(seq, len(words), term, chunker, where, targets, keys, widest)
    spans = [(0, pos[0])] + [(pos[k] + 2, pos[k + 1] if k + 1 < len(pos) else len(body)) for k in range(len(pos))]
    out = []
    for ln, (lo, hi) in enumerate(spans):
        if ln:
            out += [3, lines[ln][1][1]]
        rest = lines[ln][2:] if ln else lines[0]
        out += encode(rest, hi - lo, None, chunker, f'{where} line {ln + 1}',
                      [targets[ln]] if ln < len(targets) else (), [keys[ln]] if ln < len(keys) else (), widest)
    if term is not None:
        out.append(term)
    if len(out) != len(words):
        raise SystemExit(f'{where}: internal error, {len(out)} words for {len(words)} (lines)')
    return out


def line_keys_of(text):
    keys = [] if text.lstrip().startswith('{at ') else [None]
    for m in re.finditer(r'\{(?:at|pos) (\d+),(\d+)\}', text):
        keys.append((int(m.group(1)), int(m.group(2))))
    return keys


def Encoder_padded(words, font):
    """Per line of the original part: its pixel width if it ends in blanks, else 0."""
    out, width, last_blank = [], 0, False
    body = words[:-1] if words and words[-1] in (0, 1) else words
    i = 0
    while i < len(body):
        x = body[i]
        if x == 3 and i + 1 < len(body):
            out.append(width if last_blank else 0)
            width, last_blank = 0, False
            i += 2
            continue
        if x >= CTRL_MAX and not (i == 0 and has_header(body, font)):
            width += 12 if x & 1 else 6
            last_blank = x in (0x2000, 0x25E9)
        i += 1
    out.append(width if last_blank else 0)
    return out


def translations():
    out = {}
    for bank in BANKS:
        path = paths.TRANSLATION / 'script' / f'bank_{bank:02X}.txt'
        if not path.exists():
            continue
        for b in blocks.BlockFile(path).blocks:
            en = b.english
            if en:
                out[int(b.id, 16)] = (''.join(en), f'{path.name} @ {b.id}')
    return out


def page_start(words):
    """A dialogue page begins with 0002, sometimes after a record's two words (1A00, address)."""
    return 2 in words[:3]


def units(segs, tr):
    """Groups of parts written together: a dialogue page (a part starting with 0002 and the
    lines after it, each ended by 0001) shares one word budget; any other part stands alone."""
    k = 0
    while k < len(segs):
        addr, words = segs[k]
        if addr not in tr:
            k += 1
            continue
        unit = [k]
        if page_start(words):
            while (words[-1] == 1 and k + 1 < len(segs) and segs[k + 1][0] in tr
                   and segs[k + 1][1] and not page_start(segs[k + 1][1])):
                k += 1
                addr, words = segs[k]
                unit.append(k)
        yield unit
        k += 1


def insert(rom, strict=True):
    """Write every translated part over its Japanese. Returns (stats, dictionary, errors)."""
    font = font_table()
    tr = translations()
    L = Letters()
    runs = [v for text, where in tr.values() for k, v in items(text.replace('{end}', ''), where, font) if k == 't']
    chunker = Chunker(runs)
    widest = {}
    for text, where in tr.values():
        line, width = [], 0
        for k, v in items(text.replace('{end}', ''), where, font):
            if k == 't':
                width += L.px(v)
            elif k == 'line':
                line.append(width)
                width = 0
        line.append(width)
        for key, w in zip(line_keys_of(text), line):
            if key is not None:
                widest[key] = max(widest.get(key, 0), w)
    def run_all(chunker, write):
        done, errors, failed = 0, [], []
        for bank in BANKS:
            segs = segments(rom, bank)
            for unit in units(segs, tr):
                parts = [segs[k] for k in unit]
                where = tr[parts[0][0]][1]
                if any(protected(a, w) for a, w in parts):
                    errors.append(f'{where}: read directly by the game, cannot change')
                    continue
                try:
                    if len(parts) == 1 and not page_start(parts[0][1]):
                        addr, words = parts[0]
                        new = encode_part(tr[addr][0], words, font, chunker, where, widest)
                    else:
                        seq = []
                        for j, (addr, words) in enumerate(parts):
                            for w in page_line_widths(page_items(tr[addr][0], tr[addr][1], font), L):
                                if w > PAGE_PX.get(bank, DIALOGUE_PX):
                                    raise SystemExit(f'{tr[addr][1]}: dialogue line {w} px wide '
                                                     f'(at most {PAGE_PX.get(bank, DIALOGUE_PX)})')
                            seq += page_items(tr[addr][0], tr[addr][1], font)
                            if j < len(parts) - 1:
                                seq.append(('w', words[-1]))
                        last = parts[-1][1][-1]
                        n = sum(len(w) for a, w in parts)
                        new = encode(seq, n, last if last in (0, 1) else None, chunker, where)
                except SystemExit as e:
                    errors.append(str(e))
                    failed += [v for a, w in parts for k, v in items(tr[a][0].replace('{end}', ''), where, font)
                               if k == "t" and L.px(v) <= 96]   # whole runs up to 96 px (the upload hook copies any width)
                    continue
                if write:
                    off = rom.to_file(parts[0][0])
                    rom.data[off:off + 2 * len(new)] = b''.join(w.to_bytes(2, 'little') for w in new)
                done += len(parts)
        return done, errors, failed
    done, errors, failed = run_all(chunker, False)
    extra = EXTRA_CHUNKS + pad_chunks()   # short runs in tight slots become dictionary chunks
    chunker = Chunker(runs, failed + extra)
    chunker.used = set()
    done, errors, failed = run_all(chunker, False)
    chunker.prune()                      # keep only the chunks some string uses (ROM space)
    done, errors, failed = run_all(chunker, True)
    if errors and strict:
        raise SystemExit('script: ' + '\n'.join(errors[:40]) + (f'\n... {len(errors)} in all' if len(errors) > 40 else ''))
    letters = [[L.index[c] for c in s] for s in chunker.dict]
    insert.chunker = chunker
    return {'parts': done, 'dict': len(chunker.dict), 'errors': len(errors)}, letters, errors


def check(path, rom_path=None):
    """Encode the EN of one block file (a bank file or a part of one) and report what does not
    fit: too many chunks for the words, dialogue lines over DIALOGUE_PX, menu lines wider than
    the Japanese (a warning: they may run out of their box). Returns the number of errors."""
    rom = snes.Rom(Path(rom_path or paths.ROM).read_bytes())
    font = font_table()
    L = Letters()
    bf = blocks.BlockFile(path)
    mine = {int(b.id, 16): (''.join(b.english), f'{Path(path).name} @ {b.id}') for b in bf.blocks if b.english}
    tr = translations()
    tr.update(mine)
    runs = [v for text, where in tr.values() for k, v in items(text.replace('{end}', ''), where, font) if k == 't']
    chunker = Chunker(runs)
    errors = warnings = 0
    for bank in BANKS:
        segs = segments(rom, bank)
        bysegaddr = {a: w for a, w in segs}
        for unit in units(segs, mine):
            parts = [segs[k] for k in unit]
            where = mine[parts[0][0]][1]
            try:
                if len(parts) == 1 and not page_start(parts[0][1]):
                    addr, words = parts[0]
                    text = mine[addr][0]
                    seq = items(text.replace('{end}', ''), where, font)
                    encode_part(text, words, font, chunker, where)
                    jw = jp_line_widths(words, font)
                    for ln, w in enumerate(line_widths(seq, L)):
                        if ln < len(jw) and w > jw[ln] + 4:
                            print(f'{where}: warning: line {ln + 1} is {w} px, the Japanese {jw[ln]} px - check it fits')
                            warnings += 1
                else:
                    seq = []
                    for j, (addr, words) in enumerate(parts):
                        one = page_items(mine[addr][0], mine[addr][1], font)
                        for w in page_line_widths(one, L):
                            if w > PAGE_PX.get(bank, DIALOGUE_PX):
                                print(f'{mine[addr][1]}: ERROR: dialogue line {w} px wide (at most '
                                      f'{PAGE_PX.get(bank, DIALOGUE_PX)})')
                                errors += 1
                        seq += one
                        if j < len(parts) - 1:
                            seq.append(('w', words[-1]))
                    last = parts[-1][1][-1]
                    encode(seq, sum(len(w) for a, w in parts), last if last in (0, 1) else None, chunker, where)
            except SystemExit as e:
                print('ERROR: ' + str(e))
                errors += 1
    print(f'{path}: {len(mine)} translated blocks, {errors} error(s), {warnings} warning(s)')
    return errors


def main(argv=None):
    a = sys.argv[1:] if argv is None else argv
    if a and a[0] == 'check':
        return 1 if check(a[1], a[2] if len(a) > 2 else None) else 0
    if a and a[0] == 'dump':
        dump(a[1] if len(a) > 1 else None)
        return 0
    print(__doc__)
    return 1


if __name__ == '__main__':
    sys.exit(main())
