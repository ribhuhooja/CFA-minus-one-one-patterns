# Notes for whoever picks this up

Read `README.md` first for what the project is; this file is the mission, the state of play,
and the traps.

## The mission

**Compute `gCFK^-(P(K))` for a (1,1) pattern `P` and an arbitrary companion `K`.**

`P` is a pattern knot in the solid torus `S^1 x D^2`; `K` is a knot in `S^3`; `P(K)` is the
satellite. The bordered Floer pairing theorem does the work:

```
        CFA^-(P, S^1 x D^2)   [x]   CFDhat(S^3 - nu(K))   =   gCFK^-(P(K))
        ^                                   ^
        from a bordered Heegaard            from HFK^-(K), by Levine Thm 2.6
        diagram for the pattern             (the vertical/horizontal/unstable chains)
```

So there are three jobs, and they are three independent pieces of code:

1. **Diagram manipulation** — write down a bordered Heegaard diagram for `P`, build the
   families `Q(i,m,n)` and `H(r,s)`, validate, draw.
2. **Disc finding** — count the holomorphic discs the diagram bounds. Each disc is one
   `A_infinity` operation of `CFA^-`: a source, a target, a power of `U`, a sequence of Reeb
   chords.
3. **Algebra** — the torus algebra `A(T^2)`, type-A and type-D structures as labelled graphs,
   `CFDhat` from a knot complex, and the box tensor. **No Heegaard diagrams here at all.** Its
   only input from upstream is the disc CSV.

Everything is over `F_2` and `F_2[U]`, so there are no signs. Everything is basis-dependent
and concrete: a `CFA^-` is a graph, a `CFDhat` is a graph, a chain complex is a graph. We do
not check the `A_infinity` relations; we check `d^2 = 0`.

**Later, not now:** eliding most of the `CFDhat` and extracting whatever can be said about
`gCFK^-` from partial companion data. Noted so it is not forgotten.

## Layout

Two JS packages and one Python package, `satellite-floer` (import `satellite_floer`), no
dependencies. Modules are quarantined by language, and **everything new is Python** — it is
slower but it is what gets packaged and uploaded. `pyproject.toml` is at the repository root;
the wheel holds `satellite_floer/` and nothing else, and `tests/`, `docs/`, `figures/` and the
JS stay in the repository only.

| | |
|---|---|
| **`grid-arc-js/`** | the geometry. Given a simple arc on the unit grid, find the grid path joining its endpoints whose enclosed region contains no forbidden point. Knows nothing about Heegaard diagrams. |
| **`heegaard-js/`** | jobs 1 and 2 in JS. Builds `Q(i,m,n)` as `H(r,s)`, draws it, lifts beta to the universal cover, feeds pieces of beta to the solver, reads off Reeb chords and U powers. |
| **`satellite_floer/heegaard/`** | jobs 1 and 2 in Python: a `Diagram` you build with `add_arc`, the validator, the catalogue in `patterns.py`, `chen.py` for general `H(r,s)`, the solver, an SVG visualiser. |
| **`satellite_floer/bordered/`** | job 3. The torus algebra, `CFA^-`, `CFDhat`, `CFK^-`, the box tensor. Imports nothing from `heegaard`. |
| **`satellite_floer/cli.py`** | the one `satellite-floer` command. Each half has a `cli.py` with `register(sub)` and `run(args)`; this joins them and reports errors. It is, with `tests/test_together.py`, the only place that sees both halves. |

Inside `satellite_floer/heegaard` the two jobs are already separate: `solver.py` imports `diagram` and
`layout` and nothing else, and nothing on the diagram side imports the solver (`format.py`
defers its one `solver` import into the function body on purpose, to keep the import graph a
tree). `bordered` imports neither, and `tests/test_bordered.py` checks that by reading its
source.

`src/` in both JS packages is pure: no DOM, no Node builtins, no I/O. `index.html` (the
viewers) and the CLIs are the only impure things. **Verified**: `src/` imports nothing but its
own siblings.

Gitignored on purpose: `out/` (all regenerable), and `heegaard-js/{harvest,analyse,shapes}.js`,
which are one-off study code.

## The file formats

