"""Bordered Heegaard diagrams on the torus, as combinatorics.

The fundamental domain is a rectangle whose horizontal edges are glued to each other and
whose vertical edges are glued to each other, so its boundary carries two alpha curves:

    alpha_x   the horizontal one   (bottom edge == top edge)
    alpha_y   the vertical one     (left edge == right edge)

Beta is drawn inside as a family of arcs.  Every arc endpoint is an intersection of beta with
an alpha curve -- a generator: ``x_j`` on ``alpha_x``, ``y_j`` on ``alpha_y``.

Index ``j`` names one point of the torus but TWO slots on the rectangle's boundary: ``x_j``
on the bottom and ``x_j`` on the top.  Beta passes through the point once, so it occupies
each slot exactly once, and the two slots are the two germs of beta there.  That is the whole
bookkeeping rule.

Nothing here is drawn or measured.  A diagram is its arcs; where they are put on a page is a
rendering decision made elsewhere, and the solver never needs it.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Iterable

SIDES = ("bottom", "right", "top", "left")
#: which alpha curve each side's points live on
CURVE_OF_SIDE = {"bottom": "x", "top": "x", "left": "y", "right": "y"}
#: the side a point is glued to under the torus identification
GLUED_SIDE = {"bottom": "top", "top": "bottom", "left": "right", "right": "left"}


@dataclass(frozen=True)
class Endpoint:
    """One end of an arc: the edge it sits on, and which generator along that edge."""

    side: str
    index: int

    def __post_init__(self) -> None:
        if self.side not in SIDES:
            raise ValueError(f"{self.side!r} is not a side; expected one of {SIDES}")
        if not isinstance(self.index, int) or isinstance(self.index, bool) or self.index < 0:
            raise ValueError(f"{self.index!r} is not a generator index")

    @property
    def curve(self) -> str:
        return CURVE_OF_SIDE[self.side]

    @property
    def name(self) -> str:
        return f"{self.curve}_{self.index}"

    @property
    def glued(self) -> "Endpoint":
        """The same point of the torus, seen from the opposite edge."""
        return Endpoint(GLUED_SIDE[self.side], self.index)

    def __str__(self) -> str:
        return f"{self.side}:{self.index}"


@dataclass
class Arc:
    a: Endpoint
    b: Endpoint
    family: str = ""

    def ends(self) -> tuple[Endpoint, Endpoint]:
        return (self.a, self.b)

    def other(self, end: Endpoint) -> Endpoint:
        if end == self.a:
            return self.b
        if end == self.b:
            return self.a
        raise KeyError(f"{end} is not an end of this arc")


class DiagramError(Exception):
    """Raised when a diagram cannot be what it claims to be."""


@dataclass
class Diagram:
    """A bordered Heegaard diagram, built one arc at a time.

    >>> d = Diagram("example", x_count=2, y_count=1)
    >>> d.add_arc(0, "bottom", 1, "top")           # doctest: +ELLIPSIS
    Arc(...)
    """

    name: str = "diagram"
    x_count: int = 0
    y_count: int = 0
    arcs: list[Arc] = field(default_factory=list)
    basepoints: dict[str, int] = field(default_factory=dict)
    notes: dict = field(default_factory=dict)

    # ---------------------------------------------------------------- building

    def add_arc(self, start: int, start_edge: str, end: int, end_edge: str,
                family: str = "") -> Arc:
        """Join generator ``start`` on ``start_edge`` to generator ``end`` on ``end_edge``.

        The edge matters as well as the index: bottom and top are the same alpha curve but
        different sides of the domain, and an arc has to say which one it meets.
        """
        arc = Arc(Endpoint(start_edge, start), Endpoint(end_edge, end), family)
        self.arcs.append(arc)
        self.x_count = max(self.x_count,
                           *(e.index + 1 for e in arc.ends() if e.curve == "x"), 0)
        self.y_count = max(self.y_count,
                           *(e.index + 1 for e in arc.ends() if e.curve == "y"), 0)
        return arc

    def set_basepoint(self, name: str, inside_arc: int) -> None:
        """Shut a basepoint inside an arc -- the region that arc cuts off on its own."""
        if not 0 <= inside_arc < len(self.arcs):
            raise ValueError(f"no arc {inside_arc}; the diagram has {len(self.arcs)}")
        self.basepoints[name] = inside_arc

    @property
    def max_x(self) -> int:
        return self.x_count - 1

    @property
    def max_y(self) -> int:
        return self.y_count - 1

    def generators(self) -> list[str]:
        return ([f"x_{j}" for j in range(self.x_count)]
                + [f"y_{j}" for j in range(self.y_count)])

    # ---------------------------------------------------------------- checking

    def slot_problems(self) -> list[str]:
        """Every boundary slot must be used exactly once."""
        used = Counter(str(e) for arc in self.arcs for e in arc.ends())
        problems = []
        for slot, count in sorted(used.items()):
            if count > 1:
                problems.append(f"slot {slot} is used by {count} arc ends, expected 1")
        for side in SIDES:
            limit = self.x_count if CURVE_OF_SIDE[side] == "x" else self.y_count
            for k in range(limit):
                if f"{side}:{k}" not in used:
                    problems.append(f"nothing meets the {side} edge at {side}:{k}")
        expected = self.x_count + self.y_count
        if len(self.arcs) != expected:
            problems.append(f"expected {expected} arcs, got {len(self.arcs)}")
        return problems

    def boundary_slot(self, end: Endpoint) -> int:
        """Position of a slot going counter-clockwise from the bottom-left corner."""
        n, m = self.x_count, self.y_count
        if end.side == "bottom":
            return end.index
        if end.side == "right":
            return n + (self.max_y - end.index)
        if end.side == "top":
            return n + m + (self.max_x - end.index)
        return 2 * n + m + end.index

    def chords(self) -> list[tuple[int, int]]:
        out = []
        for arc in self.arcs:
            p, q = (self.boundary_slot(arc.a), self.boundary_slot(arc.b))
            out.append((p, q) if p < q else (q, p))
        return out

    def crossing_problems(self) -> list[str]:
        """Beta is embedded, so its chord diagram must be non-crossing."""
        chords = self.chords()
        problems = []
        for u in range(len(chords)):
            a, b = chords[u]
            for v in range(u + 1, len(chords)):
                c, d = chords[v]
                if (a < c < b) != (a < d < b):
                    problems.append(
                        f"arcs {u} and {v} must cross: chords ({a},{b}) and ({c},{d}) interleave")
        return problems

    def components(self) -> list[list[int]]:
        """Trace beta through the gluings; one list of arc indices per closed component."""
        at: dict[str, tuple[int, Endpoint]] = {}
        for i, arc in enumerate(self.arcs):
            at[str(arc.a)] = (i, arc.b)
            at[str(arc.b)] = (i, arc.a)

        seen: set[int] = set()
        out: list[list[int]] = []
        for start in range(len(self.arcs)):
            if start in seen:
                continue
            component: list[int] = []
            end = self.arcs[start].a
            while True:
                index, far = at[str(end)]
                if index in seen:
                    break
                seen.add(index)
                component.append(index)
                end = far.glued
            out.append(component)
        return out

    def intersection_number(self) -> tuple[int, int]:
        """The homology class of beta, as (crossings of alpha_y, crossings of alpha_x).

        Following beta, every time it leaves by the right edge it has gone once round the
        torus in the +x direction and re-entered on the left, so it has crossed alpha_y with
        sign +1; leaving by the left is -1.  Likewise top and bottom for alpha_x.  For a
        bordered diagram of this shape beta must run once round one way and not at all the
        other: (+/-1, 0).
        """
        left_right = top_bottom = 0
        for component in self.components():
            at: dict[str, tuple[int, Endpoint]] = {}
            for i, arc in enumerate(self.arcs):
                at[str(arc.a)] = (i, arc.b)
                at[str(arc.b)] = (i, arc.a)
            end = self.arcs[component[0]].a
            for _ in component:
                _, far = at[str(end)]
                if far.side == "right":
                    left_right += 1
                elif far.side == "left":
                    left_right -= 1
                elif far.side == "top":
                    top_bottom += 1
                else:
                    top_bottom -= 1
                end = far.glued
        return (left_right, top_bottom)

    def problems(self, *, require_connected: bool = True,
                 require_primitive: bool = True) -> list[str]:
        """Everything wrong with this diagram, in the order worth hearing it."""
        found = self.slot_problems()
        if found:
            return found                      # the rest assumes the slots line up
        found += self.crossing_problems()

        components = self.components()
        if require_connected and len(components) != 1:
            found.append(
                f"beta has {len(components)} components "
                f"(sizes {sorted(len(c) for c in components)}), expected one closed curve")

        if require_primitive:
            lr, tb = self.intersection_number()
            if (abs(lr), tb) != (1, 0):
                found.append(
                    f"beta meets (alpha_y, alpha_x) with multiplicity ({lr}, {tb}); "
                    "expected (+/-1, 0)")
        return found

    def validate(self, **kwargs) -> "Diagram":
        """Raise unless the diagram is legal.  Returns self, so it chains."""
        found = self.problems(**kwargs)
        if found:
            raise DiagramError(f"{self.name} is not a legal diagram:\n  "
                               + "\n  ".join(found))
        return self

    def __str__(self) -> str:
        return (f"{self.name}: {self.x_count} x + {self.y_count} y generators, "
                f"{len(self.arcs)} arcs")
