"""Campaign structure: acts, achievement definitions and unlock rules.

Text (act names, achievement names/descriptions) lives in the locale files under
``act.*`` and ``achievement.*``; here we keep only the structure.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .missions import MISSIONS

# Which mission ids belong to each act (1..5).
ACTS: dict[int, list[int]] = {}
for _m in MISSIONS:
    ACTS.setdefault(_m.act, []).append(_m.id)

ACT_ORDER = sorted(ACTS)
TOTAL_MISSIONS = len(MISSIONS)
MAX_STARS = TOTAL_MISSIONS * 3


def unlocked_missions(completed: set[int]) -> set[int]:
    """Mission n is playable once n-1 is complete (mission 1 is always open)."""
    open_ids = {MISSIONS[0].id}
    ordered = [m.id for m in MISSIONS]
    for prev, nxt in zip(ordered, ordered[1:]):
        if prev in completed:
            open_ids.add(nxt)
    open_ids |= completed  # anything already solved stays open
    return open_ids


def campaign_complete(completed: set[int]) -> bool:
    return all(m.id in completed for m in MISSIONS)


@dataclass(frozen=True)
class Achievement:
    id: str
    test: Callable[["AchievementContext"], bool]


@dataclass
class AchievementContext:
    completed: set[int]
    total_stars: int
    best_stars: int          # most stars earned on a single mission
    bought: int              # number of shop items owned
    crack_attempts_min: int  # fewest attempts used to clear mission 7 (or 1e9)


ACHIEVEMENTS: list[Achievement] = [
    Achievement("first-blood", lambda c: 1 in c.completed),
    Achievement("act-1", lambda c: all(i in c.completed for i in ACTS.get(1, []))),
    Achievement("act-2", lambda c: all(i in c.completed for i in ACTS.get(2, []))),
    Achievement("act-3", lambda c: all(i in c.completed for i in ACTS.get(3, []))),
    Achievement("act-4", lambda c: all(i in c.completed for i in ACTS.get(4, []))),
    Achievement("cryptographer", lambda c: all(i in c.completed for i in ACTS.get(5, []))),
    Achievement("efficient", lambda c: c.best_stars >= 3),
    Achievement("shopper", lambda c: c.bought >= 1),
    Achievement("quiet-pro", lambda c: c.crack_attempts_min <= 12),
    Achievement("star-hoarder", lambda c: c.total_stars >= 50),
    Achievement("completionist", lambda c: campaign_complete(c.completed)),
]

ACHIEVEMENT_IDS = [a.id for a in ACHIEVEMENTS]
