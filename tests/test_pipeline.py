"""End-to-end: run the real runner on the toy problem with a planted answer."""

import os
import shutil
import tempfile
import unittest
from unittest import mock

from mathrun_core import alerts, atomic, config, paths, problems, runner


def toy():
    for p in problems.discover(include_toys=True):
        if p.slug == "toy-planted":
            return p
    raise RuntimeError("toy problem missing")


class TestPipeline(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="mathrun-pipe-")
        os.environ["MATHRUN_DATA"] = self.tmp
        self.cfg = config.load("/nonexistent")
        self.cfg["alerts"]["desktop"] = False
        p = toy()
        if not p.is_built():
            self.skipTest("toy not built (run ./mathrun install)")

    def tearDown(self):
        os.environ.pop("MATHRUN_DATA", None)
        os.environ.pop("MATHRUN_TOY_LIE", None)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_units(self, n):
        r = runner.Runner(cfg=self.cfg, max_units=n, problem_list=[toy()])
        r.guards.temp_reader = lambda: 40.0
        with mock.patch.object(alerts, "send_verified", return_value=["test"]) as sent:
            self.assertEqual(r.run(), 0)
        return r, sent

    def test_planted_answer_found_verified_alerted(self):
        r, sent = self.run_units(45)  # planted answer lives in unit 41
        st = atomic.read_json(paths.state_path("toy-planted"))
        self.assertEqual(st["ledger"]["frontier"], 45)
        self.assertEqual(st["units_done"], 45)
        self.assertEqual(st["cases"], 45 * 10_000_000)
        self.assertEqual(len(st["candidates"]), 1)
        self.assertTrue(st["candidates"][0]["status"].startswith("VERIFIED"))
        self.assertIsNone(st["bug"])
        sent.assert_called_once()
        idx = atomic.read_json(os.path.join(paths.status_dir(), "index.json"))
        self.assertEqual(len(idx["alerts"]), 1)
        self.assertEqual(idx["machine"]["state"], "stopped")
        detail = atomic.read_json(os.path.join(paths.status_dir(), "toy-planted.json"))
        self.assertEqual(detail["candidates"][0]["data"]["n"], 416041631)
        self.assertTrue(detail["history"])

    def test_resume_after_restart(self):
        self.run_units(5)
        self.run_units(5)
        st = atomic.read_json(paths.state_path("toy-planted"))
        self.assertEqual(st["ledger"]["frontier"], 10)
        self.assertEqual(st["units_done"], 10)

    def test_lying_searcher_is_caught_and_paused(self):
        os.environ["MATHRUN_TOY_LIE"] = "1"
        r, sent = self.run_units(1)
        st = atomic.read_json(paths.state_path("toy-planted"))
        self.assertEqual(st["candidates"][0]["status"], "rejected by verifier (searcher bug)")
        self.assertIsNotNone(st["bug"])
        sent.assert_not_called()
        # a paused-for-bug problem gets no more work
        r2 = runner.Runner(cfg=self.cfg, max_units=1, problem_list=[toy()])
        r2.states = {"toy-planted": st}
        r2.problems = [toy()]
        self.assertEqual(r2._eligible(), [])

    def test_crashing_searcher_backs_off(self):
        p = toy()
        r = runner.Runner(cfg=self.cfg, max_units=1, problem_list=[p])
        r.states[p.slug] = runner.fresh_state(p)
        r._fail(p, "boom")
        st = r.states[p.slug]
        self.assertEqual(st["failures_in_a_row"], 1)
        self.assertGreater(st["backoff_until"], 0)
        for _ in range(runner.MAX_FAILS_IN_A_ROW):
            r._fail(p, "boom")
        self.assertTrue(st["disabled_reason"])

    def test_every_real_plugin_hooks_run(self):
        # exhausted/unit/frontier must work with the real objects the runner passes
        for p in problems.discover():
            st = runner.fresh_state(p)
            led = runner.ledger.Ledger(st["ledger"])
            if hasattr(p.plugin, "exhausted"):
                self.assertFalse(p.plugin.exhausted(st["plugin"], led), p.slug)
            u = p.plugin.unit(0, st["plugin"])
            argv = p.plugin.argv(u, {"dir": p.folder, "bin": p.path("bin"), "work": self.tmp, "seconds": 5})
            self.assertTrue(argv, p.slug)
            self.assertIn("text", p.plugin.frontier(st["plugin"], led), p.slug)

    def test_same_unit_failing_repeatedly_disables(self):
        p = toy()
        r = runner.Runner(cfg=self.cfg, max_units=1, problem_list=[p])
        r.states[p.slug] = runner.fresh_state(p)
        for _ in range(runner.MAX_FAILS_SAME_UNIT):
            r._fail(p, "boom", 7)
            r.states[p.slug]["failures_in_a_row"] = 0  # as if other units succeeded in between
        self.assertIn("unit 7", r.states[p.slug]["disabled_reason"])

    def test_frontier_marked_when_candidates_or_bug(self):
        from mathrun_core import status
        p = toy()
        st = runner.fresh_state(p)
        st["candidates"] = [{"id": "x", "status": "pending verification"}]
        self.assertIn("under review", status.problem_summary(p, st)["frontier"]["text"])
        st["bug"] = {"candidate": "x"}
        self.assertIn("UNTRUSTED", status.problem_summary(p, st)["frontier"]["text"])

    def test_bad_output_not_counted(self):
        p = toy()
        r = runner.Runner(cfg=self.cfg, max_units=1, problem_list=[p])
        r.states[p.slug] = runner.fresh_state(p)
        r.session_cpu[p.slug] = 0.0
        out = os.path.join(self.tmp, "o.txt")
        open(out, "w").write("CAND {\"data\":{}}\n")  # no DONE line
        led = runner.ledger.Ledger()
        led.issue(set())
        r.states[p.slug]["ledger"] = led.to_dict()

        class P:
            returncode = 0
            pid = 1
        j = runner.Job(p, 0, {}, P(), out, out + ".err")
        r._finish(j, 0, 0.1)
        st = r.states[p.slug]
        self.assertEqual(st["units_done"], 0)
        self.assertEqual(st["ledger"]["frontier"], 0)
        self.assertEqual(st["failures_in_a_row"], 1)


if __name__ == "__main__":
    unittest.main()
