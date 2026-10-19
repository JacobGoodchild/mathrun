# 3×3 magic square of squares ("the Parker square")

**The question.** Can you fill a 3×3 grid with nine *different* perfect squares so that every row, every column and both diagonals add up to the same total? Nobody knows. Martin Gardner popularised it in 1996. Matt Parker's famous near-miss attempt on Numberphile (2016), which repeats some numbers and gets one diagonal wrong, made "a Parker square" a byword for a heroic but not-quite-right effort.

**Why it's famous.** It sounds like a puzzle-book exercise, yet it has resisted mathematicians for decades. Christian Boyer offers a prize (€1,000 and a bottle of champagne), and it's one of the best-known open problems in recreational mathematics. Magic squares of squares are known for 4×4 and bigger (Euler found one), and 3×3 magic squares with 7 of the 9 entries square are known (Bremner, Boyer), but never 8 or 9.

**Current status (checked 19 Oct 2026).** Open. Wikipedia says unsuccessful brute-force searches suggest any solution would involve numbers above roughly 10^14, citing Boyer's survey at multimagie.com. I could not find a precise published bound, so this searcher **starts from the beginning** (it's fast enough that re-checking old ground only takes days) and the dashboard shows the exact range it has covered itself.

**What this searcher does.** Every 3×3 magic square has the form
```
c+a    c-a-b  c+b
c-a+b  c      c+a-b
c-b    c+a+b  c-a
```
1. For a square made of squares, the centre c is itself a square e². In a *primitive* one (no common factor), every prime factor of e is 1 mod 4 (Wikipedia, "Magic square of squares": properties). A non-primitive solution divides down to a primitive one with a smaller centre, which is searched too. So most e are skipped straight away, after a sieve has factored them.
2. A symmetric pair c − x, c + x are both squares exactly when 2e² = p² + q², with x = (q² − p²)/2. The searcher lists *every* such way of writing 2e², using Gaussian integers. Each prime p ≡ 1 mod 4 is split with Cornacchia's algorithm.
3. It then looks for a and b in that list with a + b and a − b also in it. That gives all nine squares, which is flagged as a candidate.
4. Along the way it counts squares where a, b and a + b work (centre plus three full pairs, seven squares).

**What counts as a win.** Nine distinct positive perfect squares forming a magic square. `verify.py` rebuilds the grid and checks everything from scratch with exact integers: squares, distinctness and all eight line sums.

**Tests (reproducing known results).**
- For every e below 3000, the list of square pairs matches a direct brute-force Python search exactly, including which e are skipped.
- Bremner's famous 7-square magic square is correctly rejected by the verifier.
- For e = 5^14 (beyond 2^32, where the pair values pass 2^64), every listed pair is exact. A reviewer caught an earlier 64-bit overflow here, now fixed with 128-bit arithmetic.
- No candidates appear below 10^6 (as expected, since no solution is known).

**Speed.** About **4 million centres per second per core** near e = 10^7, falling to roughly 2 million per second near e = 10^12. At 4 hours a day on 7 cores the searcher passes e = 10^12 (entries around 2×10^24) within a few weeks.

**Realistic odds.** Low. Many experts suspect no solution exists, and there are partial results pointing that way. Serious searchers (Boyer, Bremner, Bernstein, the "fituvalu" project) may already have gone further by other methods; their exact limits aren't clearly published. The searcher is cheap and exact, and it walks steadily into ground that is at least not documented as searched.

**References.** Wikipedia, "Magic square of squares". C. Boyer, "Some notes on the magic squares of squares problem", Math. Intelligencer 27 (2005), and multimagie.com. A. Bremner, "On squares of squares", Acta Arith. 88 (1999).
