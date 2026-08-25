# heegaard

Bordered Heegaard diagrams on the torus, and the `Q(i, m, n)` family as `H(r, s)`.

```bash
node discs.js 2 2 2                    # count every disc -> out/Q222-discs.csv
node cli.js 2 2 2                      # draw it -> out/Q222.svg and out/Q222-cover.svg
node atlas.js 2 2 2 --cell=9           # draw every disc at once -> out/Q222-atlas.svg
node serve.js                          # poke at it by hand, http://localhost:8300/heegaard-js/
node discs.js 2 2 2 --format=reference  # ... in the reference tables' own layout
node test/compare-conjecture.js 4      # check Q(i,2,2) against the closed-form tables
node test/compare-reference.js 2 2 2   # ... and against reference_Q222.csv
npm test
```

Counting is headless. `discs.js` imports `src/` and `../grid-arc-js/src/` and never touches a
DOM; the viewer is one more consumer of the same functions, not a layer anything goes
through.

```js
import { Q, layout, renderDiagram, renderUniversalCover } from './heegaard-js/src/index.js';
const diagram = Q(2, 2, 2);            // H(r=7, s=14), validated on construction
diagram.components();                  // beta traced through the gluings
renderDiagram(layout(diagram, { cell: 26 }));
```

## The picture

The fundamental domain is a rectangle whose horizontal edges are glued to each other and
whose vertical edges are glued to each other. Its boundary therefore carries two alpha
curves: `alpha_x` (bottom == top) and `alpha_y` (left == right). Beta is drawn inside.

Every intersection of beta with an alpha curve is a generator — `x_j` on `alpha_x`, `y_j`
on `alpha_y`. Index `j` names one point of the torus but **two slots** on the rectangle's
boundary (bottom and top, or left and right); beta occupies each slot exactly once, and
those two slots are the two germs of beta at that point. That is the whole bookkeeping
rule, and `validate()` enforces it, along with the requirement that the chord diagram of
arcs be non-crossing — which is what says beta is embedded.

The domain is `xCount` by `yCount` cells, so its aspect ratio reflects how many generators
sit on each alpha curve. Generator `k` sits at `(k + 1/2)` cells along its edge, which
leaves the same half-cell gap at both ends and so makes the spacing uniform across the
gluing seam — the universal cover comes out as an even grid.

`y_0` sits beside the **top**-left corner, not the bottom. That is forced rather than
chosen: `y_0 -- x_0` joins two boundary slots that are adjacent, so it has to hug a corner,
and non-crossing then fixes which one.

## The basepoint

The basepoint sits in the **top-left** corner of the domain — exactly where the grid solver
puts the forbidden point of a cell. It has to lie *beyond* the last beta arc reaching into
that corner; that is what "for small enough epsilon" means here, and it is measured off the
picture rather than fixed. `cornerClearance` is how close any arc gets to the corner along
the diagonal, and the basepoint goes at a fraction of it (`basepointFraction`, default 0.35).

It is reported as `epsilon` in units of the domain, so a cover of these domains is a unit
grid carrying a forbidden point at `(k + eps, l + 1 - eps)` — the solver's convention, with
the same number on both sides. For `Q(2,2,2)` the nearest arc is 13px from the corner along
the diagonal, giving `eps = 0.00407`.

## Q(i, m, n)

```
r    = 1 + 2im - m
s    = n + 3m - 2mn + 4imn - 4im - 2
maxx = 2r + s + m + n - 3      x generators, 0..maxx
maxy = 4im - 2m = 2r - 2       y generators, 0..maxy
```

Requires `n >= 2` (asserted), and `r >= 1`, `s >= r`. Six families of arcs; the arrows are
only how they were dictated, the arcs themselves are undirected:

