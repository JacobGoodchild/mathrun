"""Magic square of squares. Unit i covers centres e^2 for e in [1 + i*L, 1 + (i+1)*L)."""
import os

START = 1
L = 500_000_000      # e values per unit (~2 minutes on one core)


def unit(index, state):
    a = START + index * L
    return {"a": a, "b": a + L}


def argv(u, ctx):
    return [os.path.join(ctx["bin"], "magic"), str(u["a"]), str(u["b"])]


def parse(u, proto):
    d = proto["done"]
    if int(d["cases"]) != u["b"] - u["a"]:
        raise ValueError("wrong count")
    return {"cases": int(d["cases"]), "candidates": proto["cands"],
            "three_pairs": int(d.get("three_pairs", 0))}


def merge(state, u, result):
    state["three_pairs"] = state.get("three_pairs", 0) + result.get("three_pairs", 0)


def frontier(state, ledger):
    top = START + ledger.frontier * L
    return {"text": "no solution with centre e^2, e < %.4e (entries up to ~%.1e)" % (top, 2.0 * top * top),
            "value": top}


MINI = [{"name": "e < 3*10^6", "unit": {"a": 1, "b": 3_000_000},
         "check": lambda r: None if r["candidates"] == [] else (_ for _ in ()).throw(AssertionError("cand"))}]
