# grid-arc

Draw a simple arc on the unit grid; find the grid path joining its two endpoints whose
enclosed region contains no forbidden point — or prove there is none.

Implements `grid-arc-solver-prompt.md` (normative), with `alphas-prompt.txt` consulted for
ambiguities. No dependencies, no build step, Node 18+ (developed on 26.7).

```bash
npm run serve      # the visualizer, http://localhost:8123/
npm test           # examples + JSON round-trip + fuzz          (node test/test.js [N] [seed])
npm run stress     # the uniqueness study, checks U1-U10        (node test/stress.js [N] [seed])
npm run local      # are the local rules enough on their own?   (node test/localrules.js [N] [seed])
```

## Using it from another project

Everything under `src/` is a pure ES module: no DOM, no globals, no I/O, mathematical
coordinates throughout (`y` increases upward — any flip belongs to a rendering layer).

```js
import { solve } from './grid-arc/src/index.js';

const result = solve([[5.4, 5], [5.6, 5.5], [5.4, 6]], { strategy: 'walk' });
result.status;                       // 'solved' | 'no-solution' | 'invalid'
result.solutions[0].directions;      // ['E', 'N', 'W']
result.solutions[0].points;          // x_s, lattice points…, x_e
result.solutions[0].region.polygon;  // the Jordan curve bounding D
result.solutions[0].region.area;     // signed; negative means correctly oriented
result.arc.cells;                    // the cells the arc passes through
result.arc.crossings;                // arc ∩ grid, each tagged with edge and parameter
```

`solve` options, all optional:

| option | default | meaning |
|---|---|---|
| `strategy` | `'walk'` | `'walk'` the deterministic local walk; `'search'` exhaustive DFS; `'verify'` both, compared in `result.agreement` |
| `useRules` | `false` | apply the Appendix A rules while searching |
| `strictRule` | `false` | add the extra rule from the original prompt |
| `decisions` | `false` | record the per-lattice-point decision log |
| `trace` | `false` | record the DFS trace, for stepping through the search |
| `maxSolutions` | `1000` | cap |
| `searchSpace` | `'cells'` | `'bbox'` widens the candidate edges, to test the §6 lemma |
| `grid` | defaults | override the grid constants — window size, `epsForbidden`, `minLatticeDistance` |
| `assumeSimple` | `false` | skip the (2.1) self-intersection test — see below |
| `assumeValid` | `false` | skip §2 entirely — only for a sub-arc of an already-checked curve |

`assumeSimple` exists because that test is the only quadratic step in the pipeline, and on a
long arc it is the whole cost: 10.8 ms of an 11.9 ms solve on a thousand-point arc. Pass it
only when the arc is embedded by construction and you can say why — the lift of an embedded
curve to a covering space, for instance, which is what `heegaard` feeds in. A hand-drawn
stroke is not such a case. Every other check still runs.

`assumeValid` goes further and skips §2 altogether. Every check in §2 is a property of the
**curve**, not of the piece of it being solved — clearance from the lattice points,
transversality, staying in the window, crossing rather than touching at a vertex. So a caller
that validates one long curve may then solve any number of sub-arcs of it for free. The one
condition that is *not* inherited is (2.2), that both ends of the sub-arc lie in the interior
of a grid edge; a caller passing `assumeValid` has to have established that separately.
That is what makes it worth having: solving every sub-arc of a curve is exactly what disc
counting does, and re-validating the same curve 35 million times is most of the cost.

The `grid` option exists because not every arc is drawn by hand. A beta curve lifted from a
Heegaard diagram lives at a different scale and passes far closer to the lattice points than
a mouse stroke ever does, so it needs its own tolerances. `gridSettings` enforces the one
rule that must hold whatever the numbers: `epsForbidden * sqrt(2) < minLatticeDistance`, i.e.
the arc never comes closer to a lattice point than that point's own forbidden point does.
See `../heegaard/src/bridge.js` for a caller that measures both off its diagram.

