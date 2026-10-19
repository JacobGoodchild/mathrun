"""Independent check of a perfect-cuboid candidate with exact Python integers.

Accepts only if a, b, c are positive whole numbers and all four diagonals
(a^2+b^2, a^2+c^2, b^2+c^2, a^2+b^2+c^2) are perfect squares.
Exit 0 = verified candidate (needs expert review), 1 = rejected.
"""
import json
import math
import sys


def is_square(n):
    return n >= 0 and math.isqrt(n) ** 2 == n


def check(a, b, c):
    try:
        a, b, c = int(a), int(b), int(c)
    except (TypeError, ValueError):
        return 1, "edges are not whole numbers"
    if min(a, b, c) <= 0:
        return 1, "edges must be positive"
    faces = [(a, b), (a, c), (b, c)]
    for x, y in faces:
        if not is_square(x * x + y * y):
            return 1, "face %d,%d has no whole diagonal" % (x, y)
    if not is_square(a * a + b * b + c * c):
        return 1, "an Euler brick, but the space diagonal is not whole (not perfect)"
    return 0, "PERFECT CUBOID: edges %d, %d, %d; all seven lengths whole" % (a, b, c)


if __name__ == "__main__":
    try:
        d = json.load(open(sys.argv[1]))["data"]
        code, msg = check(d["a"], d["b"], d["c"])
    except Exception as e:
        code, msg = 1, "unreadable candidate: %r" % (e,)
    print(("VERIFIED: " if code == 0 else "REJECTED: ") + msg)
    sys.exit(code)
