"""Independent check of a 3x3 magic square of squares (exact integers).

Builds the square from (e, a, b), then checks from scratch: nine distinct
positive entries, every one a perfect square, and all three rows, three
columns and two diagonals with the same sum. Exit 0 = verified candidate.
"""
import json
import math
import sys


def square_from(e, a, b):
    c = e * e
    return [[c + a, c - a - b, c + b],
            [c - a + b, c, c + a - b],
            [c - b, c + a + b, c - a]]


def check_grid(g):
    flat = [x for row in g for x in row]
    if len(flat) != 9 or any(not isinstance(x, int) for x in flat):
        return 1, "not a 3x3 grid of integers"
    if min(flat) <= 0:
        return 1, "entries must be positive"
    if len(set(flat)) != 9:
        return 1, "entries are not distinct"
    for x in flat:
        if math.isqrt(x) ** 2 != x:
            return 1, "%d is not a perfect square" % x
    lines = [row for row in g] + [[g[r][k] for r in range(3)] for k in range(3)] + \
            [[g[i][i] for i in range(3)], [g[i][2 - i] for i in range(3)]]
    sums = {sum(l) for l in lines}
    if len(sums) != 1:
        return 1, "not magic: line sums %s" % sorted(sums)
    roots = [[math.isqrt(x) for x in row] for row in g]
    return 0, "MAGIC SQUARE OF SQUARES: roots %s" % roots


if __name__ == "__main__":
    try:
        d = json.load(open(sys.argv[1]))["data"]
        code, msg = check_grid(square_from(int(d["e"]), int(d["a"]), int(d["b"])))
    except Exception as ex:
        code, msg = 1, "unreadable candidate: %r" % (ex,)
    print(("VERIFIED: " if code == 0 else "REJECTED: ") + msg)
    sys.exit(code)
