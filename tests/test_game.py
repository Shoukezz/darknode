"""Tests for DarkNode. Run with: python -m unittest   (or: pytest)"""

import tempfile
import unittest
from pathlib import Path

from darknode import i18n, progress
from darknode.content import ACHIEVEMENT_IDS, ACTS, campaign_complete, unlocked_missions
from darknode.game import AccessDenied, GameSession
from darknode.missions import MISSIONS, get_mission
from darknode.network import Network, Node
from darknode.runner import play, stars_for
from darknode.sandbox import run_script
from darknode.sandbox_gen import generate
from darknode.save import SaveData
from darknode.terminal import Terminal

from tests.solutions import SOLUTIONS


class NetworkTests(unittest.TestCase):
    def test_links_are_bidirectional(self):
        net = Network()
        net.add(Node("a")); net.add(Node("b"))
        net.link("a", "b")
        self.assertEqual(net.neighbors("b"), ["a"])

    def test_weights_and_shortest_cost(self):
        net = Network()
        for h in ("a", "b", "c"):
            net.add(Node(h))
        net.link("a", "b", 5)
        net.link("a", "c", 1)
        net.link("c", "b", 1)
        self.assertEqual(net.weight("a", "b"), 5)
        self.assertEqual(net.shortest_cost("a", "b"), 2)

    def test_duplicate_host_rejected(self):
        net = Network()
        net.add(Node("a"))
        with self.assertRaises(ValueError):
            net.add(Node("a"))


class SessionTests(unittest.TestCase):
    def setUp(self):
        self.session = get_mission(7).new_session()

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

    def test_dataset_api(self):
        session = get_mission(16).new_session()
        self.assertEqual(session.size(), 100_000)
        self.assertEqual(session.at(0), 7)


class SandboxTests(unittest.TestCase):
    def test_print_is_captured(self):
        result = run_script("print('hi', 1)", {})
        self.assertTrue(result.ok)
        self.assertEqual(result.output, ["hi 1"])

    def test_forbidden_import(self):
        result = run_script("import os", {})
        self.assertFalse(result.ok)
        self.assertIn("not available", result.error)

    def test_allowed_imports(self):
        for mod in ("math", "re", "bisect", "base64", "itertools", "hashlib"):
            self.assertTrue(run_script(f"import {mod}", {}).ok, mod)

    def test_open_is_not_available(self):
        result = run_script("open('x.txt')", {})
        self.assertFalse(result.ok)
        self.assertEqual(result.error_type, "NameError")

    def test_cycle_limit(self):
        result = run_script("while True:\n    pass", {}, max_cycles=100)
        self.assertFalse(result.ok)
        self.assertEqual(result.error_type, "CycleLimitExceeded")

    def test_syntax_error_reported(self):
        result = run_script("def broken(:", {})
        self.assertFalse(result.ok)
        self.assertEqual(result.error_type, "SyntaxError")


class MissionTests(unittest.TestCase):
    def test_every_mission_solvable_in_budget(self):
        for mission in MISSIONS:
            with self.subTest(mission=mission.id):
                result = play(mission, SOLUTIONS[mission.id])
                self.assertTrue(result.success, f"m{mission.id}: {result.message_key}")
                self.assertLessEqual(result.run.cycles, mission.max_cycles)

    def test_templates_run_and_do_not_solve(self):
        for mission in MISSIONS:
            for lang in i18n.LANGUAGES:
                with self.subTest(mission=mission.id, lang=lang):
                    tpl = i18n.t(f"mission.{mission.id}.template", lang)
                    result = play(mission, tpl)
                    self.assertTrue(result.run.ok, result.run.error)
                    self.assertFalse(result.success)

    def test_twenty_five_missions_in_five_acts(self):
        self.assertEqual(len(MISSIONS), 25)
        self.assertEqual(sorted(ACTS), [1, 2, 3, 4, 5])

    def test_linear_scan_blows_budget(self):
        linear = ("target = 61803*2+7\n"
                  "for i in range(size()):\n"
                  "    if at(i)==target:\n        submit(i)\n        break\n")
        result = play(get_mission(16), linear)
        self.assertFalse(result.success)
        self.assertEqual(result.run.error_type, "CycleLimitExceeded")

    def test_naive_recursion_blows_budget(self):
        naive = ("def fib(n):\n    if n<3: return 1\n    return fib(n-1)+fib(n-2)\n"
                 "submit(fib(20))\n")
        result = play(get_mission(13), naive)
        self.assertFalse(result.success)
        self.assertEqual(result.run.error_type, "CycleLimitExceeded")

    def test_full_pin_brute_force_trips_alarm(self):
        brute = ('scan(); connect("relay"); scan()\n'
                 'for i in range(10000):\n'
                 '    if crack("gw-01", str(i).zfill(4)):\n'
                 '        connect("gw-01"); submit(cat("operator.txt")); break\n')
        result = play(get_mission(7), brute)
        self.assertFalse(result.success)
        self.assertEqual(result.message_key, "check.alarm")

    def test_partial_map_fails(self):
        result = play(get_mission(17), "submit(scan())")
        self.assertFalse(result.success)
        self.assertEqual(result.message_key, "check.m17.no")


