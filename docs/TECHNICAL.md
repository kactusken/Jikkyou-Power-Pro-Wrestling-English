# Technical notes - Jikkyou Power Pro Wrestling '96 - Max Voltage

**Conventions:** numbers in hex with `0x`; addresses are RAM addresses unless marked as file
offsets; `u16`/`u32` little-endian unless marked BE. Findings are marked *verified in game* or
*from the code*.

## Contents
- [Image](#image) · [ROM layout](#rom-layout) · [Text](#text) · [Open questions](#open-questions)

## Image
`Jikkyou Power Pro Wrestling '96 - Max Voltage (J).smc`, 4194304 bytes, SHA-1 `e24b1dcf8e60ebfdb5b0c1d4fe20756ad53f4d61`.

## ROM layout
| | |
|---|---|
| Title | `JIKKYOU-PROWRESTLING` |
| Map | LoROM FastROM (`$30`), header at `0x7fc0` |
| Size | 0x400000 bytes (32 Mbit), 128 banks of 32 KB |
| ROM | $80:8000 - $FF:FFFF |
| Cart | type `$02`, SRAM 8 KB |
| Reset | $00:FF90 |
| Checksum | `0xfe08` (fixed by tools/disc.py on every build) |

Runs of `$00`/`$FF` of 1 KB or more (free space candidates - verify nothing reads them):

| Offset | CPU | Bytes | Fill |
|---|---|---|---|
| `0x016e9c` | $82:EE9C | 0x1164 | `$ff` |
| `0x01fa7e` | $83:FA7E | 0x582 | `$ff` |
| `0x03fa7b` | $87:FA7B | 0x585 | `$ff` |
| `0x057603` | $8A:F603 | 0x9fd | `$ff` |
| `0x0777ad` | $8E:F7AD | 0x853 | `$ff` |
| `0x196e3e` | $B2:EE3E | 0x11c2 | `$ff` |
| `0x19adfc` | $B3:ADFC | 0x5204 | `$ff` |
| `0x1a3146` | $B4:B146 | 0x4eba | `$ff` |
| `0x1e7bb9` | $BC:FBB9 | 0x447 | `$ff` |
| `0x1ff5c1` | $BF:F5C1 | 0xa3f | `$ff` |
| `0x3d794b` | $FA:F94B | 0x6b5 | `$ff` |


## Text
*Verified in game* with Mesen traces unless marked *from the code*.

### Script format
- Banks `$8F` and `$90` hold the script as 16-bit words; move names are at `$B3:A100-ADFE`,
  post-match interview answers at `$B4:8000-B148` and `$B5:83A8-FE0A` (same format). Readers: `$8D:B801` (the renderers; X =
  address, `$8F:X` from `$8000` up, else `$90:8000+X`; `$7FA0+` = WRAM) and `$8D:B7E9` (the
  dialogue engine, same with a bank override in `$1E84`). A few tables are read directly
  (`tools/script.py` PROTECTED: digit strip `$8F:BDEA`, default name `$8F:8082`, blank-space
  constants `$8F:82C2/82C4`, label pool `$8F:C76A`, `$8F:B508`).
- Words: glyph codes = addresses of 12x12 (odd, 12 px advance, 24 bytes at code-1) or 6x12 (even,
  6 px, 12 bytes) glyphs in the font at `$7F:2000` (packed at `$FA:9280`, unpacked when the menus
  load). Controls below `$2B`: `0000` end, `0001` end of a part (the next part follows), `0002`
  ignored by the renderers / new page for the dialogue engine, `0003 xy` new position, `0008/09`
  names, `000E a b` choice with jump address b, `000F-001A` numbers, `001B-001E` names,
  `001F-0023` speaker portrait, `0028-002A` misc. Many strings start with a position word (x, y).
- The renderer (`$8D:ADE7`) plots into a 1bpp bitmap in WRAM `$7F` and advances 12 or 6 px
  (`$8D:AEEA`). The plotters (`$8D:B340`-`$B4AA`) keep only 6 columns of a half-width glyph.
- The dialogue engine (`$8D:BAE4`...) types one word per few frames, positions each from a
  half-column counter (`$1E88`, x table `$81:F123`, wraps at `$1E7A` = 30 columns = 180 px), reads
  every word twice (once to type it, once through the renderer), and redraws the box from
  `$8F:82C2` between pages, then goes on where it stopped.
- Every glyph is plotted as a cell that *replaces* its pixels: 6 px for half-width, 12 for full.
  A cell that starts too far right writes past the text's area: the setup name slots end at the
  bitmap's last column, and anything plotted past it lands in the font at `$7F:2000+` (it wiped
  the digits `$7F:206C-207D` used by the result times). Text bitmaps sit right below the font.
