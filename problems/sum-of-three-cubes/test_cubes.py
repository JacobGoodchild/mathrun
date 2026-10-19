import importlib.util
import os
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import verify  # noqa: E402

BIN = os.path.join(HERE, "bin", "cubes")
spec = importlib.util.spec_from_file_location("cubes_plugin", os.path.join(HERE, "plugin.py"))
plugin = importlib.util.module_from_spec(spec)
spec.loader.exec_module(plugin)

KNOWN = [  # (k, x, y, z) famous solutions
    (33, 8866128975287528, -8778405442862239, -2736111468807040),        # Booker 2019
    (42, -80538738812075974, 80435758145817515, 12602123297335631),      # Booker & Sutherland 2019
    (3, 569936821221962380720, -569936821113563493509, -472715493453327032),  # B & S 2019
]


def notes(k, d0, d1, Z):
    out = subprocess.run([BIN, str(k), str(d0), str(d1), str(Z)], capture_output=True, text=True,
                         check=True).stdout
    return [l for l in out.splitlines() if l.startswith("NOTE")], out


class TestCubes(unittest.TestCase):
    def test_reproduces_famous_solutions(self):
        for k, x, y, z in KNOWN:
            self.assertEqual(x ** 3 + y ** 3 + z ** 3, k)
            d = abs(x + y)
            got, _ = notes(k, d - 50, d + 50, abs(z) + 1)
            sols = []
            for l in got:
                import json
                n = json.loads(l[5:])
                s = plugin.solve_exact(n["k"], n["d"], n["z"])
                if s:
                    sols.append(s)
            self.assertIn(z, [s[2] for s in sols], k)
            self.assertIn({x, y}, [set(s[:2]) for s in sols], k)

    def test_small_solutions_brute_force(self):
        # every solution of x^3+y^3+z^3 = k with |x|>=|y|>=|z| and 3|x+y| <= |z| <= 300
        R = 2500
        cube_of = {c ** 3: c for c in range(-R, R + 1)}
        total = 0
        for k in (1, 2, 3, 6, 7, 8, 9, 10, 11, 15, 16, 17, 18, 19, 20, 24, 25, 26, 27, 28, 29):
            want = set()
            for z in range(-300, 301):
                z3 = z ** 3
                for x in range(-R, R + 1):
                    y = cube_of.get(k - z3 - x * x * x)
                    if y is not None and abs(x) >= abs(y) >= abs(z) and x + y and 3 * abs(x + y) <= abs(z):
                        want.add((abs(x + y), z))
            if not want:
                continue
            total += len(want)
            got, _ = notes(k, 1, max(d for d, _ in want) + 1, 300)
            import json
            found = set()
            for l in got:
                n = json.loads(l[5:])
                if plugin.solve_exact(n["k"], n["d"], n["z"]):
                    found.add((n["d"], n["z"]))
            self.assertTrue(want <= found, (k, want - found))
        self.assertGreater(total, 0)

    def test_verifier(self):
        k, x, y, z = KNOWN[0]
        self.assertEqual(verify.check(k, x, y, z)[0], 0)
        self.assertEqual(verify.check(k, x, y, z + 1)[0], 1)
        self.assertEqual(verify.check(114, x, y, z)[0], 1)
        self.assertEqual(verify.check(k, "1.5", y, z)[0], 1)


if __name__ == "__main__":
    unittest.main()