Five CSVs, and they are the whole coupling between the three jobs: `heegaard-diagram 1`,
`heegaard-discs 1`, `bordered-cfa 1`, `bordered-cfd 1`, `bordered-complex 1`. The spec is
`docs/formats.md` -- read it before touching anything that reads or writes one.

## Running things

Everything below runs from the repository root, as `satellite-floer` once installed
(`pip install -e .`) or as `python3 -m satellite_floer` without installing.

```bash
satellite-floer knots                              # the knot catalogue
satellite-floer cfk trefoil                        # a knot complex, as CSV
satellite-floer cfd trefoil -o trefoil.csv         # CFDhat, by Levine Thm 2.6
satellite-floer cfd --cfk mine.csv                 # ... from a CFK^- you wrote
satellite-floer cfa discs.csv                      # a disc table, as a CFA^-
satellite-floer box discs.csv trefoil -o out.csv   # gCFK^- of the satellite
satellite-floer box discs.csv t2 5                 # ... any companion in the catalogue
satellite-floer box cfa.csv cfd.csv                # ... both sides from files
satellite-floer check out.csv                      # d^2, and the rank at U = 1
```

Both together, which is the point of the whole thing:

```python
>>> from satellite_floer.heegaard import build, discs_to_cfa_csv
>>> from satellite_floer.heegaard.solver import enumerate_discs
>>> from satellite_floer.bordered import box, cfd, read_cfa
>>> d = build("hrs", 3, 1)
>>> box(read_cfa(discs_to_cfa_csv(enumerate_discs(d), d)), cfd("trefoil"))
```

```bash
satellite-floer pattern twin-rainbow -o t.csv    # or: generate 1 2 1, or: pattern hrs 3 1
satellite-floer solve t.csv -o discs.csv         # the discs
satellite-floer solve t.csv --format=cfa         # ... as a bordered-cfa CSV
satellite-floer draw t.csv                       # svg: domain, cover, discs
satellite-floer atlas t.csv                      # svg: every disc packed, punctured, 3 sheets
python3 -m unittest discover -s tests            # 170 tests, ~21s: 99 + 65 + 6 together
```

```bash
cd heegaard-js
node discs.js 2 3 5                  # count discs -> out/Q235-discs.csv
node cli.js 2 2 2                    # draw diagram + universal cover (svg)
node atlas.js 2 2 2 --cell=9         # draw a sample of the discs (svg + png)
node serve.js                        # http://localhost:8300/heegaard-js/ interactive
npm test                             # 347 tests
npm run regression                   # ten diagrams against a pinned fixture, ~3s
npm run conjecture                   # Q(i,2,2) vs the closed-form tables, i=1..10
cd ../grid-arc-js && npm test && npm run stress
```

## Conventions that are not obvious

- **Reeb chords**: `rho_1 = N->W`, `rho_2 = E->N`, `rho_3 = S->E`, `rho_12 = N->N`,
  `rho_23 = E->E`, `rho_123 = N->E`. This has `rho_1` and `rho_3` **swapped** relative to how
  the rule was first dictated. It is the only assignment where the composites compose, and it
  is the one that reproduces the reference tables. `REEB_CONVENTIONS.dictated` keeps the other.
- **`y` generators are `iota_0`, `x` generators are `iota_1`.** Not a choice — it is forced.
  In `A(T^2)`, `rho_1, rho_3 : iota_0 -> iota_1`, `rho_2 : iota_1 -> iota_0`,
  `rho_12 : iota_0 -> iota_0`, `rho_23 : iota_1 -> iota_1`, `rho_123 : iota_0 -> iota_1`, and
  every disc's chord word must be idempotent-composable from its source to its target. Only
  one of the two assignments works. **Verified: 0 violations in 903 discs** over
  `twin-rainbow` and five `Q(i,m,n)`. `bordered` does not hard-code it — it infers.
- **A chord word is a sequence, not a product.** `m_3(x, rho_1, rho_2)` (word `P1P2`) and
  `m_2(x, rho_12)` (word `P12`) are different operations, and in the box tensor the first
  needs a two-edge path in the `CFDhat` and the second a one-edge path. Never multiply. Note
  `(rho_2, rho_1)` is a legal argument list -- the idempotents meet -- even though
  `rho_2 . rho_1 = 0` in the algebra, and it occurs in the disc tables.
