# Max Voltage: how the career mode works

Max Voltage is the game's career mode. You join Super Japan Pro-Wrestling (SJPW) as an
18-year-old trainee in March 1996, and the career ends five years later, in March 2001. This
document covers how a month works, the story calendar, every branch and choice, the endings,
and the tools for testing the mode quickly. The story map is in the player's guide,
[guide/index.html](guide/index.html#mv-endings).

Findings are marked *from the code* (read from the 65816 code and tables) or *verified in game*
(seen in Mesen). Script addresses (`90AF2C`) are blocks in `translation/script/bank_8F.txt` /
`bank_90.txt`. Code addresses are in the original ROM.

## Contents
- [The shape of the mode](#the-shape-of-the-mode) · [A month](#a-month) · [The calendar](#the-calendar)
- [Branches and choices](#branches-and-choices) · [Titles](#titles) · [Endings](#endings)
- [Random events](#random-events) · [Memory and save format](#memory-and-save-format)
- [Bugs fixed](#bugs-fixed) · [Testing](#testing) · [Open questions](#open-questions)

## The shape of the mode
- **The story runs on the calendar.** A table at `$8D:C733` has one 6-byte row per month from
  March 1996 to March 2001 (61 rows). Each row names that month's story event (ids 1-59, 0 =
  none) and the month's two Pro-Wres News items. Story events are fixed dates; what an event
  shows depends on your promotion, flags set by earlier events, ratings and match results.
  *(from the code)*
- **There is no "must win".** You can lose any match and the calendar still moves on; losing
  only closes branches (the America tour, the Fight Tourney, belts). The two game overs are
  failing the pro test and the night escape. *(from the code)*
- **The ending depends only on the belts you hold** in March 2001: none, one to three, or all
  four. *(from the code; the four-belt ending verified in game)*
- **Four promotions.** SJPW from the start. WWK in America opens if you win the Young Tiger Cup
  (a six-month tour), and again from December 1999. REAL'S (Yu Shiina's mixed-martial-arts
  promotion) opens in January 1998, and BOM (Bando and Iwai's death-match promotion) in
  February 1999. Promotion numbers in memory: 2 SJPW, 3 WWK, 4 BOM, 5 REAL'S.

## A month
A month is a state machine on direct-page `$88` (table `$88:8007`). *(from the code; verified
in game with the autoplay log)*

1. **Intro**: "It is now {month}/{year}", the month's Pro-Wres News headline, and from 2000
   Max Mercury's move.
2. **Start-of-month event** (phase 1): the calendar event, or a random happening, or a dojo
   raider ([Random events](#random-events)).
3. **The hub**: PROFILE, RECORD, MAGAZINE, TRANSFER, MOVES, COSTUME, DIET, OPTIONS, and
   PROCEED. Trainees can't change costume.
4. **PROCEED**: in an even month (and in March and May 1996) you train: the training split
   (points to W power, S flexibility, R speed, or REST), sparring, and the coach's report. In
   an odd month your promotion runs a show: the title-shot check, then the card. Bouts that
   aren't yours are decided by rank (lower rank wins, ties go to the blue corner); your bout is
   a real match. Some shows are tournaments (the Young Tiger Cup, the Fight Tourney).
5. **After-show event** (phase 2): calendar events whose row has bit 7 set run here (debut,
   title results, tournament results), or a random happening.
6. **Month end**: "This month's activities are done" (the game autosaves) or "It was your
   birthday this month"; then a planned transfer is carried out and the month advances
   (`$88:90F3`: January adds a year, March a career year).

## The calendar
Months without an entry have no story event, only random happenings. "After" means the event
runs after the month's show. *(from the code; July, November and December 1996, May and December 1999 and
March 2001 verified in game with checkpoints)*

| Month | Event | Who sees it |
|---|---|---|
| 1996/03 | Arrival: Jonouchi, the rookie trainer, explains training (90A068) | everyone |
| 1996/04 | Nagata invites you to morning sparring (90A2CE) | everyone |
| 1996/05 | L. Wyvern back from Europe, press in the dojo (90A6B4) | everyone |
| 1996/06 | **Pro test** vs Sparrow Shiraishi; fail = game over (90AA0A) | everyone |
| 1996/07 | **Debut** vs Jonouchi (after), nickname at random from eight (90AB76) | everyone |
| 1996/08 | Heavenly King Fukunaga and Nagata (90ACE2) | everyone |
| 1996/09 | Nagata wins the SWGP title from Fukunaga (after) | everyone |
| 1996/10 | "Next month is the Young Tiger Cup" (90AE84) | everyone |
| 1996/11 | **Young Tiger Cup** (after): win = America tour, lose = Thunder goes | everyone |
| 1996/12 | America: arrival at WWK, **pick a manager** (8FE6DE) | tour |
| 1997/01-04 | Tour scenes: your manager, Richter Belmondo, Spark Star | tour |
| 1997/02-03 | Nagata's "Main Eventers vs. Rookies" (Star Hunt) show and its result | not on tour |
| 1997/05 | Tour ends, flight home, manager's farewell gift (8FF200) / Bando's slump | tour / others |
| 1997/06 | Thunder back from America (90B310) | not on tour |
| 1997/08 | **Fight Tourney** announced; you are SJPW's entrant if your REAL'S rating is 30+ | SJPW |
| 1997/09 | Fight Tourney qualifier (after) | entrant |
| 1997/11 | Fight Tourney final (after) | final four |
| 1998/01 | REAL'S founded: transfer offer opens; Shiina visits if you made the final four | everyone |
| 1998/02-03 | REAL'S belt; Shiina beats Douglas for the first title | REAL'S |
| 1998/04 | Narumi and Bando jump to REAL'S; you jump with them if your planned transfer is REAL'S | SJPW, REAL'S |
| 1998/06-11 | REAL'S training scenes (Douglas, Shiina and Bando, Concord, Yamagami) | REAL'S |
| 1998/08, 10 | Iwai reads the Bando piece; Iwai leaves SJPW | SJPW |
| 1998/12 | Press event: BOM founded (90C442) | everyone |
| 1999/02 | BOM opens: transfer offer; Bando invites you (90C61C) | everyone |
| 1999/03-08 | BOM scenes (Iwai's roster, Death Bloodman, Abra Kadabra, Temujin) / REAL'S scenes | BOM / REAL'S |
| 1999/04 | Wyvern demands a title shot, office argument (90CD80) | SJPW, not champion |
| 1999/05 | **SJPW revolt** (after): Wyvern attacks Nagata; **pick a side** | SJPW, not champion |
| 1999/10 | Iwai retires next month; you are his last opponent if your BOM rating is 120+ | BOM |
| 1999/11 | Iwai's farewell match result (after) | BOM, his opponent |
| 1999/12 | WWK announces **Max Mercury** and its plan to take every belt | everyone |
| 2000/01-2001/02 | Mercury changes promotion every month and goes after the belts | everyone |
| 2001/03 | **"March 2001"**: the ending (after) | everyone |

## Branches and choices
Choices show two options: the first jumps to another page, the second continues.
*(from the code and the script)*

| When | Choice or condition | Result |
|---|---|---|
| June 1996 | Pro test result (score from the match) | fail: "Please pack your bags", game over |
| July 1996 | Debut result: won / fought hard / lost | different congratulations; the nickname is random |
| November 1996 | Young Tiger Cup won / lost | won: America tour with WWK until May 1997 (transfers locked); lost: Thunder goes |
| December 1996 | "Miss Madeleine" / "Don Silver" | your manager on the tour; a different reward at the end |
| August 1997 | REAL'S rating 30+ | you enter the Fight Tourney instead of Narumi |
| September / November 1997 | Qualifier / final won | final four (Shiina visits in 1998) / Fight Tourney champion |
| April 1998 | Planned transfer to REAL'S | you jump with Narumi and Bando ("3 SJPW stars") |
| May 1999 | "I'm with the SJPW Loyalists!!" / "I'm joining Wyvern's Army!!" | your side in the faction war (on hold from December 1999); the original game lost this answer, see [Bugs fixed](#bugs-fixed) |
| October 1999 | BOM rating 120+ | you, not Bando, are Iwai's farewell opponent |
| Any month | TRANSFER: an offer from SJPW (Nitta), REAL'S (Shiina), BOM (Bando) or WWK (Siegfried): "Count me in!!" / "Let me think it over." | accepting plans the move for next month |
| Any month | TRANSFER: "Run off" (night escape) | game over next month |
| Dojo raider | "Leave it to me!!" / "I can't do this..." | you fight the raider, or your host does |
| Fame events | joke choices (theme song, merchandise, talk show...) | stat changes |

**Transfers** *(from the code)*: the TRANSFER menu lists every open promotion. Accepting an
offer sets a plan (`$7E51C4`), shown as "Plan: To X", carried out at the end of the month.
Transfers are locked for a month after a move and during the America tour. WWK is only open
during the tour and from December 1999; REAL'S from January 1998; BOM from February 1999.

## Titles
Each promotion has one belt: SWGP Heavyweight (SJPW), WWK World Heavyweight, World Death Match
(BOM), Multi-Battle (REAL'S). *(from the code)*
- Before each show (not tournaments or special cards): if you hold your promotion's belt,
  the show is a defense; otherwise, if your rating with that promotion is 140 or more, you get
  a title shot. After a title match you sit out the next show ("By the rules, you can't go
  for the title this month").
- Beating the champion makes you champion. From 2000, Max Mercury moves between promotions and
  takes belts; you can only challenge him in the promotion he is in.
- Ratings are per promotion (SJPW, REAL'S, WWK, BOM) and grow with matches.

## Endings
*(from the code; the night escape, no-belt and four-belt endings verified in game)*

| Ending | How | Last words |
|---|---|---|
| Pro test failed | fail the June 1996 test | "Please pack your bags" |
| Night escape | TRANSFER, "Run off", confirm | "...slip out of the dorm", then the GAME OVER screen |
| No belt | March 2001, no belts | "Wish it, and it's yours." |
| One to three belts | March 2001, one line per belt held | "Only those who make the move earn the right to win." |
| Quadruple Crown | March 2001, all four belts | "The strongest professional wrestler in the world", then a teaser: "The Overtaker" is coming |

After the four-belt ending the staff credits roll; after the no-belt ending the game returns
to the main menu. Every March 2001 ending, with or without belts, keeps your wrestler in the
Legends' Room (seven places; when it is full the game asks you to erase someone) and opens the
Legends group in the other modes ([HIDDEN_CONTENT.md](HIDDEN_CONTENT.md#legends-max-mercury-and-your-own-wrestler)).
*(verified in game: the battery save after the no-belt and four-belt endings; the full-room
prompt from the code, `$91:F330`)*

## Random events
*(from the code)*
- **Happenings**: when a month has no start-of-month event, half the time a luck event runs
  (chanko stew, a lucky tea stalk, a black cat, a ghost in the dorm... 16 kinds), each raising
  or lowering a stat. About 7 in 32 rolls are instead a **fame event** (each once per career):
  a theme song from PICNICS JAPAN, merchandise, a talk show, an autograph session, a film
  role, a quiz show, meeting the receptionist in town.
- **Dojo raiders** (Mister Saizo, Kengoro Yagyu, Masked Kraken): only in a training month with
  no story event, not on the tour, before BOM opens, once one of your ratings is 80 or more;
  a 1 in 4 chance; each raider comes once. They later join BOM.

## Memory and save format
*(from the code; the save layout verified in game by loading crafted saves)*

| WRAM | Meaning |
|---|---|
| `$1FE2` / `$1FE3` / `$1FE4` | year − 1996 / month / career year − 1 |
| `$1FE7` | promotion (2 SJPW, 3 WWK, 4 BOM, 5 REAL'S) |
| `$1FE6` | nickname (0-7) |
| `$1370`-`$139F` | story flags (flag n = bit n&7 of byte n>>3) |
| `$7E50DE` / `50E0` / `50E2` / `50E4` | rating with SJPW / REAL'S / WWK / BOM |
| `$7E51C8` / `51CA` / `51CC` / `51CE` | champion of SJPW / WWK / BOM / REAL'S (wrestler id; you are `$3B`, Max Mercury `$33`) |
| `$7E51C4` | planned transfer (promotion) |
| `$7E51C6`, `$7E5260` | matches recorded, and the history (8 bytes each) |
| `$7E51D2` | manager on the tour (1 Madeleine, 2 Silver) |
| `$7E51D3`, `$7E51D8`-`51DB` | transfer lock; title-shot lock per promotion |
| `$7E51DD` | Max Mercury's promotion |

Story flags: `$02` SJPW, `$03` WWK, `$04` BOM, `$05` REAL'S open for transfers; `$07` night
escape planned; `$08` career over; `$09` on the America tour; `$0A` Thunder on the tour; `$0B`
five years over; `$21` debuted; `$22` trainee; `$24` Fight Tourney entrant; `$25` final four;
`$2A` Fight Tourney champion; `$2B` jumped to REAL'S with Narumi and Bando; `$26` Iwai's
opponent; `$27` faction war on; `$29` joined Wyvern's Army; `$30` Max Mercury active;
`$31`-`$33` raiders done; `$11`-`$19` fame events seen; `$06` trainee coaching months; `$0C`
overseas hub; `$20` transfers locked abroad; `$23` Wyvern's argument seen; `$28` a title match fought.

**Save slots.** The battery RAM holds three slots of `$440` bytes at `$0020`, `$0460` and
`$08A0` (`$80:863C`-`$80:8959`). A slot is a plain copy of the career's WRAM: `$1F9A`-`$1FEA`,
the flags `$1370` and `$7E5090`-`$7E543F`. There is no checksum, only the word `$0234` at +2
marking it as used, so a slot can be edited or built from any WRAM dump, and the game loads it
at the hub of its month.

## Bugs fixed
Two bugs in the original game are fixed by the patch (`fixes` in `build.py`, details in
[PATCHES.md](PATCHES.md#bug-fixes)). *(from the code; the lost faction choice was also seen in game
on the original ROM; both fixes verified in game)*

- **The faction choice was lost (May 1999).** The code that records "I'm joining Wyvern's
  Army!!" (`$88:A808`, flag `$29`) read the answer `$1E86` after the next dialogue had already
  reset it to 0, so every player was counted as a Loyalist. The answer is now recorded as soon
  as the choice scene ends. The scene itself always showed the answer you picked. As far as
  the code shows, the flag changes nothing you can see: its only reader (`$88:BC76`, when a
  show card is built during the faction war) picks between two follow-ups that run the same
  code. The fix makes the save hold your real side.
- **The "faction war's on hold" scene never showed (December 1999).** When WWK announces Max
  Mercury, each promotion reacts. SJPW has two versions: one for a normal SJPW (condition 5)
  and one for after the split (condition 6, 90E220: Nagata and Wyvern put the faction war on
  hold). The event cleared the split flag `$27` before the reactions, so SJPW players after
  the split always saw the normal version. The flag is now cleared after the reactions.

## Testing
Four tools make any part of the story quick to reach. They are for testing only.

| Tool | What it does |
|---|---|
| `tools/mvsave.py` | Reads and edits save files: `info`, `set` (date, promotion, flags, any WRAM address), `fromwram` (a slot from a Mesen WRAM dump), `preset` (a story checkpoint, below) |
| `tools/mvtest.py` | Makes a test image where your card bouts are decided like the other bouts, and you always win (`--lose`: always lose). Tournament bouts are still real matches. |
| `tools/mvauto.lua` | Autoplay rules for `tools/mesen.py` (`autoplay FRAMES tools/mvauto.lua [stop=YYYYMM] [step=PH:ST] [choice=2] [split=rest]`): pages through dialogue, PROCEEDs, fills the training split, answers choices and confirms the cards; logs every state change to `auto.log` |
| `tools/mvload.lua` | From the title screen, loads a save slot and stops at the hub |
| `tools/mvcover.py` | Coverage: which script blocks have been shown, from Mesen's code/data logs (`cdl` step); `report OUT.md CDL...` lists the unseen ones |

**Checkpoints** (`python3 tools/mvsave.py presets`): `protest`, `debut`, `ytcup`, `tour`,
`thunder`, `tourend`, `tourney`, `titleshot`, `reals`, `realsjump`, `realslife`, `bom`,
`bomlife`, `revolt`, `iwai`, `mercury`, `escape`, `end0`, `end2`, `end4`. Each sets the date,
promotion and the flags the earlier story would have set, plus what its branch needs (ratings,
belts, a planned transfer). Any used slot works as the base: your own save, or one from
`fromwram`. For example, the four-belt ending:

```sh
python3 tools/mvsave.py preset MySave.srm 1 end4 -o end4.srm
python3 tools/mvtest.py "build/Jikkyou Power Pro Wrestling '96 - Max Voltage (English).smc" build/mvtest.smc
```

Load `end4.srm` as the game's battery save, continue slot 1 and PROCEED: the ending plays after
the month's show. With Mesen and the tools, a whole checkpoint runs unattended:

```
load title
write sram 0 end4.srm
autoplay 3000 tools/mvload.lua
autoplay 20000 tools/mvauto.lua
shot end
```

From a checkpoint save to the end of the four-belt ending took about 14,000 frames (four
minutes of game time; Mesen runs headless faster than that). With autoplay, the test image
played July to November 1996 in about 27,000 frames. Training months include a two-minute
sparring match that autoplay simply waits out. *(verified in game)*

With `pages=1`, autoplay takes a screenshot of every finished dialogue page and logs the
script word it started at, for a review gallery. Mesen keeps its code/data log per ROM file
across sessions, so `cdl` dumps accumulate everything ever run on that file. Mesen's headless
test runner ends itself (exit 255) after about 40,000 frames, even with nothing scripted: play
long spans in sessions of a couple of months, each continuing from the battery save the game
writes at the end of every month (`dump sram`). Run one Mesen at a time, so the code/data log
isn't written by two sessions at once.

Random events and interviews can be forced with `tools/mesen.py`'s `onexec ADDR MEM BYTE`, which
writes a byte just before an instruction runs: `$8E` at `$88:A828` picks the happening (low 5
bits: 2, 7, 10, 16, 24, 26, 29 are the fame events, any other a luck event), `$8F` at
`$88:A87F` / `$88:A8A9` the luck event (16 kinds, a different list before December 1996), and
`$8E` at `$91:BAF7` / `$91:BABD` a dojo raider (0) and which one (0-2). An interview answer is
`$B5:8000` + 2 × ((winner − 1) × 9 + variant × 3 + question); poking the winner `$12A8` right
after loading a state at the post-match screen shows any wrestler's answers.

Autoplay reads the dialogue state `$1E74`: 3 and 7 wait for a button at the end of a page or
line, 12 is a choice (Down moves to the second answer, which sets `$1E86` = 1).

Mesen savestates also work, but not during a match (saving one there crashes Mesen), and they
are tied to one build of the ROM; crafted saves work with any build.

## Open questions
- The pro test score: which match results count as a pass (`$8D:CC63`).
- The test image doesn't patch tournament bouts (Young Tiger Cup, Fight Tourney): play them,
  or set their result flags in a crafted save.
- In the test image, the RECORD screen names your simulated opponents "Emergency Name".
- Calendar bit 6 is set on most start-of-month events but no code that reads it was found.
