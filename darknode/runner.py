"""Glue between a mission, a game session and the sandbox."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

from .game import GameSession
from .missions import Mission
from .sandbox import RunResult, run_script
from .shop import helpers_for


def stars_for(used: int, budget: int) -> int:
    """1 star for solving, 2 for tidy, 3 for tight."""
    if used <= budget * 0.5:
        return 3
    if used <= budget * 0.8:
        return 2
    return 1


@dataclass
class MissionResult:
    success: bool
    message_key: str
    params: dict
    run: RunResult
    session: GameSession | None = field(default=None, repr=False)
    stars: int = 0
    cycle_bonus: int = 0


def play(
    mission: Mission,
    source: str,
    filename: str = "<script>",
    unlocked: Iterable[str] = (),
) -> MissionResult:
    """Run ``source`` against a fresh copy of ``mission``'s network."""
    session = mission.new_session()
    extra = helpers_for(unlocked)
    run = run_script(source, session.api(extra), mission.max_cycles, filename)

    if not run.ok:
        # An alarm during a crack surfaces as a run error; report it thematically.
        if session.alarm:
            return MissionResult(False, "check.alarm", {}, run, session)
        return MissionResult(False, "run.error", {"error": run.error or "script failed"},
                             run, session)

    success, key, params = mission.check(session)
    stars = cycle_bonus = 0
    if success:
        stars = stars_for(run.cycles, mission.max_cycles)
        cycle_bonus = max(0, mission.max_cycles - run.cycles)
    return MissionResult(success, key, dict(params), run, session, stars, cycle_bonus)