Instrumentation is off by default, so a batch run allocates nothing it does not need:
`solve` costs about 20 µs per arc under the default `'walk'`, 45 µs under `'search'`.

### Modules

| module | what it owns |
|---|---|
| `src/geometry.js` | vectors, segment intersection, polyline simplicity, signed area, winding number, RDP. No grid knowledge. |
| `src/grid.js` | lattice points, edge keys, cells, sides, forbidden points, compass directions. |
| `src/arc.js` | §2 validation, `arc ∩ grid`, the cell decomposition. `describeArc` returns everything derivable from the arc alone. |
| `src/endpoints.js` | §3/§5: what the arc's orientation forces at `x_s` and `x_e`. |
| `src/rules.js` | Appendix A, as a table plus shielding predicates. Never load-bearing. |
| `src/constraints.js` | (P1)–(P4), each exported separately. |
| `src/search.js` | `enumeratePaths` (DFS) and `walkPath` (the local walk). Neither decides anything. |
| `src/solve.js` | the orchestrator. |
| `src/incremental.js` | `ArcDescriptionBuilder`: the same description, built by extending rather than from scratch. |
| `src/index.js` | the public surface. |
| `src/random.js` | random valid arcs, for fuzzing. |
| `src/examples.js` | the built-in curves. |

Nothing imports upward: `geometry` and `grid` know nothing of arcs, `arc` knows nothing of
paths, `rules` and `constraints` know nothing of the search, and only `solve.js` knows all of them.

## Conventions

Cells `C(i,j) = [i,i+1] × [j,j+1]` in a 20×20 window; the arc must live in cells 2..17 and
stay ≥ 0.08 from every lattice point. The forbidden point of `C(i,j)` is `(i+1e-3, j+1−1e-3)`,
just inside its **NW** corner. Edge keys are `H:i:j` for `(i,j)–(i+1,j)` and `V:i:j` for
`(i,j)–(i,j+1)`. Directions are absolute compass directions; the words left/right/up/down
never appear relative to a direction of travel.

Two deliberate deviations from the letter of the spec:

- **The solver is a directory of modules, not one `index.html`.** Page and Node import the
  same source. Still no build step and no dependencies — but the page needs the server,
  since ES modules do not load over `file://`.
- **An interior vertex of the arc may lie on a grid line**, provided the arc genuinely
  crosses there; a tangential touch is rejected. Banning it outright, as a first reading of
  §2.4 suggests, throws out most piecewise-linear curves.

## The algorithm

1. **Describe the arc** (`describeArc`). Validate against §2 — every failure is reported with
   its offending point, nothing is repaired. Then compute `X = arc ∩ grid`: walk each segment,
   intersect it with the integer lines it spans, half-open in the segment parameter so a
   vertex sitting on a grid line is counted exactly once. Every edge carrying a crossing is
   **blocked**. Consecutive crossings bound exactly one sub-arc, whose cell is found from its
   midpoint; that gives `C`, the cells the arc passes through, and for each a record of which
   sides it entered and left by.

2. **Fix both ends** (`endpointConditions`). By §3 the enclosed region `D` lies on the
   `rotateCW(velocity)` side of the arc, so the closed curve runs clockwise. That determines
   the first and last steps of the path from edge orientation plus which side the arc occupies,
   and hence the two lattice points `v_s` and `v_e`. The partial edges `x_s→v_s` and `v_e→x_e`
   are checked for crossings strictly inside them; the crossing at `x_s` or `x_e` sits at the
   boundary and does not block.

3. **Bound the search space** by §6. If the arc misses the interior of a cell `S`, then
   `∂D ∩ int(S) ⊆ P ∩ int(S) = ∅` because `P` lies on grid lines, so `int(S)` is wholly inside
   or wholly outside `D`; inside would put `f_S` in `D`. Hence `D ⊆ closure(⋃C)`, and since
   `P ⊆ ∂D`, every edge of `P` is an edge of a cell of `C`. That is a few dozen edges, minus
   the blocked ones.

