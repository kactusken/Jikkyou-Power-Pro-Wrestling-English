#!/usr/bin/env python3
"""English labels drawn into the game's packed tile graphics (menus, buttons, captions).

  artlabels.py preview DIR         before/after PNGs of every label (Pillow not needed: own PNG)
  artlabels.py grid VRAM.bin TM CHR X Y W H [BPP]   print a tilemap region (tile/palette), to
                                   fill in a LABELS entry (TM, CHR = VRAM word addresses)

Graphics blocks are tools/kpack.py streams; a header with bit 15 set holds its tiles with the 8
rows of each bitplane pair one after the other (the decompressor interleaves them on the way to
VRAM, $80:EB24). A label names its block, the VRAM tile number where the block starts, the tile
grid of the label on screen (rows of tile numbers, as the tilemap shows them), the text, and the
colour indices: the Japanese is erased by repainting text-coloured pixels with the most common
other colour of their row, then the English is drawn (bold capitals or the plain font12 letters)
and the grid's tiles are written back. Tiles that also appear outside the label must stay the
same: list them in `keep` and the text box avoids them (an error otherwise).
The changed block is packed again: in place when it fits, else in free ROM with every 24-bit
pointer to it updated (refs are checked to be exactly the expected count).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import font12  # noqa: E402
import kpack  # noqa: E402
import pngio  # noqa: E402

# free ROM for relocated graphics blocks (after the text tables; see hooks.DICT_FREE)
GFX_FREE = [(0xB4E000, 0xB50000)]          # after the text hooks (english.HOOK_END)

LABELS = [
    # Training split window (sprites, $FF:901E at sprite tile 0): 残り(PTS), 実行, キャンセル, 休息
    dict(name='split_left', block=0xFF901E, base=0, grid=[[0x71, 0x72, 0x73], [0x81, 0x82, 0x83]],
         text='LEFT', style='plain', scrub=[(0x74, 0, 4, 15, 12), (0x84, 0, 4, 15, 12)]),
    dict(name='split_ok', block=0xFF901E, base=0, grid=[[0x90, 0x91, 0x92, 0x93], [0xa0, 0xa1, 0xa2, 0xa3]],
         text='OK', style='bold'),
    dict(name='split_back', block=0xFF901E, base=0, grid=[[0x78, 0x79, 0x7a, 0x7b], [0x88, 0x89, 0x8a, 0x8b]],
         text='Back', style='plain'),
    dict(name='split_rest', block=0xFF901E, base=0, grid=[[0x7c, 0x7d, 0x7e, 0x7f], [0x8c, 0x8d, 0x8e, 0x8f]],
         text='REST', style='plain'),
    # Rule select buttons ($FC:9BEA at VRAM tile $80, BG1 palette 3/7).
    # $B0/$B1 (lower right) are shared by STANDARD and SHOOT: erased, no text there.
    dict(name='rule_standard', block=0xFC9BEA, base=0x80,
         grid=[[0x090, 0x091, 0x092, 0x093, 0x0aa, 0x0ab, 0x0ac, 0x0ad],
               [0x096, 0x097, 0x098, 0x099, 0x0ae, 0x0af, 0x0b0, 0x0b1]],
         box=(0, 48), text='STANDARD', style='plain', fg=1),
    dict(name='rule_shoot', block=0xFC9BEA, base=0x80,
         grid=[[0x09a, 0x09b, 0x09c, 0x09d, 0x0b2, 0x0b3, 0x0b4],
               [0x09e, 0x09f, 0x0a0, 0x0a1, 0x0b5, 0x0b0, 0x0b1]],
         box=(0, 32), text='SHOOT', style='plain', fg=1),
    dict(name='rule_deathmatch', block=0xFC9BEA, base=0x80,
         grid=[[0x0a2, 0x0a3, 0x0a4, 0x0a5, 0x0b6, 0x0b7, 0x0b8, 0x0b9],
               [0x0a6, 0x0a7, 0x0a8, 0x0a9, 0x0ba, 0x0bb, 0x0bc, 0x0bd]],
         box=(0, 64), text='DEATHMATCH', style='plain', fg=1),
    # The rule tag on the Set Up screen ($FC:9302 at VRAM tile 0; $4A is the shared end cap).
    dict(name='tag_standard', block=0xFC9302, base=0, grid=[[0x4b, 0x4c, 0x4d, 0x4e, 0x4f]],
         text='STANDARD', style='tiny', fg=1),
    dict(name='tag_deathmatch', block=0xFC9302, base=0, grid=[[0x50, 0x51, 0x52, 0x53, 0x54]],
         text='DEATHMATCH', style='tiny', fg=1),
    dict(name='tag_shoot', block=0xFC9302, base=0, grid=[[0x55, 0x56, 0x57, 0x58, 0x59]],
         text='SHOOT', style='tiny', fg=1),
]


def tiles_of(data, flag, bpp=4):
    """Block bytes -> VRAM-format bytes (interleaved when the header flag is set)."""
    if not flag:
        return bytearray(data)
    out = bytearray()
    for g in range(0, len(data), 16):
        a = data[g:g + 16].ljust(16, b'\0')
        for i in range(8):
            out += bytes([a[i], a[8 + i]])
    return out[:len(data)]


def block_of(tiles, flag):
    if not flag:
        return bytes(tiles)
    out = bytearray()
    for g in range(0, len(tiles), 16):
        a = tiles[g:g + 16].ljust(16, b'\0')
        out += bytes(a[0::2]) + bytes(a[1::2])
    return bytes(out[:len(tiles)])


def decode4(t):
    rows = []
    for y in range(8):
        p = [t[2 * y], t[2 * y + 1], t[16 + 2 * y], t[17 + 2 * y]]
        rows.append([sum(((p[b] >> (7 - x)) & 1) << b for b in range(4)) for x in range(8)])
    return rows


def encode4(rows):
    t = bytearray(32)
    for y in range(8):
        for x in range(8):
            c = rows[y][x]
            for b in range(4):
                if c >> b & 1:
                    t[(16 if b >= 2 else 0) + 2 * y + (b & 1)] |= 0x80 >> x
    return bytes(t)


def compose(tiles, base, grid):
    h, w = 8 * len(grid), 8 * len(grid[0])
    img = [[0] * w for _ in range(h)]
    for gy, row in enumerate(grid):
        for gx, t in enumerate(row):
            rows = decode4(tiles[(t - base) * 32:(t - base + 1) * 32])
            for y in range(8):
                img[gy * 8 + y][gx * 8:gx * 8 + 8] = rows[y]
    return img


TINY = {   # 3x5 capitals for tags 8 px high (drawn for this project)
    'A': '.#.|#.#|###|#.#|#.#', 'B': '##.|#.#|##.|#.#|##.', 'C': '.##|#..|#..|#..|.##',
    'D': '##.|#.#|#.#|#.#|##.', 'E': '###|#..|##.|#..|###', 'F': '###|#..|##.|#..|#..',
    'G': '.##|#..|#.#|#.#|.##', 'H': '#.#|#.#|###|#.#|#.#', 'I': '###|.#.|.#.|.#.|###',
    'J': '..#|..#|..#|#.#|.#.', 'K': '#.#|#.#|##.|#.#|#.#', 'L': '#..|#..|#..|#..|###',
    'M': '#.#|###|###|#.#|#.#', 'N': '##.|#.#|#.#|#.#|#.#', 'O': '.#.|#.#|#.#|#.#|.#.',
    'P': '##.|#.#|##.|#..|#..', 'Q': '.#.|#.#|#.#|##.|.##', 'R': '##.|#.#|##.|#.#|#.#',
    'S': '.##|#..|.#.|..#|##.', 'T': '###|.#.|.#.|.#.|.#.', 'U': '#.#|#.#|#.#|#.#|###',
    'V': '#.#|#.#|#.#|#.#|.#.', 'W': '#.#|#.#|###|###|#.#', 'X': '#.#|#.#|.#.|#.#|#.#',
    'Y': '#.#|#.#|.#.|.#.|.#.', 'Z': '###|..#|.#.|#..|###', ' ': '.|.|.|.|.',
    '0': '###|#.#|#.#|#.#|###', '1': '.#.|##.|.#.|.#.|###', '2': '##.|..#|.#.|#..|###',
    '3': '##.|..#|.#.|..#|##.', '4': '#.#|#.#|###|..#|..#', '5': '###|#..|##.|..#|##.',
    '6': '.##|#..|##.|#.#|.#.', '7': '###|..#|.#.|.#.|.#.', '8': '.#.|#.#|.#.|#.#|.#.',
    '9': '.#.|#.#|.##|..#|##.', '.': '.|.|.|.|#', '-': '..|..|##|..|..', ':': '.|#|.|#|.',
}


def text_pixels(text, style):
    if style == 'plain12':               # the whole 12-row cell (lower case with descenders)
        g = font12.parse()
        cols = []
        for ch in text:
            data, adv = font12.glyph(ch, g)
            for x in range(adv):
                cols.append([1 if x < 8 and data[y] & (0x80 >> x) else 0 for y in range(12)])
        return [[c[y] for c in cols] for y in range(12)]
    if style == 'tiny':
        cols = []
        for i, ch in enumerate(text):
            rows = TINY[ch].split('|')
            if i:
                cols.append([0] * 5)
            for x in range(len(rows[0])):
                cols.append([1 if rows[y][x] == '#' else 0 for y in range(5)])
        return [[c[y] for c in cols] for y in range(5)]
    """Rows of 0/1 for a text line (caps rows 0-8 of font12, bold = each pixel doubled right)."""
    g = font12.parse()
    cols = []
    for ch in text:
        data, adv = font12.glyph(ch, g)
        w = adv + (1 if style == 'bold' else 0)
        for x in range(w):
            col = []
            for y in range(9):
                on = bool(data[y] & (0x80 >> x)) if x < 8 else False
                if style == 'bold' and x > 0:
                    on = on or bool(data[y] & (0x80 >> (x - 1)))
                col.append(1 if on else 0)
            cols.append(col)
    while cols and not any(cols[-1]):
        cols.pop()
    return [[c[y] for c in cols] for y in range(9)]


def relabel(img, text, style, fg=None, box=None):
    """Erase the ink colour (fg; default: the least common colour) and draw the text centred in
    box (x0, x1) of the label, vertically centred on where the old ink was."""
    from collections import Counter
    count = Counter(c for row in img for c in row)
    if fg is None:            # the ink: the colour of the Japanese text = least common used colour
        fg = min((c for c in count if c), key=lambda c: count[c])
    ys = [y for y, row in enumerate(img) for c in row if c == fg]
    for y, row in enumerate(img):
        others = Counter(c for c in row if c != fg)
        fill = others.most_common(1)[0][0] if others else 0
        img[y] = [fill if c == fg else c for c in row]
    tp = text_pixels(text, style)
    tw = len(tp[0]) if tp else 0
    x0, x1 = box or (0, len(img[0]))
    if tw > x1 - x0:
        raise SystemExit(f'artlabels: {text!r} is {tw} px, room {x1 - x0}')
    th = len(tp)
    top = (min(ys) + max(ys) + 1 - th) // 2 if ys else (len(img) - th) // 2
    left = x0 + (x1 - x0 - tw) // 2
    for y in range(th):
        for x in range(tw):
            if tp[y][x]:
                img[top + y][left + x] = fg
    return img


def decompose(img, tiles, base, grid):
    for gy, row in enumerate(grid):
        for gx, t in enumerate(row):
            rows = [img[gy * 8 + y][gx * 8:gx * 8 + 8] for y in range(8)]
            tiles[(t - base) * 32:(t - base + 1) * 32] = encode4(rows)


DESCRIPTORS = (0x828000, 0x82A000)   # the graphics load lists ("dest 3 bytes, source 3 bytes" entries)


def find_refs(rom, addr):
    """File offsets of 24-bit pointers to a block inside the load lists (elsewhere the same
    three bytes turn up by chance in graphics)."""
    pat = bytes([addr & 0xff, (addr >> 8) & 0xff, addr >> 16])
    lo, hi = rom.to_file(DESCRIPTORS[0]), rom.to_file(DESCRIPTORS[1] - 1) + 1
    out, i = [], lo
    while True:
        i = rom.data.find(pat, i, hi)
        if i < 0:
            return out
        out.append(i)
        i += 1


# Career hub menu: label tables at $83:C416.. (byte width, byte height, then a tilemap word per
# cell), pointed to by the list at $83:C3F2 (9 entries, bank $83). Tiles from $FF:8000 (VRAM tile 0).
HUB_PTRS = 0x83C3F2
HUB_BLOCK = 0xFF8000
HUB_TABLES = (0x83FA80, 0x840000)      # free: $83:FA7E-$83:FFFF
HUB_POS = 0x83C404                      # tilemap word offset of each label
HUB_TILEMAP = 0xF7D2EB                  # the hub's BG1 tilemap (32x32 words, packed): labels baked in
# tiles of $FF:8000 that the hub never shows (rows of a filler "ball" pattern) - new label cells
HUB_FREE_TILES = ([b + i for b in (0xa8, 0xb8, 0xc8) for i in range(8)]
                  + [0x2b, 0x45, 0x46, 0x47, 0x9e, 0x9f, 0xa0, 0xa1, 0xa2, 0xa3])   # $D8-$DD, $E8-$ED are reloaded
# The cursor box round the selected label is an animated sprite frame set (4 dashed frames per
# size): script pointer per item at $81:DCA3 (bank $81), box centre (x, y) per item at $81:DC91.
# Sizes: $DCB5 12 tiles, $DCBD 9, $DCC5 6, $DCCD 4, $DCD5 2 (centre x = left + 4*w - 1).
HUB_BOX_SCRIPTS, HUB_BOX_POS = 0x81DCA3, 0x81DC91
HUB_BOX_CENTRE = {0xDCBD: 209, 0xDCC5: 198}
HUB_BOX_SCRIPT = {2: 0xDCBD, 3: 0xDCBD, 4: 0xDCBD,     # RECORD MAGAZINE TRANSFER (were 4 wide)
                  5: 0xDCC5}                           # MOVES (was 2 wide)
HUB_LABELS = [   # (table index, columns, text, scale)
    (0, 12, 'PROCEED', 2),
    (1, 9, 'PROFILE', 1),
    (2, 7, 'RECORD', 1),
    (3, 8, 'MAGAZINE', 1),
    (4, 8, 'TRANSFER', 1),
    (5, 5, 'MOVES', 1),
    (6, 9, 'COSTUME', 1),
    (7, 6, 'DIET', 1),
    (8, 9, 'OPTIONS', 1),
]


def big_text(text, scale):
    tp = text_pixels(text, 'bold' if scale == 1 else 'plain')   # doubled letters are bold already
    return [[c for c in row for _ in range(scale)] for row in tp for _ in range(scale)]


def edge_colour(orig):
    """The outline: the colour most often next to a transparent pixel."""
    from collections import Counter
    H, W = len(orig), len(orig[0])
    cnt = Counter(orig[y][x] for y in range(H) for x in range(W) if orig[y][x] and any(
        not (0 <= y + dy < H and 0 <= x + dx < W) or not orig[y + dy][x + dx]
        for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0))))
    return cnt.most_common(1)[0][0] if cnt else None


def draw_gradient(orig, w, h, text, scale, outline=None):
    """New label image w x h tiles: the text in the original's row colours with its outline colour."""
    from collections import Counter
    allc = Counter(c for row in orig for c in row if c)
    if outline is None:
        outline = allc.most_common(1)[0][0] if allc else 15
    rowcol = []
    for row in orig:
        cnt = Counter(c for c in row if c and c != outline)
        rowcol.append(cnt.most_common(1)[0][0] if cnt else None)
    for i in range(len(rowcol)):          # rows without ink take the nearest row's colour
        if rowcol[i] is None:
            near = [j for j in range(len(rowcol)) if rowcol[j] is not None]
            rowcol[i] = rowcol[min(near, key=lambda j: abs(j - i))] if near else outline
    W, H = 8 * w, 8 * h
    img = [[0] * W for _ in range(H)]
    tp = big_text(text, scale)
    th, tw = len(tp), len(tp[0])
    if tw + 2 > W or th + 2 > H:
        raise SystemExit(f'artlabels: {text!r} is {tw}x{th} px, room {W - 2}x{H - 2}')
    top, left = (H - th) // 2, 1
    for y in range(th):
        for x in range(tw):
            if tp[y][x]:
                img[top + y][left + x] = rowcol[top + y]
    for y in range(H):
        for x in range(W):
            if img[y][x] == 0 and any(0 <= y + dy < H and 0 <= x + dx < W and tp_at(tp, top, left, y + dy, x + dx)
                                       for dy in (-1, 0, 1) for dx in (-1, 0, 1)):
                img[y][x] = outline
    return img


