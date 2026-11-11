"""H(r, s): the general (1,1) diagram, built in Chen form and then re-cut.

Two integers make one of these: ``r != 0`` and ``s > 0``.  Beta is a single closed curve
exactly when ``gcd(2|r| - 1, s + 1) = 1``.

THE CHEN FORM lives on the torus cut along one curve only -- the up-down one, ``mu`` -- so it
is an annulus, and every arc runs between its two boundary circles or turns back to the one it
came from.  Nothing crosses the left-right curve ``lambda`` at all, so the picture has no
generators on it yet.  Writing ``M = 2r + s + D`` for the number of points on each boundary,
with ``D`` explained below, the arcs are, for ``r > 0``:

    right rainbows   right(j) -- right(2r-1-j)          j = 0 .. r-1     z inside the innermost
    main strands     left(1+k) -- right(2r+k)           k = 0 .. s-1     slope 2r-1
    left rainbows    left(s+1+j) -- left(2r+s-j)        j = 0 .. r-1     w inside the innermost
    dependent        left(u) -- right(u-1)              u = 0, M-1, M-2, ..., M-D+1

The main region is everything but the last family: ``2r + s`` arcs using ``2r + s`` points a
side, leaving ``left(0)`` and ``right(2r+s)`` loose.  It is one path from the one to the other,
and the winding it picks up on the way is ``-sigma(r, s)``, computed by :func:`sigma` and
checked against the geometry by the tests.  The dependent arcs close that path up and cancel
the winding down to the ``+/-1`` a bordered diagram needs, which takes ``D = |sigma(r,s)|`` of
them; they are short strands of slope ``-1`` sitting either side of the seam.  For ``r < 0``
left and right are exchanged throughout.

THE RE-CUT is where the generators on ``lambda`` come from.  ``z`` sits inside the innermost
right rainbow, between points ``r-1`` and ``r``, and the fundamental domain is slid until
``z`` is at a corner -- so the new horizontal cut runs at exactly that height.  It meets the
picture in ``2r-1`` places: every one of the ``r`` right rainbows, since all of them arch over
that height, and ``r-1`` of the main strands, the ones that set off from the left above it.
Those meetings are new intersection points and they become the new generators.  Sliding does
not disturb the points on ``mu``; it only renumbers them, by ``r``.

Which is why this is done with real geometry rather than by counting.  How many crossings
there are can be read off, but *the order they come in along the cut* cannot -- that is a fact
about where the arcs actually run, and it is what fixes the diagram.  So the annulus is drawn,
the cut is a line across it, and the crossings are sorted by where they fall.

Finally the whole thing is turned a quarter turn, which carries ``z`` to the top left corner
and exchanges the roles of the two curves: the points on ``mu`` become the ``x`` generators
and the new ones on ``lambda`` become the ``y`` generators.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from math import gcd

from .diagram import Diagram


def sigma(r: int, s: int) -> int:
    """The winding the main region picks up, as a closed form.

    ``1 - sum_{j=1}^{2r+s-1} (-1)^floor(j(2r-1)/(2r+s))``.  The geometry is what says this is
    right; :func:`main_region_winding` computes the same number by walking the path, and a
    test holds the two together.
    """
    n = 2 * abs(r) + s
    return 1 - sum((-1) ** ((j * (2 * abs(r) - 1)) // n) for j in range(1, n))


def is_connected(r: int, s: int) -> bool:
    """Whether beta comes out as a single closed curve rather than several."""
    return gcd(2 * abs(r) - 1, s + 1) == 1


@dataclass
class Chen:
    """The Chen form: arcs on the annulus, before the horizontal cut is put back."""

    r: int
    s: int
    D: int
    M: int
    #: (left_or_right, slot, left_or_right, slot, family)
    arcs: list = field(default_factory=list)

    def counts(self) -> dict:
        out: dict = {}
        for _sa, _ia, _sb, _ib, family, _ha, _hb in self.arcs:
            out[family] = out.get(family, 0) + 1
        return out


def chen_form(r: int, s: int) -> Chen:
    """The arcs of H(r, s) on the annulus.

    Each arc carries the heights of its two ends in the covering, not modulo M, because a
    dependent arc steps one place *across the seam* and has to be drawn doing that rather than
    running the whole way down the picture.

    The dependent region takes one of two forms, which is what Fig. 15 (a) and (b) are.  When
    ``sigma`` is negative the main region has wound the wrong way and D = |sigma| strands
    sloping back by one put it right.  When ``sigma`` is positive those strands would have to
    slope the other way, and a strand cannot simply be turned round -- so the region gains a
    small rainbow at each end to turn the curve about, with sigma strands between them.  Fig.
    15 (b) is exactly that: the two little rainbows at the top corners.
    """
    if r == 0:
        raise ValueError("H(r, s): r must not be zero")
    if s <= 0:
        raise ValueError(f"H(r, s): s must be positive, got {s}")

    a, sg = abs(r), sigma(r, s)
    D = abs(sg) if sg < 0 else sg + 2
    M = 2 * a + s + D

    arcs = []
    def arc(sa, ia, sb, ib, family, ha=None, hb=None):
        arcs.append((sa, ia, sb, ib, family,
                     float(ia if ha is None else ha), float(ib if hb is None else hb)))

    for j in range(a):
        arc("right", j, "right", 2 * a - 1 - j, "rainbow-z")
    for k in range(s):
        arc("left", 1 + k, "right", 2 * a + k, "strand")
    for j in range(a):
        arc("left", s + 1 + j, "left", 2 * a + s - j, "rainbow-w")

    if sg < 0:                                       # Fig 15 (a): strands sloping back by one
        arc("left", 0, "right", M - 1, "dependent", 0, -1)
        for t in range(D - 1):
            arc("left", M - 1 - t, "right", M - 2 - t, "dependent")
    else:                                            # Fig 15 (b): turned round at both ends
        arc("right", 2 * a + s, "right", 2 * a + s + 1, "dependent-turn")
        for u in range(2 * a + s + 1, M - 1):
            arc("left", u, "right", u + 1, "dependent")
        arc("left", M - 1, "left", 0, "dependent-turn", M - 1, M)

    if r < 0:
        # Fig 16 is Fig 15 upside down: the rainbows around z drop to the bottom and the ones
        # around w rise to the top.  Heights mirror with the slots, covering and all.
        arcs = [(sa, M - 1 - ia, sb, M - 1 - ib, f, (M - 1) - ha, (M - 1) - hb)
                for sa, ia, sb, ib, f, ha, hb in arcs]
    return Chen(r=r, s=s, D=D, M=M, arcs=arcs)


def main_region_winding(r: int, s: int) -> int:
    """Walk the main region from one loose end to the other, adding up the winding."""
    form = chen_form(r, s)
    a = abs(r)
    at: dict = {}
    for sa, ia, sb, ib, family, _ha, _hb in form.arcs:
        if family.startswith("dependent"):
            continue
        at[(sa, ia)] = (sb, ib)
        at[(sb, ib)] = (sa, ia)

    near = "right" if r > 0 else "left"
    here, winding = (near, 0), 0
    while here in at:
        side, index = at[here]
        winding += 1 if side == "right" else -1
        here = ("left" if side == "right" else "right", index)
    return winding


# ------------------------------------------------------------------ the drawing

#: how far a rainbow bulges away from its own boundary, at its widest
BULGE = 0.25


def _shape(form: Chen, arc):
    """One arc as geometry on the annulus: ``x`` across, height down.

    A rainbow is a half ellipse standing on its own boundary; a strand is straight.  The
    heights come from the arc itself, so an arc that steps across the seam is drawn stepping
    across it.
    """
    sa, ia, sb, ib, family, ha, hb = arc
    if sa != sb:
        return {"kind": "strand", "family": family,
                "a": (0.0 if sa == "left" else 1.0, ha),
                "b": (0.0 if sb == "left" else 1.0, hb)}
    lo, hi = (ha, hb) if ha < hb else (hb, ha)
    scale = BULGE / max((2 * abs(form.r) - 1) / 2.0, 0.5)
    return {"kind": "rainbow", "family": family, "side": sa,
            "lo": lo, "hi": hi, "mid": (lo + hi) / 2.0, "radius": (hi - lo) / 2.0,
            "scale": scale}


def _meets(shape, height: float):
    """Where this arc meets the horizontal line at ``height``, or None.

    Every arc of a Chen form is shorter than the whole circle, so it meets a given line at
    most once, and each is cut into at most two pieces.
    """
    if shape["kind"] == "strand":
        (xa, ha), (xb, hb) = shape["a"], shape["b"]
        if not (min(ha, hb) < height < max(ha, hb)):
            return None
        return xa + (xb - xa) * (height - ha) / (hb - ha)
    lo, hi, mid, radius = shape["lo"], shape["hi"], shape["mid"], shape["radius"]
    if not lo < height < hi:
        return None
    out = shape["scale"] * math.sqrt(max(radius ** 2 - (height - mid) ** 2, 0.0))
    return out if shape["side"] == "left" else 1.0 - out


def cut_height(form: Chen) -> float:
    """The height of ``z``: inside the innermost rainbow around it.

    For ``r > 0`` that rainbow stands on points ``r-1`` and ``r`` near the top; for ``r < 0``
    the picture is upside down and it stands on their mirror images near the bottom, so the
    domain slides the other way -- up rather than down -- to put ``z`` at a corner.
    """
    a = abs(form.r)
    return a - 0.5 if form.r > 0 else form.M - a - 0.5


def recut(form: Chen) -> tuple:
    """Slide the domain so ``z`` is at a corner, and read off the diagram that results.

    Returns the diagram *before* the quarter turn, together with the crossings it found, so
    that the intermediate picture can be drawn and the count can be checked.
    """
    a, M = abs(form.r), form.M
    c = cut_height(form)
    shapes = [_shape(form, arc) for arc in form.arcs]

    # every crossing of the new cut, and where along it each one falls
    found = []
    for k, shape in enumerate(shapes):
        for band in (-1, 0, 1):
            x = _meets(shape, c + band * M)
            if x is not None:
                found.append({"arc": k, "x": x, "height": c + band * M})
    found.sort(key=lambda hit: hit["x"])
    for index, hit in enumerate(found):
        hit["index"] = index
    by_arc = {hit["arc"]: hit for hit in found}
    if len(by_arc) != len(found):
        raise ValueError("an arc met the cut twice, which a Chen form cannot do")

    first = int(math.ceil(c))                        # the point just below the new cut

    def mu(slot: int) -> int:
        """Points on mu keep their places and are only renumbered, from the cut down."""
        return (slot - first) % M

    diagram = Diagram(name=f"H({form.r},{form.s}) recut", x_count=len(found), y_count=M)
    for k, (sa, ia, sb, ib, family, ha, hb) in enumerate(form.arcs):
        hit = by_arc.get(k)
        if hit is None:
            diagram.add_arc(mu(ia), sa, mu(ib), sb, family)
            continue
        # the piece below the cut leaves through the top of its band, the piece above it
        # through the bottom of the one before
        for side, index, height in ((sa, ia, ha), (sb, ib, hb)):
            edge = "top" if height > hit["height"] else "bottom"
            diagram.add_arc(mu(index), side, hit["index"], edge, family)
    return diagram, found


def rotate_ccw(d: Diagram, name: str | None = None) -> Diagram:
    """A quarter turn anticlockwise: (x, y) -> (1-y, x).

    It carries ``z`` from the top right corner to the top left, and swaps what the two alpha
    curves are called: the points on ``mu`` become the ``x`` generators.
    """
    n = d.x_count
    def turn(e):
        if e.side == "bottom":  return ("right", n - 1 - e.index)
        if e.side == "top":     return ("left", n - 1 - e.index)
        if e.side == "left":    return ("bottom", e.index)
        return ("top", e.index)
    out = Diagram(name=name or f"{d.name} turned", x_count=d.y_count, y_count=n)
    for arc in d.arcs:
        (sa, ia), (sb, ib) = turn(arc.a), turn(arc.b)
        out.add_arc(ia, sa, ib, sb, arc.family)
    return out


def H(r: int, s: int) -> Diagram:
    """The bordered Heegaard diagram H(r, s), validated."""
    if not is_connected(r, s):
        raise ValueError(f"H({r},{s}): gcd(2|r|-1, s+1) = "
                         f"{gcd(2 * abs(r) - 1, s + 1)}, so beta is not one curve")
    form = chen_form(r, s)
    recut_diagram, crossings = recut(form)
    if len(crossings) != 2 * abs(r) - 1:
        raise ValueError(f"H({r},{s}): the cut met beta {len(crossings)} times, "
                         f"expected 2|r|-1 = {2 * abs(r) - 1}")
    out = rotate_ccw(recut_diagram, name=f"H({r},{s})")

    # Orient beta the way Q(i,m,n) does.  Which way round the curve is followed is decided by
    # which end of the first arc the walk starts from, and it shows up as the sign of every
    # disc's offset -- the same discs either way, but it is better that a diagram built here
    # and the same one built by hand agree to the letter.
    if out.intersection_number()[0] > 0:
        first = out.arcs[0]
        first.a, first.b = first.b, first.a

    inner = next(k for k, arc in enumerate(out.arcs)
                 if arc.family == "rainbow-w" and abs(arc.a.index - arc.b.index) == 1)
    out.set_basepoint("w", inner)
    out.notes = {"r": r, "s": s, "D": form.D, "sigma": sigma(r, s)}
    return out.validate()


# ------------------------------------------------------------------ drawing the annulus

def polyline(form: Chen, arc, samples: int = 40) -> list:
    """One arc as points ``(x, height)`` in the covering, running from its first end to its
    second, heights not yet wrapped back into the domain."""
    shape = _shape(form, arc)
    if shape["kind"] == "strand":
        (xa, ha), (xb, hb) = shape["a"], shape["b"]
        return [(xa + (xb - xa) * i / samples, ha + (hb - ha) * i / samples)
                for i in range(samples + 1)]
    lo, hi, mid, radius = shape["lo"], shape["hi"], shape["mid"], shape["radius"]
    out = []
    for i in range(samples + 1):
        h = lo + (hi - lo) * i / samples
        bulge = shape["scale"] * math.sqrt(max(radius ** 2 - (h - mid) ** 2, 0.0))
        out.append((bulge if shape["side"] == "left" else 1.0 - bulge, h))
    if arc[5] > arc[6]:
        out.reverse()
    return out


def wrapped(points, M: int) -> list:
    """Split a run of points where it leaves the domain, and slide each piece back in.

    The band is decided per segment, from its middle, so that a point sitting exactly on a
    boundary stays with the piece it belongs to instead of starting a new one.
    """
    if len(points) < 2:
        return [points] if points else []
    pieces, current, shift = [], [points[0]], None
    for (xa, ha), (xb, hb) in zip(points, points[1:]):
        band = math.floor((ha + hb) / 2.0 / M)
        if shift is None:
            shift = band
            current = [(xa, ha - shift * M)]
        if band != shift:
            pieces.append(current)
            shift = band
            current = [(xa, ha - shift * M)]
        current.append((xb, hb - shift * M))
    pieces.append(current)
    return pieces


def basepoints(form: Chen) -> dict:
    """Where z and w sit: each inside the innermost rainbow of its own family."""
    out = {}
    for name, family in (("z", "rainbow-z"), ("w", "rainbow-w")):
        inner = min((arc for arc in form.arcs if arc[4] == family),
                    key=lambda arc: abs(arc[6] - arc[5]), default=None)
        if inner is None:
            continue
        shape = _shape(form, inner)
        h = shape["mid"]
        edge = 0.0 if shape["side"] == "left" else 1.0
        apex = _meets(shape, h + 1e-9)
        out[name] = ((edge + apex) / 2.0 if apex is not None else edge, h % form.M)
    return out
