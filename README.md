# cfa-computation

Computing `gCFK^-(P(K))` — the associated graded knot Floer complex of a satellite — for a
(1,1) pattern `P` in the solid torus and an arbitrary companion `K` in `S^3`.

The bordered Floer pairing theorem does the work:

```
CFA^-(P, S^1 x D^2)   [x]   CFDhat(S^3 - nu(K))   =   gCFK^-(P(K))
```

so there are three jobs, and three independent pieces of code:

1. **write down the pattern** as a bordered Heegaard diagram,
2. **count the holomorphic discs** it bounds — each one is an operation of `CFA^-`,
3. **pair it with the companion**, whose `CFDhat` comes from `HFK^-(K)`.

Everything is over `F_2` and `F_2[U]`, so there are no signs.

## Counting the discs, as a puzzle about paths on a grid

A bordered Heegaard diagram on the torus is a rectangle with a curve drawn in it. Glue the
rectangle's opposite edges and you get the torus; tile the plane with copies instead and you
get a **red grid** — the alpha curves — with a **blue curve** running across it, which is beta.

A disc is then a piece of blue joined up by a path along the red grid, enclosing a region
that avoids a marked point in every square it touches. So finding discs means: given a
piece of the blue curve, find the red path that closes it up. That is a small, completely
concrete search problem, and it is what `grid-arc` solves.

Whenever a path exists it seems to be the only one — no test has ever turned up a second —
and simple local rules pick it out step by step with no searching. See `grid-arc-js/README.md`
for the evidence, which is more interesting than the code.

## The packages

| | |
|---|---|
| **`grid-arc-js/`** | the geometry, on its own. Given a simple arc on the unit grid, find the grid path joining its endpoints whose enclosed region contains no forbidden point, or prove there is none. Knows nothing about Heegaard diagrams. |
| **`heegaard-js/`** | jobs 1 and 2. Builds `Q(i,m,n)`, draws it, lifts beta to the universal cover, hands pieces of beta to the solver, reads off Reeb chords and `U` powers. |
| **`satellite_floer/`** | the Python package, `satellite-floer` on PyPI. Two halves that do not import each other: **`heegaard/`** is jobs 1 and 2 again, independently — plus `H(r,s)` for any `r, s`, and an SVG visualiser that draws from the CSV and nothing else; **`bordered/`** is job 3, the torus algebra, `CFA^-`, `CFDhat`, `CFK^-`, the box tensor. |

Two independent solvers agreeing on the same CSVs is a better correctness story than one.
Everything new is Python.

The packages share five CSV formats and nothing else — that is the whole coupling, and it is
specified in `docs/formats.md`. In particular the type-A structure a pattern carries is four columns
(source, target, `U` power, chord word), which are the first four columns of the disc table, so
the algebra reads a disc table directly and has still never heard of a Heegaard diagram.

## Doing things

```bash
pip install .                                 # or: python3 -m satellite_floer, from here
satellite-floer pattern hrs 3 1 -o P.csv      # a diagram: H(3,1) = Q(1,2,1)
satellite-floer solve P.csv -o discs.csv      # its discs
satellite-floer draw P.csv                    # svg: domain, universal cover, discs
satellite-floer knots                         # what companions are on the shelf
satellite-floer box discs.csv trefoil         # gCFK^- of the satellite
python3 -m unittest discover -s tests         # the Python tests
```

```python
from satellite_floer.heegaard import build, discs_to_cfa_csv
from satellite_floer.heegaard.solver import enumerate_discs
from satellite_floer.bordered import box, cfd, read_cfa

diagram   = build("hrs", 3, 1)                       # H(3,1) = Q(1,2,1)
pattern   = read_cfa(discs_to_cfa_csv(enumerate_discs(diagram), diagram))
satellite = box(pattern, cfd("trefoil"))

satellite.is_a_complex(), satellite.homology_rank_at_U1()      # (True, 1)
```

```bash
cd heegaard-js
node discs.js 2 2 2                 # count every disc, write out/Q222-discs.csv
node cli.js 2 2 2                   # draw the diagram and its universal cover, as SVG
node serve.js                       # then http://localhost:8300/heegaard-js/ to poke at it
npm test

cd ../grid-arc-js
npm run serve                       # http://localhost:8123/ — draw a curve, watch it solve
npm test && npm run stress          # the uniqueness study
```

## Where things are written down

- `CLAUDE.md` — the mission, the state of play, and the traps.
- `docs/formats.md` — the five CSV formats, which are the whole coupling between the parts.
- `docs/bordered.md` — the torus algebra, `CFDhat` from a knot complex, the box tensor.
- `docs/heegaard.md` — diagrams, `H(r,s)`, the solver, and how the pictures are routed.
- `heegaard-js/README.md` — the diagram conventions, the `Q(i,m,n)` arc families, the
  basepoints, how discs are counted, and the comparison against the arrow tables.
- `grid-arc-js/README.md` — the algorithm, and what the stress tests say about uniqueness.
- `grid-arc-js/alphas-prompt.txt`, `grid-arc-js/grid-arc-solver-prompt.md` — where the grid
  problem came from, in the words it was first posed in.

## Where it stands

For `Q(i,2,2)` the computed discs match the closed-form arrow tables exactly — every row,
including the `U` powers and the order of the Reeb chords, for i = 1 to 10. `Q(i,m,n)` is
`H(1 + 2im - m, n + 3m - 2mn + 4imn - 4im - 2)`, checked arc for arc.

The pairing runs end to end: diagram → discs → `CFA^-` → box with `CFDhat` → `gCFK^-`, and
every satellite complex so far has `d^2 = 0` and free homology of rank one, which is what a
knot complex must give.

Speed, for a sense of scale: `Q(2,3,5)` is 502 discs in 0.14 s, `Q(3,10,9)` is 6,401 discs in
26 s, `Q(10,10,10)` is 27,750 discs in 20 minutes (all in JS; Python is about 9x slower). See
`heegaard-js/README.md` for the scaling law and for why extrapolating it from small diagrams
runs low.

Not done: the x-snail, which is the last gap in the closed-form family table; `H(r,s)` on the
JS side; reducing a type-D structure and simplifying a `CFK^-` basis; and homology over
`F_2[U]` rather than only at `U = 1`.
