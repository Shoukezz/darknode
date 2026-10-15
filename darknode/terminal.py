"""The in-game terminal: a small command shell around the campaign."""

from __future__ import annotations

import sys
from pathlib import Path

from . import i18n, progress
from .content import ACT_ORDER, ACTS
from .missions import MISSIONS, get_mission
from .runner import play
from .sandbox_gen import generate
from .save import SaveData, load as load_save, save as write_save
from .shop import SHOP, SHOP_ORDER

BANNER = r"""
 ____             _    _   _           _
|  _ \  __ _ _ __| | _| \ | | ___   __| | ___
| | | |/ _` | '__| |/ /  \| |/ _ \ / _` |/ _ \
| |_| | (_| | |  |   <| |\  | (_) | (_| |  __/
|____/ \__,_|_|  |_|\_\_| \_|\___/ \__,_|\___|
"""


class Terminal:
    def __init__(self, scripts_dir: Path | str = "scripts",
                 save_path: Path | str | None = None,
                 autosave: bool = True) -> None:
        self.scripts_dir = Path(scripts_dir)
        self.save_path = save_path
        self.autosave = autosave
        self.data: SaveData = load_save(save_path)
        self.lang = self.data.settings.get("lang", "en")
        # legacy helper still used by a couple of tests
        self.completed: set[int] = {int(k) for k in self.data.completed}

    # --- i18n helper ---------------------------------------------------
    def tr(self, key: str, **params) -> str:
        return i18n.t(key, self.lang, **params)

    def _save(self) -> None:
        self.completed = {int(k) for k in self.data.completed}
        if self.autosave:
            try:
                write_save(self.data, self.save_path)
            except OSError:
                pass

    def _script_path(self, mission_id: int) -> Path:
        return self.scripts_dir / f"mission{mission_id}.py"

    # --- command dispatch ----------------------------------------------
    def handle(self, line: str) -> str:
        parts = line.strip().split()
        if not parts:
            return ""
        cmd, args = parts[0].lower(), parts[1:]
        try:
            if cmd == "help":
                return self._help()
            if cmd == "api":
                return self.tr("api_help")
            if cmd in ("missions", "list"):
                return self._missions()
            if cmd == "lang":
                return self._lang(args)
            if cmd == "credits":
                return self.tr("ui.credits", credits=self.data.credits)
            if cmd == "shop":
                return self._shop()
            if cmd == "buy":
                return self._buy(args[0])
            if cmd == "brief":
                return self._brief(int(args[0]))
            if cmd == "new":
                return self._new(int(args[0]))
            if cmd == "run":
                path = Path(args[1]) if len(args) > 1 else None
                return self._run(int(args[0]), path)
            if cmd in ("sandbox", "free"):
                seed = int(args[0]) if args else 1
                return self._sandbox(seed, args)
        except (IndexError, ValueError):
            return "usage error, see 'help'"
        except KeyError as exc:
            return str(exc.args[0])
        return f"unknown command: {cmd}"

    def _help(self) -> str:
        return (
            "Commands:\n"
            "  missions            list missions and your progress\n"
            "  brief <n>           briefing + concept card for mission n\n"
            "  new <n>             create scripts/mission<n>.py from a template\n"
            "  run <n> [file]      run your script for mission n\n"
            "  hint <n> <1|2|3>    show a hint (use 'brief' to read them inline)\n"
            "  shop / buy <id>     spend credits on helper commands\n"
            "  credits             show your credits\n"
            "  lang [en|uk]        show or change language\n"
            "  sandbox <seed>      free-play on a random network (after campaign)\n"
            "  api                 functions your scripts can use\n"
            "  help / exit\n"
        )

    def _missions(self) -> str:
        from .content import unlocked_missions
        completed = {int(k) for k in self.data.completed}
        open_ids = unlocked_missions(completed)
        lines = [self.tr("ui.credits", credits=self.data.credits),
                 f"stars: {self.data.total_stars()}/{len(MISSIONS) * 3}", ""]
        for act in ACT_ORDER:
            lines.append(self.tr(f"act.{act}.name"))
            for mid in ACTS[act]:
                m = get_mission(mid)
                rec = self.data.record(mid)
                if mid not in open_ids:
                    mark = "##"
                elif rec and rec.stars:
                    mark = "*" * rec.stars
                else:
                    mark = ".."
                lines.append(f"  [{mark:<3}] {mid:>2}. {self.tr(f'mission.{mid}.title')}")
            lines.append("")
        return "\n".join(lines).rstrip()

    def _lang(self, args: list[str]) -> str:
        if not args:
            names = ", ".join(f"{k} ({v})" for k, v in i18n.LANGUAGE_NAMES.items())
            return f"language: {self.lang}. available: {names}"
        new = args[0].lower()
        if new not in i18n.LANGUAGES:
            return f"unknown language: {new}"
        self.lang = new
        self.data.settings["lang"] = new
        self._save()
        return f"language set to {i18n.LANGUAGE_NAMES[new]}"

    def _shop(self) -> str:
        lines = [self.tr("ui.shop"), self.tr("ui.credits", credits=self.data.credits)]
        for item_id in SHOP_ORDER:
            item = SHOP[item_id]
            owned = item_id in self.data.unlocked
            status = self.tr("ui.owned") if owned else self.tr("ui.cost", cost=item.cost)
            name = self.tr(f"shop_items.{item_id}.name")
            desc = self.tr(f"shop_items.{item_id}.desc")
            lines.append(f"  {item_id:<6} [{status}]  {name}\n           {desc}")
        return "\n".join(lines)

    def _buy(self, item_id: str) -> str:
        result = progress.buy(self.data, item_id)
        if not result["ok"]:
            reason = result["reason"]
            if reason == "poor":
                return self.tr("ui.too_poor", need=result["need"])
            if reason == "owned":
                return self.tr("ui.owned")
            return f"no such command: {item_id}"
        self._save()
        return f"unlocked {item_id}. " + self.tr("ui.credits", credits=self.data.credits)

    def _brief(self, mission_id: int) -> str:
        m = get_mission(mission_id)
        out = [f"[#{m.id}] {self.tr(f'mission.{m.id}.title')}",
               "", self.tr(f"mission.{m.id}.briefing"),
               "", f"--- {self.tr('ui.concept')} ---",
               self.tr(f"mission.{m.id}.concept"),
               "", f"CPU budget: {m.max_cycles} cycles | reward: {m.reward} cr"]
        hints = i18n.get(f"mission.{m.id}.hints", self.lang) or []
        out.append("")
        out.append(f"--- {self.tr('ui.hint')}s ---")
        for i, h in enumerate(hints, 1):
            out.append(f"  {i}. {h}")
        return "\n".join(out)

    def _new(self, mission_id: int) -> str:
        m = get_mission(mission_id)
        path = self._script_path(mission_id)
        if path.exists():
            return f"{path} already exists; edit it and use 'run {mission_id}'"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.tr(f"mission.{m.id}.template"), encoding="utf-8")
        return f"created {path}"

    def _run(self, mission_id: int, path: Path | None) -> str:
        m = get_mission(mission_id)
        path = path or self._script_path(mission_id)
        if not path.exists():
            return f"{path} not found; create it with 'new {mission_id}'"
        result = play(m, path.read_text(encoding="utf-8"), str(path), self.data.unlocked)
        return self._format_result(m, result, award=True)

    def _sandbox(self, seed: int, args: list[str]) -> str:
        if not progress.sandbox_unlocked(self.data):
            return self.tr("ui.sandbox_locked")
        mission = generate(seed)
        path = self.scripts_dir / "sandbox.py"
        if len(args) > 1:
            path = Path(args[1])
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("# Free play. scan() from home and map it, or crack the "
                            "gateway.\n\nprint(scan())\n", encoding="utf-8")
            return f"created {path} (seed {seed}); edit it and run 'sandbox {seed} {path}'"
        result = play(mission, path.read_text(encoding="utf-8"), str(path),
                      self.data.unlocked)
        return self._format_result(mission, result, award=False)

    def _format_result(self, mission, result, award: bool) -> str:
        lines = list(result.run.output)
        lines.append("-- " + self.tr("ui.cycles", used=result.run.cycles,
                                      max=mission.max_cycles))
        message = self.tr(result.message_key, **result.params)
        if result.success:
            summary = progress.award(self.data, mission, result) if award else {}
            if award:
                self._save()
            lines.append(self.tr("ui.granted", message=message))
            if result.stars:
                lines.append("-- " + self.tr("ui.stars", stars=result.stars))
            if summary.get("awarded"):
                lines.append("-- " + self.tr("ui.awarded", awarded=summary["awarded"]))
            if summary.get("bonus"):
                lines.append("-- " + self.tr("ui.bonus", bonus=summary["bonus"]))
            for ach in summary.get("new_achievements", []):
                lines.append("-- [+] " + self.tr(f"achievement.{ach}.name"))
        else:
            lines.append(self.tr("ui.failed", message=message))
        return "\n".join(line.rstrip("\n") for line in lines)


def main() -> None:
    # The game's text includes Ukrainian (and stars); make sure the console can
    # print UTF-8 even on a legacy code page (e.g. Windows cp1252).
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    term = Terminal()
    print(BANNER)
    print(term.tr("ui.tagline"))
    print("Type 'help' to begin.\n")
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
