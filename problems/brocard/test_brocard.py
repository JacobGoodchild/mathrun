import math
import os
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import verify  # noqa: E402

BIN = os.path.join(HERE, "bin", "brocard")


def run(a, b, k=None):
    args = [BIN, str(a), str(b)] + ([str(k)] if k else [])
    out = subprocess.run(args, capture_output=True, text=True, check=True).stdout
    survivors = [int(l.split('"n":')[1].split(",")[0]) for l in out.splitlines() if l.startswith("CAND")]
    return survivors, out


class TestBrocard(unittest.TestCase):
    def test_known_solutions_exactly(self):
        # brute force with exact integers agrees: only 4, 5, 7 below 500
        exact = [n for n in range(1, 500) if math.isqrt(math.factorial(n) + 1) ** 2 == math.factorial(n) + 1]
        self.assertEqual(exact, [4, 5, 7])
        self.assertEqual(run(1, 500)[0], exact)

    def test_sieve_matches_python_prime_by_prime(self):
        # survivors after k primes must match a direct Python computation using the same primes
        a, b = 10 ** 6, 10 ** 6 + 3000
        primes, q = [], b
        while len(primes) < 3:
            q += 1
            if verify.is_probable_prime(q):
                primes.append(q)
        expect = []
        for n in range(a, b):
            ok = True
            for p in primes:
                r = (math.prod(range(1, n + 1)) if False else verify.factorial_mod(n, p)) + 1
                r %= p
                if r and pow(r, (p - 1) // 2, p) != 1:
                    ok = False
                    break
            if ok:
                expect.append(n)
        got, _ = run(a, b, 3)
        # the C program prints at most 20 candidates; compare that prefix and the count
        self.assertEqual(got, expect[:20])
        out = run(a, b, 3)[1]
        self.assertIn('"survivors":%d' % len(expect), out)

    def test_large_window_clean(self):
        got, out = run(10 ** 15, 10 ** 15 + 100000)
        self.assertEqual(got, [])
        self.assertIn('"cases":100000', out)

    def test_near_2_62_no_overflow(self):
        a = (1 << 62) - 20000
        got, out = run(a, (1 << 62) - 1)
        self.assertEqual(got, [])

    def test_verifier(self):
        for n in (4, 5, 7):
            self.assertEqual(verify.check(n)[0], 0)
        for n in (1, 2, 3, 6, 8, 100, 10 ** 15 + 7, -4, "4", 4.0, True):
            self.assertEqual(verify.check(n)[0], 1, n)


if __name__ == "__main__":
    unittest.main()
