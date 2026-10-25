#!/usr/bin/env python3
"""Code hooks for the English text (65816, assembled by tools/asm65816.py).

  hooks.py listing        print the hook labels and size

The English is written in place of the Japanese (tools/script.py), as 16-bit words like the
original, so every pointer, every caller and the dialogue engine work as before. English words
are "chunks" of letters drawn by these hooks:
  $A000 + a*128 + b    letters a and b (b = $7F: a alone); a, b index tools/font12.py CHARS
  $D000 + d            dictionary chunk d (DIDX: its 24-bit address; a length byte, then letter indices)
A chunk is at most MAX_CHUNK_PX wide. The dialogue box draws one character at a time and copies
the tile columns it touched to the upload buffer ($8D:B0BC, at most three); the hook at $8D:B0C1
copies as many as the chunk touched.

1. Drawing. $8D:B127 and $B107 draw one glyph (X = code) at $08/$0A into the text bitmap. For a
   chunk, the hook draws each letter with the game's own routine (the English letters sit in the
   font at $7F:9300 + 12*i as half-width glyphs) and leaves $0E/$0C (first tile, tiles touched)
   as one glyph would. Other codes are noted for the width hook and drawn as before.
2. Widths. The advance at $8D:AEF4 (12 px, or 6 for even codes) is the chunk's width.
3. Dialogue box. The engine places each character from a half-column counter ($1E88, 6 px steps,
   table $81:F123) and wraps at $1E7A. $8D:BFA5 now takes x from a pixel counter, and $8D:BC4D adds
   the character's real width to it (keeping $1E88 = pixels / 6, rounded up, for the wrap test).
WRAM $7E:7F20-$7E:7F4F holds the state ($7E:7000-$7FFF: never written in menus, matches, tournament or the career mode - docs/TECHNICAL.md).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import asm65816  # noqa: E402

HOOK_ORG = 0xB4B200          # free: $B4:B146-$B4:FFFF is $FF padding (code, then the tables)
FONT_BASE = 0x9908           # English letters at $7F:9908 + 12*i: glyphs only translated text used (and
                             # in the part of the font that stays loaded during matches, $6C00 up)
PAIR_BASE = 0xA000
SINGLE = 0x7F
DICT_BASE = 0xD000
# Free ROM for the dictionary letters ($FF padding at bank ends - docs/TECHNICAL.md)
DICT_FREE = [(0xB3AE00, 0xB40000), (0xB2EE40, 0xB30000), (0x82EEA0, 0x830000), (0x8AF610, 0x8B0000),
             (0xBFF5D0, 0xC00000), (0x8EF7C0, 0x8F0000), (0xFAF950, 0xFB0000), (0x87FA80, 0x880000),
             (0x83FA80, 0x840000), (0xBCFBC0, 0xBD0000)]
DICT_BYTES = sum(b - a for a, b in DICT_FREE)
DICT_MAX = (0xB4E000 - HOOK_ORG - 0x400) // 3      # DIDX entries that fit after the code (english.HOOK_END)
MAX_CHUNK_PX = 40           # up to 6 tile columns (the upload hook at $8D:B0C1 copies them all)

SOURCE = r'''
; $7E7F20 code last drawn  $7E7F22 its width  $7E7F24 dialogue pixel x  $7E7F26 first $0E
; $7E7F28 x at start  $7E7F2A letter count  $7E7F2C temp  $7E7F2E which routine  $7E7F30.. letters
.m16
.x16
gcap1:                      ; JML from $8D:B127 (draw glyph X)
    CPX #$A000
    BCS chunk1
    PHB
    TXA
    STA.l $7E7F20
    AND #$0001
    JML $8DB12C
gcap2:                      ; JML from $8D:B107
    CPX #$A000
    BCS chunk2
    PHB
    TXA
    STA.l $7E7F20
    AND #$0001
    JML $8DB10C
tramp1:                     ; JSL here = the original B127 for glyph X
    PHB
    TXA
    AND #$0001
    JML $8DB12C
tramp2:
    PHB
    TXA
    AND #$0001
    JML $8DB10C

chunk1:
    LDA #$0000
    BRA chunk
chunk2:
    LDA #$0001
chunk:                      ; draw the letters of chunk X; RTL to the caller of B127/B107
    STA.l $7E7F2E
    TXA
    STA.l $7E7F20
    JSR letters
    LDA.l $7E7F2A           ; an empty chunk (padding at the end of a part) draws nothing and keeps
    BNE ch_some             ; $0E/$0C of the letter before: the renderers upload the tile columns
    RTL                     ; up to the last glyph's (an empty one cut the last letter short)
ch_some:
    LDA $08
    STA.l $7E7F28
    LDA $0E
    STA.l $7E7F26
    LDY #$0000
ch_loop:
    TYA
    CMP.l $7E7F2A
    BCS ch_done
    PHY
    TYX
    LDA.l $7E7F30,X
    AND #$00FF
    PHA
    ASL A
    ASL A
    STA.l $7E7F2C
    ASL A
    CLC
    ADC.l $7E7F2C
    ADC #FBASE
    TAX
    LDA.l $7E7F2E
    BNE ch_t2
    JSL tramp1
    BRA ch_drawn
ch_t2:
    JSL tramp2
ch_drawn:
    PLA
    TAX
    LDA.l LW,X
    AND #$00FF
    CLC
    ADC $08
    STA $08
    PLY
    TYA
    BNE ch_next
    LDA $0E
    STA.l $7E7F26
ch_next:
    INY
    BRA ch_loop
ch_done:
    LDA.l $7E7F28
    STA $08
    LDA.l $7E7F26
    STA $0E
    LDA.l $7E7F28           ; tiles touched: (x+w-1)/8 - x/8 + 1, at least 1
    CLC
    ADC.l $7E7F22
    DEC A
    LSR A
    LSR A
    LSR A
    STA.l $7E7F2C
    LDA.l $7E7F28
    LSR A
    LSR A
    LSR A
    EOR #$FFFF
    SEC
    ADC.l $7E7F2C
    INC A
    BEQ ch_one
    BPL ch_set
ch_one:
    LDA #$0001
ch_set:
    STA $0C
    RTL

letters:                    ; A = chunk code -> letters at $7E7F30, count $7E7F2A, width $7E7F22
    CMP #DICTB
    BCS l_dict
    SEC
    SBC #$A000
    PHA
    LSR A
    LSR A
    LSR A
    LSR A
    LSR A
    LSR A
    LSR A
    SEP #$20
    STA.l $7E7F30
    REP #$20
    PLA
    AND #$007F
    CMP #$007F
    BEQ l_one
    SEP #$20
    STA.l $7E7F31
    REP #$20
    LDA #$0002
    BRA l_count
l_one:
    LDA #$0001
    BRA l_count
l_dict:                     ; DIDX: 3-byte address of a length byte + letters
    SEC
    SBC #DICTB
    STA.l $7E7F2C
    ASL A
    CLC
    ADC.l $7E7F2C
    TAX
    PHB
    SEP #$20
    LDA.l DIDX+2,X
    PHA
    PLB
    REP #$20
    LDA.l DIDX,X
    TAX
    LDA $0000,X
    AND #$00FF
    STA.l $7E7F2A
    LDY #$0000
ld_loop:
    TYA
    CMP.l $7E7F2A
    BCS ld_done
    INX
    SEP #$20
    LDA $0000,X
    PHX
    TYX
    STA.l $7E7F30,X
    PLX
    REP #$20
    INY
    BRA ld_loop
ld_done:
    PLB
    BRA l_width
l_count:
    STA.l $7E7F2A
l_width:
    LDA #$0000
    STA.l $7E7F22
    LDY #$0000
lw_loop:
    TYA
    CMP.l $7E7F2A
    BCS lw_done
    TYX
    LDA.l $7E7F30,X
    AND #$00FF
    TAX
    LDA.l LW,X
    AND #$00FF
    CLC
    ADC.l $7E7F22
    STA.l $7E7F22
    INY
    BRA lw_loop
lw_done:
    RTS

width:                      ; JSL from $8D:AEF4 instead of LDA $14 / LDX $16
    LDA.l $7E7F20
    CMP #$A000
    BCC w_orig
    LDA.l $7E7F22
    LDX #$0001
    RTL
w_orig:
    LDA $14
    LDX $16
    RTL

nameblank:                  ; JSL from $8D:B872 (the name length $8D:B85F; then BCS): carry set
    CMP.l $8F82C2           ; when A is a blank word - the game's two blank glyphs, a lone space or
    BEQ nbl_yes             ; two spaces, or a blank dictionary chunk (line padding). Names inserted
    CMP.l $8F82C4           ; into text ({c1b}) drop trailing blanks, so the padding of the roster
    BEQ nbl_yes             ; lines (kept for the name slots) leaves no gap: "Masked Robo wins!"
    CMP #$A07F
    BEQ nbl_yes
    CMP #$A000
    BEQ nbl_yes
    CMP #DICTB
    BCC nbl_no
    CMP #DBLANK1
    BCS nbl_no
nbl_yes:
    SEC
    RTL
nbl_no:
    CLC
    RTL

upload:                     ; JML from $8D:B0C1: copy $0C tile columns of 12 rows from $7F:$0E (+$100 each)
    LDA $0C                 ; to $7F:$0E+$4000 (the original did at most three). None: nothing
    BEQ up_done             ; (the count would wrap: 65536 uploads overran the DMA queue at $7E:AF00)
    LDA #$007F
    STA $00
    LDA #$0000
up_loop:
    PHA
    CLC
    ADC $0E
    PHA
    CLC
    ADC #$4000
    TAY
    PLA
    LDX #$000C
    JSL $809249
    PLA
    CLC
    ADC #$0100
    DEC $0C
    BNE up_loop
up_done:
    RTL

namepack:                   ; JSL from $8D:DC63 (A = code to add to the name at $1FD2, cursor $11F2).
    STA.l $7E7F40           ; A letter typed into slot k waits there ($7E7F46 = k+1) and the next one
    LDA $11F2               ; joins it; only then does the cursor move on (8 letters per name)
    ASL A
    TAX
    LDA $11F2
    INC A
    CMP.l $7E7F46
    BNE np_new
    LDA $1FD2,X
    JSR np_lone
    BCC np_new
    LDA.l $7E7F40
    JSR np_lone
    BCC np_new
    LDA.l $7E7F40
    SEC
    SBC #$A000
    LSR A
    LSR A
    LSR A
    LSR A
    LSR A
    LSR A
    LSR A
    STA.l $7E7F42
    LDA $1FD2,X
    AND #$FF80
    ORA.l $7E7F42
    STA $1FD2,X
    BRA np_next
np_new:
    LDA.l $7E7F40
    STA $1FD2,X
    JSR np_lone
    BCC np_next
    LDA $11F2
    INC A
    STA.l $7E7F46
    RTL
np_next:
    LDA #$0000
    STA.l $7E7F46
    LDA $11F2
    INC A
    CMP #$0008
    BCC np_set
    LDA #$0007
np_set:
    STA $11F2
    RTL
np_lone:                    ; C=1 if A is a lone letter ($A000-$CFFF, second letter $7F)
    CMP #$A000
    BCC np_no
    CMP #$D000
    BCS np_no
    AND #$007F
    CMP #$007F
    BNE np_no
    SEC
    RTS
np_no:
    CLC
    RTS

namebox:                    ; JSL from $8D:DAD7 (then RTS): the cursor box at slot $11F2 (table $8E:F79D,
    PHX                     ; 0-3 family name, 4-7 given name); on a slot whose letter waits for a
    LDA $11F2               ; second one (namepack) it goes 6 px right, where that letter will go
    CMP #$0008
    BCC nb_in
    LDA #$0007
nb_in:
    STA.l $7E7F44
    ASL A
    TAX
    LDA.l $8EF79D,X
    AND #$00FF
    CLC
    ADC #$0005
    STA $0A48
    LDA.l $8EF79E,X
    AND #$00FF
    CLC
    ADC #$0005
    STA $0A4C
    LDA.l $7E7F44
    INC A
    CMP.l $7E7F46
    BNE nb_done
    LDA $1FD2,X
    JSR np_lone
    BCC nb_done
    LDA $0A48
    CLC
    ADC #$0006
    STA $0A48
nb_done:
    PLX
    RTL

nameslot:                   ; JSL from $8D:DC9D: blank the 12 px slot, then draw the name word A
    PHA
    LDA #$25E9
    JSL $8DB0BC
    PLA
    JSL $8DB0BC
    RTL

namemode:                   ; JML from $8D:D6AF: a mode button (A = 1 hiragana, 2 katakana, 3 kanji)
    DEC A                   ; the kanji converter has no English counterpart: its button does nothing
    CMP #$0002
    BEQ nm_same
    SEP #$20
    CMP $11F5
    STA $11F5
    REP #$20
    BEQ nm_same
    LDA #$0014
    STA $11EA
nm_same:
    RTL

dlg_x:                      ; JSL from $8D:BFA5 instead of LDY $1E88 / LDA $F123,Y: A = pixel x
    LDA $1E88
    BNE dx_keep
    STA.l $7E7F24
dx_keep:
    LDA.l $7E7F24
    RTL

dlg_step:                   ; JSL from $8D:BC4D: add the width of character $08, set $1E88
    LDA $08
    CMP #$A000
    BCC ds_jp
    PHX
    PHY
    JSR letters
    PLY
    PLX
    LDA.l $7E7F22
    BRA ds_add
ds_jp:
    LSR A
    LDA #$0006
    BCC ds_add
    LDA #$000C
ds_add:
    CLC
    ADC.l $7E7F24
    STA.l $7E7F24
    CLC
    ADC #$0005
    STA.l $7E7F2C
    LDA #$0000
ds_div:
    PHA
    LDA.l $7E7F2C
    SEC
    SBC #$0006
    STA.l $7E7F2C
    PLA
    BCC ds_set
    INC A
    BRA ds_div
ds_set:
    STA $1E88
    RTL
'''


def long_addr(a):
    return bytes([a & 0xff, (a >> 8) & 0xff, a >> 16])


def jml(target):
    return bytes([0x5C, target & 0xff, (target >> 8) & 0xff, target >> 16])


def jsl(target):
    return bytes([0x22, target & 0xff, (target >> 8) & 0xff, target >> 16])


def assemble(widths, dict_addrs, last_blank=DICT_BASE):
    """(code bytes at HOOK_ORG, labels). widths: advance of each letter (font12 CHARS order);
    dict_addrs: CPU address of each dictionary chunk (length byte + letter indices), chunk
    d = DICT_BASE + d; last_blank: the last code of the leading blank chunks."""
    src = SOURCE.replace('FBASE', f'${FONT_BASE:04X}').replace('DICTB', f'${DICT_BASE:04X}')
    src = src.replace('DBLANK1', f'${last_blank + 1:04X}')
    src += 'slotw:                      ; save slot line (91:AE2C): empty, " y", "r" - set by english.py\n'
    src += '    dw $0000,$0000,$0000\n'
    src += 'LW:\n' + ''.join(f'    db ${w:02X}\n' for w in widths)
    src += 'DIDX:\n' + ''.join(f'    dl ${a:06X}\n' for a in dict_addrs)
    return asm65816.assemble(src, HOOK_ORG)


def patches(labels):
    """[(cpu address, original bytes, new bytes, what)] in bank $8D."""
    return [
        (0x8DB127, bytes.fromhex('8b8a290100'), jml(labels['gcap1']) + b'\xea', 'glyph draw: chunks (B127)'),
        (0x8DB107, bytes.fromhex('8b8a290100'), jml(labels['gcap2']) + b'\xea', 'glyph draw: chunks (B107)'),
        (0x8DAEF4, bytes.fromhex('a514a616'), jsl(labels['width']), 'proportional advance'),
        (0x8DB0C1, bytes.fromhex('a97f0085'), jml(labels['upload']), 'dialogue: upload every touched tile column'),
        (0x8DDC63, bytes.fromhex('a8adf211'), jsl(labels['namepack']), 'name entry: two letters per word'),
        (0x8DDC67, bytes.fromhex('0a'), b'\x60', None),
        (0x8DDAD7, bytes.fromhex('adf211c90800'), jsl(labels['namebox']) + b'\x60\xea', 'name entry: cursor box'),
        # save slot line "1996年 7月 name 1年目" -> "1996/7 name 1 yr" (年 -> /, 月 -> empty: english.TABLE_WORDS)
        (0x91AE44, bytes.fromhex('c2828f'), long_addr(labels['slotw']), 'save slot: nothing after the year'),
        (0x91AE87, bytes.fromhex('febd8f'), long_addr(labels['slotw'] + 2), 'save slot: " y" after the career year'),
        (0x91AE8E, bytes.fromhex('00be8f'), long_addr(labels['slotw'] + 4), 'save slot: "r"'),
        (0x8DDC9D, bytes.fromhex('22bcb08d'), jsl(labels['nameslot']), 'name entry: clear each slot'),
        (0x8DD6AF, bytes.fromhex('3ae220cd'), jml(labels['namemode']), 'name entry: no kanji converter'),
        (0x8DBFA5, bytes.fromhex('ac881eb923f1'), jsl(labels['dlg_x']) + b'\xea\xea', 'dialogue: x from pixels'),
        (0x8DBC4D, bytes.fromhex('ee881ea5084a9003ee881e'), jsl(labels['dlg_step']) + b'\xea' * 7,
         'dialogue: advance by real width'),
        (0x8DB872, bytes.fromhex('cfc2828ff01ccfc4828ff016'), jsl(labels['nameblank']) + b'\xb0\x1c' + b'\xea' * 6,
         'inserted names: no trailing padding'),
    ]


def main(argv=None):
    code, labels = assemble([6] * 98, [0xB3AE00])
    for k, v in sorted(labels.items(), key=lambda kv: kv[1]):
        print(f'{k:10} ${v:06X}')
    print(f'{len(code)} bytes')
    return 0


if __name__ == '__main__':
    sys.exit(main())
