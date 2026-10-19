# Perfect cuboid (perfect Euler brick)

**The question.** Is there a rectangular box where all seven lengths are whole numbers: the three edges, the three face diagonals and the long space diagonal through the middle? Boxes with whole edges and face diagonals do exist; they are called *Euler bricks*, and the smallest is 44 × 117 × 240. Nobody has found one where the space diagonal is whole as well, and nobody has proved it's impossible.

**Why it's famous.** It's one of the oldest unsolved problems about whole numbers (Euler studied it in the 1700s), simple enough for a child to understand, and it has featured on Numberphile and in many puzzle books.

**Current status (checked 19 Oct 2026).** Open. Exhaustive computer searches show that a perfect cuboid would need its **odd edge above 2.5×10^13** and its smallest edge above 5×10^11 (Wikipedia "Euler brick", citing Matson's searches; a 2013 report put the odd-edge bound at 5×10^12 before it was extended). Claimed "proofs" appear on arXiv regularly and none has been accepted.

**What this searcher does.** A primitive perfect cuboid has exactly one odd edge. The searcher steps through odd edges a from 2.5×10^13 upwards, in units of 10^6:
1. A segmented sieve factors every a.
2. Every even b with a² + b² a perfect square comes from a factorisation a² = u·v, giving b = (v − u)/2. These numbers can be far bigger than 2^64, so they are held in 128-bit integers.
3. Proven divisibility facts about Euler bricks rule out most pairs (b, c) before any arithmetic: two edges divisible by 3, one by 9, one by 5, one by 11, and one by 4 with another by 16 (Wikipedia "Euler brick" properties; Leech 1977).
4. Each remaining pair is tested with square-residue tables. The rare survivors are checked exactly with big integers: first b² + c² (an Euler brick), then a² + b² + c² (perfect).

**What counts as a win.** Edges a, b, c with all seven lengths whole. `verify.py` (separate code, exact Python integers) re-checks every diagonal.

**Tests (reproducing known results).**
- The smallest Euler brick (44, 117, 240) is found.
- The number of Euler bricks found matches a filter-free brute force exactly (52 with odd edge < 2000, and a window above 10^5). This checks both the leg generation and the divisibility shortcut.
- The divisibility facts hold for every small primitive Euler brick.
- The verifier rejects Euler bricks that aren't perfect, plus zero, negative and non-numeric edges.

**Speed.** About **7,500 odd edges per second per core** on the build machine. This varies a lot: an a with many divisors can have 16,000 legs and 10^8 pairs. A unit takes about 2 minutes. At 4 hours a day on 7 cores that's about 8×10^9 odd edges a month, so the frontier moves from 2.5000×10^13 to about 2.5016×10^13 per month.

**Realistic odds.** Very low. Many mathematicians suspect no perfect cuboid exists, and the published searches went much further, probably with smarter methods than this one. What the searcher honestly adds is new ground above the published odd-edge bound, plus a growing count of Euler bricks met along the way. Speed-up ideas: a pair test based on factoring b (legs of b ∩ legs of a), and further proven divisibility facts specific to perfect cuboids (for example 7, 13, 19 and 37).

**References.** Wikipedia, "Euler brick" (properties and search bounds). J. Leech, "The rational cuboid revisited", Amer. Math. Monthly 84 (1977). R. Matson, search reports (2013–2017).
