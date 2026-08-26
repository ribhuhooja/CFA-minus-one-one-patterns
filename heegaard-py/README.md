# heegaard-py

Bordered Heegaard diagrams and the discs they bound, in Python. The same algorithm and the
same answers as `heegaard-js`, reading and writing the same two CSV formats.

No dependencies. Python 3.9+.

```bash
python3 -m heegaard generate 2 2 2 -o Q222.csv     # a Q(i,m,n) diagram
python3 -m heegaard pattern                        # what else can be built
python3 -m heegaard pattern twin-rainbow -o t.csv  # ... build one by name
python3 -m heegaard solve Q222.csv -o discs.csv    # its discs
cat Q222.csv | python3 -m heegaard solve           # or as a filter
python3 -m heegaard draw Q222.csv                  # svg: domain, cover, discs
python3 -m unittest discover -s tests
```

## Building a diagram

```python
from heegaard import Diagram

d = Diagram("my diagram")
d.add_arc(0, "left", 0, "top")          # generator, edge, generator, edge
d.add_arc(0, "bottom", 5, "top")
...
d.set_basepoint("w", inside_arc=27)
d.validate()                            # raises unless it is legal
```

An endpoint names the **edge** it sits on, not just the alpha curve: bottom and top are the
same curve but different sides of the domain, and an arc has to say which one it meets. That
is the whole content of a diagram — where the arcs are *drawn* is a rendering decision made
later, and nothing in the solver depends on it.

`validate()` checks four things, in the order worth hearing them:

| | |
|---|---|
| **slots** | every boundary slot used exactly once — beta passes through each generator once, so it occupies each of the two germs there once |
| **embedding** | the chord diagram of arcs is non-crossing, which is what says beta is embedded |
| **connectedness** | beta is a single closed curve |
| **homology** | beta meets `(alpha_y, alpha_x)` with multiplicity `(±1, 0)` |

`problems()` returns the same list instead of raising, and `require_connected` /
`require_primitive` turn the last two off for diagrams that are meant to be otherwise.

## Q(i, m, n)

`heegaard.qmn` builds the family, as an example of using the base and as the thing the solver
is checked against. `Q(2,2,2)` writes a CSV byte-identical to the one `heegaard-js` writes.

## The catalogue

`heegaard.patterns` is where a diagram someone drew on paper gets written down once, checked,
and given a name — so it can be built, exported and solved without being re-entered by hand.
Q(i,m,n) is one entry (`qimn`); it is not privileged.

```python
from heegaard import build, catalogue, names

print(catalogue())                      # every pattern and what it wants
d = build("twin-rainbow")               # a diagram, already validated
d = build("qimn", 2, 2, 2)
```

| | |
|---|---|
| `qimn <i> <m> <n>` | the Q(i,m,n) family |
| `twin-rainbow` | 8 x and 5 y generators, two nested rainbows; hand-drawn, **outside** the Q family |

To add one: write a builder that ends in `.validate()` and sets the `w` basepoint, then put a
`Pattern` for it in `PATTERNS`. Nothing else in the package has to change — the tests walk the
catalogue, so a new entry is checked for legality and embedding the moment it is registered.

A builder must set `w`. A diagram with nowhere to put it has no U powers and the solver
refuses it — the trivial one-arc diagram `left:0 — right:0` is perfectly legal and cannot be
solved for exactly this reason.

## Drawing it

`python3 -m heegaard draw` writes three SVGs — one copy of the domain, the universal cover,
and every disc at once — and **it takes nothing but the CSV**:

```bash
python3 -m heegaard draw Q222.csv                    # out/Q222{,-cover,-discs}.svg
python3 -m heegaard draw Q222.csv --discs=discs.csv  # reuse a solved disc table
cat Q222.csv | python3 -m heegaard draw --only=cover # or as a filter
```

`--cell` sets pixels per copy of the domain, `--tiles` the size of the cover, `--limit` how
many discs to draw (`0` for all), `--arrange=insitu` leaves discs where the enumeration found
them instead of packing them into free slots, `--no-labels` drops the per-disc text.

`heegaard.render` is the library behind it: `render_diagram`, `render_cover`, `render_discs`.
No dependency, no rasteriser — SVG is text, and a browser or Inkscape can turn it into a PNG.

