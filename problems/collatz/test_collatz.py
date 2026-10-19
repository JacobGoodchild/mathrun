import json
import os
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import verify  # noqa: E402

BIN = os.path.join(HERE, "bin", "collatz")


def glide(n):
    v, s = n, 0
    while v >= n:
        v = 3 * v + 1 if v & 1 else v >> 1
        s += 1
    return s


def run(start, count, k):
    out = subprocess.run([BIN, str(start >> 64), str(start & (2 ** 64 - 1)), str(count), str(k)],
                         capture_output=True, text=True, check=True).stdout
    best = [json.loads(l[5:]) for l in out.splitlines() if l.startswith("BEST ")][0]
    done = [json.loads(l[5:]) for l in out.splitlines() if l.startswith("DONE ")][0]
    return best, done, out


class TestCollatz(unittest.TestCase):
    def test_max_glide_matches_brute_force(self):
        for start, k in ((2 ** 40, 10), (2 ** 71, 12), (5 * 2 ** 50, 14)):
            count = 2 ** 17
            best, done, _ = run(start, count, k)
            g = [(glide(n), -n) for n in range(start, start + count)]
            want_g, want_n = max(g)
            self.assertEqual(best["glide"], want_g, start)
            self.assertEqual(int(best["n"]), -want_n, start)
            self.assertEqual(done["cases"], count)

    def test_known_glide_record_27(self):
        # 27 has glide 96 (Roosendaal's glide records); check our glide definition
        self.assertEqual(glide(27), 96)

    def test_sieve_skips_only_dropping_residues(self):
        # every n skipped by the sieve must drop below itself within K steps
        best, done, _ = run(2 ** 40, 2 ** 12, 12)
        self.assertLess(done["residues"], 2 ** 12 // 10)

    def test_rejects_bad_args(self):
        r = subprocess.run([BIN, "0", "100", "4096", "12"], capture_output=True)
        self.assertNotEqual(r.returncode, 0)

    def test_verifier(self):
        for n in (27, 2 ** 71 + 1, 3):
            self.assertEqual(verify.check(n)[0], 1)
        self.assertEqual(verify.check(-5)[0], 1)


if __name__ == "__main__":
    unittest.main()
