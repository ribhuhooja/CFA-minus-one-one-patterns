# cfa-computation

Counting holomorphic discs in bordered Heegaard diagrams, by turning the question into a
puzzle about paths on a grid.

## The idea

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

## The two pieces

**`grid-arc-js/`** — the solver. Given a simple arc drawn on the unit grid, find the grid path
joining its endpoints whose enclosed region contains no forbidden point, or prove there is
none. It knows nothing about Heegaard diagrams; it is just geometry.

**`heegaard-js/`** — the diagrams. Builds `Q(i, m, n)` as `H(r, s)`, draws it, lifts beta to
the universal cover, hands pieces of beta to the solver, and reads off what each disc
carries: its Reeb chords and its power of `U`.

Both are plain ES modules with no dependencies, no build step and no DOM. The browser tools
are extra, not a layer anything goes through.

## Doing things

```bash
cd heegaard-js

node discs.js 2 2 2                 # count every disc, write out/Q222-discs.csv
node discs.js 2 2 2 --format=reference   # ... in the arrow-table layout instead

node cli.js 2 2 2                   # draw the diagram and its universal cover, as SVG
node serve.js                       # then http://localhost:8300/heegaard-js/ to poke at it

npm test                            # everything
node test/compare-conjecture.js 4   # computed discs vs the closed-form arrow tables
```

```bash
cd grid-arc-js

npm run serve                       # http://localhost:8123/ — draw a curve, watch it solve
npm test
npm run stress                      # the uniqueness study
```

## Where things are written down

- `grid-arc-js/README.md` — the algorithm, and what the stress tests say about uniqueness and
  about whether the local rules are enough on their own.
- `heegaard-js/README.md` — the diagram conventions, the `Q(i,m,n)` arc families, the
  basepoints, how discs are counted, and the comparison against the arrow tables.
- `grid-arc-js/alphas-prompt.txt`, `grid-arc-js/grid-arc-solver-prompt.md` — where the grid
  problem came from, in the words it was first posed in.

## Where it stands

For `Q(i,2,2)` the computed discs match the closed-form arrow tables exactly — every row,
including the U powers and the order of the Reeb chords, for i = 1 to 10.

Speed, for a sense of scale: `Q(2,3,5)` is 502 discs in 0.14 s, `Q(3,10,9)` is 6,401 discs in
26 s, `Q(10,10,10)` is 27,750 discs in 20 minutes. See `heegaard-js/README.md` for the scaling
law and for why extrapolating it from small diagrams runs low.

Two things not done:

- **Any H(r,s), not just Q(i,m,n).** Everything below `Q()` is already general; what is
  missing is a constructor for an arbitrary H(r,s). This is the main one.
- **Assembling discs into the algebra.** The disc lists are produced; nothing yet turns them
  into CFA^-.
