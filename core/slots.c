#include "slots.h"

void slots_reset(SlotState *s) {
    for (u32 i = 0; i < SLOT_COUNT; i++) {
        s->slot[i].item = 0;
        s->slot[i].variant = 0;
        s->slot[i].valid = 0;
    }
    s->age = 0;
    s->page = 0;
    s->selected = 0;
}

void slots_set_age(SlotState *s, u32 is_adult) {
    s->age = is_adult ? 1 : 0;
}

void slots_assign(SlotState *s, u32 slot, u32 item, u32 variant) {
    if (slot >= SLOT_COUNT) return;
    if (item == 0) {
        s->slot[slot].valid = 0;
        s->slot[slot].item = 0;
        s->slot[slot].variant = 0;
        return;
    }
    s->slot[slot].item = item;
    s->slot[slot].variant = variant;
    s->slot[slot].valid = 1;
}

u32 slots_item(const SlotState *s, u32 slot) {
    return slot < SLOT_COUNT && s->slot[slot].valid ? s->slot[slot].item : 0;
}

u32 slots_variant(const SlotState *s, u32 slot) {
    return slot < SLOT_COUNT ? s->slot[slot].variant : 0;
}

void slots_cycle_variant(SlotState *s, u32 slot, u32 max_variants) {
    if (slot >= SLOT_COUNT || max_variants == 0) return;
    s->slot[slot].variant = (s->slot[slot].variant + 1) % max_variants;
}

/* Logical masks used by the game's full-controller HID state:
 * L=0x40, R=0x80, ZL=0x100, ZR=0x200, R3=0x20. */
u32 slots_button_to_slot(u32 button_mask) {
    if (button_mask & 0x40) return SLOT_L;
    if (button_mask & 0x80) return SLOT_R;
    if (button_mask & 0x200) return SLOT_ZR;
    return 0xFFFFFFFFu;
}
