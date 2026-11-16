"""Game profiles ("presets") of Super Hero Boost.

Every profile is a complete configuration: it always includes the HUD and
buttonMapping (our own item buttons), and it fixes the stamina system, difficulty, heart drops
and sprint speed. Changing any option afterwards switches the profile to
Custom and keeps the user's own values.

Sprint is always ×1.25 in the profiles. It is only a starting point: the user
can change it by hand in the Stamina section.
"""
from dataclasses import dataclass

KEYS = ("jump", "attack", "sprint", "block", "shoot", "roll")
STAMINA_MODES = ("hardcore", "combat", "sprint", "advanced")   # value written to the config block
SPRINT_DEFAULT = 125


@dataclass(frozen=True)
class Profile:
    key: str
    button_mapping: bool         # buttonMapping (own item buttons); style, layout and L mode are not part of a profile
    stamina: bool
    mode: int                    # index in STAMINA_MODES
    costs: tuple                 # one bool per KEYS entry
    combat_only: bool
    enemy_hp: int                # percent of vanilla
    damage: int                  # percent of vanilla
    no_heart_drop: bool
    sprint_speed: int            # percent of vanilla
    hud_rupees: bool
    hud_clock: bool
    clock_24h: bool
    songbook: bool
    quick_boots: bool            # hold D-pad down to pick boots
    quick_mask: bool             # hold D-pad up to pick a mask
    hud_collectibles: bool       # per-area collectible counter
    hud_mode: str                # "wide" / "simple" / "map"
    enemy_double: bool           # beta options: a named profile starts with them off
    enemy_move: int              # 0 off, 1 x1.5, 2 x2, 3 x3
    enemy_anim: int
    enemy_attack: int
    great_fairy: bool
    farore_outdoor: bool
    stamina_bar: bool            # stamina UI: horizontal bar instead of the ring
    manual_shield: bool          # ZL follows the game's Hold/Toggle setting, L guards while targeting


def _profile(key, *, button_mapping=True, stamina=True, mode=0, costs=(True,) * 6, combat_only=False,
             enemy_hp=100, damage=100, no_heart_drop=False, sprint_speed=SPRINT_DEFAULT,
             hud_rupees=True, hud_clock=True, clock_24h=True, songbook=True,
             quick_boots=True, quick_mask=True, hud_collectibles=False, hud_mode="wide",
             enemy_double=False, enemy_move=0, enemy_anim=0, enemy_attack=0,
             great_fairy=False, farore_outdoor=False, stamina_bar=False, manual_shield=False):
    return Profile(key=key, button_mapping=button_mapping, stamina=stamina, mode=mode, costs=costs,
                   combat_only=combat_only, enemy_hp=enemy_hp, damage=damage,
                   no_heart_drop=no_heart_drop, sprint_speed=sprint_speed,
                   hud_rupees=hud_rupees, hud_clock=hud_clock, clock_24h=clock_24h,
                   songbook=songbook, quick_boots=quick_boots, quick_mask=quick_mask,
                   hud_collectibles=hud_collectibles, hud_mode=hud_mode,
                   enemy_double=enemy_double, enemy_move=enemy_move, enemy_anim=enemy_anim,
                   enemy_attack=enemy_attack,
                   great_fairy=great_fairy, farore_outdoor=farore_outdoor, stamina_bar=stamina_bar,
                   manual_shield=manual_shield)


