# Collatz conjecture (3n + 1)

**The question.** Start with any whole number. If it is even, halve it; if it is odd, triple it and add 1. Repeat. Do you always reach 1? Lothar Collatz asked in 1937. Nobody knows.

**Why it's famous.** Possibly the most famous "simple" unsolved problem. Erdős said "mathematics may not be ready for such problems". Terence Tao proved in 2019 that almost all numbers get "almost" down to 1. It has a well-known Veritasium video and a long Numberphile history.

**Current status (checked 19 Oct 2026).** Open. David Barina's project has verified every starting value **below 2^71 ≈ 2.36×10^21** (J. Supercomputing 81, 2025, reached on 15 Jan 2025). That took GPUs and several European supercomputers, with the code made 1,335× faster along the way. Barina's project may still be running, so ground just above 2^71 may get covered by it too.

**What this searcher does.** It checks every n from 2^71 upwards, in units of 2^37 ≈ 1.4×10^11 numbers:
1. It shows each n eventually drops below itself. Since every smaller number is already known to reach 1, so does n.
2. A **2^26 sieve** makes this fast. The first 26 steps only depend on n mod 2^26, and about 98.5% of residue classes provably drop below their start within those steps, so they are skipped without any work.
3. The rest jump 26 steps at once (T^26(n) = 3^a·m + T^26(r)) and carry on in 128-bit arithmetic.
4. Anything that would overflow 128 bits is finished off exactly in Python.
5. Anything that fails to drop within 100,000 steps is flagged as a candidate (a cycle or a runaway).
6. It also reports the longest *glide* (steps before first dropping below the start) in each unit.

**What counts as a win.** An n that never reaches 1: a new cycle, or a trajectory that grows forever. `verify.py` (separate code, Python big integers, the plain 3n+1 / n/2 map) iterates any candidate for 10^8 steps. A candidate that drops below its start is rejected and the searcher is paused as buggy.

**Tests (reproducing known results).**
- The longest glide in ranges of 2^17 numbers near 2^40, 2^71 and 5·2^50 matches a brute-force Python check exactly (number and glide length).
- The glide of 27 is 96, matching Roosendaal's glide-record table.
- Bad arguments are refused, and the verifier rejects non-counterexamples.

**Speed.** About **6×10^8 numbers per second per core** on the build machine; a unit takes about 4 minutes. At 4 hours a day on 7 cores that's about 6×10^13 numbers a day, or about 2×10^15 a month. That moves the verified bound from 2^71 by about one millionth of 2^71 per month.

**Realistic odds.** Essentially zero. Almost all experts believe the conjecture is true, and Barina's GPU code covers ground thousands of times faster than a home CPU. This searcher is here because Collatz is famous and honest work is cheap to show: it checks fresh numbers above the published bound and tracks long glides, but it will not move the frontier in any meaningful way. If you want it to use less of your computer, lower its `weight` in `config.local.toml`.

**References.** D. Barina, "Improved verification limit for the convergence of the Collatz conjecture", J. Supercomputing 81 (2025). E. Roosendaal, "On the 3x+1 problem" (glide and delay records). T. Tao, "Almost all orbits of the Collatz map attain almost bounded values" (2019).