Two things make this more than decoration:

**The picture is the embedding the answer was computed in.** Arcs are routed by
`layout.route`, the same routing the solver uses to settle its winding numbers, and z and w
are drawn where `solver._basepoints` actually puts them. A disc drawn here is the polygon that
was tested, not an illustration of it.

**A disc can be drawn from a disc CSV alone.** `discs_from_csv` reads the table back, and
`solver.attach_regions` rebuilds each disc's polygon exactly from its source, its offset and
its path — that is all the geometry there ever was. So a disc list computed by `heegaard-js`
draws here without solving anything again, and the picture is byte-identical to the one drawn
from Python's own solver. Disc order does not affect the picture either: the discs are put
into canonical order before packing.

## The solver

`enumerate_discs(diagram)` returns every disc: source, target, Reeb chords, power of U, and
how far along beta it ran. `enumerate_discs(diagram, keep_regions=True)` also keeps the
polygon each one covers in the universal cover, which is what the drawing wants and what the
CSV throws away.

Nearly all of it is combinatorial. Beta meets the alpha curves exactly at the generators, so a
piece of `k` arcs has `k+1` crossings and they are the lifted curve's nodes; which alpha edge
each lies on follows from the generator's side and index; and one copy of the domain **is**
one cell of the grid, so every arc lies in exactly one cell — its tile. The first and last
steps of the path follow from which edge the end generators sit on.

The one thing that is not combinatorial is deciding whether a finished path encloses a
basepoint. That is a winding number and it needs an embedding — but *any* embedding will do,
because two embeddings of the same combinatorics are isotopic and give the same discs. So
`layout.route` supplies one for an arbitrary valid diagram, **without assuming arcs are
straight or that the diagram comes from a family we know**.

Each arc is **one piece of geometry** — a straight segment or a single quadratic curve —
and the SVG carries it as one path command, with nothing sampled off it. An arc bulges away
from the stretch of boundary it spans, so a rainbow arches off its own edge and an arc between
two edges arches away from the corner between them; an arc joining *opposite* edges has a
whole side behind it and comes out as the straight strand across the domain that it is.

How far it bulges is the one free number, and it is **measured against the arc containing
it**, not taken from a table. Each arc casts a ray along the way it wants to bulge, finds its
parent, and takes a `h/(h+1)` share of the gap, where `h` counts the nesting levels still to
fit inside it — so a stack of nested arcs is spaced evenly rather than halving at every level,
and the rainbows around `w` stay legible.

Two simpler rules were tried and both fail, for the same reason. A shape fixed by its
endpoints — the semicircle standing on its two generators, the ellipse centred on their shared
corner — has nothing left to push it clear of what it holds, and in `twin-rainbow` the rainbow
goes straight through the flattened `y_4 → x_4` arc above it. Ranking the bulge by nesting
height fails too, because a straight strand does not bulge at all: an arc nested inside one
ranks below it and still swings out past it. Measuring against the parent is what expresses
that constraint — a straight parent hands its children its own chord to stay behind.

That is a construction, not a proof, so **the strokes are checked, not assumed**. If any two
meet, the whole diagram falls back to `route_radial` — straight chords in a disc carried back
to the square, provably embedded for any valid diagram and much worse to look at.
`layout.stroked(diagram)` says which you got. Of `Q(i,m,n)` for `i,m` up to 4 and `n` up to 5,
**47 of 64 draw as strokes**, `twin-rainbow` among them; what still falls back is the large
`i` and `m` corner of the family.

Either way the discs are the same, and a test pins that: any embedding of the same
combinatorics gives the same answers, so the two routings are a check on the solver.

## Against the JS

Disc lists agree exactly on every diagram tried — same discs, same U powers, same chord words,
and `solve` writes a byte-identical CSV from the same input. About 9x slower than JS, rather
than the 26-45x that the float-heavy general grid solver would have cost, because the inner
loop no longer contains geometry.

| | js | python |
|---|---|---|
| Q(2,2,2) | 0.03 s | 0.09 s |
| Q(2,3,5) | 0.09 s | 0.85 s |
| Q(3,3,3) | 0.12 s | 0.65 s |
