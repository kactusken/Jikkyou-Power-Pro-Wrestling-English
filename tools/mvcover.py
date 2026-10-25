#!/usr/bin/env python3
"""Which script blocks have been shown in testing: merges Mesen code/data logs and lists the
blocks never read.

  mvcover.py report OUT.md CDL... [--groups FILE.tsv]

The game reads every script word through the CPU ($8D:B801 / $8D:B7E9), so a block whose
first words carry Mesen's "read as data" flag (2) has been drawn at least once. The logs come
from tools/mesen.py (`cdl NAME`) and are indexed by ROM offset; the English text is written in
place, so logs of any build (English or the test image) work. --groups takes a TSV whose first
two columns are a block address and a group name (e.g. a scene catalogue) to sort the report.
"""
import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402

BANKS = ('8F', '90', 'B3', 'B4', 'B5')
AREAS = {'8F': 'menus, career texts, magazine', '90': 'story, cards, results', 'B3': 'move names',
         'B4': 'interview answers', 'B5': 'interview answers'}


def off(a):
    return ((a >> 16) & 0x7F) * 0x8000 + (a & 0x7FFF)


def blocks():
    """[(address, English, Japanese)] of every translated block."""
    out = []
    for b in BANKS:
        cur, jp = None, ''
        for line in open(paths.TRANSLATION / 'script' / f'bank_{b}.txt', encoding='utf-8'):
            m = re.match(r'@ ([0-9A-F]{6})', line)
            if m:
                cur, jp = int(m.group(1), 16), ''
            elif cur is not None and line.startswith('JP'):
                jp = line[3:].strip()
            elif cur is not None and line.startswith('EN'):
                out.append((cur, line[3:].strip(), jp))
                cur = None
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('report')
    p.add_argument('out')
    p.add_argument('cdl', nargs='+')
    p.add_argument('--groups')
    a = ap.parse_args(argv)
    seen = bytearray(0x400000)
    for f in a.cdl:
        c = Path(f).read_bytes()
        for i in range(min(len(c), len(seen))):
            seen[i] |= c[i]
    groups = {}
    if a.groups:
        for line in open(a.groups, encoding='utf-8'):
            col = line.rstrip('\n').split('\t')
            if len(col) > 1 and re.fullmatch(r'[0-9A-Fa-f]{6}', col[0]):
                groups[int(col[0], 16)] = col[1]
    allb = blocks()
    keys = sorted(groups)
    tally = defaultdict(lambda: [0, 0])
    unseen = defaultdict(list)
    for addr, en, jp in allb:
        o = off(addr)
        shown = any(seen[o + k] & 2 for k in range(0, 4))
        g = AREAS[f'{addr >> 16:02X}']
        if keys:
            import bisect
            i = bisect.bisect_right(keys, addr) - 1
            if i >= 0 and addr >> 16 == keys[i] >> 16:
                g = groups[keys[i]]
        tally[g][0] += shown
        tally[g][1] += 1
        if not shown:
            unseen[g].append((addr, en))
    tot = sum(t[0] for t in tally.values()), sum(t[1] for t in tally.values())
    lines = [f'# Script coverage', '', f'{tot[0]} of {tot[1]} translated blocks shown '
             f'({100 * tot[0] // max(tot[1], 1)}%), from {len(a.cdl)} code/data log(s).', '',
             '| Group | Shown | Blocks |', '|---|---:|---:|']
    for g, (s, n) in sorted(tally.items(), key=lambda x: x[1][0] / x[1][1]):
        lines.append(f'| {g} | {s} | {n} |')
    for g in sorted(unseen):
        lines += ['', f'## Not shown: {g} ({len(unseen[g])})', '']
        lines += [f'- `{ad:06X}` {en[:100]}' for ad, en in unseen[g]]
    Path(a.out).write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(f'{a.out}: {tot[0]}/{tot[1]} blocks shown')


if __name__ == '__main__':
    sys.exit(main())