| | arc | range |
|---|---|---|
| F1 | `y_j` (left) — `x_j` (top) | `j = 0 .. maxy` |
| F2 | `x_j` (bottom) — `x_{2r-1+j}` (top) | `j = 0 .. s-r` |
| F3 | `x_{s-r+1+j}` — `x_{s+r-j}`, both on the bottom (the rainbow) | `j = 0 .. r-1` |
| F4 | `x_{s+r+j}` (top) — `x_{s+r+1+j}` (bottom) (dependent) | `j = 0 .. m+n-3` |
| F5 | `y_j` (right) — `x_{maxx-j}` (top) | `j = 0 .. r-1` |
| F6 | `y_{maxy-j}` (right) — `x_{maxx-j}` (bottom) | `j = 0 .. r-2` |

That is `4r + s + m + n - 3` arcs, which is exactly `(maxx+1) + (maxy+1)` — one arc end per
boundary slot, with none left over.

**Which edge each dependent arc end sits on is forced, not chosen.** F4 was specified by
index alone. After F1, F2 and F5, the top edge is short of exactly `s+r .. s+r+m+n-3`;
after F2, F3 and F6, the bottom edge is short of exactly `s+r+1 .. s+r+m+n-2`. So the
dependent arcs run from `x_{s+r+j}` on the **top** to `x_{s+r+1+j}` on the **bottom**:
`m+n-2` strands crossing the domain, each landing one index right of where it left. The
constructor asserts the count is `m+n-2`.

## How the arcs are drawn

In any one copy of the domain an arc is a single primitive: a **straight segment** if its ends
are on different edges, or a **parabola** bulging away from the edge if they are on the same
one, of height `bulge x half-span` with `bulge = 0.45`. That primitive — `ends`, and `control`
for a bulge — is what the arc *is*. Drawing uses it directly (a quadratic Bézier survives the
map into SVG coordinates unchanged, so there is nothing to sample), and `path` is only a
sampling of it for the checks that need points. `samples` says how fine; the apex is always
among them, which is what keeps a basepoint under a bulge on the inside of the polyline too.

That is all it takes, and it is not a coincidence. With `(k+1/2)`-cell spacing and
`H = (2r-1)` cells, families F1, F2 and F6 are all lines of slope exactly `+1` cell per
cell, F5 is slope `-1`, and the dependent strands are steep. Parallel families cannot
cross each other, and the `+1` and `-1` families provably meet only outside the domain.
The rainbows sit in the wedge under the shallowest F2 line, whose foot is exactly one cell
left of the outermost rainbow's foot; keeping `bulge < 1/2` keeps the parabola's slope at
its foot below one, which is what fits it into that wedge.

`findArcCrossings` re-checks this numerically on the sampled paths rather than trusting the
argument. It returns nothing for every parameter set in the test sweep. For a diagram
outside the Q family the straight-segment rule may not suffice; it will be caught, not
silently drawn wrong.

## Colours

The alpha curves are the same pale red as the grid solver next door (`#f0b9b9`) and beta is
pale blue (`#7ea6ec`), so the two pictures read as the same object: in the universal cover
the diagram *is* a grid with a blue curve on it, which is the input the solver wants.

## Modules

| module | owns |
|---|---|
| `src/diagram.js` | `HeegaardDiagram`: slots, chords, `validate`, `components`. No geometry. |
| `src/qmn.js` | `Q(i,m,n)` and `parameters(i,m,n)`. |
| `src/layout.js` | positions and arc shapes, in mathematical coordinates (y up). No SVG. |
| `src/render.js` | SVG, single domain and universal cover. The only place y is flipped. |
| `src/track.js` | beta lifted to the universal cover: nodes, segments, sub-arcs, homology class. |
| `src/bridge.js` | normalising a cover into the grid solver's unit grid, and the tolerances that needs. |
| `src/discs.js` | enumerating discs, reading off Reeb chords, counting U, and CSV output. |
| `src/conjectured.js` | the closed-form arrow tables for Q(i,2,2), transcribed as given. |
| `src/atlas.js` | every disc of a diagram drawn at once, as one large universal cover. |
| `discs.js` | CLI: every disc of a diagram, as CSV. |
| `index.html` | the disc finder (below). `serve.js` roots at the repo so it can import grid-arc too. |

## Lifting beta, and finding discs

