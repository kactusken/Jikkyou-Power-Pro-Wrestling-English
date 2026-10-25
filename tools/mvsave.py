#!/usr/bin/env python3
"""Read and craft Max Voltage save files (the cartridge's 32 KB battery RAM, Mesen's .srm).

  mvsave.py info SRM [SLOT]                   the slots, or one slot's fields and flags
  mvsave.py set SRM SLOT KEY=VALUE... [-o OUT] change a slot (OUT defaults to SRM)
  mvsave.py copy SRM FROM TO [-o OUT]          copy a slot to another slot
  mvsave.py fromwram SRM SLOT WRAM.bin [-o OUT] fill a slot from a 128 KB WRAM dump (Mesen
                                              `dump wram 0 131072 NAME` of any career state)
  mvsave.py preset SRM SLOT NAME [-o OUT]      turn a used slot into a story checkpoint
  mvsave.py presets                            list the checkpoints

Slots are 1-3. KEY is a field below (year=1997 month=9 promo=REALS career=2 name=Family/Given ...), flag+N /
flag-N to set or clear story flag N, or a WRAM address of the career state ($7E5132=0x05,
$1370=0x44; word values with :w, e.g. $7E50E0:w=200).

The save format (from the code, $80:863C-$80:8959): the header ($700000-$70000F) and a copy at
$701FF1 hold the bytes 01..0E; each slot is $440 bytes at $700020 / $700460 / $7008A0 and is a
plain copy of the career state in WRAM - no checksum, only the word $0234 at +2 marks it used:
  +$04 $1F9A (word), +$06 $1F9C, +$07 $1F9E    options
  +$08 $1FE7    promotion (0-1 before the debut?, 2 SJPW, 3 WWK, 4 BOM, 5 REAL'S)
  +$0A $1FA2-$1FD1, +$3A $1FD2-$1FE1 (the name, 8 words)
  +$4A $1FE2 year (0 = 1996), +$4B $1FE3 month, +$4C $1FE4 career year (shown +1)
  +$4D $1FE8-$1FEA, +$50 $1FE6
  +$60 $1370-$139F    story flags (flag n = bit n&7 of byte n>>3)
  +$90 $7E:5090-$7E:543F    the wrestler, the roster and the rest of the career state
Loading copies it all back ($80:888C), so a crafted slot starts at the hub of its month.
"""
import argparse
import sys
from pathlib import Path

SLOTS = (0x20, 0x460, 0x8A0)
SLOT_SIZE = 0x440
MAGIC = 0x0234
# WRAM range -> slot offset (start, end exclusive, offset)
RANGES = [(0x1F9A, 0x1F9C, 0x04), (0x1F9C, 0x1F9D, 0x06), (0x1F9E, 0x1F9F, 0x07), (0x1FE7, 0x1FE8, 0x08),
          (0x1FA2, 0x1FD2, 0x0A), (0x1FD2, 0x1FE2, 0x3A), (0x1FE2, 0x1FE5, 0x4A), (0x1FE8, 0x1FEB, 0x4D),
          (0x1FE6, 0x1FE7, 0x50), (0x1370, 0x13A0, 0x60), (0x7E5090, 0x7E5440, 0x90)]
PROMOS = {'SJPW': 2, 'WWK': 3, 'BOM': 4, 'REALS': 5, "REAL'S": 5}
PROMO_NAMES = {2: 'SJPW', 3: 'WWK', 4: 'BOM', 5: "REAL'S"}


def slot_offset(wram):
    """The slot offset that holds WRAM address `wram` ($1370, $7E5090 ...)."""
    if 0x2000 <= wram < 0x10000:
        wram |= 0x7E0000
    elif 0x7E0000 <= wram < 0x7E2000:
        wram &= 0xFFFF                 # low WRAM: $7E:1370 = $1370
    for lo, hi, off in RANGES:
        if lo <= wram < hi:
            return off + wram - lo
    raise SystemExit(f'${wram:X} is not part of the saved career state')


class Save:
    def __init__(self, path):
        self.path = Path(path)
        self.data = bytearray(self.path.read_bytes())
        if len(self.data) < 0x2000:
            raise SystemExit(f'{path}: {len(self.data)} bytes - not a save file of this game')

    def base(self, slot):
        if not 1 <= slot <= 3:
            raise SystemExit('slots are 1-3')
        return SLOTS[slot - 1]

    def used(self, slot):
        b = self.base(slot)
        return int.from_bytes(self.data[b + 2:b + 4], 'little') == MAGIC

    def get(self, slot, off, n=1):
        b = self.base(slot)
        return int.from_bytes(self.data[b + off:b + off + n], 'little')

    def put(self, slot, off, value, n=1):
        b = self.base(slot)
        self.data[b + off:b + off + n] = (value & (256 ** n - 1)).to_bytes(n, 'little')

    def flag(self, slot, n):
        return bool(self.get(slot, 0x60 + (n >> 3)) & 1 << (n & 7))

    def set_flag(self, slot, n, on):
        v = self.get(slot, 0x60 + (n >> 3))
        v = v | 1 << (n & 7) if on else v & ~(1 << (n & 7))
        self.put(slot, 0x60 + (n >> 3), v)

    def summary(self, slot):
        if not self.used(slot):
            return f'slot {slot}: empty'
        y, m, c = self.get(slot, 0x4A), self.get(slot, 0x4B), self.get(slot, 0x4C)
        p = self.get(slot, 0x08)
        return (f'slot {slot}: {1996 + y}/{m:02d}, career year {c + 1}, '
                f'promotion {p} ({PROMO_NAMES.get(p, "?")})')

    def write(self, out=None):
        Path(out or self.path).write_bytes(bytes(self.data))


