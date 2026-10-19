# Credits and third-party code

mathrun's own code is in this repository. The only third-party source code vendored here:

| Code | Where | Licence | Source |
|---|---|---|---|
| mini-gmp (from GNU MP 6.3) | `common/vendor/mini-gmp/` | Dual: GNU LGPL v3+ or GNU GPL v2+ | https://gmplib.org/ (downloaded 2026-10-19 from gmplib.org/repo/gmp-6.3, `mini-gmp/`) |

mini-gmp is a small, single-file subset of the GNU Multiple Precision library. It is only used when the full GMP development package (`libgmp-dev`) is not installed. If it is installed, `./mathrun install` uses the real GMP library (same licences) instead, which is faster.

Algorithms and records used by each searcher are credited in that problem's `README.md`.
