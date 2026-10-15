"""Mission definitions. Each mission builds a fresh network and checks the result."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .game import HOME, GameSession
from .network import Network, Node


@dataclass(frozen=True)
class Mission:
    id: int
    title: str
    briefing: str
    max_cycles: int
    build: Callable[[], Network]
    check: Callable[[GameSession], tuple[bool, str]]
    template: str


def _caesar(text: str, shift: int) -> str:
    out = []
    for ch in text:
        if "A" <= ch <= "Z":
            out.append(chr((ord(ch) - 65 + shift) % 26 + 65))
        else:
            out.append(ch)
    return "".join(out)


# --- Mission 1: map the network ---------------------------------------------

def _build_m1() -> Network:
    net = Network()
    for host in (HOME, "relay-a", "relay-b", "cam-03", "printer", "db-core",
                 "mail", "backup", "vault-x", "lab-07"):
        net.add(Node(host))
    for a, b in [(HOME, "relay-a"), (HOME, "relay-b"), ("relay-a", "cam-03"),
                 ("relay-a", "printer"), ("relay-b", "mail"), ("mail", "db-core"),
                 ("db-core", "backup"), ("backup", "vault-x"), ("cam-03", "lab-07")]:
        net.link(a, b)
    return net


def _check_m1(s: GameSession) -> tuple[bool, str]:
    if not s.has_submitted:
        return False, "nothing submitted; call submit(...) with your host list"
    expected = s.network.reachable_from(HOME)
    try:
        got = sorted(s.submitted)
    except TypeError:
        return False, "submit a list of hostnames"
    if got == expected:
        return True, f"network mapped: {len(expected)} hosts"
    missing = len(set(expected) - set(got))
    extra = len(set(got) - set(expected))
    return False, f"map incomplete: {missing} missing, {extra} wrong"


# --- Mission 2: weak PIN -------------------------------------------------------

_M2_SECRET = "OPERATOR-ID: ghost_07"


def _build_m2() -> Network:
    net = Network()
    net.add(Node(HOME))
    net.add(Node("relay", files={"readme.txt": "gateway gw-01 guards the operator file"}))
    net.add(Node(
        "gw-01",
        password="7337",
        hint="4-digit PIN. It reads the same backwards. Digit sum is 20. Starts with 7.",
        files={"operator.txt": _M2_SECRET},
    ))
    net.link(HOME, "relay")
    net.link("relay", "gw-01")
    return net


def _check_m2(s: GameSession) -> tuple[bool, str]:
    if not s.has_submitted:
        return False, "nothing submitted; find operator.txt and submit its contents"
    if str(s.submitted).strip() == _M2_SECRET:
        return True, f"gateway cracked in {s.crack_attempts} attempts"
    return False, "that's not the operator file"


# --- Mission 3: intercepted message -----------------------------------------

_M3_PLAIN = "DARKNODE: THE KEY IS UNDER THE OLD SERVER"


def _build_m3() -> Network:
    net = Network()
    net.add(Node(HOME))
    net.add(Node("relay"))
    net.add(Node("archive", files={
        "msg.enc": _caesar(_M3_PLAIN, 7),
        "note.txt": "every message starts with the word DARKNODE",
    }))
    net.link(HOME, "relay")
    net.link("relay", "archive")
    return net


def _check_m3(s: GameSession) -> tuple[bool, str]:
    if not s.has_submitted:
        return False, "nothing submitted; submit the decrypted text"
    if str(s.submitted).strip().upper() == _M3_PLAIN:
        return True, "message decrypted"
    return False, "decryption is wrong"


MISSIONS: list[Mission] = [
    Mission(
        id=1,
        title="First Contact",
        briefing=(
            "You are on 'home'. Map every host reachable from here and\n"
            "submit the list of hostnames. Tip: scan() only shows direct links,\n"
            "so you need to keep scanning what you find."
        ),
        max_cycles=5_000,
        build=_build_m1,
        check=_check_m1,
        template=(
            "# Mission 1: First Contact\n"
            "# Find every host reachable from home and submit them as a list.\n\n"
            "print(scan())\n"
        ),
    ),
    Mission(
        id=2,
        title="Weak PIN",
        briefing=(
            "Gateway 'gw-01' hides the operator's ID in operator.txt.\n"
            "It is locked with a PIN. Read its hint, crack it, connect,\n"
            "and submit the contents of operator.txt.\n"
            "The terminal is slow: trying all 10000 PINs won't fit the CPU budget."
        ),
        max_cycles=10_000,
        build=_build_m2,
        check=_check_m2,
        template=(
            "# Mission 2: Weak PIN\n"
            "# Reach gw-01, crack it, read operator.txt and submit it.\n\n"
            "print(scan())          # what is linked to home?\n"
            "connect('relay')\n"
            "print(scan())\n"
            "print(hint('gw-01'))\n"
        ),
    ),
    Mission(
        id=3,
        title="Intercepted",
        briefing=(
            "An encrypted message sits on 'archive'. The shift is unknown,\n"
            "but there is a note that may help. Decrypt it and submit the text."
        ),
        max_cycles=20_000,
        build=_build_m3,
        check=_check_m3,
        template=(
            "# Mission 3: Intercepted\n"
            "# Decrypt msg.enc on archive and submit the plain text.\n\n"
            "scan()\n"
            "connect('relay')\n"
            "scan()\n"
            "connect('archive')\n"
            "print(ls())\n"
        ),
    ),
]


def get_mission(mission_id: int) -> Mission:
    for mission in MISSIONS:
        if mission.id == mission_id:
            return mission
    raise KeyError(f"no mission #{mission_id}")
