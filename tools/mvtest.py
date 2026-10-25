#!/usr/bin/env python3
"""Max Voltage test image: a copy of a built ROM whose career-mode bouts play themselves.

  mvtest.py ROM OUT [--lose]

Never for release - it changes how the game plays. Patches (from the code):
  $88:95A0  the show card's "your bout?" test (BEQ to the real match) becomes NOP NOP, so your
            bout is resolved by the simulator like every other bout on the card ($91:A7A0);
  $91:A7A0  the simulator (A = red corner, Y = blue corner) jumps to a hook at HOOK that makes
            your wrestler (id $3B) win (or, with --lose, lose); other bouts are decided by rank
            as before (lower rank wins, ties go to the blue corner).
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import asm65816  # noqa: E402

PLAYER = 0x3B
HOOK = 0xBFF800            # free ($FF) in the original and the English build
CARD_TEST = 0x8895A0       # F0 0B  BEQ $95AD (your bout -> the real match)
SIM = 0x91A7A0             # 48 5A 5A 22  PHA PHY PHY JSL $91A27D
RED_WINS, BLUE_WINS, AFTER = 0x91A7B7, 0x91A7D8, 0x91A7A7


def off(a):
    return ((a >> 16) & 0x7F) * 0x8000 + (a & 0x7FFF)


def hook_source(lose):
    me, other = ('blue', 'red') if lose else ('red', 'blue')
    return f"""
    CMP #${PLAYER:04X}          ; red corner is you
    BEQ {me}
    CPY #${PLAYER:04X}          ; blue corner is you
    BEQ {other}
    PHA                     ; not your bout: the original code
    PHY
    PHY
    JSL $91A27D
    JML ${AFTER:06X}
red:                        ; red wins (A = red, Y = blue, X = bout)
    CLC
    JML ${RED_WINS:06X}
blue:
    JML ${BLUE_WINS:06X}
"""


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('rom')
    ap.add_argument('out')
    ap.add_argument('--lose', action='store_true', help='your bouts are lost instead')
    a = ap.parse_args(argv)
    data = bytearray(Path(a.rom).read_bytes())
    expect = {CARD_TEST: b'\xF0\x0B', SIM: b'\x48\x5A\x5A\x22'}
    for addr, b in expect.items():
        if data[off(addr):off(addr) + len(b)] != b:
            raise SystemExit(f'{a.rom}: unexpected bytes at ${addr:06X} - not this game or already patched')
    code, _ = asm65816.assemble(hook_source(a.lose), HOOK)
    if any(x != 0xFF for x in data[off(HOOK):off(HOOK) + len(code)]):
        raise SystemExit(f'${HOOK:06X} is not free in {a.rom}')
    data[off(HOOK):off(HOOK) + len(code)] = code
    data[off(CARD_TEST):off(CARD_TEST) + 2] = b'\xEA\xEA'
    data[off(SIM):off(SIM) + 4] = bytes([0x5C, HOOK & 0xFF, HOOK >> 8 & 0xFF, HOOK >> 16])
    Path(a.out).write_bytes(bytes(data))
    print(f'{a.out}: test image, your bouts are {"lost" if a.lose else "won"} automatically')


if __name__ == '__main__':
    sys.exit(main())
