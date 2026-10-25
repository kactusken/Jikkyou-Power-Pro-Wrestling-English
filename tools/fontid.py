#!/usr/bin/env python3
"""Guess the characters of the game's 12x12 text font (research tool; Pillow, numpy).

  fontid.py FONT.bin CODES.txt OUT.tsv

FONT.bin is the unpacked font (kpack.py unpack ROM FA9280), loaded at $7F:2000. CODES.txt lists
the glyph codes to identify (hex, one per line): odd = full width (24 bytes at code-1-0x2000,
2 bytes per row), even = half width (12 bytes, 1 byte per row). Each glyph is compared with every
JIS X 0208 character (full width) or with ASCII and half-width katakana (half width) drawn by a
Japanese TrueType font, with small shifts. OUT.tsv: code, best guess, score, next guesses.
The glyphs are stored in order of first use, so no ordering helps: check low scores by eye.
"""
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

FONTS = '/mnt/c/Windows/Fonts/'
RENDERS = [(FONTS + 'msgothic.ttc', 12), (FONTS + 'msmincho.ttc', 12), (FONTS + 'BIZ-UDGothicR.ttc', 12),
           (FONTS + 'BIZ-UDGothicR.ttc', 13), (FONTS + 'BIZ-UDGothicB.ttc', 12), (FONTS + 'YuGothM.ttc', 12)]


def jis_chars():
    out = []
    for hi in list(range(0x81, 0x85)) + list(range(0x88, 0xa0)) + list(range(0xe0, 0xeb)):
        for lo in range(0x40, 0xfd):
            if lo == 0x7f:
                continue
            try:
                ch = bytes([hi, lo]).decode('shift_jis')
            except UnicodeDecodeError:
                continue
            out.append(ch)
    return out


def half_chars():
    return [chr(c) for c in range(0x21, 0x7f)] + [chr(c) for c in range(0xff61, 0xffa0)]


def norm(a):
    a = a - a.mean()
    n = np.linalg.norm(a)
    return a / n if n else a


def blur(a):
    im = Image.fromarray((a * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.8))
    return np.asarray(im, np.float32) / 255


def render(ch, w, path, size, dx=0, dy=0):
    im = Image.new('L', (w, 12), 0)
    f = ImageFont.truetype(path, size)
    d = ImageDraw.Draw(im)
    if 'ms' in path:
        d.fontmode = '1'
    bb = d.textbbox((0, 0), ch, font=f)
    cw, chh = bb[2] - bb[0], bb[3] - bb[1]
    d.text(((w - cw) // 2 - bb[0] + dx, (12 - chh) // 2 - bb[1] + dy), ch, font=f, fill=255)
    return np.asarray(im, np.float32) / 255


def glyph(font, code):
    if code & 1:
        o = (code - 1) - 0x2000
        a = np.zeros((12, 12), np.float32)
        for r in range(12):
            v = font[o + 2 * r] << 8 | font[o + 2 * r + 1]
            for x in range(12):
                a[r, x] = 1.0 if v & (0x8000 >> x) else 0.0
    else:
        o = code - 0x2000
        a = np.zeros((12, 8), np.float32)
        for r in range(12):
            for x in range(8):
                a[r, x] = 1.0 if font[o + r] & (0x80 >> x) else 0.0
    return a


def centre(a):
    ys, xs = np.nonzero(a > 0.5)
    if not len(xs):
        return a
    h, w = a.shape
    dy = (h - 1 - ys.max() - ys.min()) // 2
    dx = (w - 1 - xs.max() - xs.min()) // 2
    return np.roll(np.roll(a, dy, 0), dx, 1)


def main(argv=None):
    a = sys.argv[1:] if argv is None else argv
    font = open(a[0], 'rb').read()
    codes = [int(x, 16) for x in open(a[1]).read().split()]
    out = []
    for full in (True, False):
        chars = jis_chars() if full else half_chars()
        w = 12 if full else 8
        cand = []
        for ch in chars:
            for path, size in RENDERS:
                cand.append((ch, norm(blur(centre(render(ch, w, path, size if full else size, 0, 0)))).ravel()))
        M = np.stack([c[1] for c in cand])
        names = [c[0] for c in cand]
        for code in codes:
            if bool(code & 1) != full:
                continue
            g0 = centre(glyph(font, code))
            G = np.stack([norm(blur(np.roll(np.roll(g0, dy, 0), dx, 1))).ravel()
                          for dx in (-1, 0, 1) for dy in (-1, 0, 1)], 1)
            s = (M @ G).max(1)
            best = {}
            for i in np.argsort(-s)[:60]:
                best.setdefault(names[i], float(s[i]))
            top = sorted(best.items(), key=lambda kv: -kv[1])[:5]
            out.append((code, top))
    out.sort()
    with open(a[2], 'w', encoding='utf-8') as f:
        for code, top in out:
            f.write(f'{code:04x}\t{top[0][0]}\t{top[0][1]:.2f}\t' + ' '.join(f'{c}{s:.2f}' for c, s in top[1:]) + '\n')
    print(f'{len(out)} glyphs -> {a[2]}')


if __name__ == '__main__':
    sys.exit(main())