- **The box tensor, named.** With single letters on both sides it would be the tensor
  (Kronecker, categorical) product of edge-labelled graphs. With WORDS on the type-A side it
  is the product construction for automata: the CFA is a transducer reading chord words and
  emitting powers of U, the CFDhat is an NFA over the same alphabet, and this is their
  composition. Chop each CFA word into a path through fresh intermediate states and it is the
  plain tensor product again.
- **Why the box tensor terminates even against an unbounded `CFDhat`.** The unknot's is a
  single generator with a `rho_12` self-loop, so it has paths of every length. It is the CFA
  side that is bounded: finitely many discs means a longest word, and only paths of exactly
  that many arrows are ever enumerated.
- `tau(K) = A(xi_0) = -A(eta_0)`, where `xi_0` is the generator surviving the vertical
  homology and `eta_0` the horizontal one. Both are computed and cross-checked. With
  `d b = a + U c` the trefoil is the **right-handed** one, `tau = +1`.
- **`strategy: 'walk'` is the default** everywhere in the JS. `'search'` is the exhaustive
  reference and the only strategy that fills in `result.trace`. Test harnesses pin `'search'`
  explicitly where they mean the exhaustive answer — do not remove those.
- `assumeSimple` / `assumeValid` on `solve` skip checks that are properties of the *curve*
  rather than the piece. Only safe because beta's lift is embedded and validated once.

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
- **`Q(i,m,n) IS H(1+2im-m, n+3m-2mn+4imn-4im-2)`** — 150/150 arc for arc for i,m,n up to 6,
  disc tables identical, checked by hand out to Q(9,25,25) = H(426,20448), 22199 arcs.
- **`twin-rainbow` is Q(1,2,1) = H(3,1)**. The earlier note that it was outside the Q family
  was wrong, and wrong only because `qmn.py` refuses `n < 2`.
- **No disc table yet found has two discs agreeing in (source, target, U, chords)**, so mod-2
  cancellation has never actually fired. `bordered` reduces mod 2 anyway and says so when it
  happens.
- **The whole cycle runs.** Diagram -> discs -> `CFA^-` -> box with `CFDhat` -> `gCFK^-`, for
  `Q(i,m,n)` built as `H(r,s)` at (1,2,1), (1,2,2), (2,2,2), (1,3,2), (2,2,3) against
  `unknot`, `trefoil`, `lh-trefoil`, `figure-eight`, `T(2,5)`: **every one has `d^2 = 0` and
  free homology of rank exactly 1** at `U = 1`, which is what a knot complex must give.
  Checked twice over, once through the two CLIs and files only and once through the two APIs
  in one session.
- **`heegaard solve --format=cfa` and `bordered cfa <disc csv>` write byte-identical files**,
  and boxing either gives a byte-identical complex.
- **Boxing with the unknot keeps exactly the `iota_0` half of the CFA.** Its `CFDhat` is one
  generator, so `Q(i,m,n) [x] unknot` has one generator per `y`, and it comes out with free
  homology of rank one every time -- `Q(1,2,1)` applied to the unknot has `gCFK^-` of rank 1
  with `y_4 = U y_3 = U^2 y_2`.

