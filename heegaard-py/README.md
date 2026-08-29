# heegaard-py

Bordered Heegaard diagrams and the discs they bound, in Python. The same algorithm and the
same answers as `heegaard-js`, reading and writing the same two CSV formats.

No dependencies. Python 3.9+.

```bash
python3 -m heegaard generate 2 2 2 -o Q222.csv     # a Q(i,m,n) diagram
python3 -m heegaard pattern                        # what else can be built
python3 -m heegaard pattern twin-rainbow -o t.csv  # ... build one by name
python3 -m heegaard solve Q222.csv -o discs.csv    # its discs
python3 -m heegaard solve Q222.csv --format=cfa    # ... as a bordered-cfa CSV
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
| `hrs <r> <s>` | the general family H(r,s), of which Q(i,m,n) is one member |
| `twin-rainbow` | 8 x and 5 y generators, two nested rainbows; hand-drawn. It is **Q(1,2,1)** |

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

## H(r, s), the general family

`heegaard.chen` builds the general (1,1) diagram from two integers, `r != 0` and `s > 0`, with
beta a single closed curve exactly when `gcd(2|r|-1, s+1) = 1`. It is built in **Chen form** —
on the torus cut along the up-down curve `mu` only, so an annulus, where every arc runs between
the two boundary circles or turns back to the one it came from and nothing crosses the
left-right curve at all. Then the fundamental region is slid until `z` sits at a corner, which
cuts beta in `2|r|-1` new places; those are the new generators. A quarter turn puts `z` in the
top left corner and exchanges the two curves.

The number of dependent arcs is `|sigma(r,s)|` when `sigma < 0` and `sigma + 2` when it is not,
where `sigma` is the winding the main region picks up:

    sigma(r, s) = 1 - sum_{j=1}^{2r+s-1} (-1)^floor(j(2r-1)/(2r+s))

The positive case is the one that needs a small rainbow at each end to turn the curve about,
because a strand cannot simply be reversed. A test checks the closed form against walking the
main region and counting, on 200 pairs.

The re-cut is done with **real geometry**, not by counting. How many crossings there are can be
read off; the order they come in along the cut cannot, and that is what fixes the diagram. So
the annulus is drawn, the cut is a line across it, and the crossings are sorted by where they
fall.

**Q(i,m,n) is H(1+2im-m, n+3m-2mn+4imn-4im-2)** — checked arc for arc on all 36 diagrams with
`i` up to 4 and `m, n` in 2..4, and disc table for disc table on a sample. `twin-rainbow` is
**Q(1,2,1) = H(3,1)**; H has no `n >= 2` restriction, which is the only reason that was not
obvious. `python3 report.py` writes `out/general-diagrams.html`, which runs every check and
draws each stage.

## Handing it to the algebra

`--format=cfa` writes the same discs as a `bordered-cfa 1` file: the first four columns of the
disc table — source, target, power of `U`, chord word — and nothing else. `arcs` and `path` are
provenance, enough to rebuild each disc's polygon, and the algebra has no use for them.

The header declares which idempotent of `A(T^2)` each generator sits in: **`y` generators are
`iota_0` and `x` generators are `iota_1`**. That is forced rather than chosen. `rho_1` and
`rho_3` run `iota_0 -> iota_1` and `rho_2` runs back, so a disc's chord word only composes from
its source to its target under this assignment and not the other one — a test checks every
disc of every diagram it builds, and `bordered` infers the same splitting from the chords
without being told.

## 2-bridge names

A (1,1) pattern whose companion is the unknot is a 2-component 2-bridge link, and those have
two classical names: Schubert's `b(p, q)` and Conway's `C(a_1, ..., a_n)`. They are the same
number written twice —

    q/p = 1/(a_1 + 1/(a_2 + ...))     equivalently   p/q = [a_1; a_2, ..., a_n]

— so the `a_i` are the continued fraction of `p/q`. `heegaard.bridge` joins them to ours at
`p = 2s + 4|r|`, `q = sign(r)(2|r|-1)`:

```bash
python3 -m heegaard bridge --hrs 3 1        # H(3,1) = b(14,5) = C(2,1,4)
python3 -m heegaard bridge --schubert 14 5  # the same, from either of the others
python3 -m heegaard bridge --conway 2 1 4
```

It is **only a dictionary** — it narrows nothing. The solver, the visualiser and the algebra
take whatever diagram they are handed, and plenty of (1,1) patterns are not unknot patterns;
this is here so that one which *is* can be called by its usual name. A test asserts that
neither `diagram` nor `solver` so much as mentions it.

Two things fall out and are checked rather than assumed. `p` is always even, which is what says
the link has two components rather than one. And `b(p,q)` is a link at all only when
`gcd(p,q) = 1` — which turns out to be *exactly* the `gcd(2|r|-1, s+1) = 1` that `H(r,s)` needs
for beta to be a single curve, because `4|r| ≡ 2 (mod 2|r|-1)` makes `p ≡ 2(s+1)` and `q` is
odd. Also `H(-r,s)` comes out as `b(p, p-q)`, the mirror.

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

Each arc is **one piece of geometry** — a straight segment or a single cubic — and the SVG
carries it as one path command, with nothing sampled off it. Each has a shape it would take
given the room:

| | |
|---|---|
| two generators on one edge | the semicircle standing on them — a rainbow |
| two edges meeting at a corner | the quarter ellipse through both, centred on that corner |
| two opposite edges | a straight segment — there is a whole side behind it |

A **cubic**, not a quadratic, and that is the point rather than a detail. An arc has to leave
both its generators at a right angle to its edge *and* be shrinkable to fit inside whatever
contains it. With one control point those are the same number: pull it in to shrink the arc
and the ends stop being square-on. Two controls, one on each end's inward normal, hold the
angles exactly while the bulge slides freely.

The angles matter because of what the corner arcs are. If the bottom edge carries `r`
rainbows, then `r` arcs at the top left and `r` at the top right are not corner arcs at all:
they are the two halves of `r` **more** rainbows, hanging from the top edge and cut in two by
the seam where the left and right edges are identified — `y_j` on the left and `y_j` on the
right being one point of the torus. Meeting the seam at exactly a right angle is what lets the
halves join as one smooth rainbow in the universal cover. `render_cover` shows them.

How much of its shape an arc gets is **measured against what contains it**, outermost first,
by casting a ray along the way it bulges. A shape fixed only by its endpoints has nothing left
to clear what it holds; ranking by nesting height cannot express it either, since a straight
strand has no bulge for its children to rank below.

The share is `h/(h+1)` of the gap, `h` counting the levels still to fit inside, and it is
spent on the **apex**. A cubic peaks three-eighths of the way along its control offsets, so
spending the room on the controls quarters the space at every level instead of stepping down
evenly: the seven rainbows of `Q(2,2,2)` came out at 0.394, 0.169, 0.070, … , 0.0009 of the
domain, the innermost invisible.

Two things then correct that estimate:

- A corner arc takes a **soft** minimum of what it wants and what it has. Where a fan runs
  into something the region left for it is wedge-shaped, so it must be squeezed somewhere; a
  hard minimum squeezes nothing until it squeezes everything, and the fan of `Q(2,2,2)` used
  to sit at full size for seven arcs and then pile into a heap, its spacing dropping from
  0.063 to 0.044, 0.018, 0.014, 0.010, 0.006. Softened it tapers 0.057 → 0.011. A rainbow
  barely gives at all: its size is fixed by its own feet, so it cannot over-reach.
- Then the arc is **checked against everything already drawn** and gives up a bit at a time
  until it really is clear. The ray only asks what is straight ahead, and that is neither the
  only direction nor the only obstruction: a rainbow beside a strand rising steeply out of the
  edge next to it clears the strand at its apex and clips it with its flank — and the two are
  not nested, so no amount of care about parents would ever have compared them.

That is a construction, not a proof, so **the strokes are checked, not assumed**. If any two
meet, the whole diagram falls back to `route_radial` — straight chords in a disc carried back
to the square, provably embedded for any valid diagram and much worse to look at.
`layout.stroked(diagram)` says which you got. All 64 of `Q(i,m,n)` for `i,m` up to 4 and `n`
up to 5 currently draw as strokes, and so does `twin-rainbow`.

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
