#!/usr/bin/env python3
"""Konami LZ used by this game (decompressor $80:EEB1, 1 KB ring buffer at $7E:A000).

  kpack.py unpack ROM ADDR OUT     unpack the block at CPU address ADDR to OUT
  kpack.py test ROM ADDR           unpack, repack, unpack again: sizes and a round-trip check

Stream: u16 header (bit 15 a flag, low 15 bits the packed length counted from the header),
then commands:
  00-7F  copy (b>>2)+2 bytes from ring position ((b<<8|n) - 0x3DF) & 0x3FF   (2 bytes)
  80-9F  b&0x1F literal bytes follow
  A0-BF  (b&0x1F)+2 bytes follow, each written as 00, byte
  C0-DF  (b&0x1F)+2 copies of the next byte
  E0-FE  (b&0x1F)+2 zero bytes
  FF n   n+2 zero bytes
The stream ends at the length in the header (bit 15 of the header: output goes to VRAM).
*from the code*, checked against the font the game unpacks into $7F:2000.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import snes  # noqa: E402

RING = 0x400


def unpack(data, pos):
    """(bytes, packed length incl. header) of the stream at file offset pos."""
    start = pos
    hdr = data[pos] | data[pos + 1] << 8
    end = pos + (hdr & 0x7fff)
    pos += 2
    ring = bytearray(RING)
    out = bytearray()

    def put(b):
        ring[len(out) % RING] = b
        out.append(b)
    while pos < end:
        b = data[pos]
        if b < 0x80:
            src = (((b << 8) | data[pos + 1]) - 0x3df) & 0x3ff
            for i in range((b >> 2) + 2):
                put(ring[(src + i) % RING])
            pos += 2
        elif b < 0xa0:
            n = b & 0x1f
            for x in data[pos + 1:pos + 1 + n]:
                put(x)
            pos += 1 + n
        elif b < 0xc0:
            n = (b & 0x1f) + 2
            for x in data[pos + 1:pos + 1 + n]:
                put(0)
                put(x)
            pos += 1 + n
        elif b < 0xe0:
            for _ in range((b & 0x1f) + 2):
                put(data[pos + 1])
            pos += 2
        elif b < 0xff:
            for _ in range((b & 0x1f) + 2):
                put(0)
            pos += 1
        else:
            for _ in range(data[pos + 1] + 2):
                put(0)
            pos += 2
    return bytes(out), pos - start


def pack(data, flag=0):
    """Pack bytes into this format (greedy: longest ring copy, else runs, else literals); flag:
    bit 15 of the header, kept from the original block."""
    out = bytearray(b'\0\0')
    lit = bytearray()
    n = len(data)

    def flush():
        while lit:
            chunk = lit[:31]
            out.append(0x80 | len(chunk))
            out.extend(chunk)
            del lit[:31]
    i = 0
    # positions of each 2-byte prefix within the window, for quick match search
    heads = {}
    while i < n:
        # run of one byte value
        run = 1
        cap = 257 if data[i] == 0 else 33
        while i + run < n and data[i + run] == data[i] and run < cap:
            run += 1
        best_len, best_src = 0, 0
        if i + 1 < n:
            for j in reversed(heads.get(data[i:i + 2], [])):
                if i - j > RING - 1:
                    break
                k = 0
                while i + k < n and k < 33 and data[j + k] == data[i + k]:
                    k += 1
                if k > best_len:
                    best_len, best_src = k, j
                    if k == 33:
                        break
        if run >= 3 and run >= best_len:
            flush()
            if data[i] == 0 and run > 32:
                out += bytes([0xff, run - 2])
            elif data[i] == 0:
                out.append(0xe0 | (run - 2))
            else:
                run = min(run, 33)
                out += bytes([0xc0 | (run - 2), data[i]])
            step = run
        elif best_len >= 3:
            flush()
            w = (best_src % RING + 0x3df) & 0x3ff
            out += bytes([((best_len - 2) << 2) | (w >> 8), w & 0xff])
            step = best_len
        else:
            lit.append(data[i])
            step = 1
        for t in range(i, i + step):
            heads.setdefault(data[t:t + 2], []).append(t)
        i += step
    flush()
    if len(out) > 0x7fff:
        raise ValueError(f'packed block too big: {len(out)} bytes')
    out[0:2] = (len(out) | flag).to_bytes(2, 'little')
    return bytes(out)


def main(argv=None):
    a = sys.argv[1:] if argv is None else argv
    if len(a) == 4 and a[0] == 'unpack':
        rom = snes.Rom(Path(a[1]).read_bytes())
        out, n = unpack(rom.data, rom.to_file(int(a[2].replace('$', '').replace(':', ''), 16)))
        Path(a[3]).write_bytes(out)
        print(f'{len(out)} bytes from {n} packed')
        return 0
    if len(a) == 3 and a[0] == 'test':
        rom = snes.Rom(Path(a[1]).read_bytes())
        out, n = unpack(rom.data, rom.to_file(int(a[2].replace('$', '').replace(':', ''), 16)))
        p = pack(out, rom.data[rom.to_file(int(a[2].replace('$', '').replace(':', ''), 16)) + 1] << 8 & 0x8000)
        back, m = unpack(p, 0)
        print(f'{len(out)} bytes: original {n} packed, ours {len(p)}; round trip {"ok" if back == out else "FAILED"}')
        return 0 if back == out else 1
    print(__doc__)
    return 1


if __name__ == '__main__':
    sys.exit(main())
