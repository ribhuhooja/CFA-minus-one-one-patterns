"""The Q(i, m, n) family, as bordered Heegaard diagrams H(r, s).

    r    = 1 + 2im - m
    s    = n + 3m - 2mn + 4imn - 4im - 2
    maxx = 2r + s + m + n - 3        x generators, indexed 0..maxx
    maxy = 4im - 2m = 2r - 2         y generators, indexed 0..maxy

Six families of arcs.  Direction is not meaningful -- an arc joins its two endpoints -- the
arrows below only match how the families were first written down.

    F1  left -> top      y_j -- x_j                  j = 0 .. maxy
    F2  bottom -> top    x_j -- x_{2r-1+j}           j = 0 .. s-r
    F3  bottom rainbow   x_{s-r+1+j} -- x_{s+r-j}    j = 0 .. r-1
    F4  dependent        x_{s+r+j} -- x_{s+r+1+j}    j = 0 .. m+n-3
    F5  right -> top     y_j -- x_{maxx-j}           j = 0 .. r-1
    F6  right -> bottom  y_{maxy-j} -- x_{maxx-j}    j = 0 .. r-2

F4 was given by index alone; which edge each end sits on is forced, not chosen.  After F1, F2
and F5 the top edge is short of exactly s+r .. s+r+m+n-3, and after F2, F3 and F6 the bottom
is short of exactly s+r+1 .. s+r+m+n-2.  So the dependent arcs run from the top to the bottom,
each landing one index to the right of where it left: m+n-2 strands across the domain.

The basepoint w is shut inside the innermost rainbow, the arc x_s -- x_{s+1}; the multiplicity
of a domain there is the power of U it carries.  The other basepoint, z, sits in the top-left
corner and may never be covered.
"""

from __future__ import annotations

from dataclasses import dataclass

from .diagram import Diagram


@dataclass(frozen=True)
class Parameters:
    i: int
    m: int
    n: int
    r: int
    s: int
    max_x: int
    max_y: int
    dependent_strands: int


def parameters(i: int, m: int, n: int) -> Parameters:
    r = 1 + 2 * i * m - m
    s = n + 3 * m - 2 * m * n + 4 * i * m * n - 4 * i * m - 2
    return Parameters(i, m, n, r, s,
                      max_x=2 * r + s + m + n - 3,
                      max_y=2 * r - 2,
                      dependent_strands=m + n - 2)


def Q(i: int, m: int, n: int) -> Diagram:
    """Build Q(i, m, n), validated."""
    for name, value in (("i", i), ("m", m), ("n", n)):
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise ValueError(f"Q: {name} must be a non-negative integer, got {value!r}")
    if n < 2:
        raise ValueError(f"Q({i},{m},{n}): this family is only defined for n >= 2")

    p = parameters(i, m, n)
    if p.r < 1:
        raise ValueError(f"Q({i},{m},{n}): r = {p.r} must be positive")
    if p.s < p.r:
        raise ValueError(f"Q({i},{m},{n}): s = {p.s} must be at least r = {p.r}")
    if p.max_y != 4 * i * m - 2 * m:
        raise ValueError(f"Q({i},{m},{n}): maxy disagrees with 4im-2m")

    r, s, max_x, max_y = p.r, p.s, p.max_x, p.max_y
    d = Diagram(name=f"Q({i},{m},{n})", x_count=max_x + 1, y_count=max_y + 1)

    for j in range(max_y + 1):
        d.add_arc(j, "left", j, "top", "left-top")
    for j in range(s - r + 1):
        d.add_arc(j, "bottom", 2 * r - 1 + j, "top", "bottom-top")
    for j in range(r):
        d.add_arc(s - r + 1 + j, "bottom", s + r - j, "bottom", "rainbow")
    for j in range(m + n - 2):
        d.add_arc(s + r + j, "top", s + r + 1 + j, "bottom", "dependent")
    for j in range(r):
        d.add_arc(j, "right", max_x - j, "top", "right-top")
    for j in range(r - 1):
        d.add_arc(max_y - j, "right", max_x - j, "bottom", "right-bottom")

    dependent = sum(1 for a in d.arcs if a.family == "dependent")
    if dependent != p.dependent_strands:
        raise ValueError(f"Q({i},{m},{n}): built {dependent} dependent strands, "
                         f"expected m+n-2 = {p.dependent_strands}")

    innermost = next(k for k, a in enumerate(d.arcs)
                     if a.family == "rainbow" and abs(a.a.index - a.b.index) == 1)
    d.set_basepoint("w", innermost)
    d.notes = {"i": i, "m": m, "n": n, "r": r, "s": s,
               "maxx": max_x, "maxy": max_y, "dependentStrands": p.dependent_strands}
    return d.validate()
