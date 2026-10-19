# Sum of three cubes

**The question.** Which whole numbers k can be written as x³ + y³ + z³, where x, y and z are whole numbers (negative ones allowed)? Numbers that are 4 or 5 more than a multiple of 9 never can. Heath-Brown conjectured that every other k can, in infinitely many ways. Below 1000, seven values still have **no known solution: 114, 390, 627, 633, 732, 921 and 975**.

**Why it's famous.** In 2019 Andrew Booker found 33 = 8866128975287528³ + (−8778405442862239)³ + (−2736111468807040)³. Booker and Andrew Sutherland then cracked **42**, the "answer to life, the universe and everything", using half a million home computers on Charity Engine. They followed with a third way of writing 3, answering a question Mordell asked in 1953. It was world news and a series of Numberphile videos.

**Current status (checked 19 Oct 2026).** The seven values above are still open. Booker & Sutherland ("On a question of Mordell", PNAS 118, 2021) searched every solution with min(|x|, |y|, |z|) ≤ 10^17. They then searched the remaining values with |z| ≤ 10^19 and d ≤ 10^19/54, which found 579 in January 2021. Their paper says they hope to continue on the seven that remain.

**What this searcher does.** It uses Booker's algorithm:
1. Order a solution so |x| ≥ |y| ≥ |z| and let d = |x + y|. Then d < 0.26·|z|, d divides k − z³, and Δ = 3d(4|k − z³| − d³) is a perfect square.
2. Factor each d with a segmented sieve.
3. Find **all cube roots of k modulo d**:
   - prime by prime, with a direct formula for p ≡ 2 (mod 3) and a Tonelli–Shanks-style method for p ≡ 1 (mod 3);
   - lift each to prime powers;
   - combine them with the Chinese remainder theorem.
4. Walk every z in those residue classes with 3d ≤ |z| ≤ 10^19.
5. Test Δ for squareness modulo six tables. The few survivors are solved exactly with Python big integers, and only genuine solutions become candidates.

It covers **fresh ground just past Booker & Sutherland's search**: d from 10^19/54 ≈ 1.85×10^17 upwards, every |z| up to 10^19, for all seven k. Units rotate through the seven values, each covering 2^25 ≈ 3.4×10^7 values of d.

**What counts as a win.** Whole numbers with x³ + y³ + z³ = k for one of the seven open k. `verify.py` checks the identity exactly and says whether k was open.

**Tests (reproducing known results).**
- Starting only from the right d and a z bound, the searcher re-finds the famous solutions for **33** (Booker 2019), **42** and **3** (Booker & Sutherland 2019). Each comes out as the only survivor of the filters.
- For 21 small values of k, every solution with 3|x+y| ≤ |z| ≤ 300 found by brute force is also found by the searcher. This test caught a real bug, now fixed: there can be more than 3 cube roots modulo p^e when p² divides k, which matters for k = 975 (divisible by 25).
- The verifier rejects wrong sums and non-integers.

**Speed.** About **480,000 values of d per second per core** near d = 1.85×10^17. Because all seven k are ±3 mod 9, x, y and z must all have the same remainder mod 3. So d divisible by 3 is skipped, only one sign of z is possible for each d, and z steps by 3d: about 6 values of z per d instead of 50. A unit takes about 2 minutes.

**Realistic odds.** Very small. In Heath-Brown's heuristics, the chance of a solution in any range of d you can reach from a home PC is tiny; Booker & Sutherland's 2020 run used roughly 1,000 times more computing than this computer can manage in a year. This searcher does exactly the right thing in exactly the right (unsearched) place, so if lightning strikes it will be noticed, but please treat it as a lottery ticket. Sutherland's open-source code (github.com/AndrewVSutherland/SumsOfThreeCubes) is far more optimised: it uses cubic reciprocity, adaptive sieving and a better z/d ratio. Porting those ideas would be the obvious next step.

**References.** A. R. Booker, "Cracking the problem with 33", Res. Number Theory 5 (2019). A. R. Booker & A. V. Sutherland, "On a question of Mordell", PNAS 118 (2021), arXiv:2007.01209. D. R. Heath-Brown, "The density of zeros of forms for which weak approximation fails", Math. Comp. 59 (1992).
