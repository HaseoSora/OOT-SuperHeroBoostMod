# Classic Item Slots: hook map

All offsets are module-relative to `main` (add the ASLR base at runtime).
The release IPS stores offsets with the synthetic `+0x100` NSO header.

| # | site | stock instruction | Stamina instruction | Classic target | overlap Stamina? |
|---|---|---|---|---|---|
| 0 | 0x033A927C | 0x9779A261 `bl #0x1211c00` | 0x9779A261 `bl #0x1211c00` | 0x04F80FF0 | no |
| 1 | 0x033AAC34 | 0x97799BF3 `bl #0x1211c00` | 0x97799BF3 `bl #0x1211c00` | 0x04F80FF0 | no |
| 2 | 0x033BD928 | 0x977950B6 `bl #0x1211c00` | 0x977950B6 `bl #0x1211c00` | 0x04F80FF0 | no |
| 3 | 0x033C9AB4 | 0x97792053 `bl #0x1211c00` | 0x97792053 `bl #0x1211c00` | 0x04F80FF0 | no |
| 4 | 0x034694F8 | 0x941F64BE `bl #0x3c427f0` | 0x946C7208 `bl #0x4f85d18` | 0x04F80024 | yes |
| 5 | 0x03469524 | 0x941F64BB `bl #0x3c42810` | 0x946C7203 `bl #0x4f85d30` | 0x04F808C8 | yes |
| 6 | 0x03469550 | 0x941F64B4 `bl #0x3c42820` | 0x946C71FE `bl #0x4f85d48` | 0x04F808E0 | yes |
| 7 | 0x0346966C | 0x941F6465 `bl #0x3c42800` | 0x946C71A5 `bl #0x4f85d00` | 0x04F808B0 | yes |
| 8 | 0x03469698 | 0x941F6466 `bl #0x3c42830` | 0x946C71B2 `bl #0x4f85d60` | 0x04F808F8 | yes |
| 9 | 0x033D7124 | 0xD10383FF `sub sp, sp, #0xe0` | 0xD10383FF `sub sp, sp, #0xe0` | 0x04F80F70 | no |
| 10 | 0x033D8CC4 | 0xA9BE7BFD `stp x29, x30, [sp, #-0x20]!` | 0xA9BE7BFD `stp x29, x30, [sp, #-0x20]!` | 0x04F80F90 | no |
| 11 | 0x00D57CE4 | 0xA9BE7BFD `stp x29, x30, [sp, #-0x20]!` | 0xA9BE7BFD `stp x29, x30, [sp, #-0x20]!` | 0x04F80F80 | no |
| 12 | 0x033F6894 | 0x975902A3 `bl #0xa37320` | 0x975902A3 `bl #0xa37320` | 0x04F80FB0 | no |
| 13 | 0x033E64E0 | 0x97594410 `bl #0xa37520` | 0x97594410 `bl #0xa37520` | 0x04F80FD0 | no |

## What the five overlaps mean

Stamina already replaces these five input calls with its own handlers in
`subsdk1` (offsets 0xD00..0xD60). Classic also needs them for the extra item
buttons. A full merge must call the stock reader once, then Classic's
continuation, then the stamina input post-filter. The `experimental` build does
that with trampolines in main's text padding; the `stable` build lets Classic
own those five calls and keeps all other stamina hooks.
