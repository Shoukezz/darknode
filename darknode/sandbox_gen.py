"""Random network generator for free-play mode (unlocked after the campaign).

The RNG lives here, in the engine, so the player sandbox stays deterministic and
``random`` is never exposed to player scripts. Each seed is a fresh puzzle: map
the whole network, or crack a gateway and lift the flag behind it. The network is
rebuilt deterministically from the seed on every attempt, so a seed is replayable.
"""

from __future__ import annotations

import random
import string

from .game import HOME, GameSession
from .missions import CheckResult, Mission
from .network import Network, Node

_WORDS = ["relay", "node", "cam", "gw", "db", "lab", "mail", "cache", "edge",
          "proxy", "vault", "sensor", "router", "host", "kiosk", "beacon"]


def _clamp_size(size: int) -> int:
    return max(5, min(size, 16))


def _palindrome_pin(rng: random.Random) -> tuple[str, str]:
    a, b = rng.randint(1, 9), rng.randint(0, 9)
    pin = f"{a}{b}{b}{a}"
    digit_sum = 2 * (a + b)
    hint = (f"4-digit PIN, reads the same backwards, digits sum to {digit_sum}, "
            f"starts with {a}.")
    return pin, hint


def _blueprint(seed: int, size: int) -> dict:
    """Deterministic description of the puzzle for a seed (names, edges, flag)."""
    rng = random.Random(seed)
    size = _clamp_size(size)
    used = {HOME}
    names = [HOME]
    while len(names) < size:
        name = f"{rng.choice(_WORDS)}-{rng.randint(10, 99)}"
        if name not in used:
            used.add(name)
            names.append(name)

    edges = [(names[i], names[rng.randint(0, i - 1)]) for i in range(1, len(names))]
    for _ in range(rng.randint(1, size // 2)):
        a, b = rng.sample(names, 2)
        edges.append((a, b))

    flag_mode = seed % 2 == 1
    bp = {"names": names, "edges": edges, "flag_mode": flag_mode}
    if flag_mode:
        bp["gate"] = names[-1]
        bp["flag"] = "FLAG{" + "".join(
            rng.choice(string.ascii_uppercase + string.digits) for _ in range(8)) + "}"
        bp["pin"], bp["hint"] = _palindrome_pin(rng)
    return bp


def _network(bp: dict) -> Network:
    net = Network()
    for name in bp["names"]:
        net.add(Node(name))
    for a, b in bp["edges"]:
        if b not in net.neighbors(a):
            net.link(a, b)
    if bp["flag_mode"]:
        node = net.node(bp["gate"])
        node.password = bp["pin"]
        node.hint = bp["hint"]
        node.files["flag.txt"] = bp["flag"]
    return net


def generate(seed: int, size: int = 8) -> Mission:
    """Build a replayable free-play mission for ``seed``."""
    size = _clamp_size(size)
    bp = _blueprint(seed, size)

    if bp["flag_mode"]:
        flag = bp["flag"]

        def check(s: GameSession, _flag=flag) -> CheckResult:
            if not s.has_submitted:
                return False, "check.empty", {}
            return (True, "sandbox.flag_ok", {}) if str(s.submitted).strip() == _flag \
                else (False, "sandbox.flag_no", {})
    else:
        def check(s: GameSession) -> CheckResult:
            if not s.has_submitted:
                return False, "check.empty", {}
            expected = s.network.reachable_from(HOME)
            try:
                got = sorted(map(str, s.submitted))
            except TypeError:
                return False, "sandbox.map_no", {}
            if got == expected:
                return True, "sandbox.map_ok", {"n": len(expected)}
            missing = len(set(expected) - set(got))
            extra = len(set(got) - set(expected))
            return False, "sandbox.map_partial", {"missing": missing, "extra": extra}

    budget = 2_000 + size * 600
    return Mission(
        id=0, act=0, concept="sandbox", max_cycles=budget, reward=0,
        build=lambda bp=bp: _network(bp), check=check,
        crack_limit=200 if bp["flag_mode"] else None,
    )
