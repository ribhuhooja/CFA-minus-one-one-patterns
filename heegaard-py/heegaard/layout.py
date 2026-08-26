"""Putting a diagram on the page, without assuming anything about its shape.

The solver needs coordinates only for the last step -- deciding which side of beta a basepoint
falls on -- and any embedding will do, because two embeddings of the same combinatorics are
isotopic and give the same answer.  That freedom is worth spending on a routing that can also
be looked at, since the same coordinates are what gets drawn.

A valid diagram's arcs form a NON-CROSSING chord diagram on the boundary of the domain (that
is what ``crossing_problems`` checks).  Nesting therefore gives a routing for free: an arc
whose chord is (a, b) travels parallel to the boundary along the stretch from a to b, at a
depth set by how many arcs are nested inside it.  Deeper arcs enclose shallower ones and never
touch them.  Straight lines are not assumed anywhere.

That is what ``route`` does.  ``route_radial`` is the older one: straight chords in a disc,
carried back to the square radially.  It is correct and it is a genuinely independent
construction, which is why it is kept -- a test pins the two to the same disc lists -- but it
draws badly for reasons worth recording, because both are properties of that radial map and
not of the sampling.  Relative radius is preserved, so an arc between two nearby generators
stays jammed against the boundary; and the map creases along the ray to each corner of the
square, so an arc whose endpoints are nearly antipodal passes close to the centre, crosses
several of those rays in quick succession, and picks up a cluster of kinks in the middle of
the picture.  Neither goes away with more samples.

The domain is the unit square, so a copy of it is a unit cell of the grid the solver works on.
Generator k of a count of N sits at (k + 1/2)/N along its edge, which leaves the same half-gap
at both ends and so spaces evenly across the gluing seam.
"""

from __future__ import annotations

import math

from dataclasses import dataclass

from .diagram import CURVE_OF_SIDE, Diagram, Endpoint


def position(diagram: Diagram, end: Endpoint) -> tuple[float, float]:
    """Where a generator sits on the boundary of the unit square, y upward."""
    count = diagram.x_count if end.curve == "x" else diagram.y_count
    along = (end.index + 0.5) / count
    if end.side == "bottom":
        return (along, 0.0)
    if end.side == "top":
        return (along, 1.0)
    if end.side == "left":
        return (0.0, 1.0 - along)
    return (1.0, 1.0 - along)


def _perimeter(diagram: Diagram, end: Endpoint) -> float:
    """Distance round the boundary from the bottom-left corner, anticlockwise, out of 4."""
    x, y = position(diagram, end)
    if end.side == "bottom":
        return x
    if end.side == "right":
        return 1.0 + y
    if end.side == "top":
        return 2.0 + (1.0 - x)
    return 3.0 + (1.0 - y)


def _boundary_at(t: float) -> tuple[float, float]:
    """The point a perimeter parameter t (out of 4) picks out on the unit square."""
    t = t % 4.0
    if t < 1.0:
        return (t, 0.0)
    if t < 2.0:
        return (1.0, t - 1.0)
    if t < 3.0:
        return (3.0 - t, 1.0)
    return (0.0, 4.0 - t)


OPPOSITE = {"bottom": "top", "top": "bottom", "left": "right", "right": "left"}
#: the corner two adjacent edges share
CORNER = {frozenset(("bottom", "left")): (0.0, 0.0),
          frozenset(("bottom", "right")): (1.0, 0.0),
          frozenset(("top", "left")): (0.0, 1.0),
          frozenset(("top", "right")): (1.0, 1.0)}
#: the direction into the domain from each edge
INWARD = {"bottom": (0.0, 1.0), "top": (0.0, -1.0),
          "left": (1.0, 0.0), "right": (-1.0, 0.0)}


