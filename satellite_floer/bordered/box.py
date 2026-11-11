"""The box tensor product, ``CFA^- [x] CFDhat``.

    generators   x (x) eta, for x in the CFA and eta in the CFD lying in the SAME idempotent
    differential d(x (x) eta) = sum over operations x -U^k, (a_1..a_n)-> y of the CFA,
                                and over paths eta -a_1-> ... -a_n-> zeta of the CFD spelling
                                that same sequence, of U^k . (y (x) zeta)

The n = 0 term is the CFA's own differential m_1 against the empty path, which ends where it
started: an arrow ``x (x) eta -> y (x) eta``.

MATCH THE SEQUENCE, NEVER THE PRODUCT.  A CFA operation labelled ``rho_12`` wants a single
CFD arrow labelled ``rho_12``; one labelled ``(rho_1, rho_2)`` wants a two-arrow path.  They
are different operations of the A_infinity structure and multiplying would conflate them.

WHY THIS TERMINATES.  A CFA that came from a Heegaard diagram has finitely many operations,
so its words have some longest length, and only paths of exactly that many arrows are ever
enumerated.  The CFD need not be bounded -- the unknot's is a single generator with a
``rho_12`` self-loop, and it works fine.

WHAT IT IS, IN GRAPH TERMS.  If both sides carried single letters this would be the tensor
(Kronecker, categorical) product of edge-labelled graphs: keep a pair of edges when the labels
agree.  With words on the type-A side it is the product construction for automata -- the CFA
is a finite-state transducer reading chord words and emitting powers of U, the CFD is an NFA
over the same alphabet, and this is their composition.  Chop each CFA word into a path through
fresh intermediate states and it becomes the plain tensor product again.
"""

from __future__ import annotations

from .chain import AlgebraError, Complex
from .structures import CFA, CFD

SEPARATOR = "*"


def box(cfa: CFA, cfd: CFD, name: str | None = None) -> Complex:
    """``CFA [x] CFD``, as a chain complex over F_2[U]."""
    if not cfd.is_reduced():
        raise AlgebraError(
            f"{cfd.name}: this type-D structure has arrows with an idempotent coefficient, so "
            f"it is not reduced. The box tensor needs a reduced one -- and an unreduced "
            f"structure need not even be bounded. Reducing it is not written yet")
    cfd.index()

    by_idempotent = {i: cfd.in_idempotent(i) for i in (0, 1)}
    generators = [pair(x, e) for x in cfa.generators
                  for e in by_idempotent[cfa.idempotent[x]]]

    terms = []
    for op in cfa.operations:
        for eta in by_idempotent[cfa.idempotent[op.source]]:
            source = pair(op.source, eta)
            for zeta in cfd.paths(eta, op.word):
                terms.append((source, pair(op.target, zeta), op.power))

    c = Complex.build(name or f"{cfa.name} [x] {cfd.name}", generators, terms)
    c.notes.update(cfa=cfa.name, cfd=cfd.name, terms=len(terms))
    return c


def pair(x: str, eta: str) -> str:
    return f"{x}{SEPARATOR}{eta}"


def unpair(generator: str) -> tuple[str, str]:
    x, _, eta = generator.partition(SEPARATOR)
    return x, eta
