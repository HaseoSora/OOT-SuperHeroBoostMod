/*
 * Clean-room extra item slots for the unified mod.
 * The game-specific item IDs and menu calls are wired later; this file owns
 * the assignment/state rules.
 */
#ifndef SHB_SLOTS_H
#define SHB_SLOTS_H

typedef unsigned int u32;

#define SLOT_COUNT 4

enum {
    SLOT_ZR = 0,
    SLOT_X = 1,
    SLOT_L = 2,
    SLOT_R = 3,
};

typedef struct {
    u32 item;
    u32 variant;
    u32 valid;
} ItemSlot;

typedef struct {
    ItemSlot slot[SLOT_COUNT];
    u32 age;          /* 0 = child, 1 = adult */
    u32 page;
    u32 selected;
} SlotState;

void slots_reset(SlotState *s);
void slots_set_age(SlotState *s, u32 is_adult);
void slots_assign(SlotState *s, u32 slot, u32 item, u32 variant);
u32 slots_item(const SlotState *s, u32 slot);
u32 slots_variant(const SlotState *s, u32 slot);
void slots_cycle_variant(SlotState *s, u32 slot, u32 max_variants);
u32 slots_button_to_slot(u32 button_mask);

#endif