@dataclass(frozen=True)
class Stroke:
    """One arc of beta as a single piece of geometry: a segment, or an elliptical arc.

    ``kind`` is ``"line"`` or ``"arc"``.  An arc is always a quarter or a half of an
    axis-aligned ellipse, so the centre, the two semi-axes and the angle it sweeps say
    everything about it, and it goes out as one SVG ``A`` command.  Nothing here is sampled.

    The sweep is stored rather than recovered from the endpoints, because the endpoints do not
    determine it: two generators on one edge are joined by two semicircles, one of which lies
    outside the domain entirely, and which one is wanted depends on the edge.  So it is
    decided once, here.
    """

    kind: str
    a: tuple
    b: tuple
    control: tuple = (0.0, 0.0)

    def at(self, f: float) -> tuple:
        """A point a fraction ``f`` along, for sampling and for checking."""
        if self.kind == "line":
            return (self.a[0] + (self.b[0] - self.a[0]) * f,
                    self.a[1] + (self.b[1] - self.a[1]) * f)
        g = 1.0 - f
        return (g * g * self.a[0] + 2 * g * f * self.control[0] + f * f * self.b[0],
                g * g * self.a[1] + 2 * g * f * self.control[1] + f * f * self.b[1])

    def points(self, samples: int = 12) -> list:
        if self.kind == "line":
            return [self.a, self.b]
        out = [self.at(i / samples) for i in range(samples + 1)]
        out[0], out[-1] = self.a, self.b
        return out


def _angle(point, centre, rx, ry) -> float:
    return math.atan2((point[1] - centre[1]) / ry, (point[0] - centre[0]) / rx)


def nesting(diagram: Diagram):
    """Where to cut the boundary open, and how deep each arc has to bulge.

    An arc has two ways round between its generators and the two look nothing alike, so the
    choice is made once by cutting the boundary at a single point no arc may straddle -- the
    cut with the least total arc length, which is the compact drawing.  Depth then follows:
    an arc bulging past everything nested inside it has to be one step further than the
    tallest of them.
    """
    n = 2 * (diagram.x_count + diagram.y_count)
    slots = [(diagram.boundary_slot(arc.a), diagram.boundary_slot(arc.b))
             for arc in diagram.arcs]

    def spans(cut):
        return [(min((p - cut) % n, (q - cut) % n), max((p - cut) % n, (q - cut) % n))
                for p, q in slots]

    cut = min(range(n), key=lambda c: sum(v - u for u, v in spans(c)))
    intervals = spans(cut)

    height = [0] * len(intervals)
    for k in sorted(range(len(intervals)), key=lambda k: intervals[k][1] - intervals[k][0]):
        u, v = intervals[k]
        height[k] = 1 + max((height[j] for j, (a, b) in enumerate(intervals)
                             if j != k and u < a and b < v), default=0)
    return cut, intervals, height


def _ray_hit(origin, direction, path, cap: float) -> float:
    """How far a ray from ``origin`` travels before meeting ``path``.  ``cap`` if it misses."""
    ox, oy = origin
    dx, dy = direction
    best = cap
    for (ax, ay), (bx, by) in zip(path, path[1:]):
        ex, ey = bx - ax, by - ay
        denominator = dx * ey - dy * ex
        if abs(denominator) < 1e-12:
            continue
        t = ((ax - ox) * ey - (ay - oy) * ex) / denominator
        u = ((ax - ox) * dy - (ay - oy) * dx) / denominator
        if 1e-9 < t < best and -1e-9 <= u <= 1 + 1e-9:
            best = t
    return best