def tp_at(tp, top, left, y, x):
    yy, xx = y - top, x - left
    return 0 <= yy < len(tp) and 0 <= xx < len(tp[0]) and tp[yy][xx]


def apply_hub(rom):
    """The hub menu labels: new tables (wider where needed, extra cells from HUB_FREE_TILES)."""
    r = rom.data
    off = rom.to_file(HUB_BLOCK)
    flag = r[off + 1] & 0x80
    data, plen = kpack.unpack(r, off)
    tiles = tiles_of(data, flag)
    free = list(HUB_FREE_TILES)
    plist = rom.to_file(HUB_PTRS)
    poff = rom.to_file(HUB_POS)
    toff = rom.to_file(HUB_TILEMAP)
    tmap, tlen = kpack.unpack(r, toff)
    tmap = bytearray(tmap)
    where = rom.to_file(HUB_TABLES[0])
    end = rom.to_file(HUB_TABLES[1] - 1) + 1
    for idx, cols, text, scale in HUB_LABELS:
        p = r[plist + 2 * idx] | r[plist + 2 * idx + 1] << 8
        o = rom.to_file(0x830000 | p)
        w, h = r[o], r[o + 1]
        ents = [r[o + 2 + 2 * k] | r[o + 3 + 2 * k] << 8 for k in range(w * h)]
        attr = ents[0] & 0xfc00
        grid = [[e & 0x3ff for e in ents[y * w:(y + 1) * w]] for y in range(h)]
        orig = compose(tiles, 0, grid)
        img = draw_gradient(orig, cols, h, text, scale)
        seen, cells = set(), []
        for y in range(h):
            row = []
            for x in range(cols):
                t = grid[y][x] if x < w else None
                if t is None or t == 0 or t in seen:
                    t = free.pop(0)
                seen.add(t)
                row.append(t)
            cells.append(row)
        decompose(img, tiles, 0, cells)
        table = bytes([cols, h]) + b''.join((attr | t).to_bytes(2, 'little') for row in cells for t in row)
        if where + len(table) > end:
            raise SystemExit('artlabels: hub tables do not fit in $83:FA80')
        r[where:where + len(table)] = table
        cpu = rom.to_cpu(where)
        r[plist + 2 * idx:plist + 2 * idx + 2] = (cpu & 0xffff).to_bytes(2, 'little')
        where += len(table)
        pos = r[poff + 2 * idx] | r[poff + 2 * idx + 1] << 8
        for y in range(h):
            for x in range(cols):
                k = 2 * (pos + 32 * y + x)
                tmap[k:k + 2] = (attr | cells[y][x]).to_bytes(2, 'little')
    packed = kpack.pack(block_of(tiles, flag), flag << 8)
    if len(packed) > plen:
        raise SystemExit(f'artlabels: hub graphics grew to {len(packed)} bytes (room {plen})')
    r[off:off + len(packed)] = packed
    tflag = r[toff + 1] & 0x80
    tp = kpack.pack(bytes(tmap), tflag << 8)
    store(rom, HUB_TILEMAP, tp, tlen)
    for idx, script in HUB_BOX_SCRIPT.items():      # the cursor box: a wider frame set, re-centred
        r[rom.to_file(HUB_BOX_SCRIPTS) + 2 * idx:rom.to_file(HUB_BOX_SCRIPTS) + 2 * idx + 2] = script.to_bytes(2, 'little')
        r[rom.to_file(HUB_BOX_POS) + 2 * idx] = HUB_BOX_CENTRE[script]
    return f'{len(HUB_LABELS)} hub menu labels'


