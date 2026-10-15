"""The in-game terminal: a small command shell around missions."""

from __future__ import annotations

import sys
from pathlib import Path

from .game import API_HELP
from .missions import MISSIONS, get_mission
from .runner import play

BANNER = r"""
 ____             _    _   _           _
|  _ \  __ _ _ __| | _| \ | | ___   __| | ___
| | | |/ _` | '__| |/ /  \| |/ _ \ / _` |/ _ \
| |_| | (_| | |  |   <| |\  | (_) | (_| |  __/
|____/ \__,_|_|  |_|\_\_| \_|\___/ \__,_|\___|

Type 'help' to see commands.
"""

HELP = """\
Commands:
  missions          list missions
  brief <n>         show the briefing for mission n
  new <n>           create scripts/mission<n>.py from a template
  run <n> [file]    run your script for mission n (default scripts/mission<n>.py)
  api               show the functions your scripts can use
  help              show this help
  exit              leave the terminal
"""


class Terminal:
    def __init__(self, scripts_dir: Path | str = "scripts") -> None:
        self.scripts_dir = Path(scripts_dir)
        self.completed: set[int] = set()

    def _script_path(self, mission_id: int) -> Path:
        return self.scripts_dir / f"mission{mission_id}.py"

    def handle(self, line: str) -> str:
        """Execute one command and return the text to show."""
        parts = line.strip().split()
        if not parts:
            return ""
        cmd, args = parts[0].lower(), parts[1:]
        try:
            if cmd == "help":
                return HELP
            if cmd == "api":
                return API_HELP
            if cmd == "missions":
                return self._missions()
            if cmd == "brief":
                mission = get_mission(int(args[0]))
                return f"[#{mission.id}] {mission.title}\n{mission.briefing}"
            if cmd == "new":
                return self._new(int(args[0]))
            if cmd == "run":
                path = Path(args[1]) if len(args) > 1 else None
                return self._run(int(args[0]), path)
        except (IndexError, ValueError):
            return "usage error, see 'help'"
        except KeyError as exc:
            return str(exc.args[0])
        return f"unknown command: {cmd}"

    def _missions(self) -> str:
        lines = []
        for m in MISSIONS:
            mark = "x" if m.id in self.completed else " "
            lines.append(f"[{mark}] {m.id}. {m.title}")
        return "\n".join(lines)

    def _new(self, mission_id: int) -> str:
        mission = get_mission(mission_id)
        path = self._script_path(mission_id)
        if path.exists():
            return f"{path} already exists; edit it and use 'run {mission_id}'"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(mission.template, encoding="utf-8")
        return f"created {path}"

    def _run(self, mission_id: int, path: Path | None) -> str:
        mission = get_mission(mission_id)
        path = path or self._script_path(mission_id)
        if not path.exists():
            return f"{path} not found; create it with 'new {mission_id}'"
        result = play(mission, path.read_text(encoding="utf-8"), str(path))
        lines = list(result.run.output)
        lines.append(f"-- cycles used: {result.run.cycles}/{mission.max_cycles}")
        if result.success:
            self.completed.add(mission_id)
            lines.append(f"ACCESS GRANTED: {result.message}")
        else:
            lines.append(f"FAILED: {result.message}")
        return "\n".join(line.rstrip("\n") for line in lines)


def main() -> None:
    term = Terminal()
    print(BANNER)
    while True:
        try:
            line = input("darknode> ")
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if line.strip().lower() in {"exit", "quit"}:
            break
        out = term.handle(line)
        if out:
            print(out)
    sys.exit(0)
