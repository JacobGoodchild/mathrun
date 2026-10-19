import json
import os
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import verify  # noqa: E402

BIN = os.path.join(HERE, "bin", "beal")


def brute(amax, cmax, lo=3, hi=7):
    powers = {}
    for C in range(1, cmax + 1):
        for z in range(lo, hi + 1):
            powers.setdefault(C ** z, []).append(C)
    hits = 0
    for A in range(1, amax + 1):
        for B in range(1, A + 1):
            for x in range(lo, hi + 1):
                for y in range(lo, hi + 1):
                    hits += len(powers.get(A ** x + B ** y, []))
    return hits


def run(a0, a1, cmax):
    out = subprocess.run([BIN, str(a0), str(a1), str(cmax)], capture_output=True, text=True, check=True).stdout
    return out, json.loads(out.strip().splitlines()[-1][5:])


class TestBeal(unittest.TestCase):
    def test_exact_hits_match_brute_force(self):
        out, d = run(1, 121, 300)
        self.assertEqual(d["exact_hits"], brute(120, 300))
        self.assertEqual(d["coprime"], 0)
        self.assertNotIn("CAND", out)

    def test_known_noncoprime_examples_found(self):
        # 2^3 + 2^3 = 2^4 and 3^3 + 6^3 = 3^5 are true but share factors
        self.assertGreater(run(1, 7, 10)[1]["exact_hits"], 0)

    def test_pairs_counted(self):
        self.assertEqual(run(10, 20, 100)[1]["cases"], sum(range(10, 20)))

    def test_verifier(self):
        self.assertEqual(verify.check(2, 3, 2, 3, 2, 4)[0], 1)    # gcd 2
        self.assertEqual(verify.check(2, 5, 7, 2, 3, 4)[0], 1)    # 32 + 49 = 81 but exponent 2
        self.assertEqual(verify.check(3, 3, 4, 3, 5, 3)[0], 1)    # 27 + 64 != 125
        self.assertEqual(verify.check(3, 3, 6, 3, 3, 5)[0], 1)    # true, gcd 3
        self.assertEqual(verify.check("3", 3, 6, 3, 3, 5)[0], 1)


if __name__ == "__main__":
    unittest.main()
