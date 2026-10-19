"""Tests for the core: config, atomic writes, ledger, guards, protocol, and the
full candidate pipeline end to end using the toy problem."""

import json
import os
import shutil
import tempfile
import unittest

from mathrun_core import atomic, config, guards, ledger, paths, problems, tomlmini


class TempData(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="mathrun-test-")
        self.old = os.environ.get("MATHRUN_DATA")
        os.environ["MATHRUN_DATA"] = self.tmp

    def tearDown(self):
        if self.old is None:
            os.environ.pop("MATHRUN_DATA", None)
        else:
            os.environ["MATHRUN_DATA"] = self.old
        shutil.rmtree(self.tmp, ignore_errors=True)


class TestToml(unittest.TestCase):
    TEXT = """
# comment
name = "Sum # of cubes"   # trailing
n = 1_000
x = 2.5
on = true
list = ["a", "b",
        "c"]
[machine]
workers = 3
[problems.weights]
foo = 2
"""

    def test_mini_parser(self):
        d = tomlmini._mini_loads(self.TEXT)
        self.assertEqual(d["name"], "Sum # of cubes")
        self.assertEqual(d["n"], 1000)
        self.assertEqual(d["x"], 2.5)
        self.assertIs(d["on"], True)
        self.assertEqual(d["list"], ["a", "b", "c"])
        self.assertEqual(d["machine"]["workers"], 3)
        self.assertEqual(d["problems"]["weights"]["foo"], 2)

    def test_mini_matches_stdlib_on_our_files(self):
        if tomlmini._tomllib is None:
            self.skipTest("no tomllib")
        files = [os.path.join(paths.REPO, "config.example.toml")]
        for p in problems.discover(include_toys=True):
            files.append(p.path("problem.toml"))
        for f in files:
            text = open(f).read()
            self.assertEqual(tomlmini._mini_loads(text), tomlmini._tomllib.loads(text), f)


class TestConfig(unittest.TestCase):
    def test_defaults_and_clamps(self):
        with tempfile.NamedTemporaryFile("w", suffix=".toml", delete=False) as f:
            f.write("[machine]\nnice = -5\nmax_temp_c = 200\n[publish]\ninterval_minutes = 1\n")
        try:
            cfg = config.load(f.name)
        finally:
            os.unlink(f.name)
        self.assertEqual(cfg["machine"]["nice"], 0)
        self.assertEqual(cfg["machine"]["max_temp_c"], 100.0)
        self.assertEqual(cfg["publish"]["interval_minutes"], 60)
        self.assertFalse(cfg["publish"]["enabled"])

    def test_workers_all_but_one(self):
        cfg = config.load("/nonexistent")
        self.assertEqual(config.worker_count(cfg), max(1, (os.cpu_count() or 1) - 1))


class TestAtomic(TempData):
    def test_roundtrip_and_no_tmp_left(self):
        p = os.path.join(self.tmp, "a", "s.json")
        atomic.atomic_write_json(p, {"x": 10 ** 40})
        atomic.atomic_write_json(p, {"x": 2})
        self.assertEqual(atomic.read_json(p), {"x": 2})
        self.assertEqual(os.listdir(os.path.dirname(p)), ["s.json"])

    def test_corrupt_reads_default(self):
        p = os.path.join(self.tmp, "bad.json")
        open(p, "w").write("{half")
        self.assertEqual(atomic.read_json(p, "d"), "d")

    def test_failed_write_keeps_old(self):
        p = os.path.join(self.tmp, "s.json")
        atomic.atomic_write_json(p, {"ok": 1})
        with self.assertRaises(TypeError):
            atomic.atomic_write_json(p, {"bad": object()})
        self.assertEqual(atomic.read_json(p), {"ok": 1})
        self.assertEqual(os.listdir(self.tmp), ["s.json"])


class TestLedger(unittest.TestCase):
    def test_out_of_order(self):
        L = ledger.Ledger()
        a, b, c = L.issue(set()), L.issue({0}), L.issue({0, 1})
        self.assertEqual((a, b, c), (0, 1, 2))
        L.complete(2)
        self.assertEqual(L.frontier, 0)
        L.complete(0)
        self.assertEqual(L.frontier, 1)
        L.complete(1)
        self.assertEqual(L.frontier, 3)
        self.assertEqual(L.completed_count(), 3)

    def test_lost_units_reissued(self):
        L = ledger.Ledger()
        for i in range(3):
            L.issue(set(range(i)))
        L.complete(1)
        L2 = ledger.Ledger(json.loads(json.dumps(L.to_dict())))  # restart: nothing in flight
        self.assertEqual(L2.issue(set()), 0)
        self.assertEqual(L2.issue({0}), 2)
        self.assertEqual(L2.issue({0, 2}), 3)

    def test_never_issued(self):
        with self.assertRaises(ValueError):
            ledger.Ledger().complete(5)

    def test_double_complete_harmless(self):
        L = ledger.Ledger()
        L.issue(set())
        self.assertTrue(L.complete(0))
        self.assertFalse(L.complete(0))