On the torus beta is one closed curve; in the universal cover it is an embedded track.
Following it is mechanical: traverse an arc, then cross the alpha curve at its far end,
which means stepping into the neighbouring copy of the domain and continuing from the glued
slot. `liftBeta` does that and returns the track's **nodes** — its crossings with the alpha
curves, i.e. the lifts of the generators — together with the segment between each
consecutive pair, and the tile shift after one circuit, which is beta's homology class
(`[-1, 0]` for `Q(2,2,2)`).

A piece of beta can only be handed to the grid solver if **both its ends lie on an alpha
curve**: the solver's red path runs along the grid, so it has nowhere to start from in the
middle of a cell. So a usable piece is a run of consecutive arcs, node to node, and that is
the unit `subTrack` deals in — which is also why the tool snaps to generators rather than to
arbitrary points of beta.

`bridge.js` does the rest. Dividing by `(W, H)` turns the cover into the solver's unit grid:
copies become cells, alpha curves become the integer lines, basepoints become forbidden
points. The one thing that does not carry over is scale. The solver's defaults assume a
curve drawn by hand, which can easily stay 0.08 of a cell from every lattice point; beta
cannot, since generator `x_0` sits half a diagram-cell from a corner. So `gridSettingsFor`
measures the tolerances off the diagram, subject to the rule that beta must never come
closer to a lattice point than the forbidden point does:

    epsForbidden * sqrt(2)  <  minLatticeDistance  <  beta's closest approach

For `Q(2,2,2)`: `0.00575 < 0.00918 < 0.01529`. The test suite checks all of it, and checks
that no piece of beta is ever rejected as invalid input.

## Counting discs

`enumerateDiscs(diagram)` walks over every piece of beta worth trying and returns what each
disc carries. Beta meets each generator once per circuit, so the nodes of one circuit are
exactly the generators, once each; from each of them the enumeration runs both ways along
beta, out to the point where beta comes back to that same generator — one circuit either
side. Every disc with that source lies in that range.

**Reeb chords.** At each lattice point of the path there is an incoming direction and an
outgoing one, and the six pairs that can occur are exactly the six moves the local rules
permit — which is why there are exactly six chords to name. A path of `k+1` steps reads off
`k` chords, one per lattice point, in the order it walks them; a path with both ends on one
edge carries none.

The naming is fixed by asking the composites to compose. Writing a chord as `(in, out)`,
`rho_12` should start where `rho_1` starts and end where `rho_2` ends, and likewise the
others. That holds for exactly one of the two ways round:

| | | |
|---|---|---|
| `rho_1` = `N -> W` | `rho_12` = `N -> N` | = (start of `rho_1`, end of `rho_2`) |
| `rho_2` = `E -> N` | `rho_23` = `E -> E` | = (start of `rho_2`, end of `rho_3`) |
| `rho_3` = `S -> E` | `rho_123` = `N -> E` | = (start of `rho_1`, end of `rho_3`) |

Swap `rho_1` and `rho_3` and none of the three composites lines up. That swapped table is
available as `REEB_CONVENTIONS.dictated`, since it is how the rule was first written down;
`composed` is the default and is the one that reproduces `reference_Q222.csv`.

**The power of U** is how often the domain covers the basepoint `w`, shut inside the
innermost rainbow. On the torus that is a multiplicity; in the universal cover, where the
solver works, it is just the number of lifts of `w` the region encloses. `z` is the
basepoint that may never be covered, and the solver already refuses any path that covers it.

**CSV.** `toCSV(discs, { format })` writes either layout:

    'full'       source,target,U,chords,offset,path     everything, including how far along
                                                        beta the piece ran and the grid path
    'reference'  source,target,annotation,U,P           the reference tables' own layout, so
                                                        the two diff directly

`sort: true` orders rows by source, target, U, word, which makes two runs comparable line
for line. `node discs.js 2 2 2 --format=reference` writes it straight out.

### Q(i,2,2) against the closed-form tables

`src/conjectured.js` transcribes the predicted arrows — 14 special, a snail of `12i-7`, and
`52i-25` in families, so `64i-18` in all. `node test/compare-conjecture.js 4` compares them
against the computed discs, row for row, where a row is (source, target, U, chord word):

