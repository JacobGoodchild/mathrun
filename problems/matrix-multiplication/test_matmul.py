import json
import os
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import verify  # noqa: E402

BIN = os.path.join(HERE, "bin", "flipgraph")


def plugin():
    import importlib.util
    spec = importlib.util.spec_from_file_location("mm_plugin", os.path.join(HERE, "plugin.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run(n, m, p, secs, seed=1, start="-", target=0):
    out = subprocess.run([BIN, str(n), str(m), str(p), str(seed), str(secs), start, str(target)],
                         capture_output=True, text=True, check=True).stdout
    best = [json.loads(l[5:]) for l in out.splitlines() if l.startswith("BEST ")][0]
    return best["data"]


class TestMatMul(unittest.TestCase):
    def test_strassen_constant_is_correct(self):
        self.assertTrue(verify.is_matmul_scheme(2, 2, 2, plugin().STRASSEN))

    def test_standard_algorithm_correct_and_wrong_rejected(self):
        std = [[1 << (i * 2 + j), 1 << (j * 2 + k), 1 << (k * 2 + i)]
               for i in range(2) for j in range(2) for k in range(2)]
        self.assertTrue(verify.is_matmul_scheme(2, 2, 2, std))
        self.assertFalse(verify.is_matmul_scheme(2, 2, 2, std[1:]))

    def test_reproduces_known_optimal_ranks(self):
        for (n, m, p), want, secs in (((2, 2, 2), 7, 2), ((2, 2, 3), 11, 4), ((3, 3, 3), 23, 12)):
            d = run(n, m, p, secs * 2, target=want + 1)
            self.assertEqual(d["rank"], want, (n, m, p))
            self.assertTrue(verify.is_matmul_scheme(n, m, p, d["terms"]))

    def test_kron_product_49(self):
        P = plugin()
        s = P.kron(P.STRASSEN, (2, 2, 2), P.STRASSEN, (2, 2, 2))
        self.assertEqual(len(s), 49)
        self.assertTrue(verify.is_matmul_scheme(4, 4, 4, s))

    def test_resume_from_start_file(self):
        P = plugin()
        s = P.kron(P.STRASSEN, (2, 2, 2), P.STRASSEN, (2, 2, 2))
        path = os.path.join(HERE, "bin", "start-test.txt")
        with open(path, "w") as f:
            f.write("4 4 4 49\n" + "".join("%d %d %d\n" % tuple(t) for t in s))
        d = run(4, 4, 4, 2, start=path)
        self.assertLessEqual(d["rank"], 49)
        self.assertTrue(verify.is_matmul_scheme(4, 4, 4, d["terms"]))

    def test_compose_and_rotate(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("mm_compose", os.path.join(HERE, "compose.py"))
        compose = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(compose)
        P = plugin()
        stored = {(2, 2, 2): P.STRASSEN}
        for fmt in ((2, 2, 4), (3, 2, 2), (2, 3, 2), (4, 4, 4), (3, 3, 7), (2, 5, 3), (5, 2, 4)):
            t = compose.best_start(fmt, stored)
            self.assertTrue(verify.is_matmul_scheme(*fmt, t), fmt)
            self.assertLessEqual(len(t), fmt[0] * fmt[1] * fmt[2])
        self.assertEqual(len(compose.best_start((4, 4, 4), stored)), 56)   # 8 Strassen blocks
        rot = compose.rotate(compose.best_start((2, 2, 3), stored))
        self.assertTrue(verify.is_matmul_scheme(2, 3, 2, rot))

    def test_lifting(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("mm_lift", os.path.join(HERE, "lift.py"))
        lift = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(lift)
        P = plugin()
        signed = lift.lift(2, 2, 2, P.STRASSEN)
        self.assertIsNotNone(signed)                       # Strassen works over the integers
        self.assertTrue(verify.integer_scheme_ok(2, 2, 2, signed, P.STRASSEN))
        bad = [[dict(f) for f in t] for t in signed]
        k = next(iter(bad[0][0]))
        bad[0][0][k] = -bad[0][0][k]
        self.assertFalse(verify.integer_scheme_ok(2, 2, 2, bad, P.STRASSEN))
        s49 = P.kron(P.STRASSEN, (2, 2, 2), P.STRASSEN, (2, 2, 2))
        self.assertIsNotNone(lift.lift(4, 4, 4, s49))

    def test_verifier_record_logic(self):
        P = plugin()
        good = {"n": 2, "m": 2, "p": 2, "rank": 7, "field": "GF(2)", "terms": P.STRASSEN}
        self.assertEqual(verify.check(good)[0], 0)  # known optimum: reproduction
        s = P.kron(P.STRASSEN, (2, 2, 2), P.STRASSEN, (2, 2, 2))
        not_record = {"n": 4, "m": 4, "p": 4, "rank": 49, "field": "GF(2)", "terms": s}
        self.assertEqual(verify.check(not_record)[0], 1)
        self.assertEqual(verify.check(not_record, need_record=False)[0], 0)
        bad = dict(good, terms=[[t[0], t[1], t[2] ^ 1] for t in P.STRASSEN])
        self.assertEqual(verify.check(bad)[0], 1)
        oob = dict(good, terms=[[16, 1, 1]] + P.STRASSEN[1:])
        self.assertEqual(verify.check(oob)[0], 1)


if __name__ == "__main__":
    unittest.main()
