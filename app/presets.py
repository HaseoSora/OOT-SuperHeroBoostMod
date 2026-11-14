"""Game profiles ("presets") of Super Hero Boost.

A profile fixes every gameplay option at once: the extra-button module,
the stamina system and its mode, the per-action costs, enemy health,
damage taken, heart drops, sprint speed and the always-visible HUD.

The window treats any manual change as "custom" and keeps the user's own
values. New options can be added here as long as every profile sets them.
"""
from dataclasses import dataclass

KEYS = ("jump", "attack", "sprint", "block", "shoot", "roll")
STAMINA_MODES = ("hardcore", "combat", "sprint", "advanced")   # value written to the config block


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


PROFILES = {
    "original": Profile(
        key="original", classic=False, stamina=False, mode=0,
        costs=(True,) * 6, combat_only=False,
        enemy_hp=100, damage=100, no_heart_drop=False, sprint_speed=100,
        hud_rupees=False, hud_clock=False, clock_24h=False,
    ),
    "hero": Profile(
        key="hero", classic=False, stamina=False, mode=0,
        costs=(True,) * 6, combat_only=False,
        enemy_hp=150, damage=200, no_heart_drop=True, sprint_speed=100,
        hud_rupees=False, hud_clock=False, clock_24h=False,
    ),
    "hero-stamina": Profile(
        key="hero-stamina", classic=False, stamina=True, mode=0,
        costs=(True,) * 6, combat_only=False,
        enemy_hp=150, damage=200, no_heart_drop=True, sprint_speed=125,
        hud_rupees=False, hud_clock=False, clock_24h=False,
    ),
    "explorer": Profile(
        key="explorer", classic=True, stamina=True, mode=2,
        costs=(False, False, True, False, False, False), combat_only=False,
        enemy_hp=100, damage=100, no_heart_drop=False, sprint_speed=175,
        hud_rupees=True, hud_clock=True, clock_24h=True,
    ),
    "survival": Profile(
        key="survival", classic=True, stamina=True, mode=0,
        costs=(True,) * 6, combat_only=False,
        enemy_hp=200, damage=200, no_heart_drop=True, sprint_speed=125,
        hud_rupees=True, hud_clock=True, clock_24h=True,
    ),
    "boost": Profile(
        key="boost", classic=True, stamina=False, mode=0,
        costs=(True,) * 6, combat_only=False,
        enemy_hp=100, damage=100, no_heart_drop=False, sprint_speed=300,
        hud_rupees=True, hud_clock=True, clock_24h=False,
    ),
}

PROFILE_KEYS = ("original", "hero", "hero-stamina", "explorer", "survival", "boost", "custom")
DEFAULT_PROFILE = "hero-stamina"


def defaults() -> dict:
    """Balanced starting values (same shape as a profile, without a fixed key)."""
    return dict(classic=True, stamina=True, mode=0, costs=(True,) * 6, combat_only=False,
                enemy_hp=100, damage=100, no_heart_drop=False, sprint_speed=125,
                hud_rupees=False, hud_clock=False, clock_24h=False)


def profile_values(key: str) -> dict:
    """Settings kwargs for a profile. 'custom' returns the balanced defaults."""
    p = PROFILES.get(key)
    if p is None:
        return defaults()
    return dict(classic=p.classic, stamina=p.stamina, mode=p.mode, costs=p.costs,
                combat_only=p.combat_only, enemy_hp=p.enemy_hp, damage=p.damage,
                no_heart_drop=p.no_heart_drop, sprint_speed=p.sprint_speed,
                hud_rupees=p.hud_rupees, hud_clock=p.hud_clock, clock_24h=p.clock_24h)
