"""The torus algebra A(T^2), over F_2.

Eight nonzero elements: two idempotents and six Reeb chords.  The chords are the intervals
[i, j] in the four points where the alpha arcs meet the boundary circle:

    rho_1 = [1,2]   rho_2 = [2,3]   rho_3 = [3,4]
    rho_12 = [1,3]  rho_23 = [2,4]  rho_123 = [1,4]

The two alpha arcs end at {1,3} and {2,4}, and those are the two idempotents: iota_0 is the
arc through 1 and 3, iota_1 the arc through 2 and 4.  So a chord [i, j] runs from the
idempotent owning i to the one owning j, and that single sentence generates the whole table
below -- nothing here is a convention anyone chose.

Multiplication is concatenation: [i,j][j,k] = [i,k], and anything else is zero.  Note that
this makes rho_2 rho_1 = 0 even though the idempotents line up; a chord SEQUENCE (rho_2, rho_1)
is still perfectly legal, and does occur in the disc tables.  See ``composable``.
"""

from __future__ import annotations

IOTA = ("iota_0", "iota_1")

#: chord -> (start point, end point) on the boundary circle
SPAN = {"rho_1": (1, 2), "rho_2": (2, 3), "rho_3": (3, 4),
        "rho_12": (1, 3), "rho_23": (2, 4), "rho_123": (1, 4)}
CHORDS = tuple(SPAN)

#: which alpha arc, hence which idempotent, owns each boundary point
_OWNER = {1: 0, 2: 1, 3: 0, 4: 1}


def left(chord: str) -> int:
    """The idempotent a chord starts at: ``iota_left(rho) . rho == rho``."""
    return _OWNER[SPAN[_check(chord)][0]]


def right(chord: str) -> int:
    """The idempotent a chord ends at: ``rho . iota_right(rho) == rho``."""
    return _OWNER[SPAN[_check(chord)][1]]


def multiply(a: str, b: str) -> str | None:
    """``a * b`` in the algebra, or None for zero."""
    (i, j), (k, l) = SPAN[_check(a)], SPAN[_check(b)]
    if j != k:
        return None
    for name, span in SPAN.items():
        if span == (i, l):
            return name
    return None


def composable(word) -> bool:
    """Is this sequence of chords a legal argument list for an A_infinity operation?

    Consecutive chords must meet in the idempotents -- ``right(a) == left(b)`` -- which is
    weaker than ``multiply(a, b) != None``.  (rho_2, rho_1) passes this and multiplies to
    zero, and the disc tables contain it.
    """
    return all(right(a) == left(b) for a, b in zip(word, word[1:]))


def word_endpoints(word) -> tuple[int, int] | None:
    """The idempotents a chord word runs between, or None if it is empty."""
    if not word:
        return None
    return (left(word[0]), right(word[-1]))


# ---------------------------------------------------------------- spelling

def parse_word(text: str) -> list[str]:
    """Read a chord word.

    ``P1P23`` and ``P123`` are different words and both are unambiguous, because the P
    delimits.  ``rho_1 rho_23`` and ``1,23`` are accepted too, for anyone typing by hand.
    """
    text = (text or "").strip()
    if not text:
        return []
    if "P" in text.upper() and "RHO" not in text.upper():
        pieces = [p for p in text.upper().replace(" ", "").split("P") if p != ""]
    else:
        pieces = [p for p in text.replace(",", " ").split() if p]
        pieces = [p[4:] if p.lower().startswith("rho_") else p for p in pieces]
    return [_check("rho_" + p.strip()) for p in pieces]


def write_word(word) -> str:
    """``["rho_1", "rho_23"] -> "P1P23"``, matching the disc CSV."""
    return "".join(c.replace("rho_", "P") for c in word)


def _check(chord: str) -> str:
    if chord not in SPAN:
        raise ValueError(f"{chord!r} is not a Reeb chord of the torus algebra; "
                         f"expected one of {', '.join(SPAN)}")
    return chord
