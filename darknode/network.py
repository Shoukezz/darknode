"""The fictional network the player explores.

Everything here is made up: hosts, passwords and files exist only inside
the game. A network is a graph of nodes; some nodes are locked behind a
password puzzle.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field


@dataclass
class Node:
    """A single host in the network."""

    hostname: str
    password: str | None = None  # None means the node is open
    hint: str = ""
    files: dict[str, str] = field(default_factory=dict)
    cracked: bool = False

    @property
    def locked(self) -> bool:
        return self.password is not None and not self.cracked


class Network:
    """An undirected graph of nodes."""

    def __init__(self) -> None:
        self._nodes: dict[str, Node] = {}
        self._links: dict[str, set[str]] = {}

    def add(self, node: Node) -> Node:
        if node.hostname in self._nodes:
            raise ValueError(f"duplicate host: {node.hostname}")
        self._nodes[node.hostname] = node
        self._links[node.hostname] = set()
        return node

    def link(self, a: str, b: str) -> None:
        for host in (a, b):
            if host not in self._nodes:
                raise KeyError(f"unknown host: {host}")
        self._links[a].add(b)
        self._links[b].add(a)

    def node(self, hostname: str) -> Node:
        try:
            return self._nodes[hostname]
        except KeyError:
            raise KeyError(f"unknown host: {hostname}") from None

    def neighbors(self, hostname: str) -> list[str]:
        return sorted(self._links[self.node(hostname).hostname])

    def hosts(self) -> list[str]:
        return sorted(self._nodes)

    def reachable_from(self, start: str) -> list[str]:
        """All hosts reachable from ``start`` (used to check mission answers)."""
        seen = {start}
        queue = deque([start])
        while queue:
            for nxt in self.neighbors(queue.popleft()):
                if nxt not in seen:
                    seen.add(nxt)
                    queue.append(nxt)
        return sorted(seen)