- Match times on result screens are built by `$91:B054` from the digit strip `$8F:BDEA`, the
  unit words `$8F:C76A/C76C` and the blank `$8F:82C2` (`$2000`).

### English
- Written in place: every translated part keeps its word count and terminator position; dialogue
  pages (a `0002` part and its `0001` lines) share one budget; menu parts keep each `{pos}` line
  at its original offset (tables point at line starts - the roster names at `$82:E1D8`).
- English words are letter chunks drawn by `tools/hooks.py`: `$A000 + a*128 + b` = two letters,
  `$D000 + d` = dictionary chunk (up to 40 px; only chunks some string uses are kept). A pair's
  first letter must be below 96 (higher would reach `$D000`): letters 96+ (♥ ♪, the 1-2 px
  spacers) are one-letter dictionary chunks (`script.PAIR_FIRST`). Hooks:
  `$8D:B127/B107` draw chunks with the game's own plotter (English letters at `$7F:9908 + 12*i`,
  in the part of the font no string used; move names use the font from `$9300`), `$8D:AEF4` advance (an empty chunk leaves `$0E/$0C` alone: menu renderers upload columns up to the last glyph's), `$8D:B0C1` uploads every tile
  column a chunk touched (none when `$0C` = 0: a wrapped count once queued 65536 DMA entries, overran the queue at `$7E:AF00` and crashed the game), `$8D:BFA5/BC4D` give the dialogue box a pixel x, `$8D:DC63/DC9D` name
  entry. State in WRAM `$7E:7F20-$7E:7F4F` (`$7E:7000-$7FFF` never written - checked in menus,
  matches, tournament and the career mode).
- Padding: a line whose Japanese ended in blanks is padded with blank chunks (one dictionary word
  clears up to 40 px) to its old width, the last blank starting 6 px before the end
  (`script.pad_letters`), so no cell reaches past what the Japanese covered.
  Blank chunks are the first dictionary entries (`script.Chunker`, `last_blank()`), so one range
  test finds them: names inserted into text (`{c1b}`, copied by `$8D:B595` with the length from
  `$8D:B85F`) drop trailing blank words, and the hook `nameblank` (from `$8D:B872`) counts the
  padding chunks and lone spaces as blank too - otherwise the roster names' padding (kept for the
  name slots, which must erase a longer name) showed as a gap: "Masked Robo    wins!".
- `tools/english.py` clears the kanji only the (disabled) kana-to-kanji converter showed (lists
  `$85:F60A-$868000`) so the font still packs into its old room - but not a 24-byte glyph that
  shares bytes with a used one (a 12 px glyph overlaps two 6 px ones: the digits `$200C+` sit under
  `$2001/$2019/...`).
- Name entry (`tools/nameentry.py`): code tables `$85:F358/F448/F538` (15 columns; rows 0-5
  letters, rows 6-7 the buttons: 4 next, 5 back, 0 done / 1-3 the pages), grids
  `$90:FAAE/FB8C/FC6A`; letters are packed two per name word (slots 0-3 family, 4-7 given; box
  position table `$8E:F79D`). A first letter waits in its slot for the second (`namepack`), and the
  box (`namebox`, `$8D:DAD7`) moves onto that half slot.
- Entry form pictures: block `$8C:FCBE` (VRAM tile `$80`) under four packed BG1 tilemaps
  (`$FF:FEFB`, `$FB:9205`, `$FB:914B`, `$FA:90D1`) - `artlabels.apply_form`.

### Graphics with text
- Packed blocks (`tools/kpack.py`): u16 header (length, bit 15 = bitplane pairs stored as 8 rows
  each, interleaved by `$80:EB24` on the way to VRAM), commands 00-7F copy, 80-9F literals,
  A0-BF 00/byte pairs, C0-DF run, E0-FE zeros, FF n = n+2 zeros. Load lists (dest 3 bytes,
  source 3 bytes) in `$82:8000-$9FFF`.
- `tools/artlabels.py`: rule buttons (`$FC:9BEA`), rule tag (`$FC:9302`), career hub menu (tiles
  `$FF:8000`, hub BG1 tilemap `$F7:D2EB`, label tables `$83:C416` via `$83:C3F2`).


## Open questions
- The reading of 凰 in the default career name (Otori Rekka) is not confirmed.
- On the match announcement, a 16-letter career name reaches the right-hand portrait (accepted;
  shorter names fit).
