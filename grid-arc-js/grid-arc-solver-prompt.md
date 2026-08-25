# Task: interactive solver + visualizer for grid paths shielded by a drawn arc

Build a single self-contained `index.html` (vanilla JS + `<canvas>`, no build step, no external
dependencies) that lets me draw a curve on a square grid and computes a grid path satisfying the
constraints below, or reports that none exists.

Split the code into (a) a pure, dependency-free core `solve(blue, opts) -> Result` and (b) rendering.
The core must also be runnable headlessly under Node for the test harness in §8.

---

## 1. Conventions (follow these literally)

- **Coordinates are mathematical: `y` increases upward.** If you render to a canvas, flip at the
  drawing layer only. Never mix conventions inside the core.
- **All directions are absolute compass directions**: `N = (0,1)`, `E = (1,0)`, `S = (0,-1)`,
  `W = (-1,0)`. Do not use "left"/"right"/"up"/"down" relative to a direction of travel anywhere in
  the code or comments; the spec below never needs them.
- **Grid.** Lattice points `Z^2`. *Grid edges* are the closed unit segments between horizontally or
  vertically adjacent lattice points. *Cell* `C(i,j) = [i,i+1] x [j,j+1]`. Use a 20 x 20 window of
  cells, `0 <= i,j < 20`.
- **Forbidden points.** Each cell `C(i,j)` carries exactly one forbidden point
  `f(i,j) = (i + eps, j + 1 - eps)`, i.e. just inside its **NW (top-left)** corner. Semantically
  `eps` is infinitesimal; implement with `EPS_FORBIDDEN = 1e-3`.
- **Rotations.** Clockwise `R(a,b) = (b,-a)`; counter-clockwise `L(a,b) = (-b,a)`.

## 2. The drawn arc (`blue`)

`blue` is a polyline `x_s = b_0, b_1, ..., b_n = x_e`, produced by mouse drag and simplified with
Ramer–Douglas–Peucker (tolerance ~0.03 cells).

**Validate and reject with a specific message** — do not silently repair:

1. `blue` is simple (no self-intersections).
2. `x_s` and `x_e` lie in the *interior* of grid edges (never at a lattice point).
3. Every point of `blue` is at distance `>= 0.08` from every lattice point. *(This matters: the
   local rules in Appendix A are only valid in the limit `eps -> 0`, so `blue` must not come closer
   to a lattice point than the forbidden point does.)*
4. `blue` meets the grid transversally and in finitely many points: no segment of `blue` is
   collinear with a grid line, in particular the first and last segments are not collinear with the
   edges containing `x_s`, `x_e`.
5. `blue` stays strictly inside the window, in cells `2 <= i,j <= 17`.

Compute `X = blue ∩ grid`, the set of crossings, each tagged with the edge it crosses and its
parameter along that edge. Implement segment intersection explicitly with a stated tolerance;
reject degenerate/near-degenerate inputs rather than guessing.

## 3. Orientation (the single source of truth for endpoint behaviour)

Traverse `blue` from `x_s` to `x_e`. The *enclosed region* `D` is the side to which
`R(velocity)` points. Consequently, traversing the red path from `x_s` to `x_e`, `D` lies on the
side `L(velocity)`; equivalently the closed curve (`blue` forward, then red path reversed) is
oriented **clockwise**, so interior points have winding number `-1`.

## 4. Problem statement (normative)

Find a path `P` along the grid from `x_s` to `x_e`. Its interior vertices are lattice points; only
its first and last segments may be partial edges. `P` must satisfy:

- **(P1)** `P` is simple and visits no lattice point twice.
- **(P2)** `P ∩ blue = {x_s, x_e}`. Since both `P` and the crossings lie on grid edges, this is
  equivalent to: **`P` may not use any portion of an edge that `blue` crosses.** In particular a
  full edge crossed anywhere by `blue` is *blocked*; for the two partial end edges, only crossings
  lying in the used sub-segment block it.
- **(P3)** `blue ∪ P` is a Jordan curve; let `D` be its bounded complementary component. `D`
  contains no forbidden point.
- **(P4)** Orientation as in §3: every interior point of `D` has winding number `-1` about the
  closed curve. (Check this globally — do not merely trust the endpoint table below.)

Return **all** solutions (cap at 1000), not just the first.

## 5. Endpoint conditions (consequences of §3 — implement, then assert)

Note that a horizontal edge is the bottom edge of one cell and the top edge of another, so the only
meaningful data is *edge orientation* plus *which side `blue` occupies*. Phrase it that way:

Let `e_s` be the edge containing `x_s` and consider the first segment of `blue`.

| `e_s` | `blue` departs into the cell | first step of `P` from `x_s` |
|---|---|---|
| horizontal | above (`+y`) | `E` |
| horizontal | below (`-y`) | `W` |
| vertical | east (`+x`) | `S` |
| vertical | west (`-x`) | `N` |

Let `e_e` be the edge containing `x_e` and consider the last segment of `blue`.

| `e_e` | `blue` arrives from the cell | last step of `P` into `x_e` |
|---|---|---|
| horizontal | above | `E` |
| horizontal | below | `W` |
| vertical | east | `S` |
| vertical | west | `N` |

