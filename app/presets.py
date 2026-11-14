"""Game profiles ("presets") of Super Hero Boost.

Every profile is a complete configuration: it always includes the HUD and
Classic Item Slots, and it fixes the stamina system, difficulty, heart drops
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
    classic: bool
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


def _profile(key, *, classic=True, stamina=True, mode=0, costs=(True,) * 6, combat_only=False,
             enemy_hp=100, damage=100, no_heart_drop=False, sprint_speed=SPRINT_DEFAULT,
             hud_rupees=True, hud_clock=True, clock_24h=True):
    return Profile(key=key, classic=classic, stamina=stamina, mode=mode, costs=costs,
                   combat_only=combat_only, enemy_hp=enemy_hp, damage=damage,
                   no_heart_drop=no_heart_drop, sprint_speed=sprint_speed,
                   hud_rupees=hud_rupees, hud_clock=hud_clock, clock_24h=clock_24h)


PROFILES = {
    # Everything on: Hero Mode difficulty, hardcore stamina, HUD and Classic.
    "recommended": _profile("recommended", enemy_hp=150, damage=200, no_heart_drop=True),
    # Vanilla difficulty, but with the pack's HUD and extra buttons.
    "base": _profile("base", stamina=False),
    # Hero Mode: x1.5 enemy health, x2 damage, no hearts.
    "hero": _profile("hero", stamina=False, enemy_hp=150, damage=200, no_heart_drop=True),
    # Hero Mode plus stamina on every action.
    "hero-stamina": _profile("hero-stamina", enemy_hp=150, damage=200, no_heart_drop=True),
    # Hero Mode with stamina only on sprint.
    "hero-explorer": _profile("hero-explorer", mode=2, enemy_hp=150, damage=200, no_heart_drop=True,
                              costs=(False, False, True, False, False, False)),
    # Higher difficulty tiers.
    "super-hero": _profile("super-hero", enemy_hp=200, damage=300, no_heart_drop=True),
    "ultra-hero": _profile("ultra-hero", enemy_hp=300, damage=300, no_heart_drop=True),
    # Endurance run: no heart drops and hardcore stamina, but x2 instead of x3.
    "survival": _profile("survival", enemy_hp=200, damage=200, no_heart_drop=True),
}

PROFILE_KEYS = ("recommended", "base", "hero", "hero-stamina", "hero-explorer", "super-hero", "ultra-hero",
                "survival", "custom")
DEFAULT_PROFILE = "recommended"


def defaults() -> dict:
    """Balanced starting values (same shape as a profile, without a fixed key)."""
    return dict(classic=True, stamina=True, mode=0, costs=(True,) * 6, combat_only=False,
                enemy_hp=100, damage=100, no_heart_drop=False, sprint_speed=SPRINT_DEFAULT,
                hud_rupees=True, hud_clock=True, clock_24h=True)


def profile_values(key: str) -> dict:
    """Settings kwargs for a profile. 'custom' returns the balanced defaults."""
    p = PROFILES.get(key)
    if p is None:
        return defaults()
    return dict(classic=p.classic, stamina=p.stamina, mode=p.mode, costs=p.costs,
                combat_only=p.combat_only, enemy_hp=p.enemy_hp, damage=p.damage,
                no_heart_drop=p.no_heart_drop, sprint_speed=p.sprint_speed,
                hud_rupees=p.hud_rupees, hud_clock=p.hud_clock, clock_24h=p.clock_24h)
