import json
import math
import os
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import verify  # noqa: E402

BIN = os.path.join(HERE, "bin", "magic")


def factors(n):
    out, p = [], 2
    while p * p <= n:
        while n % p == 0:
            out.append(p)
            n //= p
        p += 1
    if n > 1:
        out.append(n)
    return out


def brute_X(e):
    N = 2 * e * e
    return sorted({(q * q - p * p) // 2 for p in range(1, e)
                   for q in [math.isqrt(N - p * p)] if q * q == N - p * p and q > p})


class TestMagic(unittest.TestCase):
    def test_pair_lists_match_brute_force(self):
        out = subprocess.run([BIN, "1", "3000", "dumpx"], capture_output=True, text=True, check=True).stdout
        got = {json.loads(l[5:])["e"]: json.loads(l[5:])["x"] for l in out.splitlines() if l.startswith("NOTE")}
        want = {e: brute_X(e) for e in range(2, 3000) if all(p % 4 == 1 for p in factors(e))}
        self.assertEqual(set(got), set(want))
        for e in want:
            self.assertEqual(got[e], want[e], e)

    def test_large_e_no_overflow(self):
        # e = 5^14 > 2^32: x values exceed 2^64 and must still be exact
        e = 5 ** 14
        out = subprocess.run([BIN, str(e), str(e + 1), "dumpx"], capture_output=True, text=True, check=True).stdout
        got = [int(v) for v in json.loads([l for l in out.splitlines() if l.startswith("NOTE")][0][5:])["x"]]
        N = 2 * e * e
        # exact x values from the Gaussian-integer formula, cross-checked by p^2 + q^2 = 2e^2
        for x in got:
            p2 = e * e - x
            q2 = e * e + x
            self.assertEqual(math.isqrt(p2) ** 2, p2)
            self.assertEqual(math.isqrt(q2) ** 2, q2)
            self.assertEqual(p2 + q2, N)
        self.assertGreater(max(got), 2 ** 64)
        self.assertEqual(len(got), len(set(got)))

    def test_bremner_seven_squares_rejected(self):
        g = [[373 ** 2, 289 ** 2, 565 ** 2], [360721, 425 ** 2, 23 ** 2], [205 ** 2, 527 ** 2, 222121]]
        self.assertEqual(len({sum(r) for r in g}), 1)  # it is magic...
        self.assertEqual(verify.check_grid(g)[0], 1)    # ...but only 7 squares

    def test_verifier_accepts_a_magic_square_of_squares_shape(self):
        # the verifier logic itself: a 3x3 magic square with square entries but repeats is rejected,
        # and the parametrisation is always magic
        g = verify.square_from(5, 1, 2)
        self.assertEqual(len({sum(r) for r in g} | {sum(c) for c in zip(*g)}), 1)
        self.assertEqual(verify.check_grid([[1] * 3] * 3)[0], 1)

    def test_no_solutions_small(self):
        out = subprocess.run([BIN, "1", "1000000"], capture_output=True, text=True, check=True).stdout
        self.assertNotIn("CAND", out)


if __name__ == "__main__":
    unittest.main()
