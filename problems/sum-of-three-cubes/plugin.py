"""Sum of three cubes for the seven open k < 1000.

Fresh ground just past Booker & Sutherland's 2020 Charity Engine search,
which covered every solution with |z| <= 10^19 and d <= 10^19/54. Here:
d > 10^19/54 (all z with 3d <= |z| <= 10^19). Unit i handles one k
(rotating through the seven) and one block of L values of d.
"""
import math
import os

KS = [114, 390, 627, 633, 732, 921, 975]
Z = 10 ** 19
DSTART = Z // 54 + 1        # 185185185185185186
L = 2 ** 25                 # d values per unit (~2 minutes on one core)


def unit(index, state):
    k = KS[index % len(KS)]
    d0 = DSTART + (index // len(KS)) * L
    return {"k": k, "d0": d0, "d1": d0 + L, "z": Z}


def argv(u, ctx):
    return [os.path.join(ctx["bin"], "cubes"), str(u["k"]), str(u["d0"]), str(u["d1"]), str(u["z"])]


def solve_exact(k, d, z):
    """Given a (d, z) survivor, return (x, y, z) if it really is a solution."""
    rhs = k - z ** 3
    if rhs == 0:
        return None
    s = d if rhs > 0 else -d                   # s = x + y has the sign of k - z^3
    delta = 3 * d * (4 * abs(rhs) - d ** 3)
    if delta < 0:
        return None
    r = math.isqrt(delta)
    if r * r != delta or r % (3 * d):
        return None
    t = r // (3 * d)                           # t = |x - y|
    if (s + t) % 2:
        return None
    x, y = (s + t) // 2, (s - t) // 2
    if x ** 3 + y ** 3 + z ** 3 == k:
        return (x, y, z)
    return None


def parse(u, proto):
    d = proto["done"]
    if int(d["cases"]) != u["d1"] - u["d0"]:
        raise ValueError("wrong number of d values")
    cands = list(proto["cands"])
    for note in proto["notes"]:
        sol = solve_exact(int(note["k"]), int(note["d"]), int(note["z"]))
        if sol:
            x, y, z = sol
            cands.append({"kind": "solution", "summary": "%d^3 + %d^3 + %d^3 = %d" % (x, y, z, u["k"]),
                          "data": {"k": u["k"], "x": str(x), "y": str(y), "z": str(z)}})
    return {"cases": int(d["cases"]), "candidates": cands, "z_checked": int(d.get("z_checked", 0))}


def frontier(state, ledger):
    blocks = ledger.frontier // len(KS)
    top = DSTART + blocks * L
    return {"text": "for all 7 open k: no solution with d = |x+y| < %.6e and |z| <= 10^19 "
                    "(Booker-Sutherland covered d <= 1.85e17)" % top,
            "value": top - DSTART}


def _found(k):
    def check(result):
        sums = [int(c["data"]["k"]) for c in result["candidates"]]
        assert sums == [k], result["candidates"]
    return check


MINI = [
    {"name": "k=33 (Booker 2019)", "unit": {"k": 33, "d0": 87723532424289, "d1": 87723532426289,
                                           "z": 3 * 10 ** 15}, "check": _found(33)},
    {"name": "k=42 (Booker-Sutherland 2019)", "unit": {"k": 42, "d0": 102980666257459,
                                                      "d1": 102980666259459, "z": 13 * 10 ** 15},
     "check": _found(42)},
]


def corruptions(cand):
    d = cand["data"]
    yield {**cand, "data": {**d, "z": str(int(d["z"]) + 1)}}
    yield {**cand, "data": {**d, "k": d["k"] + 1}}
    yield {**cand, "data": {**d, "x": "1.5"}}