4. **Produce candidates.** Two shapes need no search and are constructed directly: `x_s` and
   `x_e` on the same edge with no lattice point between them, and `v_s = v_e`. Otherwise DFS
   over states `(lattice point, incoming direction)` for all simple paths `v_s → v_e`, or the
   local walk (below).

5. **Check each candidate globally** (`checkPath`). (P1) simple, no repeated lattice point.
   (P2) no crossing of `X` lies on the path. (P4) the closed curve `arc ⧺ reverse(path)` is
   simple whenever (P1) and (P2) hold, so its orientation is decided exactly by the sign of
   its signed area — negative, no sampling needed. (P3) winding number 0 for every forbidden
   point in the bounding box, expanded by 1.

The Appendix A rules are never load-bearing: they sit behind `useRules`, default off, and
both harnesses assert that the answer is identical with them on and off.

## Would "use the rules to find the only possible path, then check" work?

Yes — that is `strategy: 'walk'`, **the default**. `walkPath` takes the single open step at
each lattice point and stops at `v_e`; `solve` then runs `checkPath` once. Linear in the
length of the path, no backtracking, and it agrees with the exhaustive search on every arc
tested (check U10).

`'search'` is still there and is what the walk is checked against; it is also the only
strategy that fills in `result.trace`, so stepping through the search in the viewer needs it.

What makes it correct is not that the local rules are complete — they are not — but the
division of labour. From `node test/localrules.js 8000`:

| | | |
|---|---|---|
| A | walk produces nothing, and no solution exists | 5816 — right |
| B | walk produces a path and it is the solution | 1766 — right |
| C | walk produces a path that fails the global check | **418 — the rules alone would be wrong** |
| D | walk produces nothing although a solution exists | **0** |

`D = 0` on every run, and the walk never has more than one open step (U6). So the local rules
are a perfect *navigator*: when a solution exists they find it, and they find only it. What
they cannot do is *reject* — in 418 of 8000 arcs the walk marches happily to `v_e` and returns
a path that then fails the global check (410 on (P3), the rest on (P1)/(P4)/(P2) in the
degenerate shapes). Keeping the global check as the final arbiter costs one winding-number
sweep and removes that entire failure mode.

Where the 418 sit, from the same run:

- **None at an interior lattice point.** Where the table and its shielding conditions actually
  apply, they were exactly right on every arc tested.
- **317 are the `v_s = v_e` shape and 22 the same-edge sub-segment** — paths with one lattice
  point or none, where the walk makes no decision and Appendix A says nothing. 277 of these
  enclose the forbidden point immediately SE of `v_s`. These look fixable by two more endpoint
  rules of the same flavour.
- **79 are genuine multi-step walks**, and in every one of them the missed forbidden point is
  *not* at a lattice point the path visits: 62 sit exactly one cell from the path, the other 16
  from 1.1 to 2.2 cells away, with no bound in sight.

That last group is the real obstruction. The arc's own wandering can encircle a cell the path
never approaches, and no rule keyed on a lattice point of the path sees it, however wide its
window. **The local rules determine which path; only (P3) determines whether.**

One scope note worth keeping in mind, since it bit the first implementation: the Appendix A
table governs steps *between lattice points*. It does not govern the first partial edge
(`x_s → v_s`) or the final one (`v_e → x_e`) — both are fixed by §5 instead, and either may
legitimately run `S` or `W`. A first partial edge of `S` or `W` occurs in 1447 of 3342 solutions.

## Solving every sub-arc of one curve

Asking for the description of prefix after prefix of the same polyline — which is what disc
counting does — costs `O(length)` each time, so `O(C^2)` for the `C` prefixes of a curve of
`C` arcs, and each answer is the previous one plus a little. Everything `describeArc`
computes is monotone under appending points: a crossing keeps its `segment` and `at`, because
new points go on the *end*; the cells, blocked edges and candidate edges only grow.

