"""Cap sets in F_3^7 and F_3^8 by local search; the best cap per dimension is kept."""
import os

# (dimension, best known size, weight in the rotation)
DIMS = [(7, 236, 1), (8, 512, 1)]     # 236: Edel (2004); 512: FunSearch (Romera-Paredes et al. 2023)
SCHEDULE = [i for i, d in enumerate(DIMS) for _ in range(d[2])]


def initial_state():
    return {"best": {}}


def unit(index, state):
    n, rec, _ = DIMS[SCHEDULE[index % len(SCHEDULE)]]
    best = state.get("best", {}).get(str(n))
    target = max(rec, best["size"] if best else 0)   # only report beating the record (or our own best)
    return {"n": n, "seed": 7919 * index + 11, "target": target, "record": rec,
            "start": best["points"] if best else None}


def argv(u, ctx):
    start = "-"
    if u.get("start"):
        start = os.path.join(ctx["work"], "start-%d-%d.txt" % (u["n"], u["seed"]))
        with open(start, "w") as f:
            f.write("\n".join(str(p) for p in u["start"]) + "\n")
    return [os.path.join(ctx["bin"], "capset"), str(u["n"]), str(u["seed"]),
            str(int(u.get("seconds", ctx["seconds"]))), start, str(u["target"])]


def parse(u, proto):
    if len(proto["bests"]) != 1:
        raise ValueError("expected one BEST line")
    b = proto["bests"][0]["data"]
    if b["n"] != u["n"] or b["size"] != len(b["points"]):
        raise ValueError("BEST does not match unit")
    return {"cases": int(proto["done"]["cases"]), "candidates": proto["cands"], "cap": b, "bests": []}


def merge(state, u, result):
    b = result["cap"]
    old = state.setdefault("best", {}).get(str(b["n"]))
    if old is None or b["size"] >= old["size"]:
        state["best"][str(b["n"])] = {"size": b["size"], "points": b["points"]}
        if old is None or b["size"] > old["size"]:
            result["bests"].append({"summary": "F_3^%d: cap of size %d (record %d)" % (
                b["n"], b["size"], u["record"]), "size": b["size"]})


def frontier(state, ledger):
    best = state.get("best", {})
    parts = ["dim %d: %s (record %d)" % (n, best[str(n)]["size"] if str(n) in best else "-", rec)
             for n, rec, _ in DIMS]
    gap = sum(rec - best[str(n)]["size"] for n, rec, _ in DIMS if str(n) in best)
    return {"text": "; ".join(parts), "value": gap if best else None}


def _size(k):
    def check(result):
        assert result["cap"]["size"] == k, result["cap"]["size"]
    return check


MINI = [  # the true maximum caps are known in low dimensions: 4, 9, 20
    {"name": "dim 3 -> 9", "unit": {"n": 3, "seed": 1, "target": 8, "record": 9, "start": None},
     "seconds": 10, "check": _size(9)},
    {"name": "dim 4 -> 20", "unit": {"n": 4, "seed": 1, "target": 19, "record": 20, "start": None},
     "seconds": 20, "check": _size(20)},
]


def corruptions(cand):
    d = cand["data"]
    pts = list(d["points"])
    yield {**cand, "data": {**d, "points": pts + [pts[0]], "size": len(pts) + 1}}
    yield {**cand, "data": {**d, "size": len(pts) + 1}}
    # add a point that completes a line through the first two
    a, b = pts[0], pts[1]
    n = d["n"]
    da = [(a // 3 ** i) % 3 for i in range(n)]
    db = [(b // 3 ** i) % 3 for i in range(n)]
    t = sum(((-(x + y)) % 3) * 3 ** i for i, (x, y) in enumerate(zip(da, db)))
    yield {**cand, "data": {**d, "points": pts + [t], "size": len(pts) + 1}}
