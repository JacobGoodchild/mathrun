"""Brocard's problem. Unit i covers n in [START + i*L, START + (i+1)*L)."""
import os

START = 10 ** 15          # published bound: no solutions for n <= 10^15
L = 250_000_000           # n values per unit (~2 minutes on one core)


def unit(index, state):
    a = START + index * L
    return {"a": a, "b": a + L}


def argv(u, ctx):
    return [os.path.join(ctx["bin"], "brocard"), str(u["a"]), str(u["b"])]


def parse(u, proto):
    done = proto["done"]
    if int(done["cases"]) != u["b"] - u["a"]:
        raise ValueError("searcher covered %s values, expected %d" % (done["cases"], u["b"] - u["a"]))
    return {"cases": int(done["cases"]), "candidates": proto["cands"]}


def frontier(state, ledger):
    top = START + ledger.frontier * L
    beyond = top - START
    return {"text": "no solution for any n < %.6e (%s beyond the published 10^15)" % (
        top, "%.3g" % beyond if beyond else "nothing yet"), "value": top}


def _small(result):
    assert sorted(c["data"]["n"] for c in result["candidates"]) == [4, 5, 7], result
    assert result["cases"] == 999


def _big(result):
    assert result["candidates"] == [], result
    assert result["cases"] == 2_000_000


MINI = [
    {"name": "known solutions 4,5,7", "unit": {"a": 1, "b": 1000}, "check": _small},
    {"name": "window at 10^15", "unit": {"a": START, "b": START + 2_000_000}, "check": _big},
]


def corruptions(cand):
    n = cand["data"]["n"]
    for bad in (n + 1, n + 2, 6, 8, START + 12345):
        if bad in (4, 5, 7):
            continue
        yield {**cand, "data": {**cand["data"], "n": bad}}
    yield {**cand, "data": {"n": str(n)}}
    yield {**cand, "data": {}}