_free = None


def store(rom, addr, packed, old_len):
    """Put a repacked block back: in place if it fits, else into GFX_FREE with the load lists
    repointed. Returns True if moved."""
    global _free
    if _free is None:
        _free = [list(r) for r in GFX_FREE]
    off = rom.to_file(addr)
    if len(packed) <= old_len:
        rom.data[off:off + len(packed)] = packed
        return False
    refs = find_refs(rom, addr)
    if not refs:
        raise SystemExit(f'artlabels: block ${addr:06X} grew and no pointer to it was found')
    r = next((r for r in _free if r[1] - r[0] >= len(packed)), None)
    if r is None:
        raise SystemExit(f'artlabels: no room to move block ${addr:06X} ({len(packed)} bytes)')
    new = r[0]
    o2 = rom.to_file(new)
    rom.data[o2:o2 + len(packed)] = packed
    for i in refs:
        rom.data[i:i + 3] = bytes([new & 0xff, (new >> 8) & 0xff, new >> 16])
    r[0] += len(packed)
    return True


# Single tiles redrawn by hand: (block, tile, 8 rows of colour indices as hex digits, '.' = 0)
TILE_ART = [
    # match clock "00分00秒" -> "00:00 " (sprite tiles of $FF:C177)
    (0xFFC177, 0x0d, ['........', '...22...', '...21...', '........', '........', '...22...', '...21...', '........']),
    (0xFFC177, 0x1d, ['........'] * 8),
]


