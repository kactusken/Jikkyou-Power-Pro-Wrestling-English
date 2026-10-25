# Translation

## Where the text is

| File | Holds | Checked by |
|---|---|---|
| `translation/script/bank_8F.txt`, `bank_90.txt` | every string of the game: menus, help, names, career mode story | `tools/script.py check` |
| `translation/tables/font.tsv` | the font's glyph codes and characters (machine-read, checked by eye) | |
| `translation/graphics.csv` | images with text | `tools/check.py` |

## File formats

Message blocks: `@ id`, source lines (`JP `), translation lines (`EN `); no `EN` lines = original
kept. A file's header says what it holds and its limits (`# limit lines=3 chars=28` is checked by
lint). Tables: original columns beside English ones (`japanese`/`english`, or `X`/`en_X`). See
`tools/blocks.py` and `tools/textdb.py`.

Control codes (`tools/script.py`): `{at X,Y}` start position, `{pos X,Y}` new line/column,
`{end}` end of a line, `{skip}` new dialogue page, `{c0f}`-`{c1a}` numbers, `{c1b}`-`{c1e}`
names, `{c1f}`-`{c23}` speaker portrait, `{c0e}{wXXXX}{wXXXX}` a choice with a jump (never
change), `{wXXXX}` data words, `{x N}` (English only) move to pixel N of the line.
Limits: a translated string uses at most the words of the Japanese (`tools/script.py check`
counts them); dialogue lines at most 180 px, 3 lines per page.

## Style guide

- Names: given name first (Kagetora Nagata), Hepburn without macrons; parody ring names in their
  English form (The G. Goemon, Richter Belmondo). Glossary: `translation/glossary.csv`.
- Speaker labels `[Name]`; quotes `"..."`; ellipsis `...`.
- The narration speaks to the player as "you"; Yu Shiina's Tosa dialect is a folksy drawl.
- The created wrestler's default name is Otori Rekka (凰 烈火; reading of 凰 not confirmed).

## Glossary

`translation/glossary.csv` (`japanese, english, notes`): lint warns when a source line contains a
term and the English doesn't use its translation (several accepted forms: `A | B`). Prefer
established community names (existing English guides) over new coinages.

## Decisions

| Decision | Who / why |
|---|---|
| Full translation from scratch (not based on the 1990s patch) | owner, 2026-10-23 |
| Menus and interface first, then the script | owner, 2026-10-23 |
| Names, terms, style above | owner, 2026-10-23 (proposed by Claude) |

## What stays untranslated

- The title logo (実況パワープロレスリング'96) and decorative background art, such as the 優勝
  ("champion") pattern on the tournament and league winner screens: art, not text the player
  needs to read.
- Labels that are already in Latin letters (1P, CPU, WWK, BOM, REAL'S, SWGP, PTS) and tables the
  code reads directly (the digit strip, the kana name grids replaced by `tools/nameentry.py`).
