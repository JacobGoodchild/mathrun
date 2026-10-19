# Cap sets

**The question.** Take the grid F₃ⁿ: every point is a list of n digits, each 0, 1 or 2. Three points lie on a line exactly when they add up to 0 in every position (counting mod 3). How many points can you pick with no three on a line? Such a set is a *cap set*. The card game SET is the n = 4 case: the most cards with no SET among them is 20.

**Why it's famous.**
- In 2016 Ellenberg and Gijswijt used the brand-new "polynomial method" of Croot, Lev and Pach to prove that caps are exponentially smaller than the whole space. Quanta called it a breakthrough.
- In 2023 DeepMind's **FunSearch** (Nature) used a language model to find a cap of size **512 in dimension 8**, beating the 496 humans had found. DeepMind described it as the first time a large language model made a discovery on an open maths problem.

**Current status (checked 19 Oct 2026).**
- The largest caps are known exactly up to dimension 6: 2, 4, 9, 20, 45 and 112.
- Dimension 7: the best known is **236** (Edel), and the upper bound is 288 (Thackeray, arXiv:2206.09804).
- Dimension 8: the best known is **512** (FunSearch, 2023).

**What this searcher does.** It runs a plain local search, with no AI involved:
1. It keeps a count, for every point outside the cap, of how many pairs inside the cap would form a line with it.
2. It adds free points. When stuck, it swaps in a point blocked by just one pair and drops one point of that pair, or occasionally drops a random point.
3. The best cap for each of dimensions 7 and 8 is checkpointed, and each unit continues from it.

**What counts as a win.** A cap bigger than 236 in dimension 7 or bigger than 512 in dimension 8. `verify.py` (separate Python code) re-checks every pair of points.

**Tests (reproducing known results).**
- It finds the true maximum caps in dimensions 2, 3 and 4 (4, 9 and 20, the SET-card answer) in seconds, and never claims more than the proven maximum.
- The verifier rejects lines, repeats, out-of-range points, and caps that don't beat the record.

**Speed and honest performance.** In a minute or so it reaches about 165 in dimension 7 and about 335 in dimension 8. That is a long way below the records (236 and 512), and it also misses the known optimum in dimension 5 (it finds 40 of 45) and dimension 6 (83 of 112). Records here come from clever algebraic and product constructions, which this simple search doesn't know about.

**Realistic odds.** **Practically none**, which is why it runs at a very low weight (0.3). It's included because the problem is famous and it's an honest, cheap baseline. The obvious next step is to seed the search with the known record constructions (Edel's caps; the FunSearch program's output) and look for local improvements, which is what serious attempts do.

**References.** J. Ellenberg & D. Gijswijt, Annals of Math. 185 (2017). B. Romera-Paredes et al., "Mathematical discoveries from program search with large language models", Nature 625 (2024). Y. Edel, "Extensions of generalized product caps", Des. Codes Cryptogr. 31 (2004). arXiv:2206.09804.
