"""Game session: the commands a player's script can call."""

from __future__ import annotations

from typing import Any, Callable

from .network import Network

HOME = "home"


class AccessDenied(Exception):
    """Raised in-game when the player touches something they can't reach."""


class AlarmTripped(Exception):
    """Raised when the player makes too much noise (too many failed cracks)."""


class GameSession:
    """State of one mission attempt and the API exposed to the script."""

    def __init__(
        self,
        network: Network,
        start: str = HOME,
        dataset: list[Any] | None = None,
        crack_limit: int | None = None,
    ) -> None:
        self.network = network
        self.current = start
        self.discovered: set[str] = {start}
        self.crack_attempts = 0
        self.failed_cracks = 0
        self.crack_limit = crack_limit
        self.dataset = dataset
        self.submitted: Any = None
        self.has_submitted = False
        self.alarm = False

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

    def links(self, host: str | None = None) -> list[tuple[str, int]]:
        """Like scan(), but each entry is ``(host, latency)`` for routing."""
        host = self.current if host is None else host
        self._require_known(host)
        found = self.network.neighbors(host)
        self.discovered.update(found)
        return [(n, self.network.weight(host, n)) for n in found]

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
        else:
            self.failed_cracks += 1
            if self.crack_limit is not None and self.failed_cracks > self.crack_limit:
                self.alarm = True
                raise AlarmTripped(
                    f"alarm tripped after {self.failed_cracks} failed attempts"
                )
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

    # --- data-oracle API (used by the search/sort missions) ------------
    def size(self) -> int:
        """Length of the dataset attached to this mission."""
        if self.dataset is None:
            raise AccessDenied("no dataset on this host")
        return len(self.dataset)

    def at(self, index: int) -> Any:
        """Read one element of the dataset (cheap, so you must search smartly)."""
        if self.dataset is None:
            raise AccessDenied("no dataset on this host")
        return self.dataset[index]

    def submit(self, answer: Any) -> None:
        """Send your answer to the mission handler."""
        self.submitted = answer
        self.has_submitted = True

    # --- wiring ---------------------------------------------------------
    def api(self, extra: dict[str, Any] | None = None) -> dict[str, Callable[..., Any]]:
        names = (
            "whoami", "scan", "links", "connect", "hint", "crack",
            "ls", "cat", "size", "at", "submit",
        )
        functions: dict[str, Any] = {name: getattr(self, name) for name in names}
        functions["AccessDenied"] = AccessDenied
        if extra:
            functions.update(extra)
        return functions
