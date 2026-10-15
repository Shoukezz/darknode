"""Game session: the commands a player's script can call."""

from __future__ import annotations

from typing import Any, Callable

from .network import Network

HOME = "home"


class AccessDenied(Exception):
    """Raised in-game when the player touches something they can't reach."""


class GameSession:
    """State of one mission attempt and the API exposed to the script."""

    def __init__(self, network: Network, start: str = HOME) -> None:
        self.network = network
        self.current = start
        self.discovered: set[str] = {start}
        self.crack_attempts = 0
        self.submitted: Any = None
        self.has_submitted = False

    # --- helpers -------------------------------------------------------
    def _require_known(self, host: str) -> None:
        if host not in self.discovered:
            raise AccessDenied(f"unknown host '{host}' (scan for it first)")

    # --- API available to player scripts --------------------------------
    def whoami(self) -> str:
        """Return the host you are currently connected to."""
        return self.current

    def scan(self, host: str | None = None) -> list[str]:
        """List hosts linked to ``host`` (default: the current host)."""
        host = self.current if host is None else host
        self._require_known(host)
        found = self.network.neighbors(host)
        self.discovered.update(found)
        return found

    def connect(self, host: str) -> str:
        """Move to a discovered, unlocked host."""
        self._require_known(host)
        if self.network.node(host).locked:
            raise AccessDenied(f"{host} is locked; crack it first")
        self.current = host
        return host

    def hint(self, host: str) -> str:
        """Read the password hint of a locked host."""
        self._require_known(host)
        return self.network.node(host).hint or "no hint available"

    def crack(self, host: str, password: str) -> bool:
        """Try a password. Returns True and unlocks the host when correct."""
        self._require_known(host)
        node = self.network.node(host)
        self.crack_attempts += 1
        if node.password is not None and str(password) == node.password:
            node.cracked = True
        return not node.locked

    def ls(self) -> list[str]:
        """List files on the current host."""
        return sorted(self.network.node(self.current).files)

    def cat(self, filename: str) -> str:
        """Read a file on the current host."""
        files = self.network.node(self.current).files
        if filename not in files:
            raise AccessDenied(f"no such file on {self.current}: {filename}")
        return files[filename]

    def submit(self, answer: Any) -> None:
        """Send your answer to the mission handler."""
        self.submitted = answer
        self.has_submitted = True

    def api(self) -> dict[str, Callable[..., Any]]:
        names = ("whoami", "scan", "connect", "hint", "crack", "ls", "cat", "submit")
        functions: dict[str, Any] = {name: getattr(self, name) for name in names}
        functions["AccessDenied"] = AccessDenied
        return functions


API_HELP = """\
Commands available inside your scripts:
  whoami()              -> current host
  scan(host=None)       -> list of linked hosts (default: current host)
  connect(host)         -> move to an unlocked host you have discovered
  hint(host)            -> password hint of a locked host
  crack(host, password) -> True if the password is right (unlocks the host)
  ls()                  -> files on the current host
  cat(filename)         -> contents of a file on the current host
  submit(answer)        -> send your answer for the mission
Allowed imports: math, string, itertools, collections, functools, heapq, base64
"""
