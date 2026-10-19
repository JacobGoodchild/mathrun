# Adding a problem to mathrun

A problem is one folder under `problems/`. The runner, dashboard, candidate pipeline, guards and selftest pick it up automatically. Nothing in `mathrun_core/` needs changing.

## Steps

1. **Research first.** Find the current record or verified bound (with sources and the date), and the best known algorithm. Check the problem isn't already solved. Add a row to `docs/problem-shortlist.md`.
2. `cp -r problems/_template problems/<slug>`. Folders starting with `_` are ignored, so the template never runs.
3. Write the searcher (`searcher.c`, or rename it and update the `Makefile` and `binaries`):
   - Take the unit's parameters on the command line. Print `CAND {json}` for anything interesting, and `DONE {"cases": N}` as the **last** line. A unit with no `DONE` line, or a non-zero exit, is never counted.
   - Budget time with `mr_cpu_seconds()` (CPU time), not the wall clock, so pausing doesn't eat the budget.
   - Never print more than a handful of `CAND` lines. More than 25 in one unit is treated as a bug.
   - Use `__int128` or big integers (`common/bignum.h`: GMP if installed, otherwise the vendored mini-gmp) wherever 64 bits could overflow. Add a test at the boundary.
4. Write `plugin.py`:
   - `unit(index, state)`: what unit number `index` covers. Units must tile the search space with **no gaps and no overlaps**. Start just past the published frontier.
   - `argv(unit, ctx)`: the command line.
   - `parse(unit, proto)`: check the `DONE` line matches what the unit should have covered, and return `cases` and `candidates`.
   - `frontier(state, ledger)`: the honest claim. Only `ledger.frontier` (the first unfinished unit) may be claimed as "searched up to". The dashboard adds "except candidates under review" and "UNTRUSTED" by itself.
   - Optional: `initial_state()`, `merge()` (keep bests, as in matrix-multiplication), `exhausted()` (the search has an end), `corruptions()` (damaged candidates the verifier must reject).
   - `MINI`: one or more short runs (under 30 s) that **reproduce known results**, used by `./mathrun selftest`.
5. Write `verify.py`, the **independent** verifier:
   - different code, written a different way, with exact arithmetic (Python integers);
   - exit 0 = verified, 1 = rejected (the runner then pauses the problem as a suspected searcher bug), 2 = couldn't decide;
   - never trust the searcher's own claim; recompute everything from the candidate data.
6. Write `test_<slug>.py` (unittest): reproduce known solutions, records or non-existence results; cross-check against brute force on small ranges; fuzz the verifier with wrong answers.
7. Write `README.md` from the template headings: plain English, sources, date checked, speed, realistic odds.
8. `./mathrun install && ./mathrun selftest`. It must pass before you commit.
9. Get a fresh reviewer (someone or something that didn't write the code) to look for off-by-one errors, overflow, over-eager pruning, and gaps between "searched" and "claimed searched".

## Good to know

- Units should take 1–4 minutes on one core (`unit_seconds`), so turning the computer off loses little.
- Work happens in `data/work/<slug>/` (the plugin's `ctx["work"]`). Outputs of failed units are kept in `data/work/<slug>/failed/` for debugging.
- Checkpoints live in `data/state/<slug>.json` and are written atomically. Never edit them while the runner is going.
- Searchers must not use the network. Third-party code must be vendored as source with its licence recorded in `CREDITS.md`.
