#!/usr/bin/env python3
"""Move data for the player's guide (docs/guide/index.html), read from the original ROM.

  python3 tools/guidedata.py [--check]

Writes a JSON block between the markers in docs/guide/index.html: every move with its English
name (translation/script/bank_B3.txt), its price in Max Voltage, and the wrestlers who have it;
and every wrestler's move set by situation. --check only reports whether the page is up to date.

ROM tables (docs/HIDDEN_CONTENT.md#moves):
  $82:E794  move table: 223 x (name pointer into bank $B3, move id word); a move set byte = id / 2
  $81:F43F  move set pointer per wrestler id 1-51 (bank $87, 64 bytes each)
  $83:C102  Max Voltage learning table: (price word, move id word) pairs, $FFFF ends it
  $82:E1D8  wrestler name pointers (bank $8F, translation/script/bank_8F.txt)
"""
import argparse
import bisect
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402

PAGE = paths.ROOT / 'docs' / 'guide' / 'index.html'
START, END = '<script type="application/json" id="guide-data">', '</script>'

# Move set byte -> (group, situation), from the Edit Moves pages ($83:BCB4); listed in the order
# the guide shows them. Grapple directions are the d-pad table at $81:ED3A read as facing right
# (checked in matches by the owner, 2026-10-25). Bytes 24-27, 37 (a copy of 36), 42 and 43 are not move slots.
_DIRS = ['neutral', '→', '↓', '←', '↑']
SLOTS = {}
for _group, _first in (('Light grapples', 44), ('Medium grapples', 49), ('Heavy grapples', 54)):
    for _i, _d in enumerate(_DIRS):
        SLOTS[_first + _i] = (_group, _d)
SLOTS.update({59: ('Back grapple', 'hold'), 60: ('Back grapple', 'throw'), 61: ('Back grapple', 'throw 2'),
              63: ('Back grapple', 'reversal')})
for _group, _base, _counter in (('Light strikes', [0, 1, 2, 3, 4], 9), ('Medium strikes', [12, 13, 14, 15, 16], 21)):
    for _pos, _what in zip(_base, ['close', 'far', 'kneeling foe, close', 'kneeling foe, far', 'foe on the ropes']):
        SLOTS[_pos] = (_group, _what)
    SLOTS[_counter] = (_group, 'counter (foe running)')
SLOTS.update({22: ('Heavy strikes', 'standing'), 23: ('Heavy strikes', 'counter (foe running)')})
for _group, _first in (('Downed foe: strikes', 5), ('Downed foe: holds', 17)):
    for _i, _what in enumerate(['face up, head', 'face up, feet', 'face down, head', 'face down, feet']):
        SLOTS[_first + _i] = (_group, _what)
SLOTS.update({28: ('Running', 'light'), 29: ('Running', 'light, diagonal'), 30: ('Running', 'light, downed foe'),
              31: ('Running', 'medium'), 32: ('Running', 'medium, diagonal'), 33: ('Running', 'medium, downed foe'),
              34: ('Running', 'heavy'), 35: ('Running', 'heavy, diagonal'),
              36: ('Dives', 'top rope'), 38: ('Dives', 'top rope 2, facing in'), 39: ('Dives', 'top rope 2, facing out'),
              40: ('Dives', 'top rope 3, facing in'), 41: ('Dives', 'top rope 3, facing out'),
              10: ('Dives', 'springboard'), 11: ('Dives', 'to the floor'), 62: ('Other', 'taunt')})
_ORDER = list(SLOTS)


def rom_bytes():
    return paths.ROM.read_bytes()


def off(addr):
    return ((addr >> 16) & 0x7F) * 0x8000 + (addr & 0x7FFF)


def script(bank):
    """{block address: English text} of one script file."""
    out, cur = {}, None
    for line in open(paths.TRANSLATION / 'script' / f'bank_{bank}.txt', encoding='utf-8'):
        m = re.match(r'@ ([0-9A-F]{6})', line)
        if m:
            cur = int(m.group(1), 16)
        elif cur is not None and line.startswith('EN '):
            out.setdefault(cur, line[3:].rstrip('\n'))
    return out


def plain(text):
    return re.sub(r'\{[^}]*\}', '', text).strip()


def build():
    rom = rom_bytes()
    w = lambda a: rom[off(a)] | rom[off(a) + 1] << 8
    b3 = script('B3')
    moves = {}
    for i in range(223):
        ptr, mid = w(0x82E794 + 4 * i), w(0x82E796 + 4 * i)
        name = plain(b3.get(0xB30000 | ptr, ''))
        if name and mid // 2 not in moves:
            moves[mid // 2] = {'name': name, 'cost': None, 'who': []}
    a = 0x83C102
    while w(a) != 0xFFFF:
        cost, mid = w(a), w(a + 2)
        if mid // 2 in moves and moves[mid // 2]['cost'] is None:
            moves[mid // 2]['cost'] = cost
        a += 4

    # wrestler names: the wrestler-select lists, one block per promotion, in id order
    b8f = script('8F')
    keys = sorted(b8f)
    names = {}
    for wid in range(1, 52):
        ptr = 0x8F0000 | w(0x82E1D8 + 2 * wid)
        block = keys[bisect.bisect_right(keys, ptr) - 1]
        names.setdefault(block, [])
    wid = 1
    for block in sorted(names):
        for part in re.split(r'\{(?:at|pos)[^}]*\}', b8f[block].split('{end}')[0]):
            if part.strip() and wid <= 51:
                names[block].append((wid, plain(part)))
                wid += 1
    wnames = {i: n for lst in names.values() for i, n in lst}

    wrestlers = {}
    for wid in range(1, 52):
        rec = rom[off(0x870000 | w(0x81F43F + 2 * (wid - 1))):][:64]
        sets = []
        for pos, byte in enumerate(rec):
            if byte in moves and moves[byte]['name'] != 'No Move' and (not SLOTS or SLOTS.get(pos)):
                sets.append([pos, byte])
                if wid not in moves[byte]['who']:
                    moves[byte]['who'].append(wid)
        sets.sort(key=lambda s: _ORDER.index(s[0]))
        wrestlers[wid] = {'name': wnames.get(wid, f'#{wid}'), 'moves': sets}
    return {'slots': {str(k): v for k, v in SLOTS.items()},
            'moves': {str(k): v for k, v in sorted(moves.items())},
            'wrestlers': {str(k): v for k, v in wrestlers.items()}}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--check', action='store_true', help='only check that the page is up to date')
    args = ap.parse_args()
    data = json.dumps(build(), ensure_ascii=False, separators=(',', ':'))
    page = PAGE.read_text(encoding='utf-8')
    i = page.index(START) + len(START)
    j = page.index(END, i)
    if page[i:j] == data:
        print('guide data up to date')
        return
    if args.check:
        sys.exit('guide data out of date: run python3 tools/guidedata.py')
    PAGE.write_text(page[:i] + data + page[j:], encoding='utf-8')
    print(f'guide data written ({len(data)} bytes)')


if __name__ == '__main__':
    main()
