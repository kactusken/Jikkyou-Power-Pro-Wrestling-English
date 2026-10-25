# Jikkyou Power Pro Wrestling '96 - Max Voltage — English Translation

An English translation patch for **Jikkyou Power Pro Wrestling '96 - Max Voltage** (Konami,
1996, Super Famicom), a wrestling game released only in Japan.

Everything you read in the game is in English:
- all menus, rules and help lines;
- the 50-wrestler roster and its 185 move names;
- the post-match interviews;
- the whole Max Voltage career mode, with its story, events, magazine and endings.

The screen titles and menu graphics are redrawn in English, and the name entry has an English
letter grid. The game draws its text from a font of square Japanese characters. The patch adds
a small text engine that draws English as letter pairs inside the game's own renderer, so the
English fits in the room the Japanese used.

**[See screenshots](docs/SCREENSHOTS.md)** of the patched game.

> **Status: v1.0.** Complete: every mode is translated and has been played. If you find text
> that is cut off, overlaps or is still in Japanese, please [report it](#reporting-problems).
> [CHANGELOG.md](CHANGELOG.md) lists what's in each release.

## Downloads

Get the latest zip from the [Releases](../../releases) page. It contains one patch:

| Patch | What you get |
|---|---|
| **Jikkyou Power Pro Wrestling '96 - Max Voltage (English)** | The translation, plus fixes for two bugs in the original story mode. |

## How to patch

You need your own copy of the original Japanese cartridge ROM. ROMs are not provided here.

- The ROM must match: *Jikkyou Power Pro Wrestling '96 - Max Voltage* (Japan), 4194304 bytes
  (no copier header), CRC32 `94c1d85c`, SHA-1 `e24b1dcf8e60ebfdb5b0c1d4fe20756ad53f4d61`.
- If your file is 4194816 bytes, it has a 512-byte copier header. Remove the header first; the
  patcher will refuse the file otherwise.

Then:

1. Apply the `.bps` patch with a BPS patcher:
   - [Rom Patcher JS](https://www.marcrobledo.com/RomPatcher.js/) runs in your web browser.
   - Floating IPS (Flips) on Windows or Linux, or MultiPatch on macOS.
   The patcher checks the ROM first, so a wrong dump is refused rather than patched badly.
2. Open the patched ROM in your emulator. Tested in Mesen.

## Notes for players

- **Names.**
  - Japanese names are written given name first, in Hepburn without macrons (Kagetora Nagata).
  - Parody ring names take their English form (The G. Goemon, Richter Belmondo).
  - Some names are shortened where the screen has no room (K. Nagata, L. Wyvern).
  - The guide's glossary lists the Japanese terms.
- **What's still in Japanese.** The title logo and some background art, such as the 優勝
  ("champion") pattern behind tournament winners, are left as they were.
- **Long career names.** A career wrestler's name of 16 letters can reach the right-hand portrait
  when a match is announced. Shorter names fit.
- **Saves.** Start a new save with the patched game. Saves from the unpatched Japanese game
  haven't been tested.
- **Guide.** [docs/guide/](docs/guide/index.html) is a player's guide to the whole game: modes,
  rules, controls, moves, the roster, the Max Voltage career mode with an interactive story map
  (spoilers are folded away), and secrets. It's a single HTML page; open it in a browser.
- **Bug fixes.** Two story bugs of the original game are fixed: the side you pick in the SJPW
  revolt (May 1999) is now recorded, and SJPW's reaction to Max Mercury after the split now
  shows. See [docs/MAX_VOLTAGE.md](docs/MAX_VOLTAGE.md#bugs-fixed).
- **Hidden content.** See [docs/HIDDEN_CONTENT.md](docs/HIDDEN_CONTENT.md).

## Reporting problems

Open an [issue](../../issues) with:

- a screenshot,
- which patch you used,
- where you were: the mode and menu, or roughly what had just happened.

Text that is cut off, overlaps, or still shows Japanese is especially helpful.

## For ROM hackers and contributors

Everything needed to rebuild the patches from the original ROM is in this repository: the
translated text, the patching code (Python 3, no dependencies for the build) and documentation of
the game's formats.

| Document | What's in it |
|---|---|
| [docs/BUILDING.md](docs/BUILDING.md) | Setting up, building, making patches, and the checking tools |
| [docs/TRANSLATION.md](docs/TRANSLATION.md) | Text file formats, scope, style guide, glossary, and naming decisions |
| [docs/EDITING.md](docs/EDITING.md) | Editing the in-game text graphics |
| [docs/PATCHES.md](docs/PATCHES.md) | How each code patch works |
| [docs/TECHNICAL.md](docs/TECHNICAL.md) | The ROM layout, text format, the English text engine, and packed graphics |
| [docs/PLATFORM.md](docs/PLATFORM.md) | SNES pitfalls for this kind of work |
| [docs/guide/](docs/guide/index.html) | The player's guide (text CC BY-SA 4.0, see its LICENSE) |
| [docs/HIDDEN_CONTENT.md](docs/HIDDEN_CONTENT.md) | Unlockables, debug features, and unused and cut content |
| [docs/MAX_VOLTAGE.md](docs/MAX_VOLTAGE.md) | The career mode: the monthly loop, the story calendar, branches, endings, save format and testing tools; the story map is in the [player's guide](docs/guide/index.html#mv-endings) |
| [tools/README.md](tools/README.md) | Every tool, what it's for and how to run it |

Quick start:

```sh
python3 tools/extract.py                 # unpack the ROM in rom/ into extracted/
python3 build.py                         # -> build/Jikkyou Power Pro Wrestling '96 - Max Voltage (English).smc
python3 make_patches.py --version v1.0   # -> release/*.bps and a zip
```

## AI disclosure

AI assisted with the translation.

## Legal

This is a non-commercial fan translation, not affiliated with or endorsed by Konami or anyone else
involved in the game. It contains no copyrighted game data that would let anyone play without
owning the game. The patch only works on your own copy of the ROM.
Jikkyou Power Pro Wrestling '96 - Max Voltage and its contents belong to their respective owners. The Japanese text in this
repository is included for translation and reference.

The code in this repository is released under the [MIT License](LICENSE).
