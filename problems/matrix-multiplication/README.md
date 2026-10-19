# Fast matrix multiplication: fewer multiplications

**The question.** The schoolbook method multiplies two n×n matrices with n³ multiplications. In 1969 Volker Strassen showed that 2×2 matrices need only 7, not 8. What is the smallest number of multiplications (the *rank*) for 3×3, 4×4, 5×5 and rectangular shapes? Nobody knows, even for 3×3: the best known method uses 23 (Laderman, 1976), and the best lower bound is 19.

**Why it's famous.** Fast matrix multiplication sits under almost all of scientific computing and machine learning. DeepMind's AlphaTensor (Nature, 2022) made headlines with 47 multiplications for 4×4 matrices over GF(2). AlphaEvolve (2025) did 48 over ordinary numbers. In between, Kauers and Moosbauer showed that a plain random search, the *flip graph*, running on ordinary computers matches or beats such records. That is exactly what this searcher does.

**Current status (checked 19 Oct 2026, Sedoglavic's catalogue fmm.univ-lille.fr).** Best known ranks for the formats searched here:

| Format | Best known | By |
|---|---|---|
| 3×3×3 | 23 | Laderman 1976 |
| 4×4×4 | 48 (47 over GF(2)) | AlphaEvolve 2025 (AlphaTensor 2022) |
| 3×4×5 | 47 | Fawzi et al. 2022 |
| 4×4×5 | 61 | AlphaEvolve 2025 |
| 4×5×5 | 76 | Fawzi et al. 2022 |
| 5×5×5 | 93 | Moosbauer & Poole 2025 |
| 3×3×4, 3×3×5, 3×4×4 | 29, 36, 38 | Smirnov 2013 |
| 2×4×5, 2×5×5, 3×5×5 | 32, 40, 58 | AlphaEvolve 2025; Hopcroft & Kerr 1971; Sedoglavic & Smirnov 2021 |
| 3×3×6, 4×4×6 | 40, 73 | Smirnov 2013, 2023 |

Recent flip-graph papers keep improving rectangular formats: Kauers & Wood 2025 (~30 formats), Perminov 2025–26 (79 schemes). The small square cases above have been searched hard.

**How it works.**
1. A scheme is a list of rank-one terms (A, B, C) of 0/1 matrices, stored as bitmasks. It is correct when the "Brent equations" hold mod 2.
2. A **flip** rewrites two terms that share a factor. It never breaks correctness.
3. A **reduction** happens when a factor becomes zero or two terms share two factors. The rank drops by one; this is how new schemes are found.
4. A **plus move**, x⊗y⊗z + x′⊗y′⊗z′ = (x+x′)⊗y⊗z + x′⊗(y+y′)⊗z + x′⊗y′⊗(z+z′), raises the rank by one to escape a dead end.
5. Each unit is a 2.5-minute random walk. The best scheme for each format is checkpointed, so the next unit carries on from where the last one stopped.
6. 4×4 starts from Strassen applied twice (49 multiplications).

**What counts as a win.** A correct scheme with fewer multiplications than the record above. Before anything is shown, `verify.py` rebuilds the full tensor with plain Python sets (separate code) and checks every Brent equation, then checks the rank is really below its own copy of the record table. A GF(2) win must also be *lifted* to integer coefficients before it counts for ordinary numbers. Some GF(2) schemes cannot be lifted (Kauers & Moosbauer saw this for 4×5×5), so a hit means "tell an expert", not "announce".

**Tests (reproducing known results).**
- From the schoolbook method, the search finds Strassen's 7 (2×2), the optimal 11 (2×2×3) and Laderman's 23 (3×3) within seconds.
- The tensor product of Strassen with itself gives a correct 49-term 4×4 scheme.
- The verifier rejects schemes with a flipped bit, a missing term, an out-of-range factor, or a rank claim that doesn't match the terms.

**Speed.** About 1–2 million flips per second per core. On the build machine, in 60 seconds from scratch, 3×4×5 got to 52 and 4×4×5 to 68. 4×4 from Strassen-squared (49) needs much longer walks. Kauers and Moosbauer report needing many CPU-hours per format, which is what a home computer provides over weeks.

**Realistic odds.** Low but genuinely non-zero. This is the one problem on the list where ordinary computers running this exact kind of search have recently set records, and that keeps happening for rectangular formats. Researchers with clusters have searched the small square cases (3×3, 4×4, 5×5) very hard, so a record there would be a real surprise. Expect the dashboard to show steady descent towards the records, and for most formats to stall a little above them.

**Ideas for later.** Hensel lifting to integers; symmetric (Z3-invariant) flip graphs (Moosbauer & Poole 2025); smarter plateau handling; more rectangular formats where recent papers still find gains.

**References.** Kauers & Moosbauer, "Flip graphs for matrix multiplication" (ISSAC 2023), arXiv:2212.01175; Kauers & Moosbauer 2025, arXiv:2505.05896; Kauers & Wood 2025, arXiv:2510.19787; Moosbauer & Poole 2025, arXiv:2502.04514; Fawzi et al., Nature 610 (2022); Sedoglavic, fmm.univ-lille.fr.
