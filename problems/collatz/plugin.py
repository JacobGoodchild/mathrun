"""Collatz: unit i checks n in [2^71 + i*L, 2^71 + (i+1)*L)."""
import os

START = 2 ** 71          # verified bound (Barina, J. Supercomputing 2025)
K = 26                   # sieve modulus 2^K
L = 2 ** 37              # numbers per unit (~4 minutes on one core)
MAX_PY_STEPS = 10 ** 7


def unit(index, state):
    a = START + index * L
    return {"hi": a >> 64, "lo": a & (2 ** 64 - 1), "count": L, "k": K}


def argv(u, ctx):
    return [os.path.join(ctx["bin"], "collatz"), str(u["hi"]), str(u["lo"]), str(u["count"]), str(u["k"])]


def drops(n, limit=MAX_PY_STEPS):
    """Exact big-integer check that n's trajectory goes below n."""
    v, steps = n, 0
    while v >= n:
        v = v // 2 if v % 2 == 0 else (3 * v + 1) // 2
        steps += 1
        if steps > limit:
            return False
    return True


def parse(u, proto):
    if int(proto["done"]["cases"]) != u["count"]:
        raise ValueError("wrong count")
    cands = list(proto["cands"])
    # 128-bit overflow cases are finished off here with Python's big integers.
    for note in proto["notes"]:
        n = int(note["overflow"])
        if not drops(n):
            cands.append({"kind": "solution", "summary": "n=%d did not drop below itself" % n,
                          "data": {"n": str(n)}})
    best = proto["bests"][0] if proto["bests"] else None
    return {"cases": u["count"], "candidates": cands, "best": best, "bests": []}


def merge(state, u, result):
    b = result.get("best")
    if b and b["glide"] > state.get("max_glide", 0):
        state["max_glide"] = b["glide"]
        state["max_glide_n"] = b["n"]
        result["bests"].append({"summary": "longest glide so far: n=%s, %d steps" % (b["n"], b["glide"]),
                                "glide": b["glide"]})


def frontier(state, ledger):
    top = START + ledger.frontier * L
    beyond = top - START
    return {"text": "all n < 2^71 + %.3e checked (2^71 = published bound)" % beyond,
            "value": beyond}


def _mini_check(result):
    assert result["candidates"] == []
    assert result["cases"] == 2 ** 30
    assert result["best"]["glide"] > 0


MINI = [{"name": "2^30 numbers above 2^71", "unit": {"hi": 128, "lo": 0, "count": 2 ** 30, "k": 20},
         "check": _mini_check}]