FIELDS = {'year': (0x4A, 1), 'month': (0x4B, 1), 'career': (0x4C, 1), 'promo': (0x08, 1)}

# Story checkpoints (docs/MAX_VOLTAGE.md): a date and the state that month's branch needs.
# story_items() adds what the earlier months would have set, so any used slot will do.
BELTS = ('$7E51C8:w', '$7E51CA:w', '$7E51CC:w', '$7E51CE:w')   # SWGP, WWK, BOM, REAL'S champion
YOU = 0x3B
PRESETS = {
    'trainee':   ('1996/03', 'SJPW', 'the trainee months: coaches, Wyvern back, raiders', ['flag+0x22', 'flag+0x06', 'flag-0x21']),
    'protest':   ('1996/06', 'SJPW', 'the pro test (fail = game over)', []),
    'debut':     ('1996/07', 'SJPW', 'debut vs Jonouchi, nickname', []),
    'ytcup':     ('1996/11', 'SJPW', 'Young Tiger Cup (win = the America tour)', []),
    'tour':      ('1996/12', 'WWK', 'America tour: arrival, pick Madeleine or Silver',
                  ['flag+0x09', 'flag+0x03', 'flag+0x20', 'flag+0x0C']),
    'thunder':   ('1996/12', 'SJPW', 'YT Cup lost: Thunder tours instead', ['flag+0x0A']),
    'tourend':   ('1997/05', 'WWK', 'the tour ends (manager reward, back to SJPW)',
                  ['flag+0x09', 'flag+0x03', 'flag+0x20', 'flag+0x0C', '$7E51D2=1']),
    'tourney':   ('1997/08', 'SJPW', 'Fight Tourney announced, you are the entrant', ['$7E50E0:w=40']),
    'reals':     ('1998/01', 'SJPW', "REAL'S founded (transfer offer opens)", []),
    'realsjump': ('1998/04', 'SJPW', "jump to REAL'S with Narumi and Bando (planned transfer)", ['$7E51C4=5']),
    'realslife': ('1998/02', "REAL'S", "a REAL'S career (REAL'S scenes each month)", []),
    'bom':       ('1999/02', 'SJPW', 'BOM founded (transfer offer opens)', []),
    'bomlife':   ('1999/03', 'BOM', 'a BOM career (BOM scenes each month)', []),
    'revolt':    ('1999/04', 'SJPW', 'SJPW revolt: April argument, May choice (not champion)', []),
    'iwai':      ('1999/10', 'BOM', "Iwai's farewell, you are his last opponent", ['$7E50E4:w=130']),
    'mercury':   ('1999/12', 'SJPW', 'WWK announces Max Mercury', []),
    'titleshot': ('1997/09', 'SJPW', 'a title challenge at the next show (rating 140)', ['$7E50DE:w=150']),
    'escape':    ('1998/06', 'SJPW', 'night escape planned (game over next month)', ['flag+0x07']),
    'end0':      ('2001/03', 'SJPW', 'March 2001 ending with no belt', [b + '=4' for b in BELTS[:1]]),
    'end2':      ('2001/03', 'SJPW', 'March 2001 ending with two belts (SWGP, WWK)',
                  [BELTS[0] + f'={YOU}', BELTS[1] + f'={YOU}']),
    'end4':      ('2001/03', 'SJPW', 'March 2001 ending with all four belts (Quadruple Crown)',
                  [b + f'={YOU}' for b in BELTS]),
}


def story_items(year, month):
    """The flags (and the career year) the story would have set by the start of year/month."""
    ym = year * 100 + month
    items = [f'career={year - 1996 + (1 if month >= 3 else 0)}', 'flag+0x00', 'flag+0x02',
             'flag-0x07', 'flag-0x08', 'flag-0x0B',
             'flag-0x09', 'flag-0x0A', 'flag-0x0C', 'flag-0x20', 'flag-0x03']   # tours: per preset
    if ym > 199606:
        items += ['flag-0x22', 'flag-0x06']                  # passed the pro test
    else:
        items += ['flag+0x22', 'flag-0x21']                  # still a trainee
    if ym > 199607:
        items += ['flag+0x21']                               # debuted
    if ym > 199801:
        items += ['flag+0x05']                               # REAL'S exists
    if ym > 199902:
        items += ['flag+0x04']                               # BOM exists
    if ym > 199912:
        items += ['flag+0x03', 'flag+0x30', '$7E51DD=3']     # WWK open again, Mercury active
    return items


