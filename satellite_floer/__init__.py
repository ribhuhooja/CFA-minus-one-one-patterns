"""Knot Floer homology of satellites with (1,1) patterns.

    CFA^-(P, S^1 x D^2)  [x]  CFDhat(S^3 - nu(K))  =  gCFK^-(P(K))

Two subpackages, which do not import each other:

- :mod:`satellite_floer.heegaard` -- bordered Heegaard diagrams for (1,1) patterns, the
  discs they bound, and pictures of both.
- :mod:`satellite_floer.bordered` -- the torus algebra, type-A and type-D structures,
  ``CFDhat`` from a knot complex, and the box tensor.

The only thing that passes between them is a CSV of discs, whose first four columns are the
type-A structure.  ``satellite-floer`` on the command line reaches both.
"""

from . import bordered, heegaard

__version__ = "0.1.0"

__all__ = ["bordered", "heegaard", "__version__"]