class TestGuards(TempData):
    def mk(self, temp=None, idle=None, progs=(), **machine):
        cfg = config.load("/nonexistent")
        cfg["machine"].update(machine)
        self.now = [0.0]
        return guards.Guards(cfg, 3, temp_reader=lambda: temp, idle_reader=lambda: idle,
                             programs_reader=lambda: set(progs), clock=lambda: self.now[0])

    def test_runs_when_fine(self):
        d = self.mk(temp=50).evaluate()
        self.assertTrue(d["running"])
        self.assertEqual(d["workers"], 3)

    def test_heat_hysteresis(self):
        temps = [90]
        cfg = config.load("/nonexistent")
        g = guards.Guards(cfg, 2, temp_reader=lambda: temps[0], idle_reader=lambda: None,
                          programs_reader=set)
        self.assertFalse(g.evaluate()["running"])
        temps[0] = 80  # cooler, but not below resume (75)
        self.assertFalse(g.evaluate()["running"])
        temps[0] = 74
        self.assertTrue(g.evaluate()["running"])

    def test_unreadable_temp_duty_cycle(self):
        g = self.mk(temp=None, fallback_run_minutes=20, fallback_rest_minutes=10)
        self.assertTrue(g.evaluate()["running"])
        self.now[0] = 25 * 60
        self.assertFalse(g.evaluate()["running"])
        self.now[0] = 31 * 60
        self.assertTrue(g.evaluate()["running"])

    def test_idle_mode(self):
        self.assertFalse(self.mk(temp=50, idle=10, only_when_idle=True).evaluate()["running"])
        self.assertTrue(self.mk(temp=50, idle=1000, only_when_idle=True).evaluate()["running"])
        # unknown idle time in idle-only mode = assume in use (fail safe)
        self.assertFalse(self.mk(temp=50, idle=None, only_when_idle=True).evaluate()["running"])

    def test_gaming_flag_and_programs(self):
        paths.ensure("control")
        open(paths.control_file("gaming"), "w").close()
        self.assertIn("gaming", self.mk(temp=50).evaluate()["reason"])
        os.unlink(paths.control_file("gaming"))
        d = self.mk(temp=50, progs={"steam_app"}, pause_for_programs=["steam_app"]).evaluate()
        self.assertFalse(d["running"])

    def test_disk_cap(self):
        with open(os.path.join(self.tmp, "big"), "wb") as f:
            f.write(b"x" * 300_000)
        self.assertFalse(self.mk(temp=50, disk_cap_gb=0.0002).evaluate()["running"])

    def test_temp_from_fake_sysfs(self):
        root = tempfile.mkdtemp()
        try:
            hw = os.path.join(root, "class/hwmon/hwmon0")
            os.makedirs(hw)
            open(os.path.join(hw, "name"), "w").write("coretemp\n")
            open(os.path.join(hw, "temp1_input"), "w").write("61000\n")
            open(os.path.join(hw, "temp2_input"), "w").write("67500\n")
            self.assertEqual(guards.cpu_temp_c(root), 67.5)
            shutil.rmtree(hw)
            z = os.path.join(root, "class/thermal/thermal_zone0")
            os.makedirs(z)
            open(os.path.join(z, "type"), "w").write("x86_pkg_temp\n")
            open(os.path.join(z, "temp"), "w").write("55000\n")
            self.assertEqual(guards.cpu_temp_c(root), 55.0)
            open(os.path.join(z, "temp"), "w").write("-1\n")
            self.assertIsNone(guards.cpu_temp_c(root))
        finally:
            shutil.rmtree(root)


class TestProtocol(unittest.TestCase):
    def test_parse(self):
        r = problems.parse_protocol('junk\nCAND {"a":1}\nBEST {"b":2}\nDONE {"cases":5}\n')
        self.assertEqual(r["done"], {"cases": 5})
        self.assertEqual(r["cands"], [{"a": 1}])

    def test_rejects_bad(self):
        for text in ('CAND {bad\nDONE {}', 'DONE {}\nDONE {}', 'DONE {}\nCAND {}'):
            with self.assertRaises(ValueError):
                problems.parse_protocol(text)

    def test_missing_done(self):
        self.assertIsNone(problems.parse_protocol('CAND {"a":1}')["done"])


if __name__ == "__main__":
    unittest.main()
