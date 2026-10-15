"""The fictional network the player explores.

Everything here is made up: hosts, passwords and files exist only inside the
game. A network is a graph of nodes; some nodes are locked behind a password
puzzle, and links can carry a "latency" cost used by the shortest-path mission.
"""

from __future__ import annotations

import heapq
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
    """An undirected graph of nodes with optional edge weights."""

    def __init__(self) -> None:
        self._nodes: dict[str, Node] = {}
        self._links: dict[str, set[str]] = {}
        self._weights: dict[tuple[str, str], int] = {}

    def add(self, node: Node) -> Node:
        if node.hostname in self._nodes:
            raise ValueError(f"duplicate host: {node.hostname}")
        self._nodes[node.hostname] = node
        self._links[node.hostname] = set()
        return node

    def link(self, a: str, b: str, weight: int = 1) -> None:
        for host in (a, b):
            if host not in self._nodes:
                raise KeyError(f"unknown host: {host}")
        self._links[a].add(b)
        self._links[b].add(a)
        self._weights[(a, b)] = weight
        self._weights[(b, a)] = weight

    def node(self, hostname: str) -> Node:
        try:
            return self._nodes[hostname]
        except KeyError:
            raise KeyError(f"unknown host: {hostname}") from None

    def neighbors(self, hostname: str) -> list[str]:
        return sorted(self._links[self.node(hostname).hostname])

    def weight(self, a: str, b: str) -> int:
        return self._weights.get((a, b), 1)

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

    def shortest_cost(self, start: str, goal: str) -> int | None:
        """Dijkstra cost of the cheapest route (used to check mission answers)."""
        best = {start: 0}
        heap = [(0, start)]
        while heap:
            cost, host = heapq.heappop(heap)
            if host == goal:
                return cost
            if cost > best.get(host, float("inf")):
                continue
            for nxt in self.neighbors(host):
                nc = cost + self.weight(host, nxt)
                if nc < best.get(nxt, float("inf")):
                    best[nxt] = nc
                    heapq.heappush(heap, (nc, nxt))
        return best.get(goal)
