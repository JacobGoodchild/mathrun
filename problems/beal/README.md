# Beal conjecture (US$1,000,000 prize)

**The question.** Can A^x + B^y = C^z, where all three exponents x, y and z are at least 3 and A, B and C share no common factor? Andrew Beal, a Texas banker and amateur mathematician, conjectured in 1993 that the answer is no. The American Mathematical Society holds his **US$1,000,000 prize** for a proof or a counterexample.

**Why it's famous.** It generalises Fermat's Last Theorem (the case x = y = z), which took 358 years and Andrew Wiles to prove. The million-dollar prize and its amateur origin make it one of the best-known open problems in number theory.

**Current status (checked 19 Oct 2026).** Open. Published computer searches have found no counterexample with bases up to 250,000 and exponents up to 7, or bases up to 10,000 and exponents up to 100 (Peter Norvig's searches and follow-ups; Dan Van Kesteren's extension). Without the gcd condition there are many solutions, such as 2³ + 2³ = 2⁴ and 3³ + 6³ = 3⁵. With an exponent of 2 there are coprime ones too (2⁵ + 7² = 3⁴), which is why the rule says "at least 3".

**What this searcher does.** It checks **every A, B and C up to 2^21 = 2,097,152** (8× the published 250,000) with every combination of exponents 3 to 7:
1. Store C^z mod p (p = 2^61 − 1) for every C ≤ 2^21 and z = 3…7 in a hash table, with a small bit-filter in front of it.
2. For every A, every B ≤ A, and every x and y, look up (A^x + B^y) mod p.
3. Re-check any hit exactly with big integers (GMP or the vendored mini-gmp).
4. Solutions with a common factor are counted (they're allowed). A coprime one is a candidate.

Work is split so every unit has about 1.5×10^8 (A, B) pairs (about 2.5 minutes). The search finishes when A reaches 2^21. Extending it after that means raising `CMAX` in `plugin.py` (the hash table grows with it).

**What counts as a win.** A coprime solution with all exponents ≥ 3. `verify.py` (separate code, exact Python integers) re-checks the equation, the exponents and the gcd.

**Tests (reproducing known results).**
- The number of exact solutions (with common factors) for bases up to 120, with C up to 300, matches a brute-force Python search exactly.
- Known examples like 2³ + 2³ = 2⁴ are found.
- The verifier rejects non-coprime solutions, exponent-2 solutions (2⁵ + 7² = 3⁴) and false equations.

**Speed.** About **1 million (A, B) pairs per second per core**, each trying all 25 exponent pairs. Speed is limited by memory lookups, so it will vary with your CPU cache. The whole 2^21 search is about 2.2×10^12 pairs, or roughly 600 core-hours: about 3 weeks at 4 hours a day on 7 cores. Each running copy uses about 150 MB of memory (for the lookup table).

**Realistic odds.** Essentially zero. Almost everyone believes the conjecture is true, it would follow from the abc conjecture for large enough numbers, and counterexamples with small exponents are ruled out in many cases by theory. The value here is an honest, exact, documented extension of the searched range to bases 8× larger than the published figure.

**References.** R. D. Mauldin, "A generalization of Fermat's Last Theorem: the Beal conjecture and prize problem", Notices AMS 44 (1997). P. Norvig, "Beal's conjecture: a search for counterexamples" (norvig.com). D. Van Kesteren, "Beal's Conjecture" (danvk.org, 2007). AMS, "Beal Prize".
