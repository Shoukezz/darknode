"""Glue between a mission, a game session and the sandbox."""

from __future__ import annotations

from dataclasses import dataclass, field

from .game import GameSession
from .missions import Mission
from .sandbox import RunResult, run_script


@dataclass
class MissionResult:
    success: bool
    message: str
    run: RunResult
    session: GameSession | None = field(default=None, repr=False)


def play(mission: Mission, source: str, filename: str = "<script>") -> MissionResult:
    """Run ``source`` against a fresh copy of ``mission``'s network."""
    session = GameSession(mission.build())
    run = run_script(source, session.api(), mission.max_cycles, filename)
    if not run.ok:
        return MissionResult(False, run.error or "script failed", run, session)
    success, message = mission.check(session)
    return MissionResult(success, message, run, session)
