#ifndef SHB_HID_H
#define SHB_HID_H

typedef unsigned int u32;
typedef unsigned long long u64;

#define HID_STRIDE 0x28
#define HID_BUTTON_OFFSET 0x08

typedef struct {
    void *samples;
    u32 count;
    u32 controller;
} HidView;

/* Console HID button bits used by the game's full-controller state. */
#define BTN_A      0x0001ull
#define BTN_B      0x0002ull
#define BTN_X      0x0004ull
#define BTN_Y      0x0008ull
#define BTN_L      0x0040ull
#define BTN_R      0x0080ull
#define BTN_ZL     0x0100ull
#define BTN_ZR     0x0200ull
#define BTN_L3     0x0010ull
#define BTN_R3     0x0020ull

u64 hid_get_buttons(const HidView *v, u32 index);
void hid_set_buttons(const HidView *v, u32 index, u64 value);
u64 hid_merge_buttons(const HidView *v);
/* Valid samples of a GetNpadStates call: what it returned (1..requested); the requested count when the return is
 * not usable. Rekarina's GetNpadStates writes only the newest state and returns 1; the rest of the game's 16-sample
 * buffer is never refreshed there, so a handler that walked all 16 read (and kept) its own old writes. */
u32 hid_sample_count(void *requested, u32 returned);

#endif
