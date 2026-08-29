"""A catalogue of knot complexes, so a companion can be named instead of typed out.

This is where a ``CFK^-`` someone worked out on paper gets written down once, checked, and
given a name.  Each entry is the differential over F_2[U] and nothing else -- the Alexander
grading is inferred (see ``cfk.infer_alexander``) unless an entry pins it, and everything
downstream, tau included, follows.

To add one: put a ``Knot`` in ``KNOTS``.  The tests walk the catalogue, so a new entry is
checked for ``d^2 = 0``, for a simplified basis, for tau agreeing with itself both ways, for
free homology of rank one, and for its type-D structure satisfying the type-D relation, the
moment it is registered.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .cfk import CFK, cfd_from_cfk
from .chain import AlgebraError
from .structures import CFD


@dataclass
class Knot:
    name: str
    parameters: tuple[str, ...]
    note: str
    make: Callable[..., CFK]


def mirror(k: CFK, name: str | None = None) -> CFK:
    """The mirror knot: reverse every arrow, negate the Alexander grading.

    Both families survive intact -- a vertical arrow of length k stays one, a horizontal
    arrow of length l stays one -- and tau changes sign, which is the point.
    """
    return CFK.build(name or f"mirror({k.name})", k.generators,
                     [(a.target, a.source, a.power) for a in k.complex.arrows],
                     alexander={g: -a for g, a in k.alexander.items()})


def _unknot() -> CFK:
    return CFK.build("unknot", ["a"], [], alexander={"a": 0})


def _t2(q: int = 3) -> CFK:
    """The staircase of the torus knot T(2, q), q odd.  Negative q is the mirror.

    ``d b_{2i-1} = b_{2i-2} + U b_{2i}``, and ``A(b_j) = j - k`` where ``q = 2k + 1``, so
    tau = k = the genus.  q = 3 is the right-handed trefoil.
    """
    if abs(q) < 3 or q % 2 == 0:
        raise AlgebraError(f"T(2,{q}) is not a knot to build here; q must be odd, |q| >= 3")
    if q < 0:
        return mirror(_t2(-q), f"T(2,{q})")
    k = (q - 1) // 2
    generators = [f"b_{j}" for j in range(2 * k + 1)]
    terms = []
    for i in range(1, k + 1):
        terms += [(f"b_{2 * i - 1}", f"b_{2 * i - 2}", 0), (f"b_{2 * i - 1}", f"b_{2 * i}", 1)]
    return CFK.build(f"T(2,{q})", generators, terms,
                     alexander={f"b_{j}": j - k for j in range(2 * k + 1)})


def _trefoil() -> CFK:
    return CFK.build("trefoil", ["a", "b", "c"], [("b", "a", 0), ("b", "c", 1)],
                     alexander={"a": -1, "b": 0, "c": 1})


def _figure_eight() -> CFK:
    """The box plus a point.  tau = 0, and the box is what makes it not an L-space knot."""
    return CFK.build("figure-eight", ["a", "b", "c", "d", "e"],
                     [("a", "b", 1), ("a", "c", 0), ("b", "d", 0), ("c", "d", 1)],
                     alexander={"a": 0, "b": 1, "c": -1, "d": 0, "e": 0})


KNOTS: dict[str, Knot] = {
    "unknot": Knot("unknot", (), "one generator, no differential; tau = 0", _unknot),
    "trefoil": Knot("trefoil", (), "right-handed; d b = a + U c, tau = +1", _trefoil),
    "lh-trefoil": Knot("lh-trefoil", (), "the mirror; tau = -1",
                       lambda: mirror(_trefoil(), "lh-trefoil")),
    "figure-eight": Knot("figure-eight", (),
                         "d a = U b + c, d b = d, d c = U d, d e = 0; tau = 0", _figure_eight),
    "t2": Knot("t2", ("q",), "the torus knot T(2,q), q odd; q = 3 is the trefoil", _t2),
}

ALIASES = {"rh-trefoil": "trefoil", "right-trefoil": "trefoil", "3_1": "trefoil",
           "left-trefoil": "lh-trefoil", "4_1": "figure-eight", "0_1": "unknot",
           "figure8": "figure-eight", "fig8": "figure-eight"}


def names() -> list[str]:
    return list(KNOTS)


def cfk(name: str, *parameters: int) -> CFK:
    """Build a knot complex by name."""
    key = ALIASES.get(name, name)
    if key not in KNOTS:
        raise AlgebraError(f"no knot called {name!r}; try one of {', '.join(KNOTS)}")
    entry = KNOTS[key]
    if len(parameters) != len(entry.parameters) and parameters:
        raise AlgebraError(f"{entry.name} takes {len(entry.parameters)} parameter(s) "
                           f"({', '.join(entry.parameters) or 'none'}), got {len(parameters)}")
    return entry.make(*parameters)


def cfd(name: str, *parameters: int) -> CFD:
    """The type-D structure of the complement, by knot name.  ``cfd("trefoil")``."""
    return cfd_from_cfk(cfk(name, *parameters))


def catalogue() -> str:
    rows = []
    for entry in KNOTS.values():
        head = " ".join([entry.name] + [f"<{p}>" for p in entry.parameters])
        rows.append(f"  {head:<22} {entry.note}")
    return "\n".join(rows)
