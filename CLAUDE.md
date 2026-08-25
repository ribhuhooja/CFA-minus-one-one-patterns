# Notes for whoever picks this up

Counting holomorphic discs in bordered Heegaard diagrams. Read `README.md` first for what the
project is; this file is the state of play and the traps.

## Layout

Two packages, no dependencies, no build step, plain ES modules.

- **`grid-arc/`** — the geometry. Given a simple arc on the unit grid, find the grid path
  joining its endpoints whose enclosed region contains no forbidden point. Knows nothing about
  Heegaard diagrams.
- **`heegaard/`** — the diagrams. Builds `Q(i,m,n)` as `H(r,s)`, draws it, lifts beta to the
  universal cover, feeds pieces of beta to the solver, reads off Reeb chords and U powers.

`src/` in both is pure: no DOM, no Node builtins, no I/O. `index.html` (the viewers) and the
CLIs are the only impure things. **Verified**: `src/` imports nothing but its own siblings.

Gitignored on purpose: `out/` (all regenerable), and `heegaard/{harvest,analyse,shapes}.js`,
which are one-off study code — the package is meant to be a package for computing CFAs.

## Running things

```bash
cd heegaard
node discs.js 2 3 5                  # count discs -> out/Q235-discs.csv
node cli.js 2 2 2                    # draw diagram + universal cover (svg)
node atlas.js 2 2 2 --cell=9         # draw a sample of the discs (svg + png)
node serve.js                        # http://localhost:8300/heegaard/ interactive disc finder
npm test                             # 347 tests
npm run regression                   # ten diagrams against a pinned fixture, ~3s
npm run conjecture                   # Q(i,2,2) vs the closed-form tables, i=1..10
cd ../grid-arc && npm test && npm run stress
```

## What is established

- **Disc count**: `2m(n+2)^2 * i - [m(n^2+2n+5) - m^2 - n^2]`. Exact on all 646 harvested
  diagrams, i up to 20. At `m=n=2` it is `64i-18`.
- **Q(i,2,2) matches the user's closed-form arrow tables exactly**, i = 1..10, all 3340 rows.
- **Raising i past 2 adds no new (chord word, U) classes**, tested to i=20. Every class count
  is linear in i; 72% do not depend on i at all. Exactly three classes are empty at i=1
  (`rho_3`, `rho_23`, `rho_123`, each U^1).
- A general-`(i,m,n)` family table covering **83.6%** of discs with **zero false positives**
  lives in `heegaard/shapes.js` as executable code. The gap is the x-side "snail" — chordless
  U^1 x->x discs. Known about it: it is the y-snail pattern repeated with period `2r-1`; the
  per-band repeat counts are what is missing.
- The user's `snail_start`/`snail_end` conjecture (`U^m` chordless and `U^n rho_23` between
  them) holds on **646/646** diagrams, with those being the only two discs between that pair.

## Conventions that are not obvious

- **Reeb chords**: `rho_1 = N->W`, `rho_2 = E->N`, `rho_3 = S->E`, `rho_12 = N->N`,
  `rho_23 = E->E`, `rho_123 = N->E`. This has `rho_1` and `rho_3` **swapped** relative to how
  the rule was first dictated. It is the only assignment where the composites compose, and it
  is the one that reproduces the reference tables. `REEB_CONVENTIONS.dictated` keeps the other.
  Words are written in path order, no reversal.
- **`strategy: 'walk'` is the default** everywhere. `'search'` is the exhaustive reference and
  the only strategy that fills in `result.trace`. Test harnesses pin `'search'` explicitly
  where they mean the exhaustive answer — do not remove those.
- `assumeSimple` / `assumeValid` on `solve` skip checks that are properties of the *curve*
  rather than the piece. Only safe because beta's lift is embedded and validated once.

## Traps, all of which cost time here

- **Extrapolating the cost exponent from small diagrams runs low.** `T ~ k*C^e` with `e = 2.27`
  fitted below `C = 475`, but really `2.68` at `C = 4219`. Predicted Q(10,10,10) at 8.5 min;
  actual 20.4. Always say the fit is from below.
- **`reference_Q222.csv` in `dependent-region-shur` is stale** on 3 rows (snail direction).
  The closed-form arrow tables are authoritative and agree with the computation.
- **`conjecture.py` in `dependent-region-shur` is the user's own work — do not edit it.** They
  want to compare their manual conjecturing against data-derived conjecturing.
- JPEG is a bad format for these pictures (2-3x *larger* than PNG as well as lossier).
- An atlas of a large diagram declares a canvas of billions of pixels. `--max-px` caps the
  raster; sampling (the default) is what actually makes it readable.

## Data on disk

`heegaard/out/harvest/` — 646 diagrams, 1,385,280 discs, 47 MB, ~69 min to regenerate with
`node harvest.js`. Untracked. `summary.csv` has one row per diagram; `discs/Q<i>-<m>-<n>.csv`
has the discs.

## What is next, in the order the user wants it

1. **A standard Heegaard-diagram class and a CSV format for it**, plus a CSV format for the
   discs, and modularisation around those two formats. Everything below depends on this.
   Open questions the user has not settled: whether the diagram format carries geometry or
   only combinatorics (leaning combinatorics + an optional layout section), and how a
   generator is identified across files (currently `x_13` / `y_7`).
2. **A Python package** that does the computation. Key realisation from this session: for a
   Heegaard diagram the crossings of beta with the alpha curves **are the generators** —
   verified 480/480 — so a Heegaard-specific solver never has to do geometric crossing
   detection, and the (P3) winding check is really integer domain multiplicity. Such a solver
   could have no floating point in it at all, which makes Python's speed penalty largely moot.
   (Measured penalty on the *current* float-heavy primitives: 26-45x versus JS.)
3. **Any `H(r,s)`, not just `Q(i,m,n)`.** Everything below `Q()` is already general; what is
   missing is a constructor and a check that the straight-segment drawing rule still gives an
   embedded picture off the Q family (`findArcCrossings` will report rather than draw wrong).
4. The x-snail, to close the family table.
5. Assembling discs into the algebra. Nothing has been done here.

The JS project is staying — the user wants to draw diagrams on canvas and solve them. Two
independent solvers agreeing on the same CSVs is a better correctness story than one.
