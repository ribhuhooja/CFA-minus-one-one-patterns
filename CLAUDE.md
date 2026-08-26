# Notes for whoever picks this up

Counting holomorphic discs in bordered Heegaard diagrams. Read `README.md` first for what the
project is; this file is the state of play and the traps.

## Layout

Three packages, no dependencies, no build step. Modules are quarantined by language.

- **`grid-arc-js/`** — the geometry. Given a simple arc on the unit grid, find the grid path
  joining its endpoints whose enclosed region contains no forbidden point. Knows nothing about
  Heegaard diagrams.
- **`heegaard-py/`** — the same, in Python: a `Diagram` class you build with `add_arc`, the
  validator, a named-diagram catalogue in `patterns.py` (`qimn`, `twin-rainbow`, ...), a
  solver, and an SVG visualiser. CSV in, CSV or SVG out.
- **`heegaard-js/`** — the diagrams. Builds `Q(i,m,n)` as `H(r,s)`, draws it, lifts beta to the
  universal cover, feeds pieces of beta to the solver, reads off Reeb chords and U powers.

`src/` in both is pure: no DOM, no Node builtins, no I/O. `index.html` (the viewers) and the
CLIs are the only impure things. **Verified**: `src/` imports nothing but its own siblings.

Gitignored on purpose: `out/` (all regenerable), and `heegaard-js/{harvest,analyse,shapes}.js`,
which are one-off study code — the package is meant to be a package for computing CFAs.

## Running things

```bash
cd heegaard-js
node discs.js 2 3 5                  # count discs -> out/Q235-discs.csv
node cli.js 2 2 2                    # draw diagram + universal cover (svg)
node atlas.js 2 2 2 --cell=9         # draw a sample of the discs (svg + png)
node serve.js                        # http://localhost:8300/heegaard-js/ interactive disc finder
npm test                             # 347 tests
npm run regression                   # ten diagrams against a pinned fixture, ~3s
npm run conjecture                   # Q(i,2,2) vs the closed-form tables, i=1..10
cd ../grid-arc-js && npm test && npm run stress
```

## What is established

Do not rely on these in the solver. This is the data that we have found.

- **Disc count**: `2m(n+2)^2 * i - [m(n^2+2n+5) - m^2 - n^2]`. Exact on all 646 harvested
  diagrams, i up to 20. At `m=n=2` it is `64i-18`.
- **Q(i,2,2) matches the user's closed-form arrow tables exactly**, i = 1..10, all 3340 rows.
- **Raising i past 2 adds no new (chord word, U) classes**, tested to i=20. Every class count
  is linear in i; 72% do not depend on i at all. Exactly three classes are empty at i=1
  (`rho_3`, `rho_23`, `rho_123`, each U^1).
- A general-`(i,m,n)` family table covering **83.6%** of discs with **zero false positives**
  lives in `heegaard-js/shapes.js` as executable code. The gap is the x-side "snail" — chordless
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

`heegaard-js/out/harvest/` — 646 diagrams, 1,385,280 discs, 47 MB, ~69 min to regenerate with
`node harvest.js`. Untracked. `summary.csv` has one row per diagram; `discs/Q<i>-<m>-<n>.csv`
has the discs.

## What is next, in the order the user wants it

0. ~~**A Heegaard-aware JS solver**~~ — **DONE**, `heegaard-js/src/fast.js`, default engine.
   Worth 2.2x (less than hoped: the incremental builder had already amortised crossing
   detection away). The real gain is that the inner loop now has no geometry in it, which is
   what makes a port to a slower language reasonable. `engine: 'generic'` keeps the old path
   and a test asserts the two agree. The remaining float is the (P1)-(P4) check on completed
   candidates — replacing that with integer domain multiplicity is still open, and the regions
   are faces of the alpha-union-beta arrangement, finer than cells, since beta cuts a cell.
   For reference, what it replaced:

   | general solver | Heegaard-aware |
   |---|---|
   | crossings by root-finding, O(points) | the generators, sliced from the node list |
   | which alpha edge | from the generator's side and index |
   | which cells | each arc's cell is fixed per diagram, then tile-shifted |
   | blocked edges | the alpha edges the generators sit on |
   | §2 validation per piece | not applicable — nothing to validate |

   Verified 480/480: a piece with `k` arcs has exactly `k+1` crossings and each **is** the
   generator at that track node. Precompute per diagram: for each arc, its (entry generator,
   exit generator, entry side, exit side, cell); per generator, its alpha edge and parameter.
   Then a piece is a run of arcs and everything above is a lookup.

   Sequence: keep the existing global check (P1)-(P4) at first, replacing only the per-piece
   derivation — that is where the time goes and it is the safe half. Verify against
   `npm run regression` and `npm run conjecture` (both must stay byte-identical), then measure.
   Only afterwards consider replacing the winding check with integer domain multiplicity;
   note the regions are faces of the alpha-union-beta arrangement, finer than cells, since
   beta cuts a cell into pieces.

