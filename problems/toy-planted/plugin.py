"""Toy plugin: unit i covers n in [i*UNIT, (i+1)*UNIT). Answer planted at n=416041631."""
import os

UNIT = 10_000_000
PLANTED = 416041631


def unit(index, state):
    return {"a": index * UNIT, "b": (index + 1) * UNIT,
            "lie": os.environ.get("MATHRUN_TOY_LIE") == "1"}


def argv(u, ctx):
    return [os.path.join(ctx["bin"], "toy"), str(u["a"]), str(u["b"])] + (["lie"] if u["lie"] else [])


def parse(u, proto):
    return {"cases": int(proto["done"]["cases"]), "candidates": proto["cands"]}


def frontier(state, ledger):
    n = ledger.frontier * UNIT
    return {"text": "all n < %d checked" % n, "value": n}


def _check(result):
    ns = [c["data"]["n"] for c in result["candidates"]]
    assert ns == [PLANTED], ns


MINI = [{"name": "planted", "unit": {"a": PLANTED - 1000, "b": PLANTED + 1000, "lie": False},
         "check": _check}]


def corruptions(cand):
    for delta in (1, -1, 2**32):
        bad = {**cand, "data": {"n": cand["data"]["n"] + delta}}
        yield bad
