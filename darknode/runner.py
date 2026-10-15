"""Glue between a mission, a game session and the sandbox."""

from __future__ import annotations

from dataclasses import dataclass

from .game import GameSession
from .missions import Mission
from .sandbox import RunResult, run_script


@dataclass
class MissionResult:
    success: bool
    message: str
    run: RunResult


def play(mission: Mission, source: str, filename: str = "<script>") -> MissionResult:
    """Run ``source`` against a fresh copy of ``mission``'s network."""
    session = GameSession(mission.build())
    run = run_script(source, session.api(), mission.max_cycles, filename)
    if not run.ok:
        return MissionResult(False, run.error or "script failed", run)
    success, message = mission.check(session)
    return MissionResult(success, message, run)
