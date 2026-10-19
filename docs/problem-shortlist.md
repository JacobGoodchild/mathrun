# Problem shortlist

Checked on the web on **19 October 2026**. Each problem is scored 1–5 on:

- **Fame**: would a win be widely recognised (Numberphile/Quanta level)?
- **Leverage**: can one home computer, running a few hours a day, really push the frontier or have a genuine shot?
- **Verify**: can a win be checked cleanly and independently?

"Total" is the sum (out of 15). Problems are built in roughly this order. Leverage is scored strictly: a 1 means "the searcher covers new ground, but the odds of a win are close to zero".

## Built (or planned), best first

| Problem | Fame | Leverage | Verify | Total | Current status (checked 2026-10-19) |
|---|---|---|---|---|---|
| Fast matrix multiplication (flip graphs, over GF(2)) | 5 | 3 | 5 | **13** | Ranks are still being improved on ordinary hardware with flip-graph searches: Kauers & Moosbauer 2025 ((n,m,6) formats), Kauers & Wood 2025 (~30 formats), Perminov 2025–26 (79 schemes). Records are tracked in Sedoglavic's catalogue (fmm.univ-lille.fr). |
| Brocard's problem n! + 1 = m² | 3 | 4 | 4 | **11** | Open. Searched to n ≤ 10^15 (Epstein & Glickman 2020, cited by Wikipedia; Matson 2017 reached ~10^12). A home PC can extend this bound by a measurable amount. "Verify" is 4 because a hit can only be checked modulo many primes (n! has ~10^16 digits). |
| Sum of three cubes (k = 114, 390, 627, 633, 732, 921, 975) | 5 | 1 | 5 | **11** | These 7 values below 1000 are still open (Booker & Sutherland, PNAS 2021). Their search (Charity Engine, ~4 million 3-hour tasks) used bounds of 10^16–10^17. A home PC can't out-search them; it can only add fresh ground. |
| Perfect cuboid | 4 | 2 | 5 | **11** | Open. Exhaustive searches show the odd edge would have to be > 2.5×10^13 and the smallest edge > 5×10^11 (Wikipedia "Euler brick"; Matson). |
| Collatz conjecture | 5 | 1 | 5 | **11** | Verified up to 2^71 ≈ 2.36×10^21 (Barina, J. Supercomputing 2025, on GPUs and supercomputers). A home CPU can only add a sliver above that. |
| Cap sets in F₃⁷ and F₃⁸ | 4 | 2 | 5 | **11** | Dimension 7: best known 236, upper bound 291. Dimension 8: FunSearch (Nature 2023) found 512, beating 496. |
| Maximal / first-occurrence prime gaps | 2 | 4 | 5 | **11** | All maximal gaps below 2^64 are known (the 81st is beyond 2^64). First-occurrence and merit records are kept in the community-maintained Nicely tables, and home searchers still add records there. Needs big-number primality tests. |
| No-three-in-line, n ≥ 71 | 3 | 2 | 5 | **10** | 2n-point solutions are now known for **every n ≤ 70**: Prellberg 2026 (CSP, n ≤ 60, then 68) and Heule June 2026 (new SAT solver, n = 69, 70). n = 71 onward is open. |
| Beal conjecture (US$1M) | 4 | 1 | 5 | **10** | Open. Published searches cover bases ≤ 250,000 with exponents ≤ 7, and bases ≤ 10,000 with exponents ≤ 100 (Norvig and follow-ups). |
| Euler sum of powers, sixth powers (6,1,5) and (6,1,6) | 3 | 2 | 5 | **10** | No sixth power is known to be a sum of 5 or 6 sixth powers. For (6,1,6), any solution must exceed 730,000 (Resta & Meyrignac 2003, OEIS A007666). |
| 3×3 magic square of squares | 4 | 1 | 5 | **10** | Open (Boyer's €1000 and champagne prize is unclaimed). Reported searches put any solution's smallest entry above ~10^14. |
| Optimal sorting networks, size for n = 13 | 3 | 2 | 5 | **10** | Optimal sizes are proven for n ≤ 12 (Harder 2020). For n = 13: 43 ≤ s(13) ≤ 45. A 44-comparator network would be news. |

## Assessed and dropped

| Problem | Fame | Leverage | Verify | Why dropped |
|---|---|---|---|---|
| Hadamard matrices (668, 716, 892, …) | 4 | 1 | 5 | Order 668 and **all remaining gaps below 2000** were announced in August 2026 (Alpöge and collaborators, with Claude; reported by J. D. Cook's blog). Nothing small is left to attack. |
| Lonely runner | 3 | 1 | 4 | Proved for 8 runners (Rosenfeld 2025), and for 9 and 10 (Trakulthongchai; Rosenfeld). Quanta (Mar 2026) notes the methods are too expensive for 11 runners. |
| Minimal superpermutation, n = 7 | 4 | 1 | 5 | The best length improved from 5906 to **5905** on 17 Aug 2026 (Teodorescu). The lower bound is 5884. Further gains need new structural ideas, not CPU time. |
| Wieferich / Wall–Sun–Sun primes | 3 | 1 | 5 | PrimeGrid searched both up to 2^64 (2020–2022). Going beyond needs 128-bit arithmetic and is many times slower, for a very low chance. |
| Goldbach verification beyond 4×10^18 | 4 | 1 | 4 | Oliveira e Silva's project used years of many machines. A home PC would add a negligible amount. |
| Lychrel / 196 | 2 | 1 | 5 | Recreational, and has already been taken past a billion digits. Fails the fame test. |
| Riemann hypothesis zeros | 5 | 1 | 2 | Platt & Trudgian verified RH up to height 3×10^12 rigorously; Odlyzko computed zeros near 10^23. A rigorous home check adds nothing new, and a non-rigorous one isn't a clean "win". Possible later showpiece. |
| Hadwiger–Nelson (6-chromatic graph) | 5 | 1 | 4 | Still 5 ≤ χ ≤ 7. A 6-chromatic graph needs a new construction idea, and the SAT checks run to millions of clauses. Brute CPU is not the bottleneck. |
| Happy ending, 7-gon (33 points) | 4 | 1 | 3 | The empty-hexagon (30 points) SAT proof (Heule & Scheucher 2024) already needed a cluster. The 7-gon case is far beyond any SAT approach. |
| Kissing numbers | 4 | 1 | 5 | Records (e.g. dim 11: 593, AlphaEvolve 2025; Ganzhinov 592) come from careful algebraic constructions plus heavy optimisation. Generic home search has very low odds. |
| Conway's 99-graph, Moore graph of degree 57 | 4 | 1 | 5 | Experts have already ruled out the natural symmetry assumptions. Without symmetry the space is astronomically large. |
| Three MOLS of order 10 | 3 | 1 | 5 | Massive exhaustive searches have been run under symmetry assumptions. Nothing realistic is left for one PC. |
| Reconstruction conjecture, 12 vertices | 3 | 1 | 5 | There are ~1.65×10^11 graphs on 12 vertices, each needing deck comparisons. That is years of CPU even with nauty, and the result would be a verification rather than a breakthrough. |
| R(5,5) | 5 | 1 | 4 | Bounds are 43 ≤ R(5,5) ≤ 46 (Angeltveit & McKay 2024). The brief says include it only with a genuinely new method; I don't have one. |
| Černý conjecture, Scholz/addition chains | 2 | 2 | 5 | Interesting, but fails the fame test against the rest of this list. Backlog. |

## Sources

- Sum of three cubes: Booker & Sutherland, "On a question of Mordell", PNAS 118 (2021), https://arxiv.org/abs/2007.01209 ; MIT News, March 2021.
- Collatz: Barina, J. Supercomputing 81 (2025); https://www.fit.vut.cz/research/publication/c197809
- Brocard: OEIS A085692 (Matson ≤ 10^12); Epstein & Glickman 2020 (n ≤ 10^15), as cited by Wikipedia "Brocard's problem".
- Perfect cuboid: https://en.wikipedia.org/wiki/Euler_brick
- Matrix multiplication: Kauers & Moosbauer, https://arxiv.org/abs/2505.05896 ; Kauers & Wood, https://arxiv.org/abs/2510.19787 ; Perminov, https://arxiv.org/abs/2511.20317 and https://arxiv.org/abs/2603.02398 ; catalogue: https://fmm.univ-lille.fr/
- No-three-in-line: Prellberg, https://arxiv.org/abs/2602.07751 ; MathWorld "No-Three-in-a-Line Problem"; Flammenkamp's tables https://wwwhomes.uni-bielefeld.de/achim/no3in/table.html
- Cap sets: https://arxiv.org/abs/2206.09804 ; Romera-Paredes et al. (FunSearch), Nature 2023.
- Beal: https://www.danvk.org/wp/beals-conjecture/ ; Norvig, "Beal's conjecture: a search for counterexamples".
- Sixth powers: OEIS A007666; Resta & Meyrignac (2003).
- Magic square of squares: https://arxiv.org/abs/2406.09364 ; Boyer, multimagie.com.
- Sorting networks: Harder (2020); https://arxiv.org/abs/1507.01428 ; Dobbelaere's list (bertdobbelaere.github.io/sorting_networks.html).
- Prime gaps: https://faculty.lynchburg.edu/~nicely/gaps/gaps.html ; https://t5k.org/notes/GapsTable.html
- Hadamard: https://www.johndcook.com/blog/2026/08/13/constructing-hadamard-matrices/ ; https://arxiv.org/abs/2411.18897
- Lonely runner: https://arxiv.org/abs/2509.14111 ; https://arxiv.org/abs/2511.22427 ; Quanta, 6 Mar 2026.
- Superpermutations: https://en.wikipedia.org/wiki/Superpermutation
- Wieferich / WSS: https://en.wikipedia.org/wiki/PrimeGrid
- Hadwiger–Nelson: https://en.wikipedia.org/wiki/Hadwiger%E2%80%93Nelson_problem
- Kissing numbers: https://arxiv.org/abs/2511.02864