1. **A standard Heegaard-diagram class and a CSV format for it**, plus a CSV format for the
   discs, and modularisation around those two formats. Everything below depends on this.
   Open questions the user has not settled: whether the diagram format carries geometry or
   only combinatorics (leaning combinatorics + an optional layout section), and how a
   generator is identified across files (currently `x_13` / `y_7`). ~~Also a way to
   visualize this from the CSV.~~ — **the visualiser is DONE**, `heegaard-py/heegaard/render.py`
   plus `python3 -m heegaard draw`: domain, universal cover and discs as SVG, from the CSV and
   nothing else. Two facts worth keeping: a disc's polygon can be rebuilt exactly from its
   (source, offset, path), which is what `solver.attach_regions` does, so a disc table written
   by the JS draws here without re-solving — verified byte-identical to drawing Python's own
   solve; and the pictures use `layout.route`, so what is drawn IS the embedding the winding
   numbers were computed in.

   `layout.route` was rewritten for this. Each arc is ONE piece of geometry -- a segment or
   a single CUBIC -- emitted as one SVG command, nothing sampled. Same edge wants the
   semicircle on its feet; two edges at a corner want the quarter ellipse through both,
   centred on that corner; opposite edges are straight. A cubic and not a quadratic on
   purpose: an arc must leave both generators square-on AND be shrinkable to fit what
   contains it, and one control point cannot do both -- pull it in to shrink and the ends
   stop being square-on. Two controls on the inward normals hold the angles exactly while the
   bulge slides.

   Square-on is not decoration. With `r` rainbows on the bottom, `r` arcs at the top left and
   `r` at the top right are the two HALVES of `r` more rainbows, hanging from the top edge and
   cut by the left/right identification (`y_j` left and `y_j` right are one point of the
   torus). Right angles at the seam are what make the halves join as one smooth rainbow in the
   cover -- `render_cover` shows it, and the tangents are exactly 0 and 180 degrees.

   How much of its shape an arc gets is measured against what CONTAINS it, outermost first,
   by casting a ray at the parent's own curve; the share is `h/(h+1)` of the gap and is spent
   on the APEX. Then two corrections, both of which cost a session to find:
   - a corner arc takes a SOFT minimum of want and room. Where a fan is pinched the region is
     wedge-shaped, so it must give somewhere; a hard min gives nothing until it gives
     everything, and Q(2,2,2)'s fan sat at full size for seven arcs then piled into a heap
     (spacing 0.063 -> 0.044, 0.018, 0.014, 0.010, 0.006). Softened it tapers 0.057 -> 0.011.
     A rainbow barely gives: its size is fixed by its own feet so it cannot over-reach, and
     softening it destroyed the even ladder (0.217, 0.183, 0.150... became geometric).
   - then the arc is CHECKED against everything already drawn and shrunk until clear. The ray
     only asks what is straight ahead: a rainbow beside a strand rising steeply out of the
     edge next to it clears it at the apex and clips it with its flank, and the two are not
     nested, so no parent-based rule would ever have compared them.

   Rules tried that DO NOT work, all of them costing time: a shape fixed by its endpoints
   alone has no freedom left to clear what it nests; ranking bulge by nesting height fails
   because straight strands have zero bulge, so their children still swing out past them;
   making only the deepest opposite-edge arc straight makes its neighbours cross it (ALL of
   them must be straight, which is safe -- straight chords in a convex square between
   non-interleaving points cannot cross); and spending the room on the CONTROL POINTS quarters
   the space each level, since a cubic peaks only 3/8 of the way along them.

   Not a proof, so strokes are CHECKED and fall back to `route_radial` if any two meet
   (`layout.stroked` says which); 64/64 Q(i,m,n) with i,m<=4, n<=5 currently draw as strokes.
   Also: `crossings_between` needed a tolerance -- arcs sharing a line give determinants of
   0.0 against 3e-18, which a strict `> 0` test calls a crossing. Two routings NOT worth
   revisiting: radial-from-disc for pictures (preserves relative radius so short arcs jam
   against the boundary, and creases along the ray to each corner), and depth-banded sweeps
   parallel to the boundary (provable, but draws a staircase and needs 25-45 points per arc
   instead of 4).

   **TODO -- the user wants the pictures more beautiful still.** Readable is not the same as
   beautiful. Known wants, recorded also as a TODO in `layout.strokes`: the fans are spaced by
   an even share of the gap rather than by eye; the straight strands could take a slight bow
   where there is room for one; and where a fan is pinched the give is spread by a soft
   minimum, which is a smooth fudge rather than a considered allocation.

2. ~~**A Python package**~~ — **DONE**, `heegaard-py/`. Same algorithm, same answers, reads
   and writes the same two CSV formats; disc lists agree with the JS exactly on every diagram
   tried and `solve` emits a byte-identical CSV. About 9x slower than JS. Its layout does NOT
   assume straight arcs: it routes as straight chords in a disc (which cannot cross when the
   chord diagram does not interleave) and carries them back to the square, so it works on any
   valid diagram.
3. **Any `H(r,s)`, not just `Q(i,m,n)`.** Everything below `Q()` is already general; what is
   missing is a constructor and a check that the straight-segment drawing rule still gives an
   embedded picture off the Q family (`findArcCrossings` will report rather than draw wrong).
4. The x-snail, to close the family table.
5. Assembling discs into the algebra. Nothing has been done here.

The JS project is staying — the user wants to draw diagrams on canvas and solve them. Two
independent solvers agreeing on the same CSVs is a better correctness story than one.