- **2-bridge names** -- `satellite_floer/heegaard/bridge.py`. A (1,1) unknot pattern is a
  2-component 2-bridge link, so it has Schubert's `b(p,q)` and Conway's `C(a_1,...,a_n)` as
  well; the `a_i` are the continued fraction of `p/q`, and ours join at `p = 2s+4|r|`,
  `q = sign(r)(2|r|-1)`. `satellite-floer bridge --hrs 3 1` prints all three. It is ONLY a
  dictionary and narrows nothing -- a test asserts `diagram.py` and `solver.py` never mention
  it, because the rest of the package takes any diagram at all and most (1,1) patterns are not
  unknot patterns. Two facts checked rather than assumed: `p` is always even, which is what
  says the link has two components; `gcd(p,q)=1` is EXACTLY the `gcd(2|r|-1,s+1)=1` that
  `H(r,s)` needs for beta to be one curve, since `4|r| = 2 mod (2|r|-1)` gives `p = 2(s+1)`
  mod q with q odd; and `|q| < p/2` (the standard range) holds WITHOUT normalising, since
  `|q| = 2|r|-1` and `p/2 = s+2|r|` make it just `s > -1`. So do NOT reduce q into (0,p) --
  that moves it out of the standard range. `b(p,-q)` is the mirror and negates every Conway
  term, and `H(-r,s)` comes out as exactly `b(p,-q)`, so reflecting the Chen form mirrors the
  link. Schubert: `b(p,q)=b(p,q')` iff `q' = q^{+-1} mod p`; `q -> q^-1` REVERSES the Conway
  word, mirrored exactly when the two reduce to opposite signs (4000 links, no exceptions).
  H(3,1) = b(14,5) = C(2,1,4).

  **That last one is a check on the whole pipeline, and it passes.** H(3,1) = b(14,5) and
  H(2,3) = b(14,3) are the same link (5*3 = 1 mod 14) but quite different diagrams -- 8x5 with
  25 discs against 8x3 with 24. Being the same pattern they must give the same satellite
  invariants, and they do: `dim H(C/UC)` over F_2, a homotopy invariant of a complex over
  F_2[U] and a plain rank computation, agrees on every companion in the catalogue (unknot 1,
  trefoil 29, lh-trefoil 31, figure-eight 31, T(2,5) 29) although the generator counts differ
  (47 against 41). Checked on 47 such pairs. Not a heegaard test -- it needs `bordered`, and
  the packages stay independent -- so it is recorded here instead.

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
- **The Alexander grading cannot be read off the arrows without two extra theorems.**
  Horizontal arrows pin differences exactly, but a vertical arrow's LENGTH is an unknown -- the
  trefoil's `k_1` is unconstrained by `d b = a + U c` alone. What closes it is that the
  vertical and horizontal length multisets agree (the i-j symmetry of `CFK^infinity`) and that
  the multiset of gradings is symmetric about 0. `infer_alexander` uses both and raises rather
  than guessing if more than one answer survives.
- **`discs_to_cfa_csv` deliberately does NOT reduce mod 2, and `read_cfa` does.** They agree
  byte for byte today only because no disc table has ever had a cancelling pair. The moment
  one does, `heegaard solve --format=cfa` and `bordered cfa <disc csv>` will differ by exactly
  those rows -- and `bordered`'s answer is the right one. The test that pins them together
  will catch it.
- `H(3,1)` is form (a), **not** the two-rainbow form: `sigma(3,1) = -1`. Form (b) needs
  `sigma` strands between its turning rainbows, so it is not even constructible when `sigma`
  is negative. The nearest form (b) neighbours are `H(2,1)`, `H(3,2)`, `H(3,3)`.

## Data on disk

`heegaard-js/out/harvest/` — 646 diagrams, 1,385,280 discs, 47 MB, ~69 min to regenerate with
`node harvest.js`. Untracked. `summary.csv` has one row per diagram; `discs/Q<i>-<m>-<n>.csv`
has the discs.

## What is next, in the order the user wants it

1. **The algebra**, `satellite_floer/bordered` -- built, and the cycle runs. Still open inside it:
   - **A PARTIAL BOX TENSOR.** The user wants to name one well-chosen generator of the
     `CFDhat` and one part of the `CFA`, tensor only those, argue that what comes out is a
     direct SUMMAND of the whole thing, and find the `F_2[U]` in there. This is the shape the
     project is heading towards, and it makes two other items below much cheaper -- so do it
     before them, not after.
   - **Homology over `F_2[U]` may not be needed at all.** The reason to want Smith normal form
     over the PID was to see the free part and the torsion separately. But if a summand can be
     computed on its own (above), it is enough to compute that summand and see that the
     `F_2[U]` lives in it -- no PID machinery, no torsion computation. Keep the rank at `U = 1`
     as the cheap global check and reach for Smith normal form only if the summand argument
     turns out not to be available.
   - **Reducing a type-D structure.** `CFDhat` from a knot complex is already reduced, so the
     box tensor rejects idempotent coefficients rather than handling them. A general
     `reduce()` (cancel arrows with invertible coefficient) is what would let arbitrary
     type-D input in.
   - **Bases that are not simultaneously simplified.** Levine Thm 2.6 wants a basis that is
     both vertically and horizontally simplified; `bordered` checks the given basis is one and
     refuses otherwise, and every knot in the catalogue satisfies it. Handling a basis that is
     only one or the other needs the change of basis `xi_p = sum a_{p,q} eta_q` carried
     explicitly.

     The user reports **a theorem that gives some help here: `xi_0 = eta_1` and
     `eta_0 = xi_1`.** Worth pinning down before building on it, because it does not hold
     index-for-index in the one example we have written out. For the trefoil under Thm 2.6's
     own labelling (`xi_{2j-1} -> xi_{2j}` is the vertical arrow, `eta_{2j-1} -> eta_{2j}` the
     horizontal one) the trefoil gives `xi = (c, b, a)` and `eta = (a, b, c)`, so
     `xi_0 = c` while `eta_1 = b`. What IS true in both worked examples is the thing the code
     already relies on: **the `xi` and the `eta` are the same SET of generators, differently
     labelled** -- trefoil `{a,b,c}` both ways, figure-eight `{a,b,c,d,e}` both ways -- so a
     single basis is simultaneously simplified and the "change of basis" is a permutation.
     Either the theorem is stated in a different indexing, or it says something sharper than
     that; find out which before relying on it.
   - **Checking the `A_infinity` relations**, and that a type-D structure really is one.
