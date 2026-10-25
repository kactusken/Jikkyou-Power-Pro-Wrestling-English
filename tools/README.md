# Tools

Everything is Python 3 and runs from the project folder or anywhere else; every tool has `--help`
(or prints its usage). Folder locations come from [paths.py](paths.py) and can be moved with the
folder options. `build.py`, `make_patches.py` and everything they import use only the standard
library; the tools marked *Pillow* or *capstone* need `.venv` (`pip install -r requirements.txt`).

Set up from the translation kit (version 06a12b0-dirty). Tools marked *game* are stubs to fill in.

## Used by the build

| Tool | What it does |
|---|---|
| [../build.py](../build.py) | builds the translated image (text steps, code patches, images, write-back) |
| [paths.py](paths.py) | every folder location and the folder options |
| [image.py](image.py) | the output image: fresh copy or fast restore from a journal; checksums |
| [disc.py](disc.py) | reads and writes files in the image (SNES; a cartridge ROM is one file - docs/PLATFORM.md) |
| [codepatch.py](codepatch.py) | applies code patch tables, checking the original bytes first |
| [catalog.py](catalog.py) | the image catalogue: which file the build uses, fingerprints, stale renders |
| [gfx.py](gfx.py) | *game*: exports the original images, imports the English ones |
| [pngio.py](pngio.py) | PNG reading and indexed PNG writing without dependencies |
| [blocks.py](blocks.py), [textdb.py](textdb.py) | message block files; every translatable string as one list |
| [snes.py](snes.py) | header, LoROM/HiROM/ExHiROM map (CPU address ↔ file offset), checksum, expansion, free space |
| [bps.py](bps.py) | BPS patches: make and apply (release patches) |
| [snesgfx.py](snesgfx.py) | planar 1/2/4/8bpp and Mode 7 tiles, BGR555 palettes, PNG sheets |
| [tbl.py](tbl.py) | `.tbl` character tables: decode, dump, encode |

## Checking

| Tool | What it does |
|---|---|
| [check.py](check.py) | runs every check (`--quick` for the pre-commit hook, `--control` for a lossless-build proof) |
| [lint.py](lint.py) | text: leftover source text, control codes, line/char/byte limits, glossary |
| [status.py](status.py) | how far along the text and images are |
| [records.py](records.py) | fixed-record text tables (names, items, menus of records): `dump` the CSV, `verify` the layout, `measure` unknown data, build step - configure `TABLES` |
| [stepcheck.py](stepcheck.py) | run one build text step against `extracted/` (no image, nothing written) and list what it changed - for testing a step while the image is busy |

## Translating

| Tool | What it does |
|---|---|
| [fill_text.py](fill_text.py) | fills repeated strings from a source → English table |
| [render.py](render.py) | *Pillow*: automatic English renders, only redrawing what changed |
| [edit.py](edit.py) | *Pillow*: hand-edit workflow - start, check, approve, reset, sheets |
| [compare.py](compare.py) | *Pillow*: original \| English sheets |
| [contact.py](contact.py) | *Pillow*: every original image on labelled sheets |

## Releasing

| Tool | What it does |
|---|---|
| [../make_patches.py](../make_patches.py) | builds every variant, makes and re-verifies the patches, README.txt and the zip |

## Research

| Tool | What it does |
|---|---|
| [extract.py](extract.py) | unpacks the disc into `extracted/` and exports the images (*game*: `unpack()`) |
| [sjisscan.py](sjisscan.py) | finds Shift-JIS text in binary files |
| [relsearch.py](relsearch.py) | relative search for text in an unknown encoding (kana orders, ASCII, 8/16-bit) |
| [dis65816.py](dis65816.py) | 65816 disassembler (M/X flags followed through REP/SEP) and reference/pointer search |
| [guidedata.py](guidedata.py) | the move data in the player's guide (docs/guide/index.html), read from the ROM: every move's name, price and owners, every wrestler's move set by situation; `--check` |

## Testing in Mesen

| Tool | What it does |
|---|---|
| [mesen.py](mesen.py) | runs Mesen headless from a step file: input, waits, screenshots, savestates, memory dumps and writes, traces, code logs, and `autoplay` with a Lua rules file |
| [mvsave.py](mvsave.py) | Max Voltage save files: `info`, `set` (date, promotion, flags, any WRAM address), `fromwram`, `copy`, and `preset` story checkpoints ([docs/MAX_VOLTAGE.md](../docs/MAX_VOLTAGE.md#testing)) |
| [mvtest.py](mvtest.py) | a test image (never for release) whose career card bouts play themselves, always won (`--lose`: lost) |
| [mvauto.lua](mvauto.lua) | autoplay rules for the career mode: dialogue, PROCEED, the training split, choices, cards; logs to `auto.log` |
| [mvload.lua](mvload.lua) | autoplay rules that load a save slot from the title screen and stop at the hub |