| i | discs | `64i-18` | rows matching | time |
|---|---|---|---|---|
| 1 | 46 | 46 | 46 / 46 | 0.0 s |
| 2 | 110 | 110 | 110 / 110 | 0.1 s |
| 3 | 174 | 174 | 174 / 174 | 0.2 s |
| 4 | 238 | 238 | 238 / 238 | 0.6 s |
| 5 | 302 | 302 | 302 / 302 | 1.1 s |
| 6 | 366 | 366 | 366 / 366 | 1.8 s |
| 7 | 430 | 430 | 430 / 430 | 2.9 s |
| 8 | 494 | 494 | 494 / 494 | 4.3 s |
| 9 | 558 | 558 | 558 / 558 | 6.1 s |
| 10 | 622 | 622 | 622 / 622 | 8.2 s |

3340 arrows over the ten cases, every one of them agreeing. Nothing is normalised away in
the comparison: the two lists have to match as multisets, row for row, including the U power
and the order of the chords.

### The older CSV

`reference_Q222.csv` in `dependent-region-shur` agrees on 107 of 110 rows. The three it
differs on are single-step discs out of the snail's `0 <= k <= i-2` families, where it has
`x_10 -> x_11`, `x_9 -> x_12`, `y_8 -> y_9` and both the computation and the closed-form
tables have them the other way round. It is superseded; `node test/compare-reference.js` is
kept only so the difference stays visible.

### How long it takes

Everything is governed by one number, the length of beta's circuit, which is also the number
of generators:

    C  =  (maxx + 1) + (maxy + 1)  =  2m(2i-1)(n+1) + 2m + 2n - 1  ~  4imn

The enumeration tries every piece of beta from each generator, both ways, out to a full
circuit: `2C^2` pieces, each costing more as it gets longer. Measured over 300 diagrams:

    T  ~  2.2e-7 * C^2.68

| diagram | generators | discs | time |
|---|---|---|---|
| Q(1,2,2) | 19 | 46 | 0.01 s |
| Q(2,2,2) | 43 | 110 | 0.02 s |
| Q(2,3,5) | 123 | 502 | 0.14 s |
| Q(2,5,5) | 199 | 830 | 0.43 s |
| Q(3,5,5) | 319 | 1,320 | 1.1 s |
| Q(2,10,10) | 699 | 4,710 | 9.3 s |
| Q(3,10,9) | 1,037 | 6,401 | 26.1 s |
| Q(10,10,10) | 4,219 | 27,750 | 20.4 min |

About 1.8 ms per disc at the sizes above — but that figure is not stable, because finding a
disc is not what costs. Ruling out the pieces that are *not* discs is: only a few percent of
the `2C^2` pieces bound one, so time grows like `C^2.68` while the disc count grows roughly
like `C`, and cost per disc grows like `C^1.7` — 180 microseconds at `Q(2,2,2)`, 44 ms at
`Q(10,10,10)`.

**A warning about extrapolating this.** Fitted on diagrams up to `C = 475` the exponent comes
out at 2.27; out at `C = 4219` it is really 2.68. Predicting `Q(10,10,10)` from the small end
gave 8.5 minutes against an actual 20.4. The residual per-piece work grows with `C`, so the
exponent drifts upward and a fit from below always runs low.

Four changes account for the constant, in the order they mattered:

1. **The self-intersection test**, the only quadratic step inside a single solve — 10.8 ms of
   an 11.9 ms solve on a thousand-point piece. Beta's lift is embedded by construction, so it
   is skipped (`assumeSimple`). About 8x.
2. **Sampling.** An arc is a primitive, not a polyline; the enumeration samples parabolas at 4
   rather than 48, with the disc lists identical at every sampling from 48 down to 2. About 4x.
3. **Validating beta once.** Every check in §2 is a property of the curve, not of the piece,
   so the lifted track is checked once and the `2C^2` solves pass `assumeValid`. About 3x.
4. **Extending rather than rebuilding** the arc description, plus indexing crossings by edge
   and deferring the shielding context. About 8x, and it took the exponent from 3 to 2.68.

