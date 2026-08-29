"""The catalogue: diagrams this package can build from nothing but a name and some integers.

Everything else in the package takes a diagram it was handed -- ``solve`` reads whatever CSV
it is given and has never heard of any particular family.  This is the other end: the place
where a diagram someone drew on paper gets written down once, checked, and given a name, so
that it can be built, exported, solved and compared without being re-entered by hand.

A pattern is a name, the integer parameters it wants, a one-line summary, and a builder that
returns a validated :class:`~heegaard.diagram.Diagram`.  Adding one means writing the builder
and putting it in ``PATTERNS``; nothing else in the package has to change.

Two rules for anything added here.  The builder ends in ``.validate()``, so an illegal diagram
cannot leave this module; and it sets the ``w`` basepoint, because a diagram with nowhere to
put ``w`` has no U powers and the solver will refuse it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .chen import H
from .diagram import Diagram
from .qmn import Q


# --------------------------------------------------------------------------- Q(i, m, n)

def qimn(i: int, m: int, n: int) -> Diagram:
    """The Q(i, m, n) family.  See :mod:`heegaard.qmn`, which is where it is built."""
    return Q(i, m, n)


# --------------------------------------------------------------------------- H(r, s)

def hrs(r: int, s: int) -> Diagram:
    """The general family H(r, s).  See :mod:`heegaard.chen`, which is where it is built.

    Q(i,m,n) is the member with ``r = 1+2im-m`` and ``s = n+3m-2mn+4imn-4im-2``, which the
    tests check arc for arc; ``twin-rainbow`` is Q(1,2,1) = H(3,1).  Unlike Q this one is
    happy with ``n = 1``, and with ``r < 0``.
    """
    return H(r, s)


# --------------------------------------------------------------------------- twin rainbow

def twin_rainbow() -> Diagram:
    """A single diagram with 8 x generators and 5 y generators, drawn by hand.

    Read off the picture exactly as dictated, with the arcs in these families:

        rainbow        bottom -- bottom    x_0 -- x_3,  x_1 -- x_2
        left-bottom    left   -- bottom    y_4 -- x_4
        left-top       left   -- top       y_j -- x_j,          j = 0 .. 3
        bottom-top     bottom -- top       x_5 -- x_4
        top-right      top    -- right     x_5 -- y_2,  x_6 -- y_1,  x_7 -- y_0
        bottom-right   bottom -- right     x_6 -- y_3,  x_7 -- y_4

    Thirteen arcs for 8 + 5 generators, which is the count a legal diagram must have.  ``w``
    goes inside the innermost rainbow x_1 -- x_2, the same convention as Q(i,m,n): the
    multiplicity of a domain there is the power of U it carries.  It bounds 25 discs,
    confirmed against heegaard-js: the same CSV through ``node solve.js`` comes back
    byte for byte.

    It **is** a member of the Q family: it is Q(1,2,1), which is H(3,1).  That was missed at
    first because the Q constructor here only admits n >= 2, and with that restriction the
    fit really is impossible -- the right fan gives r = 3 while the two rainbows give r = 2,
    and going the other way maxy = 4im - 2m = 4 forces m = 2, i = 1, and then maxx = 6n+1 = 7
    wants n = 1.  Which is the answer, not a contradiction: n = 1.  :mod:`heegaard.chen`
    builds H(r,s) for any legal r and s and has no such restriction, and a test holds this
    diagram and H(3,1) together arc for arc and disc for disc.

    Nor does the obvious one-parameter generalisation of the *picture* exist.  Reading it as
    p nested rainbows with a matching (p+1)-arc right fan reproduces this diagram at p = 2 and
    gives a legal slot pattern at every p, but beta then meets (alpha_y, alpha_x) with
    multiplicity (-1, 1) at p = 1 and (-1, 2-p) from p = 3 up -- a closed curve in the wrong
    homology class every time.  Checked p = 1 .. 6.
    """
    d = Diagram(name="twin-rainbow", x_count=8, y_count=5)

    for a, b in ((0, 3), (1, 2)):
        d.add_arc(a, "bottom", b, "bottom", "rainbow")
    d.add_arc(4, "left", 4, "bottom", "left-bottom")
    for j in range(4):
        d.add_arc(j, "left", j, "top", "left-top")
    d.add_arc(5, "bottom", 4, "top", "bottom-top")
    for x, y in ((5, 2), (6, 1), (7, 0)):
        d.add_arc(x, "top", y, "right", "top-right")
    for x, y in ((6, 3), (7, 4)):
        d.add_arc(x, "bottom", y, "right", "bottom-right")

    innermost = next(k for k, arc in enumerate(d.arcs)
                     if arc.family == "rainbow" and abs(arc.a.index - arc.b.index) == 1)
    d.set_basepoint("w", innermost)
    return d.validate()


# --------------------------------------------------------------------------- the registry

@dataclass(frozen=True)
class Pattern:
    """One entry in the catalogue."""

    name: str
    parameters: tuple[str, ...]
    summary: str
    build: Callable[..., Diagram]

    def __call__(self, *args: int) -> Diagram:
        if len(args) != len(self.parameters):
            wanted = " ".join(self.parameters) if self.parameters else "no parameters"
            raise ValueError(f"{self.name} takes {wanted}, got {len(args)} argument"
                             f"{'' if len(args) == 1 else 's'}")
        return self.build(*args)

    @property
    def usage(self) -> str:
        return " ".join((self.name, *(f"<{p}>" for p in self.parameters)))


PATTERNS: dict[str, Pattern] = {
    p.name: p for p in (
        Pattern("qimn", ("i", "m", "n"),
                "the Q(i,m,n) family: rainbows, dependent strands, and a right fan", qimn),
        Pattern("hrs", ("r", "s"),
                "the general family H(r,s); Q(i,m,n) is one member of it", hrs),
        Pattern("twin-rainbow", (),
                "8 x and 5 y generators, two nested rainbows; drawn by hand.  It is Q(1,2,1)",
                twin_rainbow),
    )
}


def names() -> list[str]:
    """Every pattern name, in catalogue order."""
    return list(PATTERNS)


def build(name: str, *args: int) -> Diagram:
    """Build a named pattern.  ``build("qimn", 2, 2, 2)``, ``build("twin-rainbow")``."""
    if name not in PATTERNS:
        raise ValueError(f"no pattern called {name!r}; there is "
                         + ", ".join(repr(k) for k in PATTERNS))
    return PATTERNS[name](*args)


def catalogue() -> str:
    """The catalogue as a block of text, for ``--help`` and for people."""
    width = max(len(p.usage) for p in PATTERNS.values())
    return "\n".join(f"  {p.usage:<{width}}  {p.summary}" for p in PATTERNS.values())
