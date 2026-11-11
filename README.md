# satellite-floer

The purpose of this package is to assist with computing bordered Floer invariants of satellite knots with 
(1, 1)-patterns. A satellite
knot involves a *pattern* `P` and a *companion* `K`, 
where one takes the pattern (inside a solid torus) and ties it in the shape
of the companion. The bordered invariant associated to a pattern is `CFA^-(P, S^1 x D^2)` and the 
one associated to the companion is `CFDhat(S^3 - nu(K))` (i.e. technically it is associated to the knot complement).

From the pairing theorem, we can compute the knot Floer homology of the satellite using the *box tensor product*:

```
CFA^-(P, S^1 x D^2)   [x]   CFDhat(S^3 - nu(K))   =   gCFK^-(P(K))
```

This program was written to compute `CFA^-(P)` from a (genus 1) bordered Heegaard diagram. 
Auxiliary capabilities include computing bordered Heegaard diagrams of (1, 1)-patterns from standard encodings
(such as the Schubert normal form), computing `CFDhat(K)` from `HFK^-(K)`, and applying the pairing theorem to get a 
chain complex.

Everything is over `F_2` and `F_2[U]`, so there are no signs.

## Disc-counting algorithm

A genus 1 bordered Heegaard diagram lives on the (punctured) torus, though we view it on the universal cover. The edges
of the squares are the red alpha curves and there is a blue beta curve passing through this grid. Starting from an 
intersection point, we trace the beta curve and then check if the embedded curve formed by tracing the alpha curve to the
same endpoint is legal. By following the rules (no reflex angles, cannot contain the `z` basepoint), there is at most
one such alpha path

This method only works for bounded `CFA`s, and will not work when there are infinitely many of these discs.

## The packages

| | |
|---|---|
| **`grid-arc-js/`** |  Given a simple arc on the unit grid, find the grid path joining its endpoints whose enclosed region contains no forbidden point, or prove there is none. Implements the algorithm used to find discs |
| **`heegaard-js/`** | Computes `CFA^-(Q(i,m,n))` |
| **`satellite_floer/`** | the Python package, `satellite-floer` on PyPI. Has two components: **`heegaard/`** produces Heegaard diagrams from parameters like `H(r,s)` for any `r, s`, computes the discs, and visualizes discs to an SVG **`bordered/`** is the algebra computations: `CFA^-`, `CFDhat`, `CFK^-`, the box tensor. |

The Python packages can be imported or called from the command line. The two components can work independently by passing CSV files to each other

## Example usage

```bash
pip install satellite-floer
satellite-floer pattern hrs 3 1 -o P.csv      # a diagram: H(3,1) = Q(1,2,1)
satellite-floer solve P.csv -o discs.csv      # its discs
satellite-floer draw P.csv                    # svg: domain, universal cover, discs
satellite-floer knots                         # what companions are on the shelf
satellite-floer box discs.csv trefoil         # gCFK^- of the satellite
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

## Documentation

- `docs/formats.md` — the CSV formats for diagrams, discs, and algebraic structures
- `docs/bordered.md` — the torus algebra, `CFDhat` from a knot complex, the box tensor.
- `docs/heegaard.md` — diagrams, `H(r,s)`, the solver.
- `heegaard-js/README.md` — the diagram conventions, and naming `Q(i,m,n)` arc families
- `grid-arc-js/README.md` — the algorithm and a visualization

## Status

Homology is currently computed only at `U = 1` instead of `F_2[U].` The construction of `CFD` from `HFK` assumes the
existence of a simultaneously vertically and horizontally simplified basis. As mentioned before, the algorithm only
works for finite (bounded) `CFA`s; it is unclear to me how to extend it to account for infinite families of discs. The 
algorithm to compute gradings on the resulting `gCFK^-`, which are necessary to compute invariants like 
Ozsvath-Szabo's `tau` or Hom's `epsilon`, has not been implemented yet, but soon will be.

## Acknowledgements
The algorithm, project structure, and test structure are mine. Most of the code was written with the assistance of Claude 
(Fable 5.1, Opus 5, and Opus 5.5). Currently some of the documentation is still AI-written, but I'm in the process of 
rewriting the user-facing parts of it myself.

This project was started during Dartmouth's SHUR 2026 REU. I'd like to thank the mentors Ina Petkova and Abhishek Mallick, 
the graduate TAs Allison Tsypin and Shreya Sinha, and my undergraduate colleagues Filip Rupchin and Sean Kim. 

While not a direct inspiration for this package, people interested in computing bordered structures should also look at
Bohua Zhan's bfh_python package (https://github.com/bzhan/bfh_python). It contains a much more sophisticated algebraic
treatment of bordered Floer homology, using the arcslides algorithm and bimodules. My package does not do anything beyond
genus 1. Robert Lipshitz has good tutorials on using this package at https://pages.uoregon.edu/lipshitz/bfh/
