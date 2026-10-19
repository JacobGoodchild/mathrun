import json
import os
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import verify  # noqa: E402

BIN = os.path.join(HERE, "bin", "capset")


def run(n, secs, target, start="-"):
    out = subprocess.run([BIN, str(n), "1", str(secs), start, str(target)], capture_output=True,
                         text=True, check=True).stdout
    return [json.loads(l[5:]) for l in out.splitlines() if l.startswith("BEST ")][0]["data"]


class TestCapset(unittest.TestCase):
    def test_reproduces_known_maxima(self):
        for n, mx in ((2, 4), (3, 9), (4, 20)):
            d = run(n, 30, mx - 1)
            self.assertEqual(d["size"], mx, n)
            self.assertEqual(verify.check(n, d["size"], d["points"])[0], 0)

    def test_never_exceeds_known_maximum(self):
        d = run(3, 2, 1000)
        self.assertLessEqual(d["size"], 9)

    def test_resume_from_start(self):
        d = run(4, 3, 19)
        path = os.path.join(HERE, "bin", "start-test.txt")
        open(path, "w").write("\n".join(map(str, d["points"])))
        d2 = run(4, 1, 1000, path)
        self.assertGreaterEqual(d2["size"], d["size"])

    def test_verifier_rejects(self):
        self.assertEqual(verify.check(2, 3, [0, 1, 2])[0], 1)          # a line
        self.assertEqual(verify.check(2, 2, [0, 0])[0], 1)             # repeat
        self.assertEqual(verify.check(2, 1, [9])[0], 1)                # out of range
        self.assertEqual(verify.check(7, 3, [0, 1, 3])[0], 1)          # valid but not a record
        self.assertEqual(verify.check(3, 3, [0, 1, 3])[0], 0)          # valid small cap


if __name__ == "__main__":
    unittest.main()
