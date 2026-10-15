"""Tests for DarkNode. Run with: python -m unittest   (or: pytest)"""

import tempfile
import unittest
from pathlib import Path

from darknode.game import AccessDenied, GameSession
from darknode.missions import MISSIONS, get_mission
from darknode.network import Network, Node
from darknode.runner import play
from darknode.sandbox import run_script
from darknode.terminal import Terminal

# Reference solutions: proof that every mission is solvable within its budget.
SOLUTIONS = {
    1: """
seen = ['home']
queue = ['home']
while queue:
    host = queue.pop(0)
    for nxt in scan(host):
        if nxt not in seen:
            seen.append(nxt)
            queue.append(nxt)
submit(seen)
""",
    2: """
scan()
connect('relay')
scan()
for a in range(10):
    for b in range(10):
        pin = f"{a}{b}{b}{a}"
        if crack('gw-01', pin):
            connect('gw-01')
            submit(cat('operator.txt'))
""",
    3: """
scan(); connect('relay'); scan(); connect('archive')
msg = cat('msg.enc')
for shift in range(26):
    text = ''.join(chr((ord(c) - 65 - shift) % 26 + 65) if c.isalpha() else c for c in msg)
    if text.startswith('DARKNODE'):
        submit(text)
""",
}


class NetworkTests(unittest.TestCase):
    def test_links_are_bidirectional(self):
        net = Network()
        net.add(Node("a"))
        net.add(Node("b"))
        net.link("a", "b")
        self.assertEqual(net.neighbors("b"), ["a"])

    def test_reachable_ignores_isolated_hosts(self):
        net = Network()
        for h in ("a", "b", "c"):
            net.add(Node(h))
        net.link("a", "b")
        self.assertEqual(net.reachable_from("a"), ["a", "b"])

    def test_duplicate_host_rejected(self):
        net = Network()
        net.add(Node("a"))
        with self.assertRaises(ValueError):
            net.add(Node("a"))


class SessionTests(unittest.TestCase):
    def setUp(self):
        self.session = GameSession(get_mission(2).build())

    def test_cannot_connect_to_undiscovered_host(self):
        with self.assertRaises(AccessDenied):
            self.session.connect("relay")

    def test_locked_host_needs_crack(self):
        self.session.scan()
        self.session.connect("relay")
        self.session.scan()
        with self.assertRaises(AccessDenied):
            self.session.connect("gw-01")
        self.assertFalse(self.session.crack("gw-01", "0000"))
        self.assertTrue(self.session.crack("gw-01", "7337"))
        self.session.connect("gw-01")
        self.assertIn("operator.txt", self.session.ls())


class SandboxTests(unittest.TestCase):
    def test_print_is_captured(self):
        result = run_script("print('hi', 1)", {})
        self.assertTrue(result.ok)
        self.assertEqual(result.output, ["hi 1"])

    def test_forbidden_import(self):
        result = run_script("import os", {})
        self.assertFalse(result.ok)
        self.assertIn("not available", result.error)

    def test_allowed_import(self):
        self.assertTrue(run_script("import math\nx = math.sqrt(4)", {}).ok)

    def test_open_is_not_available(self):
        result = run_script("open('x.txt')", {})
        self.assertFalse(result.ok)
        self.assertIn("NameError", result.error)

    def test_cycle_limit(self):
        result = run_script("while True:\n    pass", {}, max_cycles=100)
        self.assertFalse(result.ok)
        self.assertIn("out of CPU cycles", result.error)

    def test_syntax_error_reported(self):
        result = run_script("def broken(:", {})
        self.assertFalse(result.ok)
        self.assertIn("SyntaxError", result.error)


class MissionTests(unittest.TestCase):
    def test_every_mission_has_a_working_solution(self):
        for mission in MISSIONS:
            with self.subTest(mission=mission.id):
                result = play(mission, SOLUTIONS[mission.id])
                self.assertTrue(result.success, result.message)

    def test_templates_run_without_errors(self):
        for mission in MISSIONS:
            with self.subTest(mission=mission.id):
                result = play(mission, mission.template)
                self.assertTrue(result.run.ok, result.run.error)
                self.assertFalse(result.success)

    def test_naive_brute_force_runs_out_of_cycles(self):
        naive = """
scan(); connect('relay'); scan()
for i in range(10000):
    if crack('gw-01', str(i).zfill(4)):
        connect('gw-01')
        submit(cat('operator.txt'))
        break
"""
        result = play(get_mission(2), naive)
        self.assertFalse(result.success)
        self.assertIn("out of CPU cycles", result.message)

    def test_partial_map_fails(self):
        result = play(get_mission(1), "submit(scan())")
        self.assertFalse(result.success)
        self.assertIn("missing", result.message)


class TerminalTests(unittest.TestCase):
    def test_new_and_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            term = Terminal(tmp)
            self.assertIn("created", term.handle("new 1"))
            Path(tmp, "mission1.py").write_text(SOLUTIONS[1])
            out = term.handle("run 1")
            self.assertIn("ACCESS GRANTED", out)
            self.assertIn("[x] 1.", term.handle("missions"))

    def test_bad_input(self):
        term = Terminal()
        self.assertIn("usage error", term.handle("brief"))
        self.assertIn("no mission", term.handle("brief 99"))
        self.assertIn("unknown command", term.handle("rm -rf"))


if __name__ == "__main__":
    unittest.main()
