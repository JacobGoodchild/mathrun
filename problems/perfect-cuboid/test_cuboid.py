import json
import math
import os
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import verify  # noqa: E402

BIN = os.path.join(HERE, "bin", "cuboid")


def legs(a):
    out = []
    a2 = a * a
    for u in range(1, a):
        if a2 % u == 0:
            v = a2 // u
            if (v - u) % 2 == 0:
                out.append((v - u) // 2)
    return out


def brute_bricks(lo, hi):
    """All (a,b,c), a odd in [lo,hi), b<c legs of a, with b^2+c^2 square. No filters."""
    found = []
    for a in range(lo | 1, hi, 2):
        L = sorted(legs(a))
        for i in range(len(L)):
            for j in range(i + 1, len(L)):
                s = L[i] ** 2 + L[j] ** 2
                if math.isqrt(s) ** 2 == s:
                    found.append((a, L[i], L[j]))
    return found


def run(a, b):
    out = subprocess.run([BIN, str(a), str(b)], capture_output=True, text=True, check=True).stdout
    return json.loads(out.strip().splitlines()[-1][5:])


class TestCuboid(unittest.TestCase):
    def test_known_bricks(self):
        # (117, 44, 240) is the smallest Euler brick (Halcke, 1719)
        self.assertIn((117, 44, 240), brute_bricks(117, 118))
        self.assertEqual(verify.check(117, 44, 240)[0], 1)  # Euler brick, not perfect

    def test_brick_count_matches_unfiltered_brute_force(self):
        # validates both the leg generation and the divisibility pre-filter
        for lo, hi in ((3, 2000), (100001, 101001)):
            want = len(brute_bricks(lo, hi))
            got = run(lo, hi)
            self.assertEqual(got["euler_bricks"], want, (lo, hi))
            self.assertEqual(got["cases"], len(range(lo | 1, hi, 2)))

    def test_divisibility_facts_on_small_primitive_bricks(self):
        for a, b, c in brute_bricks(3, 3000):
            if math.gcd(a, math.gcd(b, c)) != 1:
                continue
            e = (a, b, c)
            self.assertGreaterEqual(sum(x % 3 == 0 for x in e), 2)
            for m in (9, 5, 11, 16):
                self.assertTrue(any(x % m == 0 for x in e), (e, m))

    def test_verifier_rejects(self):
        for t in ((3, 4, 5), (117, 44, 240), (0, 1, 1), ("x", 1, 1), (-117, 44, 240)):
            self.assertEqual(verify.check(*t)[0], 1, t)

    def test_large_window_runs(self):
        got = run(25_000_000_000_001, 25_000_000_002_001)
        self.assertEqual(got["cases"], 1000)


if __name__ == "__main__":
    unittest.main()