class StarTests(unittest.TestCase):
    def test_star_thresholds(self):
        self.assertEqual(stars_for(10, 100), 3)
        self.assertEqual(stars_for(70, 100), 2)
        self.assertEqual(stars_for(95, 100), 1)


class I18nTests(unittest.TestCase):
    def test_no_missing_keys(self):
        for lang, missing in i18n.missing_keys().items():
            self.assertEqual(missing, set(), f"{lang} missing {missing}")

    def test_every_mission_has_text_in_both_languages(self):
        for mission in MISSIONS:
            for lang in i18n.LANGUAGES:
                for part in ("title", "briefing", "concept", "template"):
                    key = f"mission.{mission.id}.{part}"
                    self.assertNotEqual(i18n.t(key, lang), key, key)
                hints = i18n.get(f"mission.{mission.id}.hints", lang)
                self.assertEqual(len(hints), 3, f"m{mission.id} {lang} hints")

    def test_check_messages_resolve(self):
        for mission in MISSIONS:
            session = mission.new_session()
            _, key, params = mission.check(session)  # the "empty" path
            self.assertNotEqual(i18n.t(key, "uk", **params), key)


class SaveTests(unittest.TestCase):
    def test_round_trip(self):
        data = SaveData()
        data.credits = 123
        data.record_success(1, 50, 3, 40)
        data.achievements.append("first-blood")
        text = data.to_json()
        back = SaveData.from_json(text)
        self.assertEqual(back.credits, 163)  # 123 + the mission-1 reward of 40
        self.assertEqual(back.record(1).stars, 3)
        self.assertIn("first-blood", back.achievements)

    def test_corrupt_json_is_rejected(self):
        with self.assertRaises(ValueError):
            SaveData.from_json("not json")

    def test_first_clear_pays_once(self):
        data = SaveData()
        first = data.record_success(5, 100, 2, 50)
        second = data.record_success(5, 90, 3, 50)
        self.assertEqual(first, 50)
        self.assertEqual(second, 0)
        self.assertEqual(data.record(5).best_cycles, 90)
        self.assertEqual(data.record(5).stars, 3)


class ProgressTests(unittest.TestCase):
    def test_award_grants_credits_and_achievement(self):
        data = SaveData()
        result = play(get_mission(1), SOLUTIONS[1])
        summary = progress.award(data, get_mission(1), result)
        self.assertEqual(summary["awarded"], get_mission(1).reward)
        self.assertIn("first-blood", data.achievements)

    def test_unlock_is_linear(self):
        self.assertEqual(unlocked_missions(set()), {1})
        self.assertEqual(unlocked_missions({1}), {1, 2})
        self.assertNotIn(3, unlocked_missions({1}))

    def test_shop_purchase(self):
        data = SaveData()
        data.credits = 100
        self.assertFalse(progress.buy(data, "nope")["ok"])
        res = progress.buy(data, "grep")
        self.assertTrue(res["ok"])
        self.assertIn("grep", data.unlocked)
        self.assertEqual(data.credits, 60)
        self.assertFalse(progress.buy(data, "grep")["ok"])  # already owned

    def test_shop_helper_available_when_unlocked(self):
        src = 'submit(grep("err", "ok\\nerr here\\nfine"))'
        locked = play(get_mission(1), src)
        self.assertFalse(locked.run.ok)  # grep not defined
        unlocked = play(get_mission(1), src, unlocked=["grep"])
        self.assertTrue(unlocked.run.ok)

    def test_campaign_complete_unlocks_sandbox(self):
        data = SaveData()
        self.assertFalse(progress.sandbox_unlocked(data))
        for m in MISSIONS:
            data.record_success(m.id, 1, 3, m.reward)
        self.assertTrue(progress.sandbox_unlocked(data))
        self.assertTrue(campaign_complete({int(k) for k in data.completed}))


