"""Runs the player's Python script with game rules applied.

Rules:
* only a small set of builtins and an allow-list of modules are available;
* every executed line costs one CPU "cycle" and the budget is limited,
  so slow brute force can run out of cycles.

This is a game mechanic, not a security boundary: only run scripts you trust.
"""

from __future__ import annotations

import builtins
import sys
from dataclasses import dataclass, field
from typing import Any, Callable

ALLOWED_MODULES = frozenset(
    {"math", "string", "itertools", "collections", "functools", "heapq", "base64"}
)

_SAFE_BUILTIN_NAMES = (
    "abs all any bool chr dict divmod enumerate filter float frozenset hash int "
    "isinstance len list map max min next ord pow print range repr reversed round "
    "set sorted str sum tuple zip bytes bytearray "
    "Exception ValueError KeyError IndexError TypeError StopIteration"
).split()


class CycleLimitExceeded(Exception):
    """Raised when a script uses more cycles than the mission allows."""


@dataclass
class RunResult:
    ok: bool
    cycles: int
    output: list[str] = field(default_factory=list)
    error: str | None = None


def _restricted_import(name, globals=None, locals=None, fromlist=(), level=0):
    root = name.split(".")[0]
    if level != 0 or root not in ALLOWED_MODULES:
        raise ImportError(f"module '{name}' is not available on this terminal")
    return builtins.__import__(name, globals, locals, fromlist, level)


def run_script(
    source: str,
    api: dict[str, Callable[..., Any]],
    max_cycles: int = 50_000,
    filename: str = "<script>",
) -> RunResult:
    """Execute ``source`` with ``api`` functions available as globals."""
    output: list[str] = []

    def game_print(*args: Any, sep: str = " ", end: str = "\n") -> None:
        output.append(sep.join(str(a) for a in args) + ("" if end == "\n" else end))

    safe_builtins = {name: getattr(builtins, name) for name in _SAFE_BUILTIN_NAMES}
    safe_builtins["print"] = game_print
    safe_builtins["__import__"] = _restricted_import
    safe_builtins["__build_class__"] = builtins.__build_class__

    env: dict[str, Any] = {"__builtins__": safe_builtins, "__name__": "__main__"}
    env.update(api)

    try:
        code = compile(source, filename, "exec")
    except SyntaxError as exc:
        return RunResult(False, 0, output, f"SyntaxError: {exc.msg} (line {exc.lineno})")

    cycles = 0

    def tracer(frame, event, arg):
        nonlocal cycles
        if frame.f_code.co_filename != filename:
            return None  # only count the player's own lines
        if event == "line":
            cycles += 1
            if cycles > max_cycles:
                raise CycleLimitExceeded(
                    f"out of CPU cycles ({max_cycles}); try a smarter algorithm"
                )
        return tracer

    old_trace = sys.gettrace()
    sys.settrace(tracer)
    try:
        exec(code, env)
    except CycleLimitExceeded as exc:
        return RunResult(False, cycles, output, str(exc))
    except Exception as exc:  # the player's bug, reported in-game
        return RunResult(False, cycles, output, f"{type(exc).__name__}: {exc}")
    finally:
        sys.settrace(old_trace)
    return RunResult(True, cycles, output)