PROFILES = {
    # Everything on: Hero Mode difficulty, hardcore stamina, HUD, buttonMapping, the world changes and manual shield.
    "recommended": _profile("recommended", enemy_hp=150, damage=200, no_heart_drop=True,
                            hud_collectibles=True, great_fairy=True, farore_outdoor=True,
                            manual_shield=True),
    # Vanilla difficulty, but with the pack's HUD and extra buttons.
    "base": _profile("base", stamina=False, hud_collectibles=True),
    # Only the manual shield: vanilla difficulty/HUD/controls off, no stamina, no extra buttons.
    "manual-shield": _profile("manual-shield", stamina=False, button_mapping=False, songbook=False,
                              hud_rupees=False, hud_clock=False, quick_boots=False, quick_mask=False,
                              hud_collectibles=False, manual_shield=True),
    # Hero Mode: x1.5 enemy health, x2 damage, no hearts, manual shield.
    "hero": _profile("hero", stamina=False, enemy_hp=150, damage=200, no_heart_drop=True,
                     hud_collectibles=True, manual_shield=True),
    # Hero Mode plus stamina on every action.
    "hero-stamina": _profile("hero-stamina", enemy_hp=150, damage=200, no_heart_drop=True,
                             hud_collectibles=True, manual_shield=True),
    # Hero Mode with stamina only on sprint.
    "hero-explorer": _profile("hero-explorer", mode=2, enemy_hp=150, damage=200, no_heart_drop=True,
                              hud_collectibles=True, costs=(False, False, True, False, False, False),
                              manual_shield=True),
    # Higher difficulty tiers.
    "super-hero": _profile("super-hero", enemy_hp=200, damage=300, no_heart_drop=True,
                           hud_collectibles=True, manual_shield=True),
    "ultra-hero": _profile("ultra-hero", enemy_hp=300, damage=300, no_heart_drop=True,
                           hud_collectibles=True, manual_shield=True),
    # Endurance run: no heart drops and hardcore stamina, but x2 instead of x3.
    "survival": _profile("survival", enemy_hp=200, damage=200, no_heart_drop=True,
                         hud_collectibles=True, manual_shield=True),
    # Only the world changes (Great Fairy rewards + Farore's Wind outdoors) on vanilla difficulty.
    "world": _profile("world", stamina=False, hud_collectibles=True, great_fairy=True,
                      farore_outdoor=True),
    # Beta options: the two enemy mods on top of the vanilla game (all enemy components x2).
    "beta-enemies": _profile("beta-enemies", stamina=False, hud_collectibles=True,
                             enemy_double=True, enemy_move=2, enemy_anim=2, enemy_attack=2),
    # Beta options: everything on, enemy mods included.
    "beta-all": _profile("beta-all", enemy_hp=150, damage=200, no_heart_drop=True,
                         hud_collectibles=True, great_fairy=True, farore_outdoor=True,
                         enemy_double=True, enemy_move=2, enemy_anim=2, enemy_attack=2,
                         manual_shield=True),
}

PROFILE_KEYS = ("recommended", "base", "manual-shield", "hero", "hero-stamina", "hero-explorer", "super-hero",
                "ultra-hero", "survival", "world", "beta-enemies", "beta-all", "custom")
DEFAULT_PROFILE = "recommended"


def defaults() -> dict:
    """Balanced starting values (same shape as a profile, without a fixed key)."""
    return dict(button_mapping=True, stamina=True, mode=0, costs=(True,) * 6, combat_only=False,
                enemy_hp=100, damage=100, no_heart_drop=False, sprint_speed=SPRINT_DEFAULT,
                hud_rupees=True, hud_clock=True, clock_24h=True, songbook=True,
                quick_boots=True, quick_mask=True, hud_collectibles=False, hud_mode="wide",
                enemy_double=False, enemy_move=0, enemy_anim=0, enemy_attack=0,
                great_fairy=False, farore_outdoor=False, stamina_bar=False, manual_shield=False)


def profile_values(key: str) -> dict:
    """Settings kwargs for a profile. 'custom' returns the balanced defaults."""
    p = PROFILES.get(key)
    if p is None:
        return defaults()
    return dict(button_mapping=p.button_mapping, stamina=p.stamina, mode=p.mode, costs=p.costs,
                combat_only=p.combat_only, enemy_hp=p.enemy_hp, damage=p.damage,
                no_heart_drop=p.no_heart_drop, sprint_speed=p.sprint_speed,
                hud_rupees=p.hud_rupees, hud_clock=p.hud_clock, clock_24h=p.clock_24h,
                songbook=p.songbook, quick_boots=p.quick_boots, quick_mask=p.quick_mask,
                hud_collectibles=p.hud_collectibles, hud_mode=p.hud_mode, enemy_double=p.enemy_double,
                enemy_move=p.enemy_move, enemy_anim=p.enemy_anim, enemy_attack=p.enemy_attack,
                great_fairy=p.great_fairy, farore_outdoor=p.farore_outdoor,
                stamina_bar=p.stamina_bar, manual_shield=p.manual_shield)
