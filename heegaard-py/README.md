# heegaard-py

Bordered Heegaard diagrams and the discs they bound, in Python. The same algorithm and the
same answers as `heegaard-js`, reading and writing the same two CSV formats.

No dependencies. Python 3.9+.

```bash
python3 -m heegaard generate 2 2 2 -o Q222.csv     # a Q(i,m,n) diagram
python3 -m heegaard solve Q222.csv -o discs.csv    # its discs
cat Q222.csv | python3 -m heegaard solve           # or as a filter
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

## The solver

`enumerate_discs(diagram)` returns every disc: source, target, Reeb chords, power of U, and
how far along beta it ran.

Nearly all of it is combinatorial. Beta meets the alpha curves exactly at the generators, so a
piece of `k` arcs has `k+1` crossings and they are the lifted curve's nodes; which alpha edge
each lies on follows from the generator's side and index; and one copy of the domain **is**
one cell of the grid, so every arc lies in exactly one cell — its tile. The first and last
steps of the path follow from which edge the end generators sit on.

The one thing that is not combinatorial is deciding whether a finished path encloses a
basepoint. That is a winding number and it needs an embedding — but *any* embedding will do,
because two embeddings of the same combinatorics are isotopic and give the same discs. So
`layout.route` supplies one for an arbitrary valid diagram, **without assuming arcs are
straight or that the diagram comes from a family we know**: it draws the arcs as straight
chords in a disc, where two chords cross if and only if their endpoints interleave and a valid
diagram's never do, then carries the disc back to the square. The result is bowed and ugly and
provably embedded, which is all the solver wants.

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