# Captions made of sprites: (block, colour, lines); a line = (text, cells), a cell = (x, top-left
# tile, width 8/16); the cells are 16 px high (tile, tile+1 / tile+16, tile+17). The text is drawn
# across the cells' positions on screen, so gaps between cells stay empty.
SPRITE_CAPTIONS = [
    # match intro: 実況 辻義就 / (テレビ朝日アナウンサー) - $FB:AC4C at sprite tile $160
    (0xFBAC4C, 8, [
        ('Call:', [(0, 0x06, 16), (16, 0x08, 16)]),
        ('Y. Tsuji', [(40, 0x0a, 16), (56, 0x0c, 16), (72, 0x0e, 16)]),
        ('(TV Asahi announcer)', [(0, 0x20, 8)] + [(8 + 16 * i, t, 16) for i, t in
                                                    enumerate((0x21, 0x23, 0x25, 0x27, 0x29, 0x2b, 0x2d, 0x40, 0x42))]),
    ]),
]


# Big 2x2-tile glyph cells: (block, top row tile, bottom row tile, text) - cell k = tiles top+2k,
# top+2k+1 over bottom+2k, bottom+2k+1; one letter per cell in the cell's own colours and outline.
GLYPH_CELLS = [
    # career hub, left column: the promotion name stacked vertically ($FB:92E5)
    (0xFB92E5, 0x60, 0x70, 'SJPW   '),       # 超日本プロレス (7 cells)
    (0xFB92E5, 0xe0, 0xf0, 'TOUR'),          # 海外遠征 (overseas tour)
    (0xFB92E5, 0x44, 0x48, ['RE', 'ST']),    # オフ (a month without matches), two cells
    (0xFB92E5, 0x3c, 0x40, ['SH', 'OW']),    # 興行 (a month with shows), two cells
]

# Labels redrawn in place in the hub's gradient style: (block, grid, text)
GRADIENT_LABELS = [
    (0xFF8000, [[0x32, 0x33], [0x34, 0x37], [0x38, 0x39]], 'MO'),        # 月 after the big month
    (0xFF8000, [[0x02, 0x03, 0x04], [0x09, 0x0a, 0x0b]], 'YR', 'flat'),  # 年目 (career year)
    (0xFF8000, [[0x06, 0x07], [0x0c, 0x0d]], 'YO', 'flat'),              # 歳 (age: 18 yo)
]


def draw_gradient_fits(text):
    return len(big_text(text, 1)[0]) + 2 <= 16


