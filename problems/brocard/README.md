# Brocard's problem: when is n! + 1 a perfect square?

**The question.** 4! + 1 = 25 = 5², 5! + 1 = 121 = 11² and 7! + 1 = 5041 = 71². Are there any more? Henri Brocard asked in 1876, and Ramanujan asked again in 1913. Nobody has found another, and nobody has proved there isn't one.

**Why it's famous.** It's one of the simplest-to-state unsolved problems in number theory. It has Ramanujan's name on it (the "Brocard–Ramanujan equation") and has its own Numberphile video. Erdős conjectured that 4, 5 and 7 are the only answers. A result of Overholt (1993) shows that the abc conjecture would imply only finitely many solutions exist.

**Current status (checked 19 Oct 2026).** Open. Computer searches have ruled out every n up to:
- 10^9: Berndt & Galway (2000);
- about 10^12: Matson (2017), noted in OEIS A085692;
- 10^15: Epstein & Glickman (2020), the bound cited by Wikipedia. This is the published frontier this searcher starts from.

**What this searcher does.** It checks n from 10^15 upwards, in units of 250 million values. For each unit it uses the method of Berndt & Galway:
1. If n! + 1 is a square, it must also be a square modulo every prime p.
2. Pick primes p just above the unit. Wilson's theorem says (p−1)! ≡ −1 (mod p), which gives n! ≡ −1 / ((n+1)(n+2)…(p−1)). So walking n downwards costs **one multiplication per number per prime**.
3. A Jacobi-symbol test then throws out roughly half of the remaining numbers for each prime. About 26–30 primes clear a whole unit.
4. Anything that survives 200 primes is flagged as a candidate.

The arithmetic is 64-bit Montgomery multiplication. The Jacobi routine is branch-light, and the tests check it against a textbook version on 20 million random inputs.

**What counts as a win.** Any n > 7 with n! + 1 a perfect square. Because n! has around 10^16 digits here, no computer can test squareness directly. A candidate is therefore re-checked by `verify.py`, which is separate code. It uses 64 different primes, plain Python integers and Euler's criterion. Passing means "a square modulo 264 primes in total", which is overwhelming evidence but not a proof, and the dashboard says so.

**Tests (reproducing known results).**
- The searcher finds exactly 4, 5 and 7 below 1000, matching an exact brute-force check with big integers.
- Its survivors after k primes match a direct Python computation, prime by prime.
- It runs cleanly near 2^62, the top of its range.
- The verifier accepts 4, 5 and 7 and rejects every wrong value fed to it.

**Speed.** About **2.4 million n per second per core** on the build machine. A unit takes about 2 minutes. At 4 hours a day on 7 cores, that's about 2.4×10^11 numbers a day, or about **7×10^12 a month**. In other words, the frontier moves from 1.000×10^15 to about 1.007×10^15 each month.

**Realistic odds.** Essentially zero for finding a new solution: heuristics suggest any further solutions are astronomically rare, and Erdős believed there are none. What this searcher *can* honestly do is extend the published verification bound beyond 10^15, slowly but measurably. That is a small, citable contribution, not a breakthrough. Speed-up ideas for later: vectorised Jacobi symbols, and fewer passes using several primes at once.

**References.** Berndt & Galway, "On the Brocard–Ramanujan Diophantine equation n! + 1 = m²", Ramanujan J. 4 (2000). OEIS A085692. Wikipedia, "Brocard's problem".