def strokes(diagram: Diagram) -> list:
    """Every arc of beta as one line or one quadratic curve -- three points, nothing sampled.

    An arc bulges away from the stretch of boundary it spans: a rainbow arches up off its own
    edge, an arc joining two edges arches away from the corner between them, and one joining
    *opposite* edges has a whole side behind it, so it is drawn as the straight strand across
    the domain that it is.

    How far it bulges is the one free number, and it is measured against the arc that contains
    it rather than taken from a table.  Two earlier rules both failed, and for the same
    reason.  A shape fixed by its endpoints -- the semicircle standing on its two generators,
    the ellipse centred on the corner through them -- has nothing left to push it clear of
    what it holds, and a rainbow goes straight through the flattened arc above it.  Ranking
    the bulge by nesting height fails too, because the straight strands do not bulge at all:
    an arc nested inside one is ranked below it and still swings out past it.

    So each arc looks at its parent, casts a ray along the way it wants to bulge, and takes a
    share of the distance to it.  Outermost first, so the parent is always already drawn.  A
    straight parent gives its children the chord itself to stay behind, which is exactly the
    constraint the ranking could not express.

    The share is ``h / (h + 1)`` of the gap, where ``h`` counts the levels of nesting still to
    fit inside this arc.  That spaces a stack evenly: a leaf takes half the room to its
    parent, an arc with one thing inside it takes two thirds and leaves that thing the same
    gap again.  A fixed fraction would instead halve the space at every level, and the
    innermost rainbows -- the ones around ``w``, which are the point of the picture -- would
    be squashed flat against the edge.
    """
    cut, intervals, height = nesting(diagram)
    n = 2 * (diagram.x_count + diagram.y_count)

    parent = [None] * len(intervals)
    for k, (u, v) in enumerate(intervals):
        best = None
        for j, (a, b) in enumerate(intervals):
            if j != k and a < u and v < b and (best is None or b - a < intervals[best][1] - intervals[best][0]):
                best = j
        parent[k] = best

    out: list = [None] * len(intervals)
    drawn: list = [None] * len(intervals)
    for k in sorted(range(len(intervals)), key=lambda k: -(intervals[k][1] - intervals[k][0])):
        arc = diagram.arcs[k]
        pa, pb = position(diagram, arc.a), position(diagram, arc.b)
        if OPPOSITE[arc.a.side] == arc.b.side:
            out[k] = Stroke("line", pa, pb)
            drawn[k] = [pa, pb]
            continue

        # the stretch of boundary this arc spans runs forward from whichever end the cut puts
        # first, and the arc arches away from the middle of that stretch
        forward = (((diagram.boundary_slot(arc.a) - cut) % n)
                   < ((diagram.boundary_slot(arc.b) - cut) % n))
        near, far = (arc.a, arc.b) if forward else (arc.b, arc.a)
        t0 = _perimeter(diagram, near)
        behind = _boundary_at(t0 + ((_perimeter(diagram, far) - t0) % 4.0) / 2.0)

        mid = ((pa[0] + pb[0]) / 2.0, (pa[1] + pb[1]) / 2.0)
        dx, dy = mid[0] - behind[0], mid[1] - behind[1]
        reach = math.hypot(dx, dy)
        if reach < 1e-9:                            # the chord sits on the stretch it spans
            dx, dy = INWARD[near.side]
            reach = 1.0
        dx, dy = dx / reach, dy / reach

        above = parent[k]
        limit = min(0.9 if above is None else _ray_hit(mid, (dx, dy), drawn[above], 0.9), 0.9)
        lift = limit * height[k] / (height[k] + 1.0)
        out[k] = Stroke("curve", pa, pb, (mid[0] + lift * dx, mid[1] + lift * dy))
        drawn[k] = out[k].points(10)
    return out


def _box(path):
    xs = [q[0] for q in path]
    ys = [q[1] for q in path]
    return (min(xs), min(ys), max(xs), max(ys))


def route(diagram: Diagram, samples: int = 12) -> list[list[tuple[float, float]]]:
    """A polyline per arc, all inside the unit square and pairwise disjoint.

    These are ``strokes`` sampled, and they exist only because the solver wants polygons; the
    drawing uses the strokes themselves and samples nothing.  Sampling is what an embedding
    check needs too, so the strokes are verified here rather than argued about: each of the
    three shapes nests correctly against others of its own kind, but a rainbow and a corner
    and a straight strand are three different families, and whether they miss each other
    depends on the diagram.  If any pair meets, the whole diagram falls back to
    ``route_radial``, which is provably embedded for any valid diagram.
    """
    signature = (samples, diagram.x_count, diagram.y_count,
                 tuple((a.a.side, a.a.index, a.b.side, a.b.index) for a in diagram.arcs))
    cached = getattr(diagram, "_routed", None)
    if cached is not None and cached[0] == signature:
        return cached[1]

    paths = [stroke.points(samples) for stroke in strokes(diagram)]
    boxes = [_box(path) for path in paths]
    clear = True
    for i in range(len(paths)):
        for j in range(i + 1, len(paths)):
            p, q = boxes[i], boxes[j]
            if p[2] < q[0] or q[2] < p[0] or p[3] < q[1] or q[3] < p[1]:
                continue
            if crossings_between([paths[i], paths[j]]):
                clear = False
                break
        if not clear:
            break
    if not clear:
        paths = route_radial(diagram)
    diagram._stroked = clear
    diagram._routed = (signature, paths)
    return paths


