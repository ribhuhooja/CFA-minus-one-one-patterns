"""Knot complexes, and the type-D structure of a knot complement.

A ``CFK^-`` is a chain complex over F_2[U] together with an Alexander grading.  The grading is
exactly the extra data that makes it a knot complex rather than any old complex, and it is
what the whole construction below reads.

In CFK^infinity coordinates a generator ``x`` sits at ``(0, A(x))`` and ``U^k x`` at
``(-k, A(x) - k)``.  So a differential term ``x -> U^k y``:

    k == 0   preserves i and drops j -- a VERTICAL arrow, of length ``A(x) - A(y)``
    k > 0    drops i by k and preserves j -- a HORIZONTAL arrow of length k,
             and then ``A(y) = A(x) + k``.  Horizontal arrows RAISE the Alexander grading.

A basis in which the vertical arrows are a set of disjoint pairs, and the horizontal ones are
too, is what Levine's Proposition 2.4 asks for.  Each pairing leaves exactly one generator
over: ``xi_0`` vertically and ``eta_0`` horizontally, and ``tau(K) = A(xi_0) = -A(eta_0)``.
Both are computed and cross-checked.  With ``d b = a + U c`` this makes the trefoil the
RIGHT-handed one, tau = +1.

We check that a given basis is simplified and refuse otherwise.  Producing one from an
arbitrary complex is not written -- see CLAUDE.md.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from itertools import permutations, product

from .chain import AlgebraError, Complex
from .structures import CFD


@dataclass(frozen=True)
class KnotArrow:
    source: str
    target: str
    length: int


@dataclass
class CFK:
    """A reduced ``CFK^-`` over F_2[U], with its Alexander grading."""

    complex: Complex
    alexander: dict[str, int] = field(default_factory=dict)

    @classmethod
    def build(cls, name, generators, terms, alexander=None) -> "CFK":
        c = Complex.build(name, generators, terms).require_complex()
        grading = dict(alexander) if alexander else infer_alexander(c)
        missing = [g for g in c.generators if g not in grading]
        if missing:
            raise AlgebraError(f"{name}: no Alexander grading for {', '.join(missing)}")
        return cls(complex=c, alexander=grading).validate()

    @property
    def name(self) -> str:
        return self.complex.name

    @property
    def generators(self) -> list[str]:
        return self.complex.generators

    # ------------------------------------------------------------ the two families

    def vertical(self) -> list[KnotArrow]:
        return [KnotArrow(a.source, a.target, self.alexander[a.source] - self.alexander[a.target])
                for a in self.complex.arrows if a.power == 0]

    def horizontal(self) -> list[KnotArrow]:
        return [KnotArrow(a.source, a.target, a.power)
                for a in self.complex.arrows if a.power > 0]

    def validate(self) -> "CFK":
        for a in self.complex.arrows:
            if a.power == 0:
                drop = self.alexander[a.source] - self.alexander[a.target]
                if drop < 1:
                    raise AlgebraError(
                        f"{self.name}: the vertical arrow {a.source} -> {a.target} has length "
                        f"{drop}; a differential cannot raise the Alexander grading")
            else:
                want = self.alexander[a.source] + a.power
                if self.alexander[a.target] != want:
                    raise AlgebraError(
                        f"{self.name}: the horizontal arrow {a.source} -> U^{a.power} "
                        f"{a.target} needs A({a.target}) = {want}, but the grading says "
                        f"{self.alexander[a.target]}")
        self.survivors()                              # raises if the basis is not simplified
        return self

    def survivors(self) -> tuple[str, str]:
        """``(xi_0, eta_0)``: the generators the two pairings leave over."""
        xi = _survivor(self.name, "vertical", self.generators, self.vertical())
        eta = _survivor(self.name, "horizontal", self.generators, self.horizontal())
        nv, nh = len(self.vertical()), len(self.horizontal())
        if nv != nh:
            raise AlgebraError(f"{self.name}: {nv} vertical arrows but {nh} horizontal ones; "
                               f"a knot complex has the same number of each")
        return xi, eta

    def tau(self) -> int:
        xi, eta = self.survivors()
        t, t2 = self.alexander[xi], -self.alexander[eta]
        if t != t2:
            raise AlgebraError(f"{self.name}: A(xi_0) = {t} but -A(eta_0) = {t2}; these are "
                               f"both tau and they disagree, so the grading is wrong")
        return t

    def __str__(self) -> str:
        return (f"{self.name}: CFK^- with {len(self.generators)} generators, "
                f"{len(self.vertical())} vertical + {len(self.horizontal())} horizontal "
                f"arrows, tau = {self.tau()}")


def _survivor(name, kind, generators, arrows) -> str:
    sources = Counter(a.source for a in arrows)
    targets = Counter(a.target for a in arrows)
    for g, n in (sources + targets).items():
        if n > 1 or (sources[g] and targets[g]):
            raise AlgebraError(
                f"{name}: the basis is not {kind}ly simplified -- {g!r} is an end of "
                f"{sources[g] + targets[g]} {kind} arrows, and a simplified basis pairs "
                f"generators up two at a time")
    left = [g for g in generators if g not in sources and g not in targets]
    if len(left) != 1:
        raise AlgebraError(
            f"{name}: the {kind} arrows leave {len(left)} generators unpaired "
            f"({', '.join(left) or 'none'}); a knot complex leaves exactly one")
    return left[0]


# ---------------------------------------------------------------- inferring the grading

def infer_alexander(c: Complex, span: int | None = None) -> dict[str, int]:
    """Recover the Alexander grading from the arrows alone, when it is determined.

    Three facts do it.  Horizontal arrows pin differences exactly (``A(y) = A(x) + k``).  The
    multiset of vertical lengths equals the multiset of horizontal lengths, by the symmetry of
    CFK^infinity under exchanging i and j -- so the unknown vertical lengths are a permutation
    of known numbers.  And the multiset of gradings is symmetric about 0, which fixes the
    remaining shifts absolutely.

    Raises rather than guesses if that leaves more than one answer.  An explicit grading
    always wins over this.
    """
    horizontal = [a for a in c.arrows if a.power > 0]
    vertical = [a for a in c.arrows if a.power == 0]
    if len(vertical) != len(horizontal):
        raise AlgebraError(
            f"{c.name}: {len(vertical)} vertical and {len(horizontal)} horizontal arrows. "
            f"Cannot infer the Alexander grading from an unbalanced complex -- give it "
            f"explicitly with an # alexander: line")

    lengths = sorted(a.power for a in horizontal)
    span = span or (sum(lengths) + len(c.generators) + 1)

    solutions = []
    for assignment in {p for p in permutations(lengths)}:
        base = _relative(c.generators, horizontal, zip(vertical, assignment))
        if base is None:
            continue
        solutions += _fix_shifts(c.generators, base, span)
        if len(solutions) > 1:
            break
    unique = {tuple(sorted(s.items())) for s in solutions}
    if not unique:
        raise AlgebraError(f"{c.name}: no Alexander grading fits these arrows; give one "
                           f"explicitly with an # alexander: line")
    if len(unique) > 1:
        raise AlgebraError(f"{c.name}: the arrows admit more than one Alexander grading; "
                           f"give the one you mean with an # alexander: line")
    return dict(unique.pop())


def _relative(generators, horizontal, verticals):
    """Offsets within each connected component, or None if the constraints clash."""
    offset = {}
    component = {}
    edges = defaultdict(list)
    for a in horizontal:
        edges[a.source].append((a.target, a.power))
        edges[a.target].append((a.source, -a.power))
    for a, length in verticals:
        edges[a.source].append((a.target, -length))
        edges[a.target].append((a.source, length))

    for root in generators:
        if root in offset:
            continue
        offset[root], component[root] = 0, root
        stack = [root]
        while stack:
            g = stack.pop()
            for h, delta in edges[g]:
                if h not in offset:
                    offset[h], component[h] = offset[g] + delta, root
                    stack.append(h)
                elif offset[h] != offset[g] + delta:
                    return None
    return offset, component


def _fix_shifts(generators, base, span):
    """Choose one shift per component so that the multiset of gradings negates to itself."""
    offset, component = base
    roots = sorted({component[g] for g in generators})
    if len(roots) > 4:
        raise AlgebraError("too many disconnected pieces to infer a grading; give it "
                           "explicitly with an # alexander: line")
    found = []
    for shifts in product(range(-span, span + 1), repeat=len(roots)):
        by_root = dict(zip(roots, shifts))
        grading = {g: offset[g] + by_root[component[g]] for g in generators}
        values = Counter(grading.values())
        if values == Counter({-a: n for a, n in values.items()}):
            found.append(grading)
            if len(found) > 1:
                return found
    return found


# ---------------------------------------------------------------- Levine Theorem 2.6

def cfd_from_cfk(cfk: CFK, name: str | None = None) -> CFD:
    """The type-D structure of the knot complement, from the knot complex.

    Levine, Theorem 2.6.  The iota_0 part is the CFK^- basis itself, 2n+1 generators; the
    iota_1 part is one chain of new generators per arrow, plus the unstable chain.

        vertical arrow xi_{2j-1} -> xi_{2j} of length k, contributing k generators:
            xi_{2j} -D123-> kappa_1 -D23-> ... -D23-> kappa_k <-D1- xi_{2j-1}

        horizontal arrow eta_{2j-1} -> eta_{2j} of length l, contributing l:
            eta_{2j-1} -D3-> lambda_1 -D23-> ... -D23-> lambda_l -D2-> eta_{2j}

        the unstable chain, s = 2|tau| generators:
            tau > 0:   eta_0 -D3->   mu_1 -D23-> ... -D23-> mu_s <-D1- xi_0
            tau == 0:  xi_0 -D12-> eta_0
            tau < 0:   xi_0 -D123-> mu_1 -D23-> ... -D23-> mu_s -D2-> eta_0

    For the unknot n = 0, so xi_0 and eta_0 are the same single generator and the tau = 0 case
    is a self-loop labelled rho_12 -- the only chord that runs iota_0 to iota_0.
    """
    xi_0, eta_0 = cfk.survivors()
    tau = cfk.tau()
    rows: list[tuple[str, str, str]] = []
    extra: list[str] = []

    def chain(prefix, head, head_chord, tail, tail_chord, length, reverse_tail):
        """``head -head_chord-> g_1 -rho_23-> ... -> g_length`` then the tail arrow."""
        new = [f"{prefix}_{p}" for p in range(1, length + 1)]
        extra.extend(new)
        rows.append((head, new[0], head_chord))
        rows.extend((new[p], new[p + 1], "rho_23") for p in range(length - 1))
        if reverse_tail:
            rows.append((tail, new[-1], tail_chord))
        else:
            rows.append((new[-1], tail, tail_chord))
        return new

    for j, arrow in enumerate(cfk.vertical(), start=1):
        chain(f"kappa_{j}", arrow.target, "rho_123", arrow.source, "rho_1",
              arrow.length, reverse_tail=True)
    for j, arrow in enumerate(cfk.horizontal(), start=1):
        chain(f"lambda_{j}", arrow.source, "rho_3", arrow.target, "rho_2",
              arrow.length, reverse_tail=False)

    if tau > 0:
        chain("mu", eta_0, "rho_3", xi_0, "rho_1", 2 * tau, reverse_tail=True)
    elif tau < 0:
        chain("mu", xi_0, "rho_123", eta_0, "rho_2", -2 * tau, reverse_tail=False)
    else:
        rows.append((xi_0, eta_0, "rho_12"))

    idempotent = {g: 0 for g in cfk.generators}
    idempotent.update({g: 1 for g in extra})
    d = CFD.build(name or cfk.name, rows, idempotent=idempotent)
    d.notes.update(tau=tau, xi_0=xi_0, eta_0=eta_0, source=cfk.name)
    return d
