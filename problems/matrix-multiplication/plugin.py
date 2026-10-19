"""Fast matrix multiplication: flip-graph search over GF(2).

Units rotate through a list of formats. The best scheme found so far for
each format is kept in the checkpoint, and each unit continues the random
walk from it, so progress is never lost between runs.
"""
import os

# Best known ranks from Sedoglavic's catalogue (fmm.univ-lille.fr, read
# 2026-10-19; over any coefficient ring) and, where lower, GF(2)-only
# records. A candidate must go strictly below "target".
FORMATS = [
    # (n, m, p, catalogue_rank, gf2_record_or_None, weight)
    (3, 3, 3, 23, None, 3),
    (4, 4, 4, 48, 47, 3),      # 47 over GF(2): AlphaTensor (Fawzi et al. 2022)
    (3, 4, 5, 47, None, 2),
    (4, 4, 5, 61, None, 2),
    (4, 5, 5, 76, None, 2),
    (5, 5, 5, 93, None, 2),
    (3, 3, 4, 29, None, 1),
    (3, 3, 5, 36, None, 1),
    (3, 4, 4, 38, None, 1),
    (2, 4, 5, 32, None, 1),
    (2, 5, 5, 40, None, 1),
    (3, 5, 5, 58, None, 1),
    (3, 3, 6, 40, None, 1),
    (4, 4, 6, 73, None, 1),
]
SCHEDULE = [i for i, f in enumerate(FORMATS) for _ in range(f[5])]

# Strassen's algorithm in this program's bit layout (A bit i*m+j, B bit j*p+k, C bit k*n+i).
STRASSEN = [[5, 15, 8], [13, 13, 9], [2, 8, 5], [15, 12, 1], [1, 2, 12], [8, 5, 10], [12, 1, 3]]


def key(n, m, p):
    return "%dx%dx%d" % (n, m, p)


def target(fmt):
    n, m, p, cat, gf2, _ = fmt
    return min(cat, gf2) if gf2 else cat


def kron(s1, d1, s2, d2):
    """Tensor (Kronecker) product of two schemes: <n1,m1,p1> x <n2,m2,p2>."""
    n1, m1, p1 = d1
    n2, m2, p2 = d2
    N, M, P = n1 * n2, m1 * m2, p1 * p2

    def bits(x, rows, cols):
        return [(b // cols, b % cols) for b in range(rows * cols) if x >> b & 1]

    out = []
    for a1, b1, c1 in s1:
        for a2, b2, c2 in s2:
            A = sum(1 << ((i1 * n2 + i2) * M + (j1 * m2 + j2))
                    for i1, j1 in bits(a1, n1, m1) for i2, j2 in bits(a2, n2, m2))
            B = sum(1 << ((j1 * m2 + j2) * P + (k1 * p2 + k2))
                    for j1, k1 in bits(b1, m1, p1) for j2, k2 in bits(b2, m2, p2))
            C = sum(1 << ((k1 * p2 + k2) * N + (i1 * n2 + i2))
                    for k1, i1 in bits(c1, p1, n1) for k2, i2 in bits(c2, p2, n2))
            out.append([A, B, C])
    return out


def start_scheme(state, fmt):
    n, m, p = fmt[:3]
    best = state.get("best", {}).get(key(n, m, p))
    if best:
        return best["terms"]
    if (n, m, p) == (4, 4, 4):
        return kron(STRASSEN, (2, 2, 2), STRASSEN, (2, 2, 2))  # rank 49
    return None


def initial_state():
    return {"best": {}}


def unit(index, state):
    fmt = FORMATS[SCHEDULE[index % len(SCHEDULE)]]
    n, m, p = fmt[:3]
    best = state.get("best", {}).get(key(n, m, p))
    tgt = target(fmt) if not best else min(target(fmt), best["rank"])  # never re-report our own find
    return {"n": n, "m": m, "p": p, "seed": 1000003 * index + 17, "target": tgt,
            "record": target(fmt), "start": start_scheme(state, fmt)}


def argv(u, ctx):
    start = "-"
    if u.get("start"):
        start = os.path.join(ctx["work"], "start-%dx%dx%d-%d.txt" % (u["n"], u["m"], u["p"], u["seed"]))
        with open(start, "w") as f:
            f.write("%d %d %d %d\n" % (u["n"], u["m"], u["p"], len(u["start"])))
            for a, b, c in u["start"]:
                f.write("%d %d %d\n" % (a, b, c))
    return [os.path.join(ctx["bin"], "flipgraph"), str(u["n"]), str(u["m"]), str(u["p"]),
            str(u["seed"]), str(int(u.get("seconds", ctx["seconds"]))), start, str(u["target"])]


def parse(u, proto):
    bests = proto["bests"]
    if len(bests) != 1:
        raise ValueError("expected exactly one BEST line")
    b = bests[0]["data"]
    if (b["n"], b["m"], b["p"]) != (u["n"], u["m"], u["p"]) or b["rank"] != len(b["terms"]):
        raise ValueError("BEST does not match the unit")
    return {"cases": int(proto["done"]["cases"]), "candidates": proto["cands"],
            "scheme": b, "bests": []}


def merge(state, u, result):
    b = result["scheme"]
    k = key(b["n"], b["m"], b["p"])
    old = state.setdefault("best", {}).get(k)
    if old is None or b["rank"] <= old["rank"]:
        # same rank: still keep the end of the walk, so the next unit continues from there
        state["best"][k] = {"rank": b["rank"], "terms": b["terms"]}
        if old is None or b["rank"] < old["rank"]:
            result["bests"].append({"summary": "<%s> reached rank %d over GF(2) (record %d)" % (
                k.replace("x", ","), b["rank"], u.get("record", u["target"])), "format": k,
                "rank": b["rank"]})


def frontier(state, ledger):
    best = state.get("best", {})
    parts, gap = [], 0
    for fmt in FORMATS:
        k = key(*fmt[:3])
        if k in best:
            parts.append("%s: %d (rec %d)" % (k, best[k]["rank"], target(fmt)))
            gap += best[k]["rank"] - target(fmt)
    if not parts:
        return {"text": "not started", "value": None}
    return {"text": "; ".join(parts[:6]) + (" …" if len(parts) > 6 else ""),
            "value": gap, "note": "value = total ranks above record, lower is better"}


def exhausted(state, ledger):
    return False


def _expect(rank):
    def check(result):
        assert result["scheme"]["rank"] == rank, result["scheme"]["rank"]
    return check


MINI = [
    {"name": "Strassen 2x2x2 -> 7", "unit": {"n": 2, "m": 2, "p": 2, "seed": 1, "target": 8,
                                              "start": None}, "seconds": 3, "check": _expect(7)},
    {"name": "3x3x3 -> 23 (Laderman)", "unit": {"n": 3, "m": 3, "p": 3, "seed": 1, "target": 24,
                                                 "start": None}, "seconds": 25, "check": _expect(23)},
]


def corruptions(cand):
    d = cand["data"]
    t = [list(x) for x in d["terms"]]
    bad1 = [list(x) for x in t]
    bad1[0][0] ^= 1
    yield {**cand, "data": {**d, "terms": bad1}}
    yield {**cand, "data": {**d, "terms": t[1:], "rank": len(t) - 1}}
    yield {**cand, "data": {**d, "rank": len(t) - 1}}
    yield {**cand, "data": {**d, "terms": t + [t[0]], "rank": len(t) + 1}}