2. **The x-snail**, to close the family table in `heegaard-js/shapes.js`.
3. **More beautiful pictures.** Readable is not the same as beautiful. Recorded also as a TODO
   in `layout.strokes`: the fans are spaced by an even share of the gap rather than by eye;
   the straight strands could take a slight bow where there is room; and where a fan is
   pinched the give is spread by a soft minimum, which is a smooth fudge rather than a
   considered allocation.
   - **Pictures re-space before drawing** (`layout.tune_spacing`): the generators of each
     alpha curve may be gathered into part of the edge and the strands across the domain
     bowed into square-on S-curves, whichever `layout.crowding` likes best. On Q(2,2,2) that
     takes the closest 1% of beta from 0.25 of a spacing to 0.79 -- the left-edge fan had
     been jammed against the strand rising from the hole. Pictures only; the solver keeps
     even spacing and straight strands, and a test checks the disc table is identical
     either way. Neither change alone helps: re-spacing alone moves the jam to the top
     edge, and bowing alone with even spacing makes Q(2,2,2) cross and fall back to radial.
     Matching an arc's angle to a straight strand across the seam was tried and did not help.
   - **The user's hand-drawn Q(i,2,2) sheets, redrawn** -- `figures/qi22.py`,
     with the six sheets transcribed as data in `figures/qi22_spec.py`: each family's source
     and target in the user's notation (i, j, k) and the cell where they drew it. Drawn at
     i=2, j=3, k=0 -- j=3 is the largest at which every j-family exists when i=2, and the
     thin edge families (rho_1, rho_12, rho_2) grow with j. The U power and chords come from
     the computed table, not the handwriting. `render_atlas(centres=, rows=, names=,
     caption=False, key=False, colours=)` is what lays a sheet out by hand. No caption and no
     key on these, by request -- set six to a page, a key beside each grid is ~2pt text.
     Coloured by kind as the user coloured them by hand (`GROUPS` in the spec: orange
     families, green special arrows, pink snail), so same-coloured discs can touch and each
     gets a darker outline; `--key` puts the key back.
   - **TODO: a `punctured` toggle for the universal cover** (Python at least):
     `render_cover` and `render_discs` should take the same `punctured=` option that
     `render_atlas` already has, drawing every lattice point as a hole -- the corner of the
     square is the boundary of the bordered diagram -- and `draw` should get the flag. The
     ellipse-drawing loop in `render_atlas` is the thing to lift out.
4. **`H(r,s)` on the JS side.** Python has it (`satellite_floer/heegaard/chen.py`); JS does not.
5. **Integer domain multiplicity** in place of the winding-number check on completed
   candidates — the last float in the JS solver. Note the regions are faces of the
   alpha-union-beta arrangement, finer than cells, since beta cuts a cell.

The JS project is staying — the user wants to draw diagrams on canvas and solve them. Two
independent solvers agreeing on the same CSVs is a better correctness story than one.

## Done, and worth not re-deriving

- **The algebra** -- `satellite_floer/bordered`. The torus algebra derived from the four boundary
  points rather than tabulated; `CFA^-` and `CFDhat` as labelled graphs with idempotents
  inferred from the chords; `CFK^-` with the Alexander grading inferred when it is
  determined; Levine Thm 2.6; the box tensor; three CSV formats; 65 tests of its own. It imports nothing
  but the standard library, and a test asserts that the string "heegaard" does not appear in
  any of its modules.
