"""Beal conjecture: all bases A, B, C <= CMAX, exponents 3..7.

Unit i handles A in [a(i), a(i+1)) (with every B <= A), where a(i) grows
like sqrt(i) so every unit has about the same number of (A, B) pairs.
"""
import math
import os

CMAX = 2 ** 21          # 2,097,152: 8x the published 250,000 for exponents <= 7
XMIN, XMAX = 3, 7
Q = 300_000_000         # ~ 2 * pairs per unit (~2.5 minutes on one core)


def a_of(i):
    return min(math.isqrt(i * Q) + 1, CMAX + 1)


def unit(index, state):
    return {"a0": a_of(index), "a1": a_of(index + 1), "cmax": CMAX}


def argv(u, ctx):
    return [os.path.join(ctx["bin"], "beal"), str(u["a0"]), str(u["a1"]), str(u["cmax"]),
            str(XMIN), str(XMAX)]


def exhausted(state, ledger):
    return a_of(ledger.next) > CMAX and a_of(ledger.frontier) > CMAX


def parse(u, proto):
    d = proto["done"]
    want = sum(range(u["a0"], u["a1"]))
    if u["a1"] > u["a0"] and int(d["cases"]) != want:
        raise ValueError("searcher checked %s pairs, expected %d" % (d["cases"], want))
    return {"cases": int(d["cases"]), "candidates": proto["cands"],
            "trivial": int(d.get("exact_hits", 0)) - int(d.get("coprime", 0))}


def merge(state, u, result):
    state["non_coprime_solutions"] = state.get("non_coprime_solutions", 0) + result["trivial"]


def frontier(state, ledger):
    top = a_of(ledger.frontier) - 1
    if top >= CMAX:
        return {"text": "finished: no counterexample with A, B, C <= %d, exponents %d-%d" % (CMAX, XMIN, XMAX),
                "value": CMAX}
    return {"text": "no counterexample with A, B, C <= %d (exponents %d-%d); target %d" % (
        top, XMIN, XMAX, CMAX), "value": top}


def _mini(result):
    assert result["candidates"] == []
    assert result["trivial"] == 58, result


MINI = [{"name": "bases <= 200", "unit": {"a0": 1, "a1": 201, "cmax": 200}, "check": _mini}]
