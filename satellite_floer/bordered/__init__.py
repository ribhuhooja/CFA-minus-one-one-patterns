"""Bordered Floer algebra: type-A and type-D structures over the torus algebra, and the box
tensor that pairs a pattern with a companion.

    CFA^-(P, S^1 x D^2)  [x]  CFDhat(S^3 - nu(K))  =  gCFK^-(P(K))

No Heegaard diagrams here.  The only thing this reads from upstream is a CSV of discs, whose
first four columns -- source, target, U power, chord word -- are the type-A structure.
"""

from . import knots, torus
from .box import box, pair, unpair
from .cfk import CFK, cfd_from_cfk, infer_alexander
from .chain import AlgebraError, Arrow, Complex
from .format import (CFA_FORMAT, CFD_FORMAT, COMPLEX_FORMAT, read_cfa, read_cfd, read_cfk,
                     read_complex, write_cfa, write_cfd, write_cfk, write_complex)
from .knots import cfd, cfk, mirror
from .structures import CFA, CFD, DArrow, Operation

__all__ = ["CFA", "CFD", "CFK", "Complex", "Arrow", "Operation", "DArrow", "AlgebraError",
           "box", "pair", "unpair", "cfd", "cfk", "cfd_from_cfk", "mirror",
           "infer_alexander", "knots", "torus",
           "CFA_FORMAT", "CFD_FORMAT", "COMPLEX_FORMAT",
           "read_cfa", "read_cfd", "read_cfk", "read_complex",
           "write_cfa", "write_cfd", "write_cfk", "write_complex"]