End to end that is roughly 140x: `Q(10,10,10)` began at an estimated 47 hours.

### Q(i,2,2) against the closed-form tables

`src/conjectured.js` transcribes the predicted arrows — 14 special, a snail of `12i-7`, and
`52i-25` in families, so `64i-18` in all. `node test/compare-conjecture.js 4` compares them
against the computed discs, row for row, where a row is (source, target, U, chord word):

| i | discs | `64i-18` | rows matching | time |
|---|---|---|---|---|
| 1 | 46 | 46 | 46 / 46 | 0.0 s |
| 2 | 110 | 110 | 110 / 110 | 0.1 s |
| 3 | 174 | 174 | 174 / 174 | 0.2 s |
| 4 | 238 | 238 | 238 / 238 | 0.6 s |
| 5 | 302 | 302 | 302 / 302 | 1.1 s |
| 6 | 366 | 366 | 366 / 366 | 1.8 s |
| 7 | 430 | 430 | 430 / 430 | 2.9 s |
| 8 | 494 | 494 | 494 / 494 | 4.3 s |
| 9 | 558 | 558 | 558 / 558 | 6.1 s |
| 10 | 622 | 622 | 622 / 622 | 8.2 s |

3340 arrows over the ten cases, every one of them agreeing. Nothing is normalised away in
the comparison: the two lists have to match as multisets, row for row, including the U power
and the order of the chords.

### The older CSV

`reference_Q222.csv` in `dependent-region-shur` agrees on 107 of 110 rows. The three it
differs on are single-step discs out of the snail's `0 <= k <= i-2` families, where it has
`x_10 -> x_11`, `x_9 -> x_12`, `y_8 -> y_9` and both the computation and the closed-form
tables have them the other way round. It is superseded; `node test/compare-reference.js` is
kept only so the difference stays visible.

### How long it takes

Everything is governed by one number, the length of beta's circuit, which is also the number
of generators:

    C  =  (maxx + 1) + (maxy + 1)  =  2m(2i-1)(n+1) + 2m + 2n - 1  ~  4imn

The enumeration runs from each of the `C` generators, both ways, out to a full circuit, so it
solves `2C^2` pieces of beta; and a piece of length `L` costs time proportional to `L`, with
an average of `C/2`. So

    T  ~  k C^3  ~  k (4imn)^3        k ~ 0.7 microseconds

which is **cubic in each of i, m and n separately**. Measured against that fit: `Q(2,2,2)`
C=43 in 0.08 s, `Q(2,3,5)` C=123 in 1.3 s, `Q(10,2,2)` C=235 in 8.2 s, and `Q(10,10,10)`
C=4219 extrapolates to about 15 hours.

`n` is the cheapest of the three to raise and `i` the dearest, but only by the constant: all
three are cubes. Doubling any one multiplies the work by roughly eight.

Four things brought `k` down, in the order they mattered:

1. **The self-intersection test.** It is the only quadratic step inside a single solve, and on
   a thousand-point piece it was the whole cost: 10.8 ms of 11.9 ms. Beta's lift is embedded
   by construction, so it is skipped. Worth about 8x.
2. **Sampling.** With that gone, `validateArc` dominates, and it is linear in the number of
   points — so the 48-segment sampling of every parabola was most of what remained. An arc is
   a primitive, not a polyline; `enumerateDiscs` samples it at 4. Worth another 4x, with the
   disc lists identical at every sampling from 48 down to 2.
3. **Validating beta once.** Every check in §2 is a property of the curve rather than of the
   piece being solved, so the whole lifted track is checked once and the `2C^2` solves that
   follow pass `assumeValid`. Worth another 3x, and it was three quarters of what was left.
4. **The walk.** `strategy: 'walk'` is the default everywhere.

| | `Q(10,2,2)` | `Q(10,10,10)` (extrapolated) |
|---|---|---|
| before | 131.8 s | 47 hours |
| after | 8.2 s | 15 hours |

