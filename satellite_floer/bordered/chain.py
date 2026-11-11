"""Chain complexes over F_2[U], as graphs.

A complex is a set of generators and a set of arrows, an arrow ``x -> U^k y`` meaning that
``U^k y`` is one term of ``d x``.  Coefficients live in F_2[U], so an arrow is just a power of
U, two identical arrows cancel, and there are no signs to get wrong.

No grading.  Gradings are a separate matter and this project does not carry them here; the
Alexander grading that a CFK^- needs is kept beside the complex in ``cfk.py``, not inside it.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field


class AlgebraError(Exception):
    """Something about a structure does not hold together."""


@dataclass(frozen=True)
class Arrow:
    """One term of a differential: ``d(source) contains U^power . target``."""

    source: str
    target: str
    power: int

    def __post_init__(self) -> None:
        if self.power < 0:
            raise AlgebraError(f"U^{self.power} is not a coefficient in F_2[U]")


@dataclass
class Complex:
    """A chain complex over F_2[U]."""

    name: str = "complex"
    generators: list[str] = field(default_factory=list)
    arrows: list[Arrow] = field(default_factory=list)
    notes: dict = field(default_factory=dict)

    # ------------------------------------------------------------ building

    @classmethod
    def build(cls, name: str, generators, terms) -> "Complex":
        """From ``terms = [(source, target, power), ...]``, reduced mod 2."""
        c = cls(name=name, generators=list(dict.fromkeys(generators)))
        c.arrows = reduce_mod2(Arrow(s, t, k) for s, t, k in terms)
        c.check_generators()
        return c

    def check_generators(self) -> "Complex":
        known = set(self.generators)
        for a in self.arrows:
            for end in (a.source, a.target):
                if end not in known:
                    raise AlgebraError(f"the arrow {a.source} -> {a.target} names {end!r}, "
                                       f"which is not a generator of {self.name}")
        return self

    def out_of(self, generator: str) -> list[Arrow]:
        return [a for a in self.arrows if a.source == generator]

    # ------------------------------------------------------------ checking

    def d_squared(self) -> list[Arrow]:
        """The terms of ``d^2``, reduced mod 2.  Empty is what we want."""
        return reduce_mod2(Arrow(a.source, b.target, a.power + b.power)
                           for a in self.arrows for b in self.arrows if b.source == a.target)

    def is_a_complex(self) -> bool:
        return not self.d_squared()

    def require_complex(self) -> "Complex":
        bad = self.d_squared()
        if bad:
            first = ", ".join(f"{a.source} -> U^{a.power} {a.target}" for a in bad[:4])
            raise AlgebraError(f"{self.name}: d^2 is not zero -- {len(bad)} terms survive "
                               f"({first}{', ...' if len(bad) > 4 else ''})")
        return self

    def homology_rank_at_U1(self) -> int:
        """dim_F2 H(C / (U - 1)).

        Setting U = 1 turns the complex into one over F_2 and kills every F_2[U]-torsion
        summand of the homology, so what survives is the rank of the free part.  For a knot
        complex -- and so for a box tensor that really is one -- that must be exactly 1.
        Cheap, and it catches almost anything that has gone wrong.
        """
        index = {g: k for k, g in enumerate(self.generators)}
        rows = defaultdict(int)                     # source -> a bitmask over targets
        for a in self.arrows:
            rows[a.source] ^= 1 << index[a.target]
        rank = _rank_mod2([v for v in rows.values() if v])
        return len(self.generators) - 2 * rank

    def __str__(self) -> str:
        return (f"{self.name}: {len(self.generators)} generators, "
                f"{len(self.arrows)} arrows")


def reduce_mod2(arrows) -> list[Arrow]:
    """Cancel repeated arrows in pairs, and put what is left in a canonical order."""
    parity: dict[Arrow, int] = defaultdict(int)
    for a in arrows:
        parity[a] ^= 1
    return sorted((a for a, odd in parity.items() if odd),
                  key=lambda a: (a.source, a.target, a.power))


def _rank_mod2(vectors: list[int]) -> int:
    """Gaussian elimination over F_2, rows as bitmasks."""
    pivots: list[int] = []
    for v in vectors:
        for p in pivots:
            v = min(v, v ^ p)
        if v:
            pivots.append(v)
            pivots.sort(reverse=True)
    return len(pivots)
