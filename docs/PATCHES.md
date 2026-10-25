# Patches

What the build changes besides text and images, one section per patch: what the original code
does, what changed, why it works, the tool that makes it, limits to respect, and whether it was
*verified in game*.

## Bug fixes
Two fixes for bugs in the original game's Max Voltage story, group `fixes` in `build.py`
(`CODE_PATCHES`, applied by `tools/codepatch.py`, which checks every original byte first). They are
on in every build and in the release patch; `--unlocks none` leaves them out. The new code
(38 bytes) sits at `$88:FF00`, in the `$FF` padding at the end of bank `$88`. What the bugs do in
the game: [MAX_VOLTAGE.md](MAX_VOLTAGE.md#bugs-fixed).

**The faction answer (May 1999).** The revolt event runs as steps `$18`-`$1B` of the phase-1 step
table (`$88:9EDB`): `$18` starts the scene, `$19` (`$88:AD34`) runs it to the end, `$1A` closes the
window, and `$1B` (`$88:A808`) clears flag `$29` and sets it again if the choice answer `$1E86` is
not 0. But `$1E86` is reset to 0 whenever a dialogue starts (`$8D:BB38`), and one starts between the
end of the scene and step `$1B`, so the flag was never set. Now:
- `$88:AD69` (`LDA #$0190`, run when step `$19`'s dialogue ends, still with the answer in `$1E86`)
  becomes `JSR $FF00`. On step `$19` only, the new code clears flag `$29` and sets it for the
  second answer, then does the replaced `LDA #$0190`. The same code also runs for steps 3 and `$24`;
  the step check leaves those alone.
- `$88:A808` becomes `JMP $A81B`, the end of the original step, so it no longer clears the flag.

**The Mercury reactions (December 1999).** The event (`$88:A797`) cleared flag `$27` (the SJPW
split) at `$88:A7A5` before steps `$1C`-`$22` showed the reactions, whose SJPW version is picked by
condition 5 (no split) or 6 (split). Now those 7 bytes are NOPs, and table entry `$22` (`$88:9F1F`,
was `$A81B`) points to new code that clears flag `$27` and jumps to `$A81B`. Step `$22` of that
table is only reached from this event (step `$1C` is only set at `$88:A7D6`).

*Verified in game:* option 2 sets flag `$29` and option 1 leaves it clear (in the June 1999 save);
an SJPW player after the split sees 90E220 ("No more time for faction wars") and flag `$27` is
clear afterwards.
