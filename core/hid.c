#include "hid.h"

static unsigned char *sample_ptr(const HidView *v, u32 index) {
    return (unsigned char *)v->samples + (u64)index * HID_STRIDE;
}

u64 hid_get_buttons(const HidView *v, u32 index) {
    if (!v || !v->samples || index >= v->count) return 0;
    return *(volatile u64 *)(sample_ptr(v, index) + HID_BUTTON_OFFSET);
}

void hid_set_buttons(const HidView *v, u32 index, u64 value) {
    if (!v || !v->samples || index >= v->count) return;
    *(volatile u64 *)(sample_ptr(v, index) + HID_BUTTON_OFFSET) = value;
}

u64 hid_merge_buttons(const HidView *v) {
    u64 out = 0;
    if (!v) return 0;
    for (u32 i = 0; i < v->count; i++) out |= hid_get_buttons(v, i);
    return out;
}

u32 hid_sample_count(void *requested, u32 returned) {
    u32 want = (u32)(unsigned long)requested;
    if (want == 0 || want > 64) want = 64;
    if (returned >= 1 && returned <= want) return returned;
    want = (u32)(unsigned long)requested;
    return (want >= 1 && want <= 64) ? want : 0;
}
