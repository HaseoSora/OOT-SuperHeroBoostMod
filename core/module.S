/* MOD0 header matching the known-good subsdk1 container layout.
 * All executable code is ours; only the container/metadata offsets are fixed. */
.section .module, "ax"
.global _module_header
_module_header:
    .word 0xD65F03C0          // 0x00: harmless ret
    .word 0x20                // 0x04: MOD0 offset
    .space 0x18               // 0x08..0x1F
    .ascii "MOD0"             // 0x20
    .word __dynamic_off       // 0x24: dynamic section (module-relative, from link.ld)
    .word __bss_start_off     // 0x28: bss start (module-relative)
    .word __bss_end_off       // 0x2C: bss end (module-relative)
    .word 0                   // 0x30: eh_frame start (none)
    .word 0                   // 0x34: eh_frame end (none)
    .word __module_object_off // 0x38: module object inside bss
    .word 0                   // 0x3C

/* Minimal dynamic section: a single DT_NULL terminator. */
.section .dynamic, "aw"
    .quad 0
    .quad 0

.section .text
.global _start
.type _start, %function
_start:
    ret
.size _start, . - _start