def apply_gradient_labels(rom):
    byblock = {}
    for addr, grid, text, *style in GRADIENT_LABELS:
        byblock.setdefault(addr, []).append((grid, text, style[0] if style else 'gradient'))
    for addr, items in byblock.items():
        off = rom.to_file(addr)
        flag = rom.data[off + 1] & 0x80
        data, plen = kpack.unpack(rom.data, off)
        tiles = tiles_of(data, flag)
        for grid, text, style in items:
            orig = compose(tiles, 0, grid)
            if style == 'flat':          # solid background: letters in the main ink colour
                from collections import Counter
                cnt = Counter(c for row in orig for c in row)
                bg = cnt.most_common(1)[0][0]
                ink = next(c for c, n in cnt.most_common() if c != bg)
                tp = big_text(text, 1)
                H, W = len(orig), len(orig[0])
                img = [[bg] * W for _ in range(H)]
                top = (H - len(tp)) // 2
                for y in range(len(tp)):
                    for x in range(len(tp[0])):
                        if tp[y][x]:
                            img[top + y][x] = ink
            else:
                img = draw_gradient(orig, len(grid[0]), len(grid), text, 1)
            bgc = img[0][0]
            xs = [x for row in img for x, c in enumerate(row) if c != bgc]
            shift = (len(img[0]) - (max(xs) + 1 - min(xs))) // 2 - min(xs)
            img = [[row[x - shift] if 0 <= x - shift < len(row) else bgc for x in range(len(row))] for row in img]
            decompose(img, tiles, 0, grid)
        store(rom, addr, kpack.pack(block_of(tiles, flag), flag << 8), plen)
    return f'{len(GRADIENT_LABELS)} gradient labels'


def apply_cells(rom):
    byblock = {}
    for addr, top, bot, text in GLYPH_CELLS:
        byblock.setdefault(addr, []).append((top, bot, text))
    for addr, items in byblock.items():
        off = rom.to_file(addr)
        flag = rom.data[off + 1] & 0x80
        data, plen = kpack.unpack(rom.data, off)
        tiles = tiles_of(data, flag)
        ref = None
        for top, bot, text in items:
            for k, ch in enumerate(text):
                grid = [[top + 2 * k, top + 2 * k + 1], [bot + 2 * k, bot + 2 * k + 1]]
                if len(ch) > 1 and draw_gradient_fits(ch):
                    pass
                orig = compose(tiles, 0, grid)
                if any(any(r) for r in orig):
                    ref = orig
                img = (draw_gradient(ref or orig, 2, 2, ch, 1, edge_colour(ref or orig)) if ch.strip()
                       else [[0] * 16 for _ in range(16)])
                if ch.strip():          # centre the letter in the cell
                    xs = [x for row in img for x, c in enumerate(row) if c]
                    shift = (16 - (max(xs) + 1 - min(xs))) // 2 - min(xs)
                    img = [[row[x - shift] if 0 <= x - shift < 16 else 0 for x in range(16)] for row in img]
                decompose(img, tiles, 0, grid)
        store(rom, addr, kpack.pack(block_of(tiles, flag), flag << 8), plen)
    return f'{sum(len(t) for *_, t in GLYPH_CELLS)} glyph cells'