- **A Heegaard-aware JS solver** — `heegaard-js/src/fast.js`, the default engine. Worth 2.2x
  (less than hoped: the incremental builder had already amortised crossing detection away).
  The real gain is that the inner loop has no geometry in it. `engine: 'generic'` keeps the
  old path and a test asserts the two agree. Verified 480/480: a piece with `k` arcs has
  exactly `k+1` crossings and each **is** the generator at that track node.
- **The Python diagrams and solver** — `satellite_floer/heegaard/`. Same algorithm, same answers, same two CSV formats;
  disc lists agree with the JS exactly on every diagram tried and `solve` emits a
  byte-identical CSV. About 9x slower than JS.
- **Any `H(r,s)`, not just `Q(i,m,n)`** — `satellite_floer/heegaard/chen.py`. Built in Chen form on
  the annulus, then the region is slid until `z` is at a corner, which cuts beta in `2|r|-1`
  new places — those are the new generators — and a quarter turn puts `z` top left. The re-cut
  uses real geometry on purpose: the crossing COUNT can be read off, but their ORDER along the
  cut cannot, and the order is what fixes the diagram. `python3 figures/report.py` writes
  `out/general-diagrams.html` with every stage drawn.
- **The SVG visualiser** — `satellite_floer/heegaard/render.py` and `satellite-floer draw`:
  domain, universal cover and discs, from the CSV and nothing else. Two facts worth keeping: a
  disc's polygon can be rebuilt exactly from its (source, offset, path), so a disc table
  written by the JS draws here without re-solving — verified byte-identical to drawing
  Python's own solve; and the pictures use `layout.route`, so what is drawn IS the embedding
  the winding numbers were computed in.
- **`layout.route`.** Each arc is ONE piece of geometry — a segment or a single CUBIC — emitted
  as one SVG command, nothing sampled. Same edge wants the semicircle on its feet; two edges at
  a corner want the quarter ellipse through both, centred on that corner; opposite edges are
  straight. A cubic and not a quadratic on purpose: an arc must leave both generators
  square-on AND be shrinkable to fit what contains it, and one control point cannot do both.
  Two controls on the inward normals hold the angles exactly while the bulge slides.

  Square-on is not decoration. With `r` rainbows on the bottom, `r` arcs at the top left and
  `r` at the top right are the two HALVES of `r` more rainbows, hanging from the top edge and
  cut by the left/right identification. Right angles at the seam are what make the halves join
  as one smooth rainbow in the cover.

  How much of its shape an arc gets is measured against what CONTAINS it, outermost first, by
  casting a ray at the parent's own curve; the share is `h/(h+1)` of the gap and is spent on
  the APEX. Then two corrections, both of which cost a session to find: a corner arc takes a
  SOFT minimum of want and room (a hard min gives nothing until it gives everything, and
  Q(2,2,2)'s fan sat at full size for seven arcs then piled into a heap); and then the arc is
  CHECKED against everything already drawn and shrunk until clear (the ray only asks what is
  straight ahead, and a rainbow beside a steeply rising strand clears it at the apex and clips
  it with its flank, and the two are not nested, so no parent-based rule would compare them).

  Rules tried that DO NOT work, all costing time: a shape fixed by its endpoints alone has no
  freedom left to clear what it nests; ranking bulge by nesting height fails because straight
  strands have zero bulge; making only the deepest opposite-edge arc straight makes its
  neighbours cross it (ALL of them must be straight, which is safe); and spending the room on
  the CONTROL POINTS quarters the space each level, since a cubic peaks only 3/8 along them.

  Not a proof, so strokes are CHECKED and fall back to `route_radial` if any two meet
  (`layout.stroked` says which); 64/64 `Q(i,m,n)` with i,m<=4, n<=5 currently draw as strokes.
  Also: `crossings_between` needed a tolerance — arcs sharing a line give determinants of 0.0
  against 3e-18, which a strict `> 0` test calls a crossing. Two routings NOT worth
  revisiting: radial-from-disc for pictures, and depth-banded sweeps parallel to the boundary.
