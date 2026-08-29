"""Type-A and type-D structures over the torus algebra, as labelled graphs.

Both are pure data.  A CFA^- is a graph whose edges carry a power of U and a SEQUENCE of Reeb
chords; a CFDhat is a graph whose edges carry one Reeb chord.  We do not check the
A_infinity relations and we do not check that a type-D structure really is one -- see the
TODO in CLAUDE.md.  What we do check is the bookkeeping that the box tensor needs: that every
chord sequence composes in the idempotents, and that its ends agree with the idempotents of
the generators it runs between.

IDEMPOTENTS ARE INFERRED, NOT DECLARED.  Every chord pins the idempotent at each of its ends
(rho_1 runs iota_0 -> iota_1, and so on -- see ``torus``), and an arrow with no chord forces
its two ends to agree.  So the arrows alone determine the splitting, except for a generator
that no arrow touches.  That keeps this module from having to know anything about where the
CFA came from: nothing here has heard of a Heegaard diagram, or of the ``x_``/``y_`` naming
that one particular producer of these files happens to use.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from . import torus
from .chain import AlgebraError


@dataclass(frozen=True)
class Operation:
    """One A_infinity operation: ``m_{n+1}(source, *word) = U^power . target``.

    An empty word is ``m_1``, the plain differential of the type-A structure.  The word is a
    sequence and not a product: ``(rho_1, rho_2)`` and ``(rho_12,)`` are different operations
    and pair with different paths in a type-D structure.
    """

    source: str
    target: str
    power: int
    word: tuple[str, ...] = ()

    def spelled(self) -> str:
        return torus.write_word(self.word)


@dataclass(frozen=True)
class DArrow:
    """One term of ``delta^1``: ``delta^1(source) contains rho ⊗ target``.

    ``chord`` may be None, meaning an idempotent coefficient.  Nothing in this project
    produces one; the box tensor refuses them rather than pretending.
    """

    source: str
    target: str
    chord: str | None

    def spelled(self) -> str:
        return torus.write_word([self.chord] if self.chord else [])


# ---------------------------------------------------------------- inference

def _infer_idempotents(name, generators, same, pins, hint=None):
    """Solve the idempotent constraints.

    ``same`` is a list of pairs that must agree, ``pins`` a list of (generator, value).
    ``hint`` is consulted only for a generator that nothing constrains.
    """
    parent = {g: g for g in generators}

    def find(g):
        while parent[g] != g:
            parent[g] = parent[parent[g]]
            g = parent[g]
        return g

    for a, b in same:
        parent[find(a)] = find(b)

    value: dict[str, int] = {}
    for g, i in pins:
        root = find(g)
        if value.setdefault(root, i) != i:
            raise AlgebraError(
                f"{name}: the arrows disagree about which idempotent {g!r} is in -- it is "
                f"forced into both iota_0 and iota_1, so the chord labels cannot all be right")

    out = {}
    unconstrained = []
    for g in generators:
        root = find(g)
        if root in value:
            out[g] = value[root]
        elif hint and hint(g) is not None:
            out[g] = hint(g)
        else:
            unconstrained.append(g)
    if unconstrained:
        raise AlgebraError(
            f"{name}: no arrow touches {', '.join(sorted(unconstrained)[:5])}"
            f"{' ...' if len(unconstrained) > 5 else ''}, so which idempotent they are in is "
            f"not determined; give an # iota0:/# iota1: line in the file")
    return out


def name_hint(generator: str):
    """The last-resort guess: ``y_*`` is iota_0 and ``x_*`` is iota_1.

    That is the convention of the Heegaard diagrams upstream, where a generator on alpha_y is
    in iota_0 and one on alpha_x is in iota_1 -- forced, not chosen, since it is the only
    assignment under which every disc's chord word composes.  It is a hint here and nothing
    more: a file whose arrows say otherwise wins.
    """
    if generator.startswith("y_"):
        return 0
    if generator.startswith("x_"):
        return 1
    return None


# ---------------------------------------------------------------- type A

@dataclass
class CFA:
    """A type-A structure over A(T^2), with coefficients in F_2[U]."""

    name: str = "cfa"
    generators: list[str] = field(default_factory=list)
    idempotent: dict[str, int] = field(default_factory=dict)
    operations: list[Operation] = field(default_factory=list)
    notes: dict = field(default_factory=dict)

    @classmethod
    def build(cls, name, rows, idempotent=None, hint=name_hint) -> "CFA":
        """From ``rows = [(source, target, power, word), ...]``.

        Rows are reduced mod 2: two operations agreeing in all four fields cancel.
        """
        ops, cancelled = _reduce_ops(rows)
        generators = _ordered({g for op in ops for g in (op.source, op.target)}
                              | set(idempotent or ()))
        a = cls(name=name, generators=generators, operations=ops)
        a.notes["cancelled"] = cancelled
        a.idempotent = dict(idempotent) if idempotent else a._infer(hint)
        return a.validate()

    def _infer(self, hint):
        same, pins = [], []
        for op in self.operations:
            ends = torus.word_endpoints(op.word)
            if ends is None:
                same.append((op.source, op.target))
            else:
                pins += [(op.source, ends[0]), (op.target, ends[1])]
        return _infer_idempotents(self.name, self.generators, same, pins, hint)

    def validate(self) -> "CFA":
        known = set(self.generators)
        for op in self.operations:
            for end in (op.source, op.target):
                if end not in known:
                    raise AlgebraError(f"{self.name}: {end!r} is not a generator")
            if op.power < 0:
                raise AlgebraError(f"{self.name}: U^{op.power} is not a coefficient")
            if not torus.composable(op.word):
                raise AlgebraError(
                    f"{self.name}: the word {op.spelled()} on {op.source} -> {op.target} does "
                    f"not compose -- some chord ends where the next one does not begin")
            ends = torus.word_endpoints(op.word)
            want = (self.idempotent[op.source], self.idempotent[op.target])
            got = ends if ends is not None else want if want[0] == want[1] else None
            if got != want:
                raise AlgebraError(
                    f"{self.name}: {op.source} -> {op.target} labelled "
                    f"{op.spelled() or 'no chords'} runs between idempotents {got}, but its "
                    f"generators are in {want}")
        return self

    def in_idempotent(self, which: int) -> list[str]:
        return [g for g in self.generators if self.idempotent[g] == which]

    def by_source(self) -> dict[str, list[Operation]]:
        out = defaultdict(list)
        for op in self.operations:
            out[op.source].append(op)
        return out

    def max_word_length(self) -> int:
        return max((len(op.word) for op in self.operations), default=0)

    def __str__(self) -> str:
        n0, n1 = len(self.in_idempotent(0)), len(self.in_idempotent(1))
        return (f"{self.name}: CFA^- with {n0} + {n1} generators, {len(self.operations)} "
                f"operations, words up to length {self.max_word_length()}")


def _reduce_ops(rows):
    parity: dict[Operation, int] = defaultdict(int)
    for source, target, power, word in rows:
        parity[Operation(source, target, int(power), tuple(word))] ^= 1
    kept = sorted((op for op, odd in parity.items() if odd),
                  key=lambda op: (_key(op.source), _key(op.target), op.power, op.spelled()))
    return kept, sum(1 for op, odd in parity.items() if not odd)


def _key(name: str):
    """Sort ``x_2`` before ``x_10``, and leave anything else alphabetical."""
    head, sep, tail = name.rpartition("_")
    return (head, int(tail)) if sep and tail.isdigit() else (name, -1)


def _ordered(names) -> list[str]:
    return sorted(names, key=_key)


# ---------------------------------------------------------------- type D

@dataclass
class CFD:
    """A type-D structure over A(T^2)."""

    name: str = "cfd"
    generators: list[str] = field(default_factory=list)
    idempotent: dict[str, int] = field(default_factory=dict)
    arrows: list[DArrow] = field(default_factory=list)
    notes: dict = field(default_factory=dict)

    @classmethod
    def build(cls, name, rows, idempotent=None, hint=name_hint) -> "CFD":
        arrows, cancelled = _reduce_arrows(rows)
        generators = _ordered({g for a in arrows for g in (a.source, a.target)}
                              | set(idempotent or ()))
        d = cls(name=name, generators=generators, arrows=arrows)
        d.notes["cancelled"] = cancelled
        d.idempotent = dict(idempotent) if idempotent else d._infer(hint)
        return d.validate()

    def _infer(self, hint):
        same, pins = [], []
        for a in self.arrows:
            if a.chord is None:
                same.append((a.source, a.target))
            else:
                pins += [(a.source, torus.left(a.chord)), (a.target, torus.right(a.chord))]
        return _infer_idempotents(self.name, self.generators, same, pins, hint)

    def validate(self) -> "CFD":
        known = set(self.generators)
        for a in self.arrows:
            for end in (a.source, a.target):
                if end not in known:
                    raise AlgebraError(f"{self.name}: {end!r} is not a generator")
            want = (self.idempotent[a.source], self.idempotent[a.target])
            got = ((torus.left(a.chord), torus.right(a.chord)) if a.chord
                   else want if want[0] == want[1] else None)
            if got != want:
                raise AlgebraError(
                    f"{self.name}: {a.source} -> {a.target} labelled "
                    f"{a.spelled() or 'the identity'} runs between idempotents {got}, but its "
                    f"generators are in {want}")
        return self

    def d_squared(self) -> list[tuple[str, str, str]]:
        """The terms of the type-D relation that fail to cancel.  Empty is what we want.

        For a reduced structure the relation is that for every pair of generators the sum of
        the products ``a . b`` over two-step paths vanishes in the algebra.  Products that are
        zero in A(T^2) drop out on their own -- which, for the chains Levine's theorem builds,
        is every single one of them.
        """
        parity: dict[tuple[str, str, str], int] = defaultdict(int)
        for first in self.arrows:
            for second in self.arrows:
                if second.source != first.target:
                    continue
                if first.chord is None or second.chord is None:
                    raise AlgebraError(f"{self.name}: an idempotent coefficient; this check "
                                       f"only knows how to read a reduced structure")
                product = torus.multiply(first.chord, second.chord)
                if product is not None:
                    parity[(first.source, second.target, product)] ^= 1
        return sorted(k for k, odd in parity.items() if odd)

    def require_type_d(self) -> "CFD":
        bad = self.d_squared()
        if bad:
            shown = ", ".join(f"{s} -{c}-> {t}" for s, t, c in bad[:4])
            raise AlgebraError(f"{self.name}: the type-D relation fails, {len(bad)} terms "
                               f"survive ({shown}{', ...' if len(bad) > 4 else ''})")
        return self

    def in_idempotent(self, which: int) -> list[str]:
        return [g for g in self.generators if self.idempotent[g] == which]

    def is_reduced(self) -> bool:
        """No arrow has an idempotent coefficient."""
        return all(a.chord is not None for a in self.arrows)

    def out_by_chord(self) -> dict[tuple[str, str | None], list[str]]:
        out = defaultdict(list)
        for a in self.arrows:
            out[(a.source, a.chord)].append(a.target)
        return out

    def paths(self, start: str, word) -> list[str]:
        """Every path out of ``start`` whose chords spell ``word``, as its list of endpoints.

        With multiplicity, and in particular ``paths(g, ()) == [g]`` -- the empty path, which
        is what pairs with the type-A differential ``m_1``.
        """
        table = self._table if self._table is not None else self.out_by_chord()
        ends = [start]
        for chord in word:
            ends = [t for g in ends for t in table[(g, chord)]]
            if not ends:
                return []
        return ends

    _table: dict | None = field(default=None, repr=False, compare=False)

    def index(self) -> "CFD":
        """Cache the adjacency, for a box tensor that will ask many times."""
        self._table = self.out_by_chord()
        return self

    def __str__(self) -> str:
        n0, n1 = len(self.in_idempotent(0)), len(self.in_idempotent(1))
        return f"{self.name}: CFDhat with {n0} + {n1} generators, {len(self.arrows)} arrows"


def _reduce_arrows(rows):
    parity: dict[DArrow, int] = defaultdict(int)
    for source, target, chord in rows:
        parity[DArrow(source, target, chord or None)] ^= 1
    kept = sorted((a for a, odd in parity.items() if odd),
                  key=lambda a: (_key(a.source), _key(a.target), a.spelled()))
    return kept, sum(1 for a, odd in parity.items() if not odd)
