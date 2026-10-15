"""Ties the save file to the campaign: credits, stars, shop and achievements.

Both front-ends go through this module (the browser calls it through Pyodide),
so the rules live in exactly one place.
"""

from __future__ import annotations

from typing import Any

from .content import (
    ACHIEVEMENTS, AchievementContext, campaign_complete, unlocked_missions,
)
from .missions import Mission
from .runner import MissionResult
from .save import SaveData
from .shop import SHOP

#: credits earned per 50 unused cycles, on the first clear only
BONUS_PER = 50


def _bonus_credits(cycle_bonus: int) -> int:
    return cycle_bonus // BONUS_PER


def _context(save: SaveData, result_attempts: int, mission_id: int) -> AchievementContext:
    completed = {int(k) for k in save.completed}
    best_stars = max((rec.stars for rec in save.completed.values()), default=0)
    # "quiet-pro": mission 7 cleared in few crack attempts (this run)
    quiet = result_attempts if mission_id == 7 else 10 ** 9
    return AchievementContext(
        completed=completed,
        total_stars=save.total_stars(),
        best_stars=best_stars,
        bought=len(save.unlocked),
        crack_attempts_min=quiet,
    )


def _refresh_achievements(ctx: AchievementContext, save: SaveData) -> list[str]:
    earned: list[str] = []
    for ach in ACHIEVEMENTS:
        if ach.id not in save.achievements and ach.test(ctx):
            save.achievements.append(ach.id)
            earned.append(ach.id)
    return earned


def award(save: SaveData, mission: Mission, result: MissionResult) -> dict[str, Any]:
    """Apply a run's outcome to ``save`` and return a summary of what changed."""
    save.note_attempt(mission.id)

    summary: dict[str, Any] = {
        "awarded": 0,
        "bonus": 0,
        "stars": 0,
        "cycle_bonus": result.cycle_bonus,
        "new_achievements": [],
        "credits": save.credits,
    }

    if not result.success:
        return summary

    bonus = _bonus_credits(result.cycle_bonus)
    base = save.record_success(mission.id, result.run.cycles, result.stars, mission.reward)
    # pay the cycle bonus only alongside the first clear's base reward
    if base > 0 and bonus:
        save.credits += bonus
        summary["bonus"] = bonus

    crack_attempts = getattr(result.session, "crack_attempts", 0) if result.session else 0
    ctx = _context(save, crack_attempts, mission.id)
    new_ach = _refresh_achievements(ctx, save)

    summary.update({
        "awarded": base,
        "stars": result.stars,
        "new_achievements": new_ach,
        "credits": save.credits,
    })
    return summary


def can_play(save: SaveData, mission_id: int) -> bool:
    completed = {int(k) for k in save.completed}
    return mission_id in unlocked_missions(completed)


def sandbox_unlocked(save: SaveData) -> bool:
    return campaign_complete({int(k) for k in save.completed})


def buy(save: SaveData, item_id: str) -> dict[str, Any]:
    if item_id not in SHOP:
        return {"ok": False, "reason": "unknown"}
    if item_id in save.unlocked:
        return {"ok": False, "reason": "owned"}
    cost = SHOP[item_id].cost
    if save.credits < cost:
        return {"ok": False, "reason": "poor", "need": cost - save.credits}
    save.credits -= cost
    save.unlocked.append(item_id)
    # buying may trigger the "shopper" achievement
    ctx = _context(save, 10 ** 9, -1)
    new_ach = _refresh_achievements(ctx, save)
    return {"ok": True, "credits": save.credits, "new_achievements": new_ach}