def apply_captions(rom):
    for addr, colour, lines in SPRITE_CAPTIONS:
        off = rom.to_file(addr)
        flag = rom.data[off + 1] & 0x80
        data, plen = kpack.unpack(rom.data, off)
        tiles = tiles_of(data, flag)
        for text, cells in lines:
            x0 = min(x for x, t, w in cells)
            width = max(x + w for x, t, w in cells) - x0
            tp = text_pixels(text, 'plain12')
            canvas = [[0] * width for _ in range(16)]
            for y in range(len(tp)):
                for x in range(min(len(tp[0]), width)):
                    if tp[y][x]:
                        canvas[2 + y][cells[0][0] - x0 + x if False else x] = colour
            for x, t, w in cells:
                for k in range(w // 8):
                    for half in range(2):
                        rows = [canvas[8 * half + y][x - x0 + 8 * k:x - x0 + 8 * k + 8] for y in range(8)]
                        tn = t + k + 16 * half
                        tiles[tn * 32:(tn + 1) * 32] = encode4(rows)
        store(rom, addr, kpack.pack(block_of(tiles, flag), flag << 8), plen)
    return f'{len(SPRITE_CAPTIONS)} sprite captions'


def apply_tiles(rom):
    byblock = {}
    for addr, tile, art in TILE_ART:
        byblock.setdefault(addr, []).append((tile, art))
    for addr, edits in byblock.items():
        off = rom.to_file(addr)
        flag = rom.data[off + 1] & 0x80
        data, plen = kpack.unpack(rom.data, off)
        tiles = tiles_of(data, flag)
        for tile, art in edits:
            rows = [[0 if c == '.' else int(c, 16) for c in r] for r in art]
            tiles[tile * 32:(tile + 1) * 32] = encode4(rows)
        store(rom, addr, kpack.pack(block_of(tiles, flag), flag << 8), plen)
    return f'{len(TILE_ART)} tiles'


# The entry form (Max Voltage, new wrestler): block $8C:FCBE (VRAM tile $80 up; $9B = blank) under
# four packed BG1 tilemaps (32x32): $FF:FEFB name, $FB:9205 birthday, $FB:914B sports, $FA:90D1
# summary. The title 入門届作成 took 10x2 cells with two tiles repeated: it goes onto its 18
# different tiles as 9x2 in every map. Name page: 名字/名前 (sharing their 名 tiles) are blanked -
# "Family name"/"Given name" are text in the screen's string ($90:FA54). Summary: 名前 誕生日
# スポーツ歴 become NAME BORN SPORTS on the tiles those three used. Dates: 月 (a mirrored pair)
# becomes "/" on its own tiles, 日 is blanked - "9 / 13".
FORM_BLOCK, FORM_BASE, FORM_BLANK = 0x8CFCBE, 0x80, 0x9B
FORM_MAPS = (0xFFFEFB, 0xFB9205, 0xFB914B, 0xFA90D1)
FORM_TITLE_OLD = [[0x81, 0x82, 0x83, 0x83, 0x84, 0x85, 0x86, 0x87, 0x88, 0x89],
                  [0x8a, 0x8a, 0x8b, 0x8c, 0x8d, 0x8e, 0x8f, 0x90, 0x91, 0x92]]
FORM_TITLE = [[0x81, 0x82, 0x83, 0x84, 0x85, 0x86, 0x87, 0x88, 0x89],
              [0x8a, 0x8b, 0x8c, 0x8d, 0x8e, 0x8f, 0x90, 0x91, 0x92]]
# (text, colours from these old tiles, new grid, map, row, column, cells cleared before)
FORM_LABELS = [
    ('ENTRY FORM', FORM_TITLE_OLD, FORM_TITLE, None, 1, 1, [(r, c) for r in (1, 2) for c in range(1, 11)]),
    ('NAME', [[0x93, 0x94], [0x97, 0x98]], [[0x93, 0x94, 0x95, 0x96], [0x97, 0x98, 0x99, 0x9a]],
     0xFA90D1, 5, 1, [(r, c) for r in (5, 6) for c in range(1, 9)]),
    ('BORN', [[0x93, 0x94], [0x97, 0x98]], [[0x80, 0x9c, 0x9d, 0x9e], [0xa1, 0xa2, 0xa3, 0xa4]],
     0xFA90D1, 8, 1, [(r, c) for r in (8, 9) for c in range(1, 9)]),
    ('SPORTS', [[0x93, 0x94], [0x97, 0x98]], [[0xa9, 0xaa, 0xab, 0xac, 0xad, 0xae], [0xb1, 0xb2, 0xb3, 0xb4, 0xb5, 0xb6]],
     0xFA90D1, 14, 1, [(r, c) for r in (14, 15) for c in range(1, 9)]),
    ('/', [[0xa0, 0xa0], [0xa6, 0xa7]], [[0xa0, 0xaf], [0xa6, 0xa7]], 0xFB9205, 7, 13, []),
    ('/', [[0xa0, 0xa0], [0xa6, 0xa7]], [[0xa0, 0xaf], [0xa6, 0xa7]], 0xFA90D1, 8, 14, []),
]
FORM_BLANKED = {0xFFFEFB: [(r, c) for r in (5, 6, 8, 9) for c in range(8, 12)],
                0xFB9205: [(r, c) for r in (7, 8) for c in (21, 22)],
                0xFA90D1: [(r, c) for r in (11, 12) for c in (14, 15)]}


def apply_form(rom):
    off = rom.to_file(FORM_BLOCK)
    flag = rom.data[off + 1] & 0x80
    data, plen = kpack.unpack(rom.data, off)
    tiles = tiles_of(data, flag)
    old = bytes(tiles)
    for text, src, grid, *_ in FORM_LABELS:
        orig = compose(old, FORM_BASE, src)
        inks = {c for row in orig for c in row if c}
        if len(inks) == 1:               # one colour, no outline (名前 誕生日 スポーツ歴 月): flat letters
            ink = inks.pop()
            tp = big_text(text, 1)
            H, W = 8 * len(grid), 8 * len(grid[0])
            if len(tp[0]) + 2 > W:
                raise SystemExit(f'artlabels: {text!r} is {len(tp[0])} px, room {W - 2}')
            top = (H - len(tp)) // 2
            img = [[0] * W for _ in range(H)]
            for y in range(len(tp)):
                for x in range(len(tp[0])):
                    if tp[y][x]:
                        img[top + y][1 + x] = ink
        else:
            img = draw_gradient(orig, len(grid[0]), len(grid), text, 1)
        if text == '/':                  # centred in its cell
            bgc = img[0][0]
            xs = [x for row in img for x, c in enumerate(row) if c != bgc]
            shift = (len(img[0]) - (max(xs) + 1 - min(xs))) // 2 - min(xs)
            img = [[row[x - shift] if 0 <= x - shift < len(row) else bgc for x in range(len(row))] for row in img]
        decompose(img, tiles, FORM_BASE, grid)
    store(rom, FORM_BLOCK, kpack.pack(block_of(tiles, flag), flag << 8), plen)
    for addr in FORM_MAPS:
        off = rom.to_file(addr)
        mflag = rom.data[off + 1] & 0x80
        mdata, mlen = kpack.unpack(rom.data, off)
        m = bytearray(mdata)

        def get(r, c):
            return m[2 * (32 * r + c)] | m[2 * (32 * r + c) + 1] << 8

        def put(r, c, v):
            m[2 * (32 * r + c):2 * (32 * r + c) + 2] = v.to_bytes(2, 'little')
        for text, src, grid, where, r0, c0, clear in FORM_LABELS:
            if where not in (None, addr):
                continue
            attr = get(r0, c0) & 0x3C00            # palette and priority, no flips
            for r, c in clear:
                put(r, c, FORM_BLANK)
            for gy, row in enumerate(grid):
                for gx, t in enumerate(row):
                    put(r0 + gy, c0 + gx, attr | t)
        for r, c in FORM_BLANKED.get(addr, []):
            put(r, c, FORM_BLANK)
        store(rom, addr, kpack.pack(bytes(m), mflag << 8), mlen)
    return f'entry form ({len(FORM_LABELS)} labels)'


# Career screen titles in the same style as the entry form's: (text, block, VRAM tile of the block,
# packed BG1 tilemaps (none: drawn in place, the screen builds its map in code), old cells (for
# the colours), new grid (the old title's distinct tiles, plus free ones), row, column, columns
# the old title covered, tiles to clear).
_EDIT_PAGES = (0xFCA22C, 0xFB858C, 0xFB8000, 0xFB8117, 0xFB81F8, 0xFB8337, 0xFB848C, 0xFB8675,
               0xFB8775, 0xFB8875, 0xFB89BA)
TITLES = [
    ('PROFILE', 0xFC90AF, 0x80, (0xFC8FDB,),
     [[0x81, 0x82, 0x83, 0x83, 0x81, 0x84, 0x85, 0x86, 0x87, 0x87, 0x88, 0x89],
      [0x8a, 0x8b, 0x8c, 0x8c, 0x8a, 0x8b, 0x8d, 0x8e, 0x87, 0x87, 0x8f, 0x90]],
     [[0x81, 0x82, 0x83, 0x84, 0x85, 0x86, 0x87, 0x88], [0x89, 0x8a, 0x8b, 0x8c, 0x8d, 0x8e, 0x8f, 0x90]],
     1, 1, 12, ()),
    # 戦績: 4x2 cells; $8B-$8E are free in the block
    ('RECORD', 0xF799A7, 0x80, (0xFB8B12,),
     [[0x81, 0x82, 0x83, 0x84], [0x85, 0x86, 0x87, 0x88]],
     [[0x81, 0x82, 0x83, 0x84, 0x8b, 0x8c], [0x85, 0x86, 0x87, 0x88, 0x8d, 0x8e]], 1, 1, 6, ()),
    # 月刊プロレス通信 and 連載ページ (the magazine)
    ('PRO-WRES NEWS', 0xF79CD0, 0x80, (0xF79517,),
     [[0x88, 0x89, 0x8c, 0x8d, 0x90, 0x91, 0x94, 0x95, 0xa5, 0xa6, 0x98, 0x99, 0x9d, 0x9e, 0xa1, 0xa2],
      [0x8a, 0x8b, 0x8e, 0x8f, 0x92, 0x93, 0x96, 0x97, 0xa7, 0xa8, 0x9a, 0x9c, 0x9f, 0xa0, 0xa3, 0xa4]],
     [[0x88, 0x89, 0x8c, 0x8d, 0x90, 0x91, 0x94, 0x95, 0xa5, 0xa6, 0x98, 0x99, 0x9d, 0x9e, 0xa1, 0xa2],
      [0x8a, 0x8b, 0x8e, 0x8f, 0x92, 0x93, 0x96, 0x97, 0xa7, 0xa8, 0x9a, 0x9c, 0x9f, 0xa0, 0xa3, 0xa4]],
     1, 1, 16, ()),
    ('FEATURES', 0xF79CD0, 0x80, (0xF79517,),
     [[0xa9, 0xaa, 0xab, 0xac, 0xad, 0xae, 0xaf, 0xb0, 0xb1, 0xb2],
      [0xb3, 0xb4, 0xb5, 0xb6, 0xb7, 0xb8, 0xb9, 0xba, 0xbb, 0xbc]],
     [[0xa9, 0xaa, 0xab, 0xac, 0xad, 0xae, 0xaf, 0xb0, 0xb1, 0xb2],
      [0xb3, 0xb4, 0xb5, 0xb6, 0xb7, 0xb8, 0xb9, 0xba, 0xbb, 0xbc]], 10, 1, 10, ()),
    # 技設定 (moves menu) and コンバート (learn moves: map built in code - in place)
    ('MOVES', 0xF8ABC4, 0x80, (0xF8B048,),
     [[0x81, 0x82, 0x83, 0x84, 0x85, 0x85], [0x8d, 0x8e, 0x8f, 0x90, 0x91, 0x92]],
     [[0x81, 0x82, 0x83, 0x84, 0x85], [0x8d, 0x8e, 0x8f, 0x90, 0x91]], 1, 1, 6, ()),
    ('LEARN', 0xF8ABC4, 0x80, (),
     [[0xa9, 0xaa, 0xab, 0xac, 0xad, 0xae], [0xb2, 0xb3, 0xb4, 0xb5, 0xb6, 0xb7]],
     [[0xa9, 0xaa, 0xab, 0xac, 0xad, 0xae], [0xb2, 0xb3, 0xb4, 0xb5, 0xb6, 0xb7]], 0, 0, 0,
     (0xaf, 0xa7, 0xa8, 0xb0, 0xb1)),
    # エディット (edit moves, every page map); PAGE:n after it stays
    ('EDIT', 0xFCF9FC, 0x80, _EDIT_PAGES,
     [[0x81, 0x81, 0x82, 0x83, 0x84, 0x85, 0x86, 0x87, 0x88, 0x89],
      [0x8a, 0x8a, 0x8b, 0x8c, 0x8d, 0x8e, 0x8f, 0x90, 0x91, 0x92]],
     [[0x81, 0x82, 0x83, 0x84], [0x8a, 0x8b, 0x8c, 0x8d]], 1, 1, 10, ()),
    # 試合 (the show card, results of each bout): block $F7:963E, map $FB:8BE8; the right column was
    # the middle tile flipped - $A0/$A1 are free
    ('CARD', 0xF7963E, 0x80, (0xFB8BE8,),
     [[0x81, 0x82, 0x83, 0x83], [0x84, 0x85, 0x86, 0x86]],
     [[0x81, 0x82, 0x83, 0xa0], [0x84, 0x85, 0x86, 0xa1]], 1, 1, 4, ()),
    # 移籍 (transfer): block $F7:9C00, map $F7:9450, 4x2 distinct tiles
    ('MOVE', 0xF79C00, 0x80, (0xF79450,),
     [[0x80, 0x81, 0x82, 0x83], [0x84, 0x85, 0x86, 0x87]],
     [[0x80, 0x81, 0x82, 0x83], [0x84, 0x85, 0x86, 0x87]], 1, 1, 4, ()),
    # コスチューム (costume)
    ('COSTUME', 0x8BDC5B, 0x80, (0xF8CB79,),
     [[0x81, 0x82, 0x83, 0x84, 0x85, 0x86, 0x87, 0x88, 0x89], [0x8a, 0x8b, 0x8c, 0x8d, 0x8e, 0x8f, 0x90, 0x91, 0x92]],
     [[0x81, 0x82, 0x83, 0x84, 0x85, 0x86, 0x87], [0x8a, 0x8b, 0x8c, 0x8d, 0x8e, 0x8f, 0x90]], 1, 1, 9, ()),
    # 食事量 (diet)
    ('DIET', 0xF79B1F, 0x80, (0xF79385,),
     [[0x81, 0x81, 0x82, 0x82, 0x83, 0x83], [0x84, 0x85, 0x86, 0x87, 0x88, 0x88]],
     [[0x81, 0x82, 0x83, 0x84], [0x85, 0x86, 0x87, 0x88]], 1, 1, 6, ()),
]

# Point kinds 打 投 極 (strike, throw, submission) on the moves screens: 2x2 cells, one flat colour;
# three letters in 16 px with a narrow T and U.
POINT_CELLS = (0xF8ABC4, 0x80, [('STR', [[0x9a, 0xbb], [0x9c, 0x9d]]), ('THR', [[0x9f, 0xa0], [0xa1, 0xa2]]),
                                ('SUB', [[0xa3, 0xa4], [0xa5, 0xa6]])])
NARROW = {'T': ['###', '.#.', '.#.', '.#.', '.#.', '.#.', '.#.', '.#.', '.#.'],
          'U': ['#..#', '#..#', '#..#', '#..#', '#..#', '#..#', '#..#', '#..#', '.##.']}


def tight_text(text):
    cols = []
    for i, ch in enumerate(text):
        if ch in NARROW:
            g = NARROW[ch]
            c = [[1 if g[y][x] == '#' else 0 for y in range(9)] for x in range(len(g[0]))]
        else:
            tp = text_pixels(ch, 'plain')
            c = [[tp[y][x] for y in range(9)] for x in range(len(tp[0]))]
            while c and not any(c[-1]):
                c.pop()
        if i:
            cols.append([0] * 9)
        cols += c
    return [[c[y] for c in cols] for y in range(9)]


def flat_draw(orig, w, h, tp, centre=False):
    ink = next(c for row in orig for c in row if c)
    W, H = 8 * w, 8 * h
    if len(tp[0]) > W:
        raise SystemExit(f'artlabels: flat text {len(tp[0])} px, room {W}')
    img = [[0] * W for _ in range(H)]
    top, left = (H - len(tp)) // 2, (W - len(tp[0])) // 2 if centre else 1
    for y in range(len(tp)):
        for x in range(len(tp[0])):
            if tp[y][x]:
                img[top + y][left + x] = ink
    return img


def apply_titles(rom):
    byblock = {}
    for t in TITLES:
        byblock.setdefault(t[1], []).append(t)
    for block, items in byblock.items():
        off = rom.to_file(block)
        flag = rom.data[off + 1] & 0x80
        data, plen = kpack.unpack(rom.data, off)
        tiles = tiles_of(data, flag)
        old_tiles = bytes(tiles)
        for text, _, base, maps, old, new, r0, c0, width, erase in items:
            orig = compose(old_tiles, base, old)
            inks = {c for row in orig for c in row if c}
            if len(inks) == 1:
                img = flat_draw(orig, len(new[0]), len(new), big_text(text, 1))
            else:
                img = draw_gradient(orig, len(new[0]), len(new), text, 1)
            decompose(img, tiles, base, new)
            for t in erase:
                tiles[(t - base) * 32:(t - base + 1) * 32] = bytes(32)
        if block == POINT_CELLS[0]:
            for text, grid in POINT_CELLS[2]:
                orig = compose(old_tiles, POINT_CELLS[1], grid)
                decompose(flat_draw(orig, 2, 2, tight_text(text), True), tiles, POINT_CELLS[1], grid)
        store(rom, block, kpack.pack(block_of(tiles, flag), flag << 8), plen)
    bymap = {}
    for t in TITLES:
        for addr in t[3]:
            bymap.setdefault(addr, []).append(t)
    for addr, items in bymap.items():
        off = rom.to_file(addr)
        mflag = rom.data[off + 1] & 0x80
        mdata, mlen = kpack.unpack(rom.data, off)
        m = bytearray(mdata)
        for text, _, base, maps, old, new, r0, c0, width, erase in items:
            k0 = 2 * (32 * r0 + c0)
            attr = (m[k0] | m[k0 + 1] << 8) & 0x3C00
            for gy in range(len(old)):
                for gx in range(width):
                    t = attr | new[gy][gx] if gx < len(new[gy]) else FORM_BLANK
                    k = 2 * (32 * (r0 + gy) + c0 + gx)
                    m[k:k + 2] = t.to_bytes(2, 'little')
        store(rom, addr, kpack.pack(bytes(m), mflag << 8), mlen)
    return f'{len(TITLES)} screen titles'


def apply(rom, labels=LABELS):
    """Draw every label into its block and store the blocks. Returns a summary string."""
    byblock = {}
    for lb in labels:
        byblock.setdefault(lb['block'], []).append(lb)
    global _free
    _free = None
    moved = 0
    for addr, lbs in byblock.items():
        off = rom.to_file(addr)
        flag = rom.data[off + 1] & 0x80
        data, plen = kpack.unpack(rom.data, off)
        tiles = tiles_of(data, flag)
        for lb in lbs:
            img = compose(tiles, lb['base'], lb['grid'])
            img = relabel(img, lb['text'], lb.get('style', 'bold'), lb.get('fg'), lb.get('box'))
            decompose(img, tiles, lb['base'], lb['grid'])
            for t, x0, x1, ink, fill in lb.get('scrub', ()):   # stray ink in a neighbouring tile
                k = (t - lb['base']) * 32
                rows = decode4(tiles[k:k + 32])
                rows = [[fill if x0 <= x < x1 and c == ink else c for x, c in enumerate(r)] for r in rows]
                tiles[k:k + 32] = encode4(rows)
        packed = kpack.pack(block_of(tiles, flag), flag << 8)
        moved += store(rom, addr, packed, plen)
    return (f'{len(labels)} picture labels in {len(byblock)} blocks ({moved} moved), ' + apply_hub(rom)
            + ', ' + apply_tiles(rom) + ', ' + apply_captions(rom) + ', ' + apply_cells(rom)
            + ', ' + apply_gradient_labels(rom) + ', ' + apply_form(rom) + ', ' + apply_titles(rom))


def main(argv=None):
    a = sys.argv[1:] if argv is None else argv
    if a and a[0] == 'grid':
        v = Path(a[1]).read_bytes()
        tm, chr_, x, y, w, h = (int(s, 0) for s in a[2:8])
        for ty in range(y, y + h):
            print(ty, ' '.join(f'{(v[2 * (tm + ty * 32 + tx)] | v[2 * (tm + ty * 32 + tx) + 1] << 8) & 0x3ff:03x}'
                               f'/{(v[2 * (tm + ty * 32 + tx) + 1] >> 2) & 7}' for tx in range(x, x + w)))
        return 0
    if a and a[0] == 'preview':
        import snes
        import paths
        rom = snes.Rom(paths.ROM.read_bytes())
        out = Path(a[1])
        out.mkdir(parents=True, exist_ok=True)
        for lb in LABELS:
            off = rom.to_file(lb['block'])
            flag = rom.data[off + 1] & 0x80
            tiles = tiles_of(kpack.unpack(rom.data, off)[0], flag)
            before = compose(tiles, lb['base'], lb['grid'])
            after = relabel([r[:] for r in before], lb['text'], lb.get('style', 'bold'), lb.get('fg'), lb.get('box'))
            grey = [(i * 17, i * 17, i * 17) for i in range(16)]
            rows = before + [[0] * len(before[0])] * 2 + after
            big = [[c for c in row for _ in range(4)] for row in rows for _ in range(4)]
            pngio.write_indexed(out / f'{lb["name"]}.png', big, grey) if hasattr(pngio, 'write_indexed') else None
            print(lb['name'])
        return 0
    print(__doc__)
    return 1


if __name__ == '__main__':
    sys.exit(main())