def stroked(diagram: Diagram) -> bool:
    """Whether this diagram's strokes are clear, so the drawing can use them as they are.

    When they are not, the picture falls back to sampled polylines, which is a worse-looking
    but always-correct drawing.  Nothing else changes: the discs are the same either way,
    because either routing is an embedding and any embedding gives the same answers.
    """
    route(diagram)
    return getattr(diagram, "_stroked", False)


def route_radial(diagram: Diagram, samples: int = 24) -> list[list[tuple[float, float]]]:
    """A polyline per arc, all inside the unit square and pairwise disjoint.

    Done in a disc rather than in the square, because there the answer is free: points in
    convex position, two straight chords cross if and only if their endpoints interleave, and
    a valid diagram's chords never interleave.  So draw straight chords between the boundary
    points placed by perimeter, then carry the disc back to the square radially -- a
    homeomorphism, so nothing that was disjoint becomes crossing.

    The arcs come out bowed toward the middle rather than looking like anyone's drawing of a
    Heegaard diagram.  That is fine: the solver only needs an embedding, and every embedding
    of the same combinatorics gives the same discs.
    """
    centre = (0.5, 0.5)
    paths = []
    for arc in diagram.arcs:
        ta, tb = _perimeter(diagram, arc.a), _perimeter(diagram, arc.b)
        angle_a, angle_b = ta * math.pi / 2.0, tb * math.pi / 2.0
        ax, ay = math.cos(angle_a), math.sin(angle_a)
        bx, by = math.cos(angle_b), math.sin(angle_b)

        points = []
        for step in range(samples + 1):
            f = step / samples
            x, y = ax + (bx - ax) * f, ay + (by - ay) * f
            radius = math.hypot(x, y)
            if radius < 1e-12:
                points.append(centre)
                continue
            t = math.atan2(y, x) * 2.0 / math.pi          # back to a perimeter parameter
            edge = _boundary_at(t)
            points.append((centre[0] + radius * (edge[0] - centre[0]),
                           centre[1] + radius * (edge[1] - centre[1])))
        points[0] = position(diagram, arc.a)
        points[-1] = position(diagram, arc.b)
        paths.append(points)
    return paths


def crossings_between(paths, eps: float = 1e-9) -> list[tuple[int, int]]:
    """Any two arcs that meet.  Should be empty; a diagram that validates cannot produce one.

    The tolerance is not decoration.  ``route`` puts arcs on rays out of the centre, so two
    legs in opposite directions are exactly collinear, and their orientation determinants come
    out as 0.0 against 3e-18 -- noise, which a strict ``> 0`` test reads as opposite sides and
    reports as a crossing that is not there.  So a straddle has to be strict on both sides,
    and the collinear case is decided by whether the segments actually overlap rather than by
    the sign of a rounding error.
    """
    def side(a, b, c):
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])

    def straddles(d1, d2) -> bool:
        return (d1 > eps and d2 < -eps) or (d1 < -eps and d2 > eps)

    def overlap(p1, p2, p3, p4) -> bool:
        """Collinear segments: an overlap of positive length, not a touch at one end."""
        axis = 0 if abs(p2[0] - p1[0]) >= abs(p2[1] - p1[1]) else 1
        lo1, hi1 = sorted((p1[axis], p2[axis]))
        lo2, hi2 = sorted((p3[axis], p4[axis]))
        return min(hi1, hi2) - max(lo1, lo2) > eps

    def hit(p1, p2, p3, p4) -> bool:
        d1, d2 = side(p3, p4, p1), side(p3, p4, p2)
        d3, d4 = side(p1, p2, p3), side(p1, p2, p4)
        if straddles(d1, d2) and straddles(d3, d4):
            return True
        if max(abs(d) for d in (d1, d2, d3, d4)) <= eps:
            return overlap(p1, p2, p3, p4)
        return False

    bad = []
    for u in range(len(paths)):
        for v in range(u + 1, len(paths)):
            P, Q = paths[u], paths[v]
            if any(hit(P[i], P[i + 1], Q[j], Q[j + 1])
                   for i in range(len(P) - 1) for j in range(len(Q) - 1)):
                bad.append((u, v))
    return bad