These fix a start lattice point `v_s` (the far end of the first partial edge) and an end lattice
point `v_e` (the lattice point from which the final partial edge is traversed). Two special cases,
both of which you must handle rather than skip:

- The required first partial edge or final partial edge is blocked per (P2) ⇒ report **no solution**
  immediately.
- `x_s` and `x_e` lie on the *same* edge and the sub-segment between them, traversed in the required
  direction, contains no crossing of `blue` and no lattice point ⇒ that sub-segment alone is a
  candidate `P` with no lattice points; validate it against (P1)–(P4) like any other. Note the
  other case on the same edge (required direction points away from `x_e`) is not special: the path
  goes out to `v_s` and back around, so it is handled by the general search.
- If `v_s = v_e`, the concatenation of the two partial edges is a candidate; still validate it.

## 6. Search space (use this — it makes brute force cheap and correct)

**Lemma.** Let `C` be the set of cells whose *interior* `blue` passes through. Then `D` is contained
in the closure of the union of `C`.

*Proof.* If `blue` misses the interior of a cell `S`, then `∂D ∩ int(S) ⊆ P ∩ int(S) = ∅`, since `P`
lies on grid lines. So `int(S)` is entirely inside or entirely outside `D`; inside would put `f_S`
in `D`, contradicting (P3). ∎

Hence every edge of `P` is an edge of a cell in `C`. Build the candidate edge set from `C` alone,
delete blocked edges, and search that graph — it has size `O(|C|)`, a few dozen edges for any curve
I will draw. Terminate by (P1): the graph is finite and paths are simple.

## 7. Algorithm requirements

- Enumerate simple paths from `v_s` to `v_e` (DFS over states `(lattice point, incoming direction)`)
  in the candidate graph, requiring the correct final direction, then run the **global** checks (P1)–(P4)
  on each completed candidate. Test (P3)/(P4) with a winding-number computation against every
  forbidden point of every cell in the bounding box of the closed curve, expanded by 1.
- **Do not make the local pruning rules of Appendix A load-bearing.** They are my conjectures and
  part of the point of this tool is to test them. Put them behind a flag `opts.prune`, default
  **off**, and have the harness assert that the solution set is identical with pruning on and off
  for every test input.
- Record a **decision log**: for each lattice point on a returned path, which of the (at most 3)
  outgoing edges were available in the unpruned graph, which survived, which rule of Appendix A
  would have eliminated each, and whether the move was forced.

## 8. Testing / instrumentation (please do not skip this section)

- Headless harness runnable as `node test.js`:
  - Fuzz with randomly generated valid polylines (random walk through cells, then RDP-simplified,
    rejected unless it passes §2).
  - Assertions per input: the number of valid paths is `<= 1`; pruned and unpruned solution sets
    agree; every returned `P` re-validates against (P1)–(P4); winding sign is `-1` throughout `D`.
  - Report any counterexample as JSON I can load in the UI.
- JSON save/load of a drawn curve, and ~6 built-in examples including: a same-edge start/end with no
  lattice point; a case whose final step is `W`; a case whose final step is `S`; a case with no
  solution.

## 9. UI

- Grid drawn in light red; the solution path overdrawn in dark red, thicker. Shade `D` at ~20% alpha.
- Draw `blue` by click-drag; show validation failures as text, and mark the offending point.
- Toggles: forbidden points, `blue ∩ grid` crossings, candidate cells `C`, region shading, pruning.
- Panel: status (`solved` / `no solution` / `invalid input`), number of solutions, the path as a
  direction string (e.g. `E N N E S`), and the decision log from §7. Buttons: clear, undo,
  save/load JSON, cycle solutions, single-step the search, run self-tests.
- If a candidate fails (P3), offer a debug view highlighting the offending forbidden point.

---

## Appendix A — conjectured local rules (NON-NORMATIVE)

These are my own guesses about what the constraints imply locally. **They are hints for pruning and
targets for verification only.** Correctness of the solver must not depend on any of them, and the
tool should be able to contradict them.

At a lattice point `v`, the forbidden point `f = v + (eps, -eps)` sits arbitrarily close to `v` in
its SE quadrant. Combined with (P3)–(P4) this appears to constrain the next step by incoming
direction alone:

| arriving at `v` moving | permitted next steps | count |
|---|---|---|
| `W` | none | 0 |
| `S` | `E` | 1 |
| `E` | `E`, `N` | 2 |
| `N` | `E`, `N`, `W` | 3 |

So `W`-moving and `S`-moving segments should only ever occur as the final partial edge into `x_e`.
Further conjectures about which of the multiple options is realisable, all of the form "`blue` must
shield the path from the forbidden point of the adjacent cell":

- Arriving `E`: the step `E` is available only if `blue` crosses the `N` edge at `v` (which
  simultaneously blocks the step `N`), so the choice looks forced either way.
- Arriving `N`: the step `E` likewise requires `blue` to cross the `N` edge at `v`. The step `N`
  requires `blue` to pass through the cell NW of `v` from its S side to its N side, or from its W
  side to its N side. The step `W` requires `blue` to cross the `W` edge at `v`.

If these hold, the walk is deterministic and the solution is unique when it exists. I would like the
tool to tell me empirically whether that is so.
