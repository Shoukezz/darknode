"""Player save file: progress, credits, achievements, best scores.

The same structure is used by the terminal (stored at ``~/.darknode/save.json``)
and by the browser (mirrored in ``localStorage``). Keep it small and JSON-only so
it can be exported to a file and imported back on another device.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

SAVE_VERSION = 1

DEFAULT_SETTINGS: dict[str, Any] = {
    "lang": "en",
    "skin": "amber",
    "crt": True,
    "scanlines": True,
    "flicker": True,
    "music": 0.4,
    "sfx": 0.6,
}


def _default_path() -> Path:
    return Path.home() / ".darknode" / "save.json"


@dataclass
class MissionRecord:
    best_cycles: int | None = None
    stars: int = 0
    attempts: int = 0


@dataclass
class SaveData:
    version: int = SAVE_VERSION
    credits: int = 0
    completed: dict[str, MissionRecord] = field(default_factory=dict)
    achievements: list[str] = field(default_factory=list)
    unlocked: list[str] = field(default_factory=list)
    settings: dict[str, Any] = field(default_factory=lambda: dict(DEFAULT_SETTINGS))

    # --- (de)serialisation -------------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "credits": self.credits,
            "completed": {k: asdict(v) for k, v in self.completed.items()},
            "achievements": list(self.achievements),
            "unlocked": list(self.unlocked),
            "settings": dict(self.settings),
        }

    def to_json(self, indent: int | None = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SaveData":
        if not isinstance(data, dict):
            raise ValueError("save data must be an object")
        settings = dict(DEFAULT_SETTINGS)
        settings.update(data.get("settings") or {})
        completed: dict[str, MissionRecord] = {}
        for key, rec in (data.get("completed") or {}).items():
            rec = rec or {}
            completed[str(key)] = MissionRecord(
                best_cycles=rec.get("best_cycles"),
                stars=int(rec.get("stars", 0)),
                attempts=int(rec.get("attempts", 0)),
            )
        return cls(
            version=int(data.get("version", SAVE_VERSION)),
            credits=int(data.get("credits", 0)),
            completed=completed,
            achievements=list(data.get("achievements") or []),
            unlocked=list(data.get("unlocked") or []),
            settings=settings,
        )

    @classmethod
    def from_json(cls, text: str) -> "SaveData":
        return cls.from_dict(json.loads(text))

    # --- queries -----------------------------------------------------------
    def is_completed(self, mission_id: int) -> bool:
        return str(mission_id) in self.completed

    def record(self, mission_id: int) -> MissionRecord | None:
        return self.completed.get(str(mission_id))

    def total_stars(self) -> int:
        return sum(rec.stars for rec in self.completed.values())

    # --- mutations ---------------------------------------------------------
    def note_attempt(self, mission_id: int) -> None:
        rec = self.completed.setdefault(str(mission_id), MissionRecord())
        rec.attempts += 1

    def record_success(self, mission_id: int, cycles: int, stars: int, reward: int) -> int:
        """Record a win. Returns credits actually awarded (0 on a repeat with no
        improvement; the base reward is only paid the first time)."""
        key = str(mission_id)
        rec = self.completed.get(key)
        first_time = rec is None or rec.best_cycles is None
        if rec is None:
            rec = MissionRecord()
            self.completed[key] = rec
        improved = rec.best_cycles is None or cycles < rec.best_cycles
        if improved:
            rec.best_cycles = cycles
        rec.stars = max(rec.stars, stars)
        awarded = reward if first_time else 0
        self.credits += awarded
        return awarded


def load(path: Path | str | None = None) -> SaveData:
    path = Path(path) if path else _default_path()
    if not path.exists():
        return SaveData()
    try:
        return SaveData.from_json(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return SaveData()


def save(data: SaveData, path: Path | str | None = None) -> None:
    path = Path(path) if path else _default_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(data.to_json(), encoding="utf-8")
