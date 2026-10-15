"""Mission mechanics: networks, datasets, answer checks and budgets.

All player-facing prose (titles, briefings, concept cards, hints, templates and
the success/failure lines) lives in ``darknode/locales/*.json`` keyed by mission
id. A checker returns ``(success, key, params)`` where ``key`` is an i18n key
under ``check.*`` that the front-end formats in the player's language.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass, field
from typing import Any, Callable

from .game import HOME, GameSession
from .network import Network, Node

CheckResult = tuple[bool, str, dict]


# --- cipher helpers used to build mission data ------------------------------

def caesar(text: str, shift: int) -> str:
    out = []
    for ch in text:
        if "A" <= ch <= "Z":
            out.append(chr((ord(ch) - 65 + shift) % 26 + 65))
        elif "a" <= ch <= "z":
            out.append(chr((ord(ch) - 97 + shift) % 26 + 97))
        else:
            out.append(ch)
    return "".join(out)


def vigenere(text: str, key: str, decrypt: bool = False) -> str:
    out = []
    ki = 0
    for ch in text:
        if "A" <= ch <= "Z":
            k = ord(key[ki % len(key)].upper()) - 65
            if decrypt:
                k = -k
            out.append(chr((ord(ch) - 65 + k) % 26 + 65))
            ki += 1
        else:
            out.append(ch)
    return "".join(out)


def xor_b64(text: str, key: str) -> str:
    kb = key.encode()
    data = bytes(b ^ kb[i % len(kb)] for i, b in enumerate(text.encode()))
    return base64.b64encode(data).decode()


def toy_hash(text: str) -> int:
    """A deliberately tiny, insecure hash the crypto act asks players to rebuild."""
    h = 0
    for ch in text:
        h = (h * 31 + ord(ch)) % 100003
    return h


# --- mission model ----------------------------------------------------------

@dataclass(frozen=True)
class Mission:
    id: int
    act: int
    concept: str                       # short tag for UI grouping / help card
    max_cycles: int
    reward: int
    build: Callable[[], Network]
    check: Callable[[GameSession], CheckResult]
    data: Callable[[], list] | None = None
    crack_limit: int | None = None

    def new_session(self) -> GameSession:
        return GameSession(
            self.build(),
            dataset=self.data() if self.data else None,
            crack_limit=self.crack_limit,
        )


def _home(files: dict[str, str] | None = None) -> Node:
    return Node(HOME, files=files or {})


def _as_list(value: Any) -> list | None:
    try:
        return list(value)
    except TypeError:
        return None


# ===========================================================================
# ACT 1 — ORIENTATION
# ===========================================================================

def _b1() -> Network:
    net = Network()
    net.add(_home({"welcome.txt": "Type `submit(\"ONLINE\")` to report in."}))
    return net


def _c1(s: GameSession) -> CheckResult:
    if not s.has_submitted:
        return False, "check.empty", {}
    if str(s.submitted).strip().upper() == "ONLINE":
        return True, "check.m1.ok", {}
    return False, "check.m1.no", {"got": str(s.submitted)[:40]}


def _b2() -> Network:
    return _home_net()


def _home_net(files: dict[str, str] | None = None) -> Network:
    net = Network()
    net.add(_home(files or {}))
    return net


def _c2(s: GameSession) -> CheckResult:
    if not s.has_submitted:
        return False, "check.empty", {}
    try:
        got = int(s.submitted)
    except (TypeError, ValueError):
        return False, "check.m2.nan", {}
    return (True, "check.m2.ok", {}) if got == 96 else (False, "check.m2.no", {"got": got})


def _c3(s: GameSession) -> CheckResult:
    if not s.has_submitted:
        return False, "check.empty", {}
    return (True, "check.m3.ok", {}) if str(s.submitted).strip() == "OMNI-0042" \
        else (False, "check.m3.no", {"got": str(s.submitted)[:40]})


def _c4(s: GameSession) -> CheckResult:
    if not s.has_submitted:
        return False, "check.empty", {}
    # rank 7 >= 5 and not flagged (False) -> GRANT
    return (True, "check.m4.ok", {}) if str(s.submitted).strip().upper() == "GRANT" \
        else (False, "check.m4.no", {})


# ===========================================================================
# ACT 2 — LOOPS & COLLECTIONS
# ===========================================================================

def _c5(s: GameSession) -> CheckResult:
    if not s.has_submitted:
        return False, "check.empty", {}
    return (True, "check.m5.ok", {}) if s.submitted == 2550 \
        else (False, "check.m5.no", {"got": s.submitted})


_M6_PORTS = """\
port 22 open
port 23 closed
port 80 open
port 139 closed
port 443 open
port 445 closed
port 3306 open
port 8080 open
port 9999 closed"""

_M6_OPEN = sorted([22, 80, 443, 3306, 8080])


def _b6() -> Network:
    return _home_net({"scan.txt": _M6_PORTS})


def _c6(s: GameSession) -> CheckResult:
    if not s.has_submitted:
        return False, "check.empty", {}
    got = _as_list(s.submitted)
    if got is None:
        return False, "check.m6.type", {}
    try:
        got = sorted(int(x) for x in got)
    except (TypeError, ValueError):
        return False, "check.m6.type", {}
    return (True, "check.m6.ok", {"n": len(_M6_OPEN)}) if got == _M6_OPEN \
        else (False, "check.m6.no", {})


_M7_SECRET = "OPERATOR-ID: ghost_07"


def _b7() -> Network:
    net = Network()
    net.add(_home())
    net.add(Node("relay", files={"readme.txt": "gateway gw-01 guards the operator file"}))
    net.add(Node(
        "gw-01",
        password="7337",
        hint="4-digit PIN. Reads the same backwards. Digits sum to 20. Starts with 7.",
        files={"operator.txt": _M7_SECRET},
    ))
    net.link(HOME, "relay")
    net.link("relay", "gw-01")
    return net


def _c7(s: GameSession) -> CheckResult:
    if s.alarm:
        return False, "check.m7.alarm", {}
    if not s.has_submitted:
        return False, "check.empty", {}
    if str(s.submitted).strip() == _M7_SECRET:
        return True, "check.m7.ok", {"n": s.crack_attempts}
    return False, "check.m7.no", {}


_M8_LOG = """\
user=alice action=login
user=bob action=login
user=alice action=read
user=carol action=login
user=alice action=read
user=bob action=read
user=alice action=write
user=carol action=read
user=alice action=login"""
# alice: 5, bob: 2, carol: 2  -> busiest = alice


def _b8() -> Network:
    return _home_net({"events.log": _M8_LOG})


def _c8(s: GameSession) -> CheckResult:
    if not s.has_submitted:
        return False, "check.empty", {}
    return (True, "check.m8.ok", {}) if str(s.submitted).strip() == "alice" \
        else (False, "check.m8.no", {"got": str(s.submitted)[:40]})


_M9_A = "alpha bravo delta echo foxtrot golf hotel"
_M9_B = "bravo charlie delta foxtrot india hotel juliet"
_M9_BOTH = sorted(set(_M9_A.split()) & set(_M9_B.split()))  # bravo delta foxtrot hotel


def _b9() -> Network:
    return _home_net({"sensor-a.txt": _M9_A, "sensor-b.txt": _M9_B})


def _c9(s: GameSession) -> CheckResult:
    if not s.has_submitted:
        return False, "check.empty", {}
    got = _as_list(s.submitted)
    if got is None:
        return False, "check.m9.type", {}
    return (True, "check.m9.ok", {"n": len(_M9_BOTH)}) if sorted(map(str, got)) == _M9_BOTH \
        else (False, "check.m9.no", {})


# ===========================================================================
# ACT 3 — FUNCTIONS & TEXT
# ===========================================================================

_M10_BADGES = ["1407", "2230", "9981", "3031", "7000", "1234", "7770", "0000"]
# valid if digit sum % 7 == 0: 1407->12 no;2230->7 yes;9981->27 no;3031->7 yes;
# 7000->7 yes;1234->10 no;7770->21 yes;0000->0 yes  => 5 valid


def _b10() -> Network:
    return _home_net({"badges.txt": "\n".join(_M10_BADGES)})


def _c10(s: GameSession) -> CheckResult:
    if not s.has_submitted:
        return False, "check.empty", {}
    try:
        got = int(s.submitted)
    except (TypeError, ValueError):
        return False, "check.m10.type", {}
    return (True, "check.m10.ok", {}) if got == 5 else (False, "check.m10.no", {"got": got})


_M11_RECORD = "  NAME :  Ghost ; ROLE: operator ; CLEAR:  9  "


def _b11() -> Network:
    return _home_net({"record.txt": _M11_RECORD})


def _c11(s: GameSession) -> CheckResult:
    if not s.has_submitted:
        return False, "check.empty", {}
    return (True, "check.m11.ok", {}) if str(s.submitted).strip() == "Ghost" \
        else (False, "check.m11.no", {"got": str(s.submitted)[:40]})


_M12_PLAIN = "KEY-UNDER-THE-OLD-SERVER"
_M12_SCRAMBLED = _M12_PLAIN[::-1]


def _b12() -> Network:
    return _home_net({"cipher0.txt": _M12_SCRAMBLED,
                      "note.txt": "someone reversed it character by character"})


def _c12(s: GameSession) -> CheckResult:
    if not s.has_submitted:
        return False, "check.empty", {}
    return (True, "check.m12.ok", {}) if str(s.submitted).strip() == _M12_PLAIN \
        else (False, "check.m12.no", {})


def _c13(s: GameSession) -> CheckResult:
    if not s.has_submitted:
        return False, "check.empty", {}
    try:
        got = int(s.submitted)
    except (TypeError, ValueError):
        return False, "check.m13.type", {}
    return (True, "check.m13.ok", {}) if got == 6765 else (False, "check.m13.no", {"got": got})


_M14_NUMS = [3, 8, 11, 2, 7, 4, 15, 6, 9, 20, 1, 13]
_M14_EXPECT = sorted(n * n for n in _M14_NUMS if n % 2 == 1)  # squares of odds, sorted


def _b14() -> Network:
    return _home_net({"nums.txt": " ".join(map(str, _M14_NUMS))})


def _c14(s: GameSession) -> CheckResult:
    if not s.has_submitted:
        return False, "check.empty", {}
    got = _as_list(s.submitted)
    if got is None:
        return False, "check.m14.type", {}
    try:
        got = sorted(int(x) for x in got)
    except (TypeError, ValueError):
        return False, "check.m14.type", {}
    return (True, "check.m14.ok", {}) if got == _M14_EXPECT else (False, "check.m14.no", {})


# ===========================================================================
# ACT 4 — ALGORITHMS
# ===========================================================================

_M15_RECORDS = [
    ("relay-a", 40), ("db-core", 95), ("cam-03", 40),
    ("vault-x", 95), ("mail", 70), ("backup", 55),
]
# sort by score desc, then name asc:
_M15_EXPECT = [name for name, _ in
               sorted(_M15_RECORDS, key=lambda r: (-r[1], r[0]))]


def _b15() -> Network:
    lines = "\n".join(f"{name} {score}" for name, score in _M15_RECORDS)
    return _home_net({"targets.txt": lines})


def _c15(s: GameSession) -> CheckResult:
    if not s.has_submitted:
        return False, "check.empty", {}
    got = _as_list(s.submitted)
    if got is None:
        return False, "check.m15.type", {}
    return (True, "check.m15.ok", {}) if list(map(str, got)) == _M15_EXPECT \
        else (False, "check.m15.no", {})


_M16_N = 100_000
_M16_TARGET = 61_803 * 2 + 7  # value present at index 61803


def _m16_data() -> list:
    return [i * 2 + 7 for i in range(_M16_N)]


def _b16() -> Network:
    return _home_net({"index.txt": f"{_M16_N} sorted records. Target value: {_M16_TARGET}."})


def _c16(s: GameSession) -> CheckResult:
    if not s.has_submitted:
        return False, "check.empty", {}
    try:
        got = int(s.submitted)
    except (TypeError, ValueError):
        return False, "check.m16.type", {}
    return (True, "check.m16.ok", {}) if got == 61_803 else (False, "check.m16.no", {"got": got})


def _b17() -> Network:
    net = Network()
    for host in (HOME, "relay-a", "relay-b", "cam-03", "printer", "db-core",
                 "mail", "backup", "vault-x", "lab-07"):
        net.add(Node(host))
    for a, b in [(HOME, "relay-a"), (HOME, "relay-b"), ("relay-a", "cam-03"),
                 ("relay-a", "printer"), ("relay-b", "mail"), ("mail", "db-core"),
                 ("db-core", "backup"), ("backup", "vault-x"), ("cam-03", "lab-07")]:
        net.link(a, b)
    return net


def _c17(s: GameSession) -> CheckResult:
    if not s.has_submitted:
        return False, "check.empty", {}
    expected = s.network.reachable_from(HOME)
    got = _as_list(s.submitted)
    if got is None:
        return False, "check.m17.type", {}
    got = sorted(map(str, got))
    if got == expected:
        return True, "check.m17.ok", {"n": len(expected)}
    missing = len(set(expected) - set(got))
    extra = len(set(got) - set(expected))
    return False, "check.m17.no", {"missing": missing, "extra": extra}


def _b18() -> Network:
    net = Network()
    for host in (HOME, "a", "b", "c", "d", "e", "vault"):
        net.add(Node(host))
    for x, y in [(HOME, "a"), (HOME, "b"), ("a", "c"), ("b", "c"),
                 ("c", "d"), ("d", "vault"), ("b", "e")]:
        net.link(x, y)
    return net


def _c18(s: GameSession) -> CheckResult:
    if not s.has_submitted:
        return False, "check.empty", {}
    path = _as_list(s.submitted)
    if path is None or not path:
        return False, "check.m18.type", {}
    path = [str(p) for p in path]
    if path[0] != HOME or path[-1] != "vault":
        return False, "check.m18.ends", {}
    for a, b in zip(path, path[1:]):
        if b not in s.network.neighbors(a):
            return False, "check.m18.broken", {"a": a, "b": b}
    return True, "check.m18.ok", {"hops": len(path) - 1}


def _b19() -> Network:
    net = Network()
    for host in (HOME, "n1", "n2", "n3", "n4", "core"):
        net.add(Node(host))
    for a, b, w in [(HOME, "n1", 4), (HOME, "n2", 1), ("n2", "n3", 2),
                    ("n1", "core", 1), ("n3", "n1", 1), ("n3", "n4", 5),
                    ("n4", "core", 1)]:
        net.link(a, b, w)
    # cheapest home->core: home-n2(1)-n3(2)-n1(1)-core(1) = 5
    return net


def _c19(s: GameSession) -> CheckResult:
    if not s.has_submitted:
        return False, "check.empty", {}
    try:
        got = int(s.submitted)
    except (TypeError, ValueError):
        return False, "check.m19.type", {}
    best = s.network.shortest_cost(HOME, "core")
    return (True, "check.m19.ok", {"cost": best}) if got == best \
        else (False, "check.m19.no", {"got": got})


# ===========================================================================
# ACT 5 — CRYPTOGRAPHY & FORENSICS
# ===========================================================================

_M20_PLAIN = "OMNIGRID INTERNAL THE KEY IS UNDER THE OLD SERVER"


def _b20() -> Network:
    net = Network()
    net.add(_home())
    net.add(Node("archive", files={
        "msg.enc": caesar(_M20_PLAIN, 7),
        "note.txt": "every internal memo starts with the word OMNIGRID",
    }))
    net.link(HOME, "archive")
    return net


def _c20(s: GameSession) -> CheckResult:
    if not s.has_submitted:
        return False, "check.empty", {}
    return (True, "check.m20.ok", {}) if str(s.submitted).strip().upper() == _M20_PLAIN \
        else (False, "check.m20.no", {})


_M21_PLAIN = "MOVE THE PAYLOAD TO DOCK SEVEN AT MIDNIGHT"
_M21_KEY = "RAVEN"


def _b21() -> Network:
    net = Network()
    net.add(_home())
    net.add(Node("archive", files={
        "msg.vig": vigenere(_M21_PLAIN, _M21_KEY),
        "key.txt": f"Vigenere key: {_M21_KEY}",
    }))
    net.link(HOME, "archive")
    return net


def _c21(s: GameSession) -> CheckResult:
    if not s.has_submitted:
        return False, "check.empty", {}
    return (True, "check.m21.ok", {}) if str(s.submitted).strip().upper() == _M21_PLAIN \
        else (False, "check.m21.no", {})


_M22_PLAIN = "ACCESS CODE IS FALCON NINE NINE"
_M22_KEY = "k3y"


def _b22() -> Network:
    net = Network()
    net.add(_home())
    net.add(Node("relay", files={
        "msg.b64": xor_b64(_M22_PLAIN, _M22_KEY),
        "key.txt": f"xored with the repeating key: {_M22_KEY}",
    }))
    net.link(HOME, "relay")
    return net


def _c22(s: GameSession) -> CheckResult:
    if not s.has_submitted:
        return False, "check.empty", {}
    return (True, "check.m22.ok", {}) if str(s.submitted).strip().upper() == _M22_PLAIN \
        else (False, "check.m22.no", {})


_M23_WORDS = ["hunter2", "letmein", "falcon99", "swordfish", "trustno1",
              "zxcvbn", "ghost07", "password", "qwerty", "dragon"]
_M23_TARGET_WORD = "falcon99"
_M23_TARGET_HASH = toy_hash(_M23_TARGET_WORD)


def _b23() -> Network:
    wordlist_b64 = base64.b64encode("\n".join(_M23_WORDS).encode()).decode()
    return _home_net({
        "shadow.txt": f"admin:{_M23_TARGET_HASH}",
        "wordlist.b64": wordlist_b64,
        "scheme.txt": "hash: h = 0; for each char: h = (h*31 + ord(char)) % 100003",
    })


def _c23(s: GameSession) -> CheckResult:
    if not s.has_submitted:
        return False, "check.empty", {}
    return (True, "check.m23.ok", {}) if str(s.submitted).strip() == _M23_TARGET_WORD \
        else (False, "check.m23.no", {})


_M24_LOG = """\
10.0.0.5 GET /index 200
10.0.0.9 GET /login 200
10.0.0.5 GET /vault 403
203.0.113.7 GET /login 200
203.0.113.7 GET /vault 403
203.0.113.7 GET /vault 403
203.0.113.7 GET /admin 403
203.0.113.7 GET /vault 200
10.0.0.9 GET /index 200
203.0.113.7 GET /secrets 200"""
# intruder = IP with the most 403 (denied) events: 203.0.113.7 (3)


def _b24() -> Network:
    return _home_net({"access.log": _M24_LOG})


def _c24(s: GameSession) -> CheckResult:
    if not s.has_submitted:
        return False, "check.empty", {}
    return (True, "check.m24.ok", {}) if str(s.submitted).strip() == "203.0.113.7" \
        else (False, "check.m24.no", {"got": str(s.submitted)[:40]})


_M25_PLAIN = "OMNIGRID MAINFRAME ROOT SHELL UNLOCKED GG"
_M25_KEY = "DARK"
_M25_PIN = "12347"  # 5 strictly-increasing non-zero digits summing to 17


def _b25() -> Network:
    net = Network()
    for host in (HOME, "edge", "junction", "mainframe"):
        net.add(Node(host) if host != "mainframe" else Node(
            "mainframe",
            password=_M25_PIN,
            hint="5-digit PIN, strictly increasing digits, digits sum to 17, no zeros.",
            files={
                "payload.vig": vigenere(_M25_PLAIN, _M25_KEY),
                "key.txt": f"Vigenere key: {_M25_KEY}",
            },
        ))
    # weighted so the cheap route matters; all routes reach mainframe
    for a, b, w in [(HOME, "edge", 2), (HOME, "junction", 5),
                    ("edge", "junction", 1), ("junction", "mainframe", 3),
                    ("edge", "mainframe", 9)]:
        net.link(a, b, w)
    return net


def _c25(s: GameSession) -> CheckResult:
    if s.alarm:
        return False, "check.m25.alarm", {}
    if not s.has_submitted:
        return False, "check.empty", {}
    return (True, "check.m25.ok", {}) if str(s.submitted).strip().upper() == _M25_PLAIN \
        else (False, "check.m25.no", {})


# ---------------------------------------------------------------------------

def _m(id, act, concept, cycles, reward, build, check, **kw) -> Mission:
    return Mission(id=id, act=act, concept=concept, max_cycles=cycles,
                   reward=reward, build=build, check=check, **kw)


MISSIONS: list[Mission] = [
    _m(1, 1, "print", 500, 40, _b1, _c1),
    _m(2, 1, "arithmetic", 500, 40, _b2, _c2),
    _m(3, 1, "strings", 500, 40, _home_net, _c3),
    _m(4, 1, "booleans", 500, 50, _home_net, _c4),
    _m(5, 2, "for-range", 2_000, 50, _home_net, _c5),
    _m(6, 2, "lists", 2_000, 60, _b6, _c6),
    _m(7, 2, "nested-loops", 9_000, 80, _b7, _c7, crack_limit=50),
    _m(8, 2, "dicts", 3_000, 70, _b8, _c8),
    _m(9, 2, "sets", 3_000, 70, _b9, _c9),
    _m(10, 3, "functions", 3_000, 80, _b10, _c10),
    _m(11, 3, "string-methods", 2_000, 80, _b11, _c11),
    _m(12, 3, "slicing", 2_000, 80, _b12, _c12),
    _m(13, 3, "recursion", 2_000, 100, _home_net, _c13),
    _m(14, 3, "comprehensions", 3_000, 90, _b14, _c14),
    _m(15, 4, "sorting", 3_000, 100, _b15, _c15),
    _m(16, 4, "binary-search", 400, 140, _b16, _c16, data=_m16_data),
    _m(17, 4, "bfs", 6_000, 120, _b17, _c17),
    _m(18, 4, "dfs-path", 6_000, 120, _b18, _c18),
    _m(19, 4, "shortest-path", 8_000, 150, _b19, _c19),
    _m(20, 5, "caesar", 20_000, 140, _b20, _c20),
    _m(21, 5, "vigenere", 20_000, 160, _b21, _c21),
    _m(22, 5, "xor", 20_000, 170, _b22, _c22),
    _m(23, 5, "toy-hash", 15_000, 180, _b23, _c23),
    _m(24, 5, "log-parsing", 8_000, 180, _b24, _c24),
    _m(25, 5, "final", 40_000, 300, _b25, _c25, crack_limit=200),
]


def get_mission(mission_id: int) -> Mission:
    for mission in MISSIONS:
        if mission.id == mission_id:
            return mission
    raise KeyError(f"no mission #{mission_id}")
