You are building, overnight and on your own, **mathrun**: a home-run research platform that attacks **famous, widely recognised open problems** with plain, AI-free search programs. The searchers run on my own computer (a **Linux Mint desktop computer**) whenever it's switched on. They pause cleanly when it's off and resume where they left off. A dashboard shows the status of every problem: progress, frontier reached, speed, candidates found, and history.

The repo is empty right now. Your first job is to save this whole brief as `CLAUDE.md` in the repo root, so every later session (and you, after any context reset) can re-read it. Keep a progress log at the bottom.

## 0. Time and working rules: read this first

- **Work continuously until 05:40 UTC on Monday 19 October 2026 (06:40 UK time).** Do not stop early, do not ask me questions, and do not wait for approval. I am asleep.
- Run `date -u` at the start of every task and keep track of how much time is left. Finishing the plan is never a reason to stop. If you run out of planned items, go to the backlog (section 9) and keep going until the deadline.
- In the **last 20 minutes**, stop starting new work. Make sure `main` is clean and works, then write the morning summary (section 10).
- Make every sensible decision yourself and record each one in the progress log, one line per decision.
- Do one feature or one searcher per commit. Run the tests before every commit and push to `main` after each green commit.
- **Never leave `main` broken.** If something breaks and you can't fix it quickly, revert it.
- Use the web freely while building (checking each problem's current status, papers, algorithms). The searchers themselves must not need the internet (see section 2).
- You can only run short test runs here. The real long runs happen on my computer. Build everything so it's ready to run there with one command.

## 1. The goal in one paragraph

Instead of paying AI rates for hours of loops, the AI (you, tonight) does the thinking **once**: choosing the right problems, researching the best known methods and current records, and writing fast, correct, tested searchers. After that, plain code grinds **for free, indefinitely**, on my computer. The platform is easy to add new problems to, so it can grow to dozens of searchers over time. **Correctness and honesty beat everything.** A false "counterexample found!" is the worst possible bug, so every candidate is re-checked by a separate, independent verifier before anything is reported.

## 2. Safety rules (non-negotiable)

These rules protect my computer, my data and my GitHub account. Follow every one.

**GitHub: zero risk to the account**
- **No GitHub Actions at all.** No `.github/workflows/` folder, ever. No GitHub-hosted compute is used for anything. All searching happens on my computer.
- GitHub is used only for normal things: storing the code, and optionally hosting the dashboard on GitHub Pages ("Deploy from a branch", `main` → `/docs`), which needs no workflow.
- **Publishing the dashboard is off by default.** When I switch it on, `mathrun publish` pushes a small status snapshot (under 1 MB) **at most once an hour**, and only while the computer is on. Raw logs, checkpoints and big data never go into git (`.gitignore` them). Commits are small JSON summaries only.

**My computer**
- No `sudo`, nothing installed system-wide, and no files written outside the repo folder (plus an optional user-level autostart file, only if I run the command that creates it).
- Searchers run at **lowest priority** (`nice 19`, idle I/O class). By default they use **all cores but one**, which is configurable.
- **Computer guards**: pause automatically when the CPU temperature is above a configurable limit (default 85°C; read `/sys/class/thermal` or `sensors`, and if it can't be read, fall back to a safe duty cycle), and back off while I'm actively using the computer (optional "only when idle" mode, plus a "gaming mode" switch that pauses everything). Resume automatically when conditions are fine again.
- A disk-space cap for data and logs (default 5 GB total) with automatic log rotation.
- Saving progress and quitting must be clean: `mathrun stop` or a shutdown must never corrupt a checkpoint. Write to a temp file, then rename (atomic writes).

**Code and network**
- No network access from searchers. The only optional network actions are:
  - `mathrun publish` (git push);
  - an optional phone/email alert through **ntfy.sh**, off until I configure it (message text only: problem name and "candidate verified, check dashboard").
- No cryptomining, no remote code, no `eval` of downloaded content, and no downloads at runtime.
- Any third-party code (e.g. a SAT solver such as CaDiCaL or Kissat, MIT) is **vendored as source in the repo**, licence recorded in `CREDITS.md`, and built locally by the install script. Only use well-known, properly licensed code.
- **No secrets in git.** Personal settings (ntfy topic, git remote preferences) live in `config.local.toml`, which is `.gitignore`d. Commit a `config.example.toml` instead.
- The local dashboard server binds to `127.0.0.1` only (never exposed to the network).

## 3. Architecture

- **Languages:** Python 3 (standard library only) for the runner, scheduler, dashboard data and CLI. **C (gcc -O3)** for every hot search loop, or another compiled language if a problem truly needs it, plus exact big-integer arithmetic where needed (e.g. GMP if available, with a safe fallback). Everything must build on a stock Linux Mint with `build-essential` and `python3`. The install script checks for these and prints the exact `apt` command if something's missing; it never runs it itself.
- **CLI:** `./mathrun install | start | stop | status | dashboard | publish | add-autostart | remove-autostart | selftest`.
- **Runner:**
  - a long-lived background process that hands out work units to searchers across cores;
  - restarts crashed searchers (with back-off) and checkpoints every few minutes;
  - records progress history (frontier over time, cases checked, speed) to small JSON files.
- **Plugin layout:** one folder per problem under `problems/<slug>/`, each containing:
  - `README.md`: the problem in plain English; why it's famous; **current status with sources and the date checked**; the best known bounds or verification limits; exactly what counts as a win; and an honest note on the realistic odds;
  - the searcher (C) plus a small `problem.toml` (name, category, how to split work, checkpoint format, priority weight);
  - an **independent verifier**: different code, written differently, using exact arithmetic (Python big integers, or a SAT proof checker such as DRAT-trim for SAT results) that re-checks any candidate from scratch;
  - tests that **reproduce known results** (small known solutions, previously found records, known non-existence at small sizes) to prove the searcher is correct before it's trusted.
- **Candidate pipeline:**
  1. A searcher flags a candidate.
  2. It is saved immediately.
  3. The independent verifier checks it.
  4. Only if it passes is it marked **"VERIFIED CANDIDATE — needs human review"**, which triggers alerts.

  Failed verifications are logged as searcher bugs and the searcher is paused. Wording is always careful: never "proved" or "solved", always "candidate, independently verified by computer, needs expert review".
- **Alerts:** a desktop notification (`notify-send`) plus the optional ntfy push or email. Also highlighted at the top of the dashboard.
- **Dashboard** (static HTML/CSS/JS in `docs/`, reading `docs/status/*.json`):
  - a sleek, modern, slightly colourful design;
  - one card per problem showing status, frontier vs the world record, speed, total compute-hours spent, last checkpoint and a sparkline of progress;
  - a detail page per problem with its README, history chart and candidates;
  - a top banner for any verified candidate, and a machine panel (running/paused and why: heat, in use, stopped);
  - works locally via `mathrun dashboard` (opens `http://127.0.0.1:<port>`) and on GitHub Pages when publishing is on;
  - no external libraries from the web (vendor anything you use).
- **Work splitting** has to suit a computer that's on for a few hours at a time: lots of small work units, each finishing in minutes, so turning off loses at most a few minutes of work.

## 4. Choosing the problems

I want **major, widely recognised problems**: the kind of thing that, if a home computer made progress, Numberphile, Quanta or the wider maths/CS community would actually care about. I do **not** want closed-form formula hunts, obscure sequence trivia or niche Ramsey bounds.

Below is my candidate list. For **each** one:
1. Check its **current status on the web** (several of these facts are from memory and may be out of date). Some may have been solved recently.
2. Score it from 1–5 on three things: **fame** (would a win be recognised widely?), **home-PC leverage** (can a computer running a few hours a day realistically push the frontier or have a genuine shot?), and **verifiability** (is a win cleanly checkable?).
3. Write the results to `docs/problem-shortlist.md` with sources.

Then build searchers for the best ones in score order, aiming for **10–12 working searchers by morning**. Drop anything already solved, or where a home computer adds nothing beyond what huge projects have already done. Say so in the shortlist instead.

**Number theory**
- **Sum of three cubes:** x³+y³+z³=k for the remaining unsolved k below 1000 (believed to be 114, 390, 627, 633, 732, 921, 975; check). k=33 and k=42 were famous 2019 news. Use the Booker / Booker–Sutherland method.
- **Collatz conjecture:** cycle and divergence search beyond the verified bound (about 2^71 as of 2025; check), plus new delay/glide record hunting.
- **Beal conjecture** (US$1M prize): counterexample search beyond published bounds.
- **Euler's sum of powers:** find a sixth power equal to a sum of five (or six) sixth powers. Check what's known; the k=5 counterexample by Lander and Parkin (1966) is a famous computer-search story.
- **Perfect cuboid / perfect Euler brick:** extend the searched range beyond the published bounds.
- **3×3 magic square of squares** (the "Parker square" problem).
- **Brocard's problem:** n! + 1 = m², extend beyond the searched bound.
- **Maximal and first-occurrence prime gaps:** new record gaps, which are tracked in public records tables.
- **Riemann hypothesis:** compute and verify zeros of ζ in a fresh high window (Odlyzko–Schönhage / Riemann–Siegel). Mainly a showpiece; be honest about how it compares to the big projects.
- **Wall–Sun–Sun primes** (none known) and **Wieferich primes:** extend beyond the searched bounds if feasible.
- **Goldbach (strong) verification** beyond 4×10^18: probably low value; assess honestly.
- **Lychrel / 196:** recreational, probably drop; assess.

**Geometry and combinatorics**
- **Hadwiger–Nelson problem (chromatic number of the plane):** search for a 6-chromatic unit-distance graph (SAT + graph constructions). An amateur, Aubrey de Grey, found the first 5-chromatic one in 2018, which was huge news.
- **Happy ending problem (Erdős–Szekeres), 7-gon:** do 33 points in general position always contain a convex heptagon? SAT-based search, building on the 17-point hexagon result.
- **Kissing numbers and sphere packings** in dimensions about 5–24: better configurations than current records. AlphaEvolve improved dimension 11 in 2025; check the records tables.
- **Cap sets** in F₃ⁿ for n = 7, 8 and beyond: bigger cap sets than known (FunSearch 2023 was a Nature paper).
- **Heilbronn triangle problem and the no-three-in-line problem:** small-n records.
- **Lonely runner conjecture:** check current status (recent progress on more runners) and whether computation helps.
- **Minimal superpermutations, n = 7:** beat the best known length (the famous anonymous-internet-post and Greg Egan story); check the current upper bound.

**Graph theory and design theory**
- **Conway's 99-graph problem** (US$1000 Conway prize): an srg(99,14,1,2), a search under symmetry assumptions.
- **Moore graph of degree 57:** existence search under symmetry assumptions (famous open case).
- **Three mutually orthogonal Latin squares of order 10.**
- **Reconstruction conjecture:** verified up to 11 vertices; assess whether extending to 12 is feasible in pieces.
- **Hadamard matrices:** order 668 was just solved (human + AI, per Epoch AI). Find the **next** smallest open order and assess it.
- **R(5,5):** the most famous Ramsey number, bounds 43 ≤ R(5,5) ≤ 46 (check). Include only if the method is genuinely new; otherwise drop.

**Computer science**
- **Fast matrix multiplication:** new low-rank decompositions of small matrix-multiplication tensors (e.g. 4×4, 5×5, rectangular cases) using flip-graph search (Kauers & Moosbauer found records on ordinary hardware). AlphaTensor and AlphaEvolve made headlines here. Check the current records table.
- **Optimal sorting networks:** minimal size and depth for n ≥ 13 (Knuth-famous); SAT and symmetry methods.
- **Černý conjecture:** search for synchronizing automata with unusually long shortest reset words.
- **Addition chains / Scholz conjecture:** extend verification.

Feel free to add better candidates you find while researching, as long as they meet the fame test. Don't use Busy Beaver, GIMPS/Mersenne primes or Erdős-problem-site items; I've ruled those out.

## 5. For each searcher you build

- Research the best known algorithm and current record first. Implement the strongest method you can, not a naive loop. Note the papers in the README.
- **Reproduce known results first** in tests (e.g. known sum-of-three-cubes solutions, known 5-chromatic graphs, known cap-set sizes, known optimal sorting networks for small n).
- **Start where the known frontier ends.** Searching ground that's already covered is wasted time. If a frontier can only be approached, say so honestly.
- Benchmark here, and record the expected speed on a typical computer core in the README ("about X cases per second per core; at 4 hours a day the frontier moves about Y per month").
- Give an honest **"realistic odds"** paragraph. No hype.

## 6. Quality passes (run these)

- After every few searchers, have a **fresh reviewer** (a subagent that didn't write the code) check correctness. It reads the searcher and verifier, looks for off-by-one errors, overflow, wrong search-space pruning, and gaps between "searched" and "claimed searched", and checks the README claims against sources. Fix everything it finds.
- **Fuzz the verifiers:** feed them deliberately wrong candidates and confirm they reject every one.
- **Overflow:** use exact or big-integer arithmetic wherever 64-bit could overflow, and add tests at the boundaries.
- `./mathrun selftest` runs every problem's tests and a 30-second mini-run of each searcher. It must pass before every commit.

## 7. Morning setup document

Write `SETUP.md` in plain English for my computer (Linux Mint): exactly which commands to run, step by step. Include:
- `git clone`, the one `apt` line if anything is missing, `./mathrun install`, `./mathrun selftest`, `./mathrun start` and `./mathrun dashboard`;
- how to switch on publishing (and the GitHub Pages setting: Deploy from a branch, `main`, `/docs`);
- how to set up the optional ntfy phone/email alert;
- how to stop everything, and how to uninstall.

## 8. Build order

1. Repo skeleton, CLAUDE.md, CLI, `.gitignore`, `config.example.toml`, safety guards (nice, heat, idle mode, disk), and atomic checkpoints, with tests.
2. Runner/scheduler, work units, crash restart, progress history and the candidate pipeline, using a toy problem with a planted "counterexample" to prove the pipeline end to end.
3. The dashboard (local first), then `publish`.
4. Research the problem shortlist (section 4) and write `docs/problem-shortlist.md`.
5. Searchers in score order, each with README, verifier and tests, plus a review pass every 2–3 searchers.
6. Alerts (notify-send, ntfy), `add-autostart` (systemd user service, opt-in) and SETUP.md.
7. Polish: dashboard design, charts, empty states and screenshots (Playwright, headless). Look at them and fix what's ugly.

Priority if time runs short: safety + correct pipeline > a few excellent searchers > many mediocre ones > dashboard polish.

## 9. Backlog (keep going here until 05:40 UTC)

- More searchers from the shortlist, and speed-ups to existing ones (profiling, better pruning, symmetry breaking).
- A "compute ledger" page: total CPU-hours per problem, and the frontier moved per hour.
- A clear `ADDING_A_PROBLEM.md` guide plus a template folder, so future sessions can add searchers quickly.
- More reviewer passes. Every bug caught is a win.

## 10. Morning summary (last 20 minutes)

At the bottom of CLAUDE.md, write a dated summary in plain English:
- Which problems have working searchers.
- For each: where it starts, its expected speed on a computer, and its honest odds.
- The shortlist scores and anything dropped (and why).
- How correctness was checked (tests, reproductions of known results, reviewer findings fixed).
- Exactly what I need to do on my computer to start it (point to SETUP.md).
- The top 5 next steps.

---

# Progress log

(One line per decision or milestone, newest at the bottom. Times are UTC.)

- 2026-10-18 20:20 Session start. Repo empty. Build machine: 4 cores, gcc 13.3, Python 3.13, no GMP headers.
- 2026-10-18 20:20 Decision: brief saved verbatim (from section heading onward) as CLAUDE.md.
- 2026-10-19 06:50 Build had stopped at ~21:00 (usage limit). Core modules written but untested, pushed as WIP to the dev branch only.
- 2026-10-19 06:55 New deadline from user: work until 16:40 UK time = 15:40 UTC on 19 Oct 2026. Last 20 minutes (from 15:20 UTC) = wrap-up and summary. An hourly scheduled task re-wakes the session if the usage limit interrupts.
- Decision: pushes go to both the dev branch `ccr-c3ca9c32-2ylwxr` and `main` (the brief explicitly asks for `main`), and only after tests pass.
- 2026-10-19 07:06 Core + runner + candidate pipeline tested end to end with a toy problem (planted answer found, verified, alerted; lying searcher caught and paused; restart resumes). selftest passes.
- 2026-10-19 07:20 Dashboard (docs/: index + detail page + compute ledger, light/dark, hand-written SVG charts, own markdown renderer, no external libs) done; screenshots checked.
- 2026-10-19 07:25 Shortlist researched and written to docs/problem-shortlist.md. Dropped: Hadamard (all gaps <2000 announced Aug 2026), lonely runner (proved to 10), superpermutation n=7 (5905 found Aug 2026), Wieferich/WSS (PrimeGrid did 2^64), Goldbach, 196, RH, Hadwiger-Nelson, happy ending, kissing, Conway-99/Moore-57, MOLS10, reconstruction, R(5,5).
- Decision: no-three-in-line target moved to n >= 71 (n <= 70 all solved in 2026).
- Decision: build order = Brocard, matrix multiplication, sum of three cubes, perfect cuboid, Collatz, cap sets, then Beal / sixth powers / magic squares / sorting networks / no-three-in-line / prime gaps as time allows.
- 2026-10-19 07:18 Searcher 1: Brocard (from n=10^15, Wilson-trick sieve, ~2.4M n/s/core). Reproduces 4,5,7; cross-checked vs Python prime by prime.
- 2026-10-19 07:33 Searcher 2: matrix multiplication flip graph over GF(2), 14 formats, best scheme per format checkpointed. Reproduces 7/11/15/23. Caught & fixed: wrong hand-typed Strassen constant (verifier caught it), plus-move that undid itself.
- 2026-10-19 07:38 Searcher 3: Collatz from 2^71 (2^26 sieve, 128-bit, ~6e8 n/s/core). Honest odds: none; included for fame. Decision: sum of three cubes moved later (needs cube roots mod large d; region a home PC can add is tiny).
- 2026-10-19 07:45-10:55 Session interrupted again (usage limit); resumed 10:56 via the hourly scheduled task. ~4h40m left.
- 2026-10-19 10:57 Searcher 4: perfect cuboid from odd edge 2.5e13 (sieve factoring, legs from a^2=uv, Euler-brick divisibility pre-filter, exact mini-gmp check). Brick counts match unfiltered brute force. Vendored mini-gmp (LGPL3/GPL2, CREDITS.md); install uses real GMP if present.
- 2026-10-19 11:00 Searcher 5: magic square of squares (centre e^2, Gaussian-integer pair lists, from e=1 since no precise published bound found; ~4M e/s/core).
- 2026-10-19 11:04 Searcher 6: Beal (all bases <= 2^21, exps 3-7, mod 2^61-1 hash + exact recheck; ~1M pairs/s/core, ~600 core-h total). Fixed a fingerprint bug (all small values shared one fingerprint) found while benchmarking.
- 2026-10-19 11:15 Searcher 7: sum of three cubes (Booker's method; fresh region d > 1e19/54, |z| <= 1e19, 7 open k; ~3e5 d/s/core). Reproduces 33, 42, 3. Brute-force test caught a real bug (>3 cube roots mod p^e when p^2 | k; affected k=975) - fixed.
- 2026-10-19 11:17 Review pass 1 (fresh subagent, 4 searchers): no false-verify or skipped-solution bugs found. Fixed all 8 findings: frontier text now flags candidates under review / UNTRUSTED after a failed verification; matmul no longer re-alerts its own find and keeps same-rank walks; Collatz argument guard + overflow numbers count for glide records; Brocard checks every survivor is reported and verifier primes start 10^6 above n; cuboid verifier strict ints; runner disables a problem if the same unit fails 5 times.
- 2026-10-19 11:18 SETUP.md (plain-English Mint guide), ADDING_A_PROBLEM.md and problems/_template/ written.
- 2026-10-19 11:25 Decision: no-three-in-line dropped after a prototype (symmetric DFS + forward checking solved n=16 but not n=20 in 30 s; the open case n=71 needed a new SAT solver in 2026). Would need a vendored SAT solver; backlog. Decision: favour quality (review, matmul, dashboard) over adding weak searchers.
- 2026-10-19 11:26 End-to-end run of all 7 searchers under the real runner: caught and fixed a runner crash (exhausted() got a dict, not a Ledger) and made plugin hook errors non-fatal. Dashboard screenshots with live data checked (desktop + phone dark); 'idle' renamed 'queued'.
- 2026-10-19 11:33 Searcher 8: cap sets dims 7/8 (local search, weight 0.5; reproduces maxima 4/9/20; honest: far below records 236/512).
- 2026-10-19 11:38 Review pass 2 (fresh subagent: cubes, beal, magic, runner). SEVERE bug found and fixed: magic-square x values overflowed 64 bits for e > 2^32 (would have silently skipped ground from ~unit 8); now 128-bit, with a test at e=5^14. Also fixed: Beal end-of-range empty unit, CAND lines from failed units now rescued and verified, unit failure counts pruned, merge errors shown, README citations (Jarnicki-Konerding; 'primitive' wording). Cube-root and sum-of-three-cubes region checked correct against the paper and 357,852 brute-force cases.
- 2026-10-19 11:42 Matmul: added 9 rectangular formats from the catalogue (3x3x7=49 and 3x6x6=80 are only constructions - best targets). Benchmarks in 80 s from scratch: 3x3x4 -> 30 (rec 29), 2x4x5 -> 33 (32), 3x3x5 -> 38 (36), 3x3x7 -> 56 (49).
- 2026-10-19 11:45 Matmul: GF(2) record candidates now get an automatic +-1 integer lift attempt (Hensel step mod 4 + exact check over Z); verifier independently re-checks any lift. Strassen and Strassen^2 lift; tests added.
- 2026-10-19 11:49 Review pass 3 (fresh subagent: cap sets, runner, all safety rules): no critical bugs; fixed 13 findings. Biggest: publish rewritten to build one commit with a private index + commit-tree on top of the remote branch (tested: user's unpushed commit and dirty files untouched); unit time limit now CPU-time based; timed-out units' candidates rescued; 256 MB output cap per searcher; SIGTERM/logout is not a failure; KillMode=mixed; selftest temp files inside data/; published snapshot drops candidate data/paths; cap-set dim-7 upper bound corrected to 288; idle detection under systemd.
- 2026-10-19 12:00 Matmul experiment: 4x4 from Strassen^2 (49) never moved in 3x170 s (no shared factors -> no flips); from schoolbook all walk-length settings reach 52 in 150 s. Decision: all formats start from schoolbook; walk continues across units.
- 2026-10-19 12:01 Decision: no more searchers today (Euler sixth powers needs the Resta-Meyrignac method, which doesn't fit the time left; RH zeros risk false alarms from double precision). Final 10-minute full-runner check started.

---

# Summary — Monday 19 October 2026 (written 12:10 UTC, checked again before 15:40 UTC)

## What you have
A working platform (runner, guards, crash-safe checkpoints, candidate pipeline with independent verifiers, alerts, dashboard, optional publishing, autostart) and **8 searchers**. Everything passes `./mathrun selftest`, and the whole thing has been run end to end under the real runner.

| Searcher | Where it starts | Speed (one core, build machine) | Honest odds |
|---|---|---|---|
| Fast matrix multiplication (23 formats, GF(2) flip graphs) | schoolbook method; keeps its best scheme per format | 1–2 M flips/s. In 80 s: 3×3×4 → 30 (record 29), 2×4×5 → 33 (32), 3×3×5 → 38 (36); 4×4 → 52 in 150 s (record 47) | Low but real. The best chance of a genuine record, especially 3×3×7 (49) and 3×6×6 (80), whose records are only constructions. Finds are auto-lifted to integers if possible. |
| Brocard n!+1=m² | n = 10^15 (published bound) | 2.4 M n/s → about +7×10^12 a month (4 h/day, 7 cores) | No new solution expected; it really extends the verified bound |
| Sum of three cubes (114, 390, 627, 633, 732, 921, 975) | just past Booker & Sutherland: d > 10^19/54, \|z\| ≤ 10^19 | 300 k d/s | A lottery ticket in exactly the right, unsearched place |
| Perfect cuboid | odd edge 2.5×10^13 | about 7,500 odd edges/s (very uneven) | Very low; extends the published bound slowly |
| Beal (US$1M) | all bases ≤ 2^21 (8× published), exponents 3–7 | about 1 M base pairs/s; whole job about 600 core-hours (~3 weeks) | Essentially zero; a documented extension |
| Magic square of squares | e = 1 (no precise published bound found) | 2–4 M centres/s | Low |
| Collatz | 2^71 | 6×10^8 n/s | Essentially zero (Barina's GPUs are far faster); included for fame |
| Cap sets (dims 7 and 8) | its own best cap | reaches about 165 / 335 (records 236 / 512) | Practically none; low weight 0.5 |

## Shortlist
Scores and sources are in `docs/problem-shortlist.md`. **Dropped:**
- Hadamard: every gap below 2000 was announced in Aug 2026.
- Lonely runner: proved for up to 10 runners; 11 is out of reach.
- Superpermutation n=7: 5905 was found in Aug 2026.
- Wieferich / Wall–Sun–Sun: PrimeGrid did 2^64.
- Goldbach, 196, Riemann zeros: no home-PC value, or a risk of false alarms.
- Hadwiger–Nelson, happy-ending 7-gon, kissing numbers, Conway-99, Moore-57, MOLS(10), reconstruction n=12, R(5,5): beyond any home PC, or need new ideas rather than CPU time.
- No-three-in-line: everything up to n=70 was solved in 2026. My prototype couldn't reach the open n=71; that needs a SAT solver.
- Euler sixth powers and prime gaps: built neither, for lack of time.

## How correctness was checked
- **Known results reproduced in tests:**
  - matrix multiplication: Strassen 7, 2×2×3 → 11, Laderman 23, and an integer lift of Strassen;
  - sum of three cubes: Booker's 33, Booker–Sutherland's 42 and 3, plus a brute-force cross-check over 21 small k;
  - Brocard: 4, 5, 7, and a prime-by-prime cross-check against Python;
  - Collatz: glide records against brute force;
  - perfect cuboid: Euler-brick counts against a filter-free brute force;
  - magic square: pair lists against brute force, including e > 2^32;
  - Beal: exact-hit counts against brute force;
  - cap sets: maxima 4, 9 and 20.
- **Verifiers:** every one is separate Python code with exact integers, fuzzed with damaged candidates in `selftest`.
- **Three fresh-reviewer passes** (subagents) covered all searchers, the runner and the safety rules. Real bugs found and fixed:
  - a 64-bit overflow in magic squares (it would have silently skipped ground from about unit 8);
  - a missed-roots bug for k=975 in sum of three cubes (caught by my own brute-force test);
  - `publish` could push the user's own commits (rewritten to use a private index plus commit-tree, and tested);
  - CPU- vs wall-clock time-outs;
  - candidates lost from failed units;
  - a runner crash in Beal's `exhausted()` (caught by the end-to-end run);
  - repeated alerts in matmul;
  - plus about 20 smaller fixes, all listed in the progress log above.

## What to do on your computer
Follow **SETUP.md**: `git clone …`, `./mathrun install` (it prints the one `apt` line if anything is missing), `./mathrun selftest`, `./mathrun start`, `./mathrun dashboard`. Optional extras: `libgmp-dev` for speed, `./mathrun add-autostart`, ntfy alerts, GitHub Pages publishing.

## Top 5 next steps
1. **Matrix multiplication**: add the symmetric (Z₃-invariant) flip graph of Moosbauer & Poole and smarter plateau handling, and try more rectangular formats where 2025–26 papers still find gains. This is the best shot at a real record.
2. **Sum of three cubes**: port Booker–Sutherland's cubic-reciprocity and adaptive sieving tricks (2–4× fewer z) from their open-source code.
3. **Perfect cuboid**: a faster pair test (legs of b ∩ legs of a) and the perfect-cuboid-specific divisibility facts (7, 13, 19, 37).
4. **New searchers**: Euler sixth powers, using the Resta–Meyrignac method, and first-occurrence prime gaps, which have real record potential and need GMP.
5. **No-three-in-line n ≥ 71**: vendor CaDiCaL (MIT) and use a symmetric SAT encoding like Heule's.
- 2026-10-19 12:32 Sum of three cubes: mod-3 constraint (k = +-3 mod 9 => x=y=z mod 3): skip 3|d, one z sign per d, z steps 3d. 8x fewer z, 1.6x faster overall; famous 33/42/3 and brute-force tests still pass.
