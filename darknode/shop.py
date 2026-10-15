"""The command shop: helper functions players can buy with credits.

These are *conveniences* — generic utilities that speed up log-wrangling and
tallying. None of them solve a mission on their own (no cipher breakers here),
so every mission stays solvable from the base API with zero purchases. When a
command is unlocked it is injected into the player's sandbox as a global.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from typing import Any, Callable, Iterable


def _grep(pattern: str, text: str) -> list[str]:
    """Return the lines of ``text`` that match the regular expression ``pattern``."""
    rx = re.compile(pattern)
    return [line for line in str(text).splitlines() if rx.search(line)]


def _freq(seq: Iterable[Any]) -> dict[Any, int]:
    """Count how often each item appears, like collections.Counter."""
    return dict(Counter(seq))


def _nums(text: str) -> list[int]:
    """Pull every whole number out of a blob of text, in order."""
    return [int(m) for m in re.findall(r"-?\d+", str(text))]


def _uniq(seq: Iterable[Any]) -> list[Any]:
    """Unique items, keeping first-seen order."""
    seen: set[Any] = set()
    out: list[Any] = []
    for item in seq:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


@dataclass(frozen=True)
class ShopItem:
    id: str
    cost: int
    fn: Callable[..., Any]


SHOP: dict[str, ShopItem] = {
    "grep": ShopItem("grep", 40, _grep),
    "freq": ShopItem("freq", 50, _freq),
    "nums": ShopItem("nums", 40, _nums),
    "uniq": ShopItem("uniq", 30, _uniq),
}

SHOP_ORDER = ["grep", "freq", "nums", "uniq"]


def helpers_for(unlocked: Iterable[str]) -> dict[str, Callable[..., Any]]:
    """Map of helper name -> function for the player's unlocked commands."""
    return {name: SHOP[name].fn for name in unlocked if name in SHOP}
