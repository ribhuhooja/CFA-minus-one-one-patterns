"""2-bridge links: b(p, q), C(a_1, ..., a_n), and H(r, s).

A (1,1) pattern whose companion is the unknot is a 2-component 2-bridge link, and those have
two classical names.  **Schubert normal form** ``b(p, q)`` gives the double branched cover as
the lens space L(p, q).  **Conway form** ``C(a_1, ..., a_n)`` gives the rational tangle, and
the two are the same number written two ways::

    q / p = 1 / (a_1 + 1 / (a_2 + ... ))        equivalently   p / q = [a_1; a_2, ..., a_n]

so the ``a_i`` are just the continued fraction of ``p/q``.  Our own parameters join on at::

    p = 2s + 4|r|            q = sign(r) (2|r| - 1)

This module is only a dictionary between the three.  **It does not narrow anything.**  The
solver, the visualiser and the algebra take whatever diagram they are handed, and plenty of
(1,1) patterns are not unknot patterns at all; nothing here is imposed on them.  It is here so
that a diagram which *does* come from a 2-bridge link can be called by its usual name.

One thing worth knowing, because it is not a coincidence.  ``b(p, q)`` is a link at all only
when ``gcd(p, q) = 1``, and that is exactly the condition :func:`heegaard.chen.is_connected`
puts on ``H(r, s)`` -- because ``4|r| = 2 mod (2|r|-1)``, so ``p = 2(s+1) mod q``, and ``q`` is
odd, giving ``gcd(p, q) = gcd(2|r|-1, s+1)``.  A test checks the two agree.  ``p`` comes out
even always, which is what says the link has two components rather than one.
"""

from __future__ import annotations

from fractions import Fraction
from math import gcd


def schubert(r: int, s: int) -> tuple:
    """The Schubert form ``b(p, q)`` of ``H(r, s)``.

    >>> schubert(3, 1)
    (14, 5)
    """
    if r == 0:
        raise ValueError("H(r, s): r must not be zero")
    if s <= 0:
        raise ValueError(f"H(r, s): s must be positive, got {s}")
    a = abs(r)
    return 2 * s + 4 * a, (1 if r > 0 else -1) * (2 * a - 1)


def normalise(p: int, q: int) -> int:
    """``q`` brought into ``0 < q < p``.  It is only ever defined modulo ``p``."""
    if p <= 0:
        raise ValueError(f"b({p},{q}): p must be positive")
    return q % p


def parameters(p: int, q: int) -> tuple:
    """The ``(r, s)`` whose Schubert form is ``b(p, q)``: the inverse of :func:`schubert`.

    ``q`` is read as given rather than reduced, so a negative ``q`` asks for the ``r < 0``
    diagram.  ``b(p, q)`` and ``b(p, q - p)`` are the same link and give the two different
    diagrams for it; :func:`readings` returns both.
    """
    if p % 2:
        raise ValueError(f"b({p},{q}): p must be even for a two-component link")
    if q % 2 == 0:
        raise ValueError(f"b({p},{q}): q must be odd")
    a = (abs(q) + 1) // 2
    s, remainder = divmod(p - 4 * a, 2)
    if remainder or s <= 0:
        raise ValueError(f"b({p},{q}): no H(r, s) has this form "
                         f"(s would be {(p - 4 * a) / 2})")
    return ((1 if q > 0 else -1) * a, s)


def readings(p: int, q: int) -> list:
    """Every ``(r, s)`` that presents this link, both signs of ``r`` where both work."""
    out = []
    for candidate in (normalise(p, q), normalise(p, q) - p):
        try:
            out.append(parameters(p, candidate))
        except ValueError:
            pass
    return out


def conway(p: int, q: int, reduce: bool = True) -> tuple:
    """The Conway form ``C(a_1, ..., a_n)``: the continued fraction of ``p/q``.

    With ``reduce`` (the default) ``q`` is first brought into ``0 < q < p``, which is where it
    is only defined anyway and which is what makes every ``a_i`` positive.  Without it the
    fraction is taken as handed over, and a negative ``q`` gives a leading negative term.

    >>> conway(14, 5)
    (2, 1, 4)
    """
    if q == 0:
        raise ValueError(f"b({p},{q}): q must not be zero")
    if gcd(p, abs(q)) != 1:
        raise ValueError(f"b({p},{q}): gcd is {gcd(p, abs(q))}, so this is not a link")
    top, bottom = p, (normalise(p, q) if reduce else q)
    out = []
    while bottom:
        whole = top // bottom
        out.append(whole)
        top, bottom = bottom, top - whole * bottom
    return tuple(out)


def schubert_of_conway(*terms: int) -> tuple:
    """``b(p, q)`` from ``C(a_1, ..., a_n)``: the inverse of :func:`conway`.

    >>> schubert_of_conway(2, 1, 4)
    (14, 5)
    """
    if not terms:
        raise ValueError("C(): needs at least one term")
    value = Fraction(terms[-1])
    for term in reversed(terms[:-1]):
        if value == 0:
            raise ValueError(f"C{terms}: the fraction divides by zero part way along")
        value = term + 1 / value
    if value <= 0:
        raise ValueError(f"C{terms}: gives p/q = {value}, which is not a link")
    return value.numerator, value.denominator


# ---------------------------------------------------------------- straight through

def conway_of(r: int, s: int, reduce: bool = True) -> tuple:
    """The Conway form of ``H(r, s)``, going by way of Schubert."""
    return conway(*schubert(r, s), reduce=reduce)


def parameters_of_conway(*terms: int) -> tuple:
    """The ``(r, s)`` of ``C(a_1, ..., a_n)``, going by way of Schubert."""
    p, q = schubert_of_conway(*terms)
    found = readings(p, q)
    if not found:
        raise ValueError(f"C{terms} = b({p},{q}): no H(r, s) has this form")
    return found[0]


def name(r: int, s: int) -> str:
    """All three names of one pattern, for a caption or a table."""
    p, q = schubert(r, s)
    terms = ",".join(str(a) for a in conway(p, q))
    return f"H({r},{s}) = b({p},{normalise(p, q)}) = C({terms})"
