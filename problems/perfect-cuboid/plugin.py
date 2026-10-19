"""Perfect cuboid. Unit i covers odd edges a in [START + i*L, START + (i+1)*L)."""
import os

START = 25_000_000_000_001    # odd edge > 2.5e13 published bound (Matson)
L = 2_000_000                 # range per unit (1e6 odd edges, ~2 minutes)


def unit(index, state):
    a = START + index * L
    return {"a": a, "b": a + L}


def argv(u, ctx):
    return [os.path.join(ctx["bin"], "cuboid"), str(u["a"]), str(u["b"])]


def parse(u, proto):
    d = proto["done"]
    want = len(range(u["a"] | 1, u["b"], 2))
    if int(d["cases"]) != want:
        raise ValueError("searcher checked %s odd edges, expected %d" % (d["cases"], want))
    return {"cases": int(d["cases"]), "candidates": proto["cands"],
            "euler_bricks": int(d.get("euler_bricks", 0))}


def merge(state, u, result):
    state["euler_bricks"] = state.get("euler_bricks", 0) + result.get("euler_bricks", 0)


def frontier(state, ledger):
    top = START + ledger.frontier * L
    return {"text": "no perfect cuboid with odd edge < %.7e (%d Euler bricks met on the way)" % (
        top, state.get("euler_bricks", 0)), "value": top}


def _small(result):
    assert result["candidates"] == []
    assert result["euler_bricks"] == 52, result["euler_bricks"]


MINI = [{"name": "Euler bricks with odd edge < 2000", "unit": {"a": 3, "b": 2000}, "check": _small},
        {"name": "window at 2.5e13", "unit": {"a": START, "b": START + 20000},
         "check": lambda r: None}]
