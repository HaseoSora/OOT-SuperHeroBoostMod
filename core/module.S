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

/* Minimal dynamic section: a symbol table, its strings and a SysV hash, which Rekarina's loader requires
 * (runtime/loader.c parse_dynamic), then DT_NULL. Values are module-relative (the loader adds the base). */.section .dynamic, "aw"
    .quad 6, __shb_dynsym_off          // DT_SYMTAB
    .quad 5, __shb_dynstr_off          // DT_STRTAB
    .quad 4, __shb_hash_off            // DT_HASH
    .quad 0, 0                         // DT_NULL

/* One symbol (the null one) and a SysV hash: the loader only requires the tables to exist; this module's calls
 * are direct PC-relative branches and it imports nothing. */
.section .shb_dynstr, "a"
    .asciz ""

.section .shb_dynsym, "a"
    .p2align 3
    .quad 0, 0, 0                      // symbol 0: null

.section .shb_hash, "a"
    .p2align 2
    .word 1                            // nbucket
    .word 1                            // nchain = number of symbols
    .word 0                            // bucket[0]
    .word 0                            // chain[0]

.section .text
.global _start
.type _start, %function
_start:
    ret
.size _start, . - _start