class SandboxModeTests(unittest.TestCase):
    def test_map_seed_is_solvable(self):
        mission = generate(2)  # even seed -> map objective
        src = ("seen={'home'}; q=['home']\n"
               "while q:\n"
               "    for n in scan(q.pop(0)):\n"
               "        if n not in seen:\n            seen.add(n); q.append(n)\n"
               "submit(sorted(seen))\n")
        result = play(mission, src)
        self.assertTrue(result.success, result.message_key)

    def test_flag_seed_has_gateway(self):
        mission = generate(1)  # odd seed -> flag objective
        session = mission.new_session()
        locked = [h for h in session.network.hosts()
                  if session.network.node(h).locked]
        self.assertTrue(locked)

    def test_seed_is_deterministic(self):
        a = generate(5).new_session().network.hosts()
        b = generate(5).new_session().network.hosts()
        self.assertEqual(a, b)


class BridgeTests(unittest.TestCase):
    def _bridge(self):
        import importlib.util
        path = Path(__file__).resolve().parent.parent / "web" / "bridge.py"
        spec = importlib.util.spec_from_file_location("darknode_bridge", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_catalog_has_everything(self):
        import json
        cat = json.loads(self._bridge().catalog("uk"))
        self.assertEqual(len(cat["missions"]), 25)
        self.assertEqual(len(cat["acts"]), 5)
        self.assertTrue(cat["shop"])
        self.assertIn("ui", cat["strings"])

    def test_run_updates_save(self):
        import json
        bridge = self._bridge()
        out = json.loads(bridge.run_json(1, SOLUTIONS[1], "", "en"))
        self.assertTrue(out["success"])
        # first-clear reward plus the cycle bonus for finishing well under budget
        self.assertGreaterEqual(out["save"]["credits"], get_mission(1).reward)
        self.assertEqual(out["award"]["awarded"], get_mission(1).reward)
        self.assertIn(2, out["unlocked_missions"])

    def test_validate_save(self):
        import json
        bridge = self._bridge()
        self.assertFalse(json.loads(bridge.validate_save("garbage"))["ok"])
        good = SaveData().to_json()
        self.assertTrue(json.loads(bridge.validate_save(good))["ok"])


class TerminalTests(unittest.TestCase):
    def test_new_run_and_progress(self):
        with tempfile.TemporaryDirectory() as tmp:
            term = Terminal(tmp, save_path=Path(tmp, "save.json"))
            self.assertIn("created", term.handle("new 1"))
            Path(tmp, "mission1.py").write_text(SOLUTIONS[1])
            out = term.handle("run 1")
            self.assertIn("ACCESS GRANTED", out)
            self.assertIn("✓", term.handle("missions"))

    def test_language_switch(self):
        with tempfile.TemporaryDirectory() as tmp:
            term = Terminal(tmp, save_path=Path(tmp, "save.json"))
            term.handle("lang uk")
            self.assertEqual(term.lang, "uk")
            out = term.handle("brief 1")
            self.assertIn("Поняття", out)  # Ukrainian "Concept" label
            self.assertIn("Перший контакт", out)

    def test_bad_input(self):
        term = Terminal(autosave=False)
        self.assertIn("usage error", term.handle("brief"))
        self.assertIn("no mission", term.handle("brief 99"))
        self.assertIn("unknown command", term.handle("rm -rf"))

    def test_sandbox_locked_until_campaign_done(self):
        with tempfile.TemporaryDirectory() as tmp:
            term = Terminal(tmp, save_path=Path(tmp, "save.json"))
            self.assertIn(i18n.t("ui.sandbox_locked", "en"), term.handle("sandbox 1"))


if __name__ == "__main__":
    unittest.main()