`ArcDescriptionBuilder` appends instead. The one thing not simply appended is the final
crossing: `findCrossings` records the last point explicitly as `kind: 'end'`, and extending
the arc turns that point into an ordinary crossing, which the half-open `[0,1)` rule then
picks up again as `t = 0` of the first new segment. So the builder keeps the interior
crossings and re-derives the end marker on demand.

Descriptions also carry `crossingsByEdge`. A long arc crosses the grid thousands of times but
over only a few dozen distinct edges, so "is anything on this edge, between here and there"
is a lookup rather than a scan — which matters because that question decides **82%** of all
solves: most pieces of a curve die on a blocked forced partial edge, before any search starts.
For the same reason the shielding context is built on demand rather than up front.

The builder is not cleverer than `describeArc`, just lazier. A test in `heegaard` checks the
two agree exactly — crossings, cells, sub-arcs, blocked and candidate edges — over every
prefix of four real curves in both directions.

## Findings from the stress test

`npm run stress` — 15 000 randomly generated valid arcs, all ten checks pass, on every seed tried:

| | | |
|---|---|---|
| U1 | at most one path satisfies (P1)–(P4) | **holds** — never 2 |
| U2 | rules-on solution set == rules-off | holds |
| U3 | ... and with the extra strict rule | holds |
| U4 | every returned path re-validates | holds |
| U5 | winding is −1 throughout `D` (adaptive dense sampling) | holds |
| U6 | the local walk is deterministic | holds — never more than one open step |
| U7 | `W`/`S` steps out of a lattice point only as the final partial edge | holds |
| U8 | the cell set `C` matches a dense resampling of the arc | holds |
| U9 | widening the search space finds no extra solutions | holds, where exhaustive enumeration is feasible |
| U10 | `'walk'` agrees with `'search'` | holds |

Two results beyond the answer above:

1. **Uniqueness does not come from the local rules.** At every decision on a solution path,
   the geometry alone — candidate cells, minus edges the arc crosses, minus revisits — already
   left exactly **one** option. The Appendix A rules removed a branch **0 times** in 6049
   decisions. They are consistent with the geometry everywhere tested, and redundant on
   solution paths.
2. **Branching happens, but never between two valid paths.** Of 41 524 arcs, 100 produced two
   candidates reaching `v_e`. In 97 of them both failed the global check; in the other 3 the
   survivor beat only the degenerate `x_s → v_s → x_e` candidate, which retraces an edge and so
   fails (P1). No arc has ever produced two genuinely valid paths.

About 78% of random arcs have no solution, essentially always because `D` swallows a forbidden
point. That is the constraint being tight, not a bug.

Counterexamples, if a check ever fails, are written to `counterexamples.json`, which the UI's
**load JSON** button reads directly.

## The visualizer

Click-drag to draw. The stroke is smoothed, then **extended along its own direction at each end
until it meets a grid line** — so `x_s` and `x_e` always land in the interior of an edge without
discarding anything you drew. The added tails are dashed, and the two end edges are highlighted.
If extending yields an invalid curve the stroke is trimmed back to its first and last crossings
instead. Then RDP at tolerance 0.03.

Scroll to zoom about the cursor, shift-drag or right-drag to pan, arrow keys to nudge; `fit`
frames the current curve, `all` shows the whole window. The path re-solves live while you drag.

Toggles for forbidden points, `arc ∩ grid`, candidate cells `C`, region shading, and the
Appendix A rules; a strategy selector for search / walk / verify. Buttons: clear, undo,
save/load JSON, cycle solutions, single-step the search, run self-tests (400 arcs in-browser).
Rejected candidates are listed with the rule they broke; **show** draws one in grey with its
offending forbidden point ringed.

Forbidden points are drawn pulled off their corner so they are visible; they really sit at
`(i+1e-3, j+1−1e-3)`.