def apply(save, slot, item):
    key, _, val = item.partition('=')
    if key == 'name':                       # $1FD2: family then given name, 4 words each,
        sys.path.insert(0, str(Path(__file__).resolve().parent))   # two letters per word
        import script
        L = script.Letters()
        words = []
        for part in val.split('/'):
            if len(part) > 8:
                raise SystemExit(f'{part!r}: 8 letters at most per name')
            w = [L.pair(part[i:i + 2]) for i in range(0, len(part), 2)]
            words += w + [0] * (4 - len(w))
        for i, w in enumerate(words[:8]):
            save.put(slot, 0x3A + 2 * i, w, 2)
        return
    if key.startswith(('flag+', 'flag-')):
        save.set_flag(slot, int(key[5:], 0), key[4] == '+')
        return
    if not val:
        raise SystemExit(f'{item}: expected KEY=VALUE')
    if key == 'promo' and val.upper() in PROMOS:
        v = PROMOS[val.upper()]
    else:
        v = int(val, 0)
    if key == 'year' and v >= 1996:
        v -= 1996
    if key == 'career':
        v -= 1
    if key in FIELDS:
        off, n = FIELDS[key]
    elif key.startswith('$'):
        addr, _, size = key[1:].partition(':')
        off, n = slot_offset(int(addr, 16)), 2 if size == 'w' else 1
    else:
        raise SystemExit(f'{key}: unknown field (year, month, career, promo, flag+N, flag-N, $WRAM)')
    save.put(slot, off, v, n)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('info')
    p.add_argument('srm')
    p.add_argument('slot', type=int, nargs='?')
    p = sub.add_parser('set')
    p.add_argument('srm')
    p.add_argument('slot', type=int)
    p.add_argument('items', nargs='+')
    p.add_argument('-o', '--out')
    p = sub.add_parser('copy')
    p.add_argument('srm')
    p.add_argument('src', type=int)
    p.add_argument('dst', type=int)
    p.add_argument('-o', '--out')
    p = sub.add_parser('preset')
    p.add_argument('srm')
    p.add_argument('slot', type=int)
    p.add_argument('name', choices=sorted(PRESETS))
    p.add_argument('-o', '--out')
    sub.add_parser('presets')
    p = sub.add_parser('fromwram')
    p.add_argument('srm')
    p.add_argument('slot', type=int)
    p.add_argument('wram')
    p.add_argument('-o', '--out')
    a = ap.parse_args(argv)
    if a.cmd == 'presets':
        for name, (date, promo, what, _) in PRESETS.items():
            print(f'{name:<10} {date} {promo:<7} {what}')
        return
    s = Save(a.srm)
    if a.cmd == 'info':
        for slot in ([a.slot] if a.slot else (1, 2, 3)):
            print(s.summary(slot))
            if a.slot and s.used(slot):
                flags = [n for n in range(0x30 * 8) if s.flag(slot, n)]
                print('  flags set:', ' '.join(f'{n}(${n:02X})' for n in flags) or 'none')
    elif a.cmd == 'set':
        if not s.used(a.slot):
            raise SystemExit(f'slot {a.slot} is empty: copy a used slot to it first')
        for item in a.items:
            apply(s, a.slot, item)
        s.write(a.out)
        print(s.summary(a.slot))
    elif a.cmd == 'preset':
        if not s.used(a.slot):
            raise SystemExit(f'slot {a.slot} is empty: copy a used slot to it first')
        date, promo, what, extra = PRESETS[a.name]
        y, m = map(int, date.split('/'))
        for item in [f'year={y}', f'month={m}', f'promo={promo}', '$7E51C4=0', '$7E51D3=0'] + story_items(y, m) + extra:
            apply(s, a.slot, item)
        s.write(a.out)
        print(s.summary(a.slot), '-', what)
    elif a.cmd == 'fromwram':
        w = Path(a.wram).read_bytes()
        if len(w) != 0x20000:
            raise SystemExit(f'{a.wram}: {len(w)} bytes, expected a 128 KB WRAM dump')
        b = s.base(a.slot)
        s.data[b:b + SLOT_SIZE] = bytes(SLOT_SIZE)
        s.put(a.slot, 2, MAGIC, 2)
        for lo, hi, off in RANGES:
            lo16 = lo & 0x1FFFF if lo >= 0x10000 else lo
            s.data[b + off:b + off + hi - lo] = w[lo16:lo16 + hi - lo]
        s.write(a.out)
        print(s.summary(a.slot))
    elif a.cmd == 'copy':
        b, d = s.base(a.src), s.base(a.dst)
        s.data[d:d + SLOT_SIZE] = s.data[b:b + SLOT_SIZE]
        s.write(a.out)
        print(s.summary(a.dst))


if __name__ == '__main__':
    sys.exit(main())