What would move it again is not a constant but the exponent: the piece at offset `d+1` is the
piece at offset `d` plus one arc, yet every solve rebuilds its crossings and cells from
scratch. Maintaining those incrementally as the piece grows would make the inner loop O(1)
amortised and the whole enumeration `O(C^2)` rather than `O(C^3)`. Not done.

## The atlas

`node atlas.js 2 2 2` draws a readable sample of the discs, and writes a PNG beside the SVG when
Inkscape is installed (`--no-png` to skip, `--dpi=110` to change the size, `--max-px=40` for
the raster cap, `0` to lift it). The cap matters: the canvas grows with both the number of
discs and the size of a domain, so `Q(4,7,3)` declares 157272 x 153302 user units, and asking
for that at 110 dpi is a 31 gigapixel image — which does not fail, it simply never finishes.
The dpi is lowered as far as needed and the reduction is reported. If the picture comes out
too coarse, shrink the vector instead with a smaller `--cell`. PNG rather than
JPEG on purpose: these are line drawings, and on these very files JPEG at quality 92 came out
two to three times *larger* than PNG as well as lossier, because a DCT codec spends its bits
on ringing around every grid line. Nothing else in the package shells out, and nothing
depends on it working — without Inkscape you still get the SVG and a line saying why there is
no PNG. A disc translated by a lattice vector is
another lift of the same disc, so the picture stays honest whichever copy each one is drawn
in — which is what makes a catalogue possible. Left where the enumeration found them they sit
on top of one another, so by default each is slid into its own slot by a whole number of
copies (shelf packing, tallest first, the number of columns chosen so the result comes out
roughly square given how wide a copy is). `--arrange=insitu` leaves them where they were
found instead.

**What gets drawn.** By default a sample, not everything: the largest disc of every distinct
(chord word, U power) class first — that is the whole variety of the diagram, one specimen
each — then the largest ones left over, up to `--sample=80`. `--all` draws every disc, which
for a large diagram is a canvas nobody can read. `--per-class=2` takes two specimens of each
class instead of one.

On `Q(2,3,5)`, which has 502 discs in 59 classes: a sample of 20 covers 20 classes, 40 covers
40, and 80 covers all 59 while still leaving room for the biggest. Below 80 you lose classes
before you lose size, which is the intended trade.

The colours mean nothing. They cycle in placement order so that neighbouring slots differ,
with a repair pass for any two that end up the same colour and close enough to read as one
shape. Hovering a disc gives its source, target, U power and chord word.

Beta is written into the file once and `<use>`d for every copy, which is the difference
between an 82 KB file and a 1.7 MB one.

## The disc finder

`node serve.js`, then <http://localhost:8300/heegaard-js/>.

Click the start, then click the end. Both snap to the nearest generator, and the blue curve
is the piece of beta between them; the second click solves and draws the red path and the
shaded region `D`. A third click starts a new pair, clicking the start again cancels it, and
escape clears. The arrow keys move the far end one arc along beta, shift for five, so a pair
can be nudged without re-clicking. When there is no disc the panel says why, and any
basepoint that `D` swallowed is ringed in the picture.

Neither click is restricted in range: beta folds back on itself in the cover, so the nearest
generator to a click can be sixty arcs away along the curve, and if that is where you
clicked then that is what you meant.

**Scan** solves every piece within `scan range` of the current start and lists the ones that
bound a disc, each clickable. That is the disc count for that generator, and it is what the
whole thing is for.

## What is next

**The solver should work on any H(r,s), not only the ones that come from Q(i,m,n).**
Everything below `Q()` is already general — `HeegaardDiagram` takes an arbitrary arc list,
`validate` checks it, and `layout`, `liftBeta` and `enumerateDiscs` never ask where a diagram
came from. What is missing is the way in: a constructor for a general H(r,s), and a check
that the straight-segment drawing rule still gives an embedded picture outside the Q family
(`findArcCrossings` will say so rather than draw it wrong). Not started.

## Open questions

- Only one basepoint is drawn. If there is a second (a `w` to the `z`), say where and it
  can go in; nothing computes with it yet either way.
- The solver treats each piece of beta independently. Nothing yet tracks which discs share a
  source generator, or assembles them into the algebra that `conjecture.py` writes down.
