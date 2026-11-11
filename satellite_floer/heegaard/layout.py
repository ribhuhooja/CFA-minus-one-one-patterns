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
at both ends and so spaces evenly across the gluing seam -- or at the same fraction of a
narrower stretch of it, when :func:`tune_spacing` has found that draws better.
"""

from __future__ import annotations

import math

from dataclasses import dataclass

from .diagram import CURVE_OF_SIDE, Diagram, Endpoint


UNIFORM = {"x": (0.0, 1.0), "y": (0.0, 1.0), "bow": 0.0}


def spacing(diagram: Diagram) -> dict:
    """The stretch of each alpha curve its generators are spread over, evenly, and how much
    the strands across the domain bow.

    ``(0, 1)`` -- the whole edge -- and straight strands, unless :func:`tune_spacing` has
    found something that draws better.  The stretch is measured from the corner where z
    sits, top left: along the top from the left, down the left side from the top.
    """
    return getattr(diagram, "_spacing", None) or UNIFORM


def position(diagram: Diagram, end: Endpoint) -> tuple[float, float]:
    """Where a generator sits on the boundary of the unit square, y upward.

    Moving them is free: it is an isotopy of the whole diagram, so it changes no disc.  It is
    only ever done to draw better -- see :func:`tune_spacing`."""
    count = diagram.x_count if end.curve == "x" else diagram.y_count
    lo, hi = spacing(diagram)[end.curve]
    along = lo + (hi - lo) * (end.index + 0.5) / count
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
#: how sharply an arc's wanted shape gives way to the room it actually has; smaller is
#: gentler, and 1 would be the harmonic mean, which gives way far too early
SOFTNESS = 2.0
#: how far along its inward normals a strand across the domain reaches, when it bows at all
#: -- see strokes() and tune_spacing()
STRAND_BOW = 0.3
#: rainbows barely give at all -- see strokes()
SOFTNESS_RAINBOW = 8.0
#: the direction into the domain from each edge
INWARD = {"bottom": (0.0, 1.0), "top": (0.0, -1.0),
          "left": (1.0, 0.0), "right": (-1.0, 0.0)}


#: control-point offset that makes a cubic match a circular quarter turn
KAPPA = 0.5522847498


@dataclass(frozen=True)
class Stroke:
    """One arc of beta as a single piece of geometry: a segment, or one cubic curve.

    A cubic and not a quadratic, because a quadratic has one control point and that is one
    too few.  An arc has to leave both its generators at a right angle to the edge it starts
    from *and* be shrinkable to fit inside whatever contains it, and with a single control
    those are the same number: pull the control in to shrink the arc and the ends stop being
    square-on.  Two controls, one on each end's inward normal, hold the angles exactly while
    the bulge slides freely.  It is still one SVG ``C`` command.
    """

    kind: str
    a: tuple
    b: tuple
    ca: tuple = (0.0, 0.0)
    cb: tuple = (0.0, 0.0)

    def at(self, f: float) -> tuple:
        """A point a fraction ``f`` along, for sampling and for checking."""
        if self.kind == "line":
            return (self.a[0] + (self.b[0] - self.a[0]) * f,
                    self.a[1] + (self.b[1] - self.a[1]) * f)
        g = 1.0 - f
        w0, w1, w2, w3 = g * g * g, 3 * g * g * f, 3 * g * f * f, f * f * f
        return (w0 * self.a[0] + w1 * self.ca[0] + w2 * self.cb[0] + w3 * self.b[0],
                w0 * self.a[1] + w1 * self.ca[1] + w2 * self.cb[1] + w3 * self.b[1])

    def points(self, samples: int = 12) -> list:
        if self.kind == "line":
            return [self.a, self.b]
        out = [self.at(i / samples) for i in range(samples + 1)]
        out[0], out[-1] = self.a, self.b
        return out


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


def _box(path):
    xs = [q[0] for q in path]
    ys = [q[1] for q in path]
    return (min(xs), min(ys), max(xs), max(ys))



def _overlapping(p, q) -> bool:
    return not (p[2] < q[0] or q[2] < p[0] or p[3] < q[1] or q[3] < p[1])


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
    """Every arc of beta as one line or one cubic curve -- four points, nothing sampled.

    Each arc has a shape it would take given the room, and takes as much of it as the arc
    containing it allows.

    **Two generators on one edge** -- a rainbow -- wants the semicircle standing on them.

    **Two edges meeting at a corner** wants the quarter ellipse through both, centred on the
    corner.  ``r`` of these at the top left and ``r`` at the top right are not corner arcs at
    all but the two halves of ``r`` more rainbows, hanging from the top edge and cut in two by
    the seam where the left and right edges are identified -- ``y_j`` on the left and ``y_j``
    on the right being one point of the torus.  Both shapes leave their generators square-on,
    and that is what lets the halves meet as one smooth rainbow in the universal cover.

    **Two opposite edges** has a whole side behind it and is drawn straight -- or, in a
    picture that :func:`tune_spacing` has found it helps, as a gentle S: one cubic, leaving
    each end square-on like everything else, its controls ``bow`` along the two inward
    normals.  A straight strand leaves the edge at a slant while the corner fan beside it
    leaves square, so the fan's outer arcs have to turn hard at once, and on Q(2,2,2) they
    piled into a band a tenth of a spacing wide.  Every strand bows by the same amount, which
    is what keeps them apart: a cubic's height does not depend on its ends' x, so two strands
    are both ``x = a + (b - a) s(y)`` for one shared ``s``, and their order at every height
    is their order at the ends.

    Every arc keeps its angles whatever else happens to it, because the two controls sit on
    the inward normals and only their length changes.  What changes is one number: how much of
    its shape it gets.  That is measured against the arc containing it, outermost first, by
    casting a ray along the way it bulges -- a shape fixed only by its endpoints has nothing
    left to clear what it holds, and ranking by nesting height cannot express it either, since
    a straight strand has no bulge for its children to rank below.

    The share is ``h / (h + 1)`` of the gap, ``h`` counting the levels still to fit inside,
    spent on the **apex**: spend it on the controls instead and the space quarters at every
    level rather than stepping down evenly.  And it is taken as a *soft* minimum against the
    shape the arc wanted.  Where a fan runs into something -- the corner arcs meeting a
    straight strand -- the region left is wedge-shaped, so it must be squeezed somewhere; a
    hard minimum squeezes nothing until it squeezes everything, and the fan stays at full size
    and then piles into a heap at the first arc that meets the obstruction.

    TODO: better, but the user still wants these more beautiful.  Known wants: the fans are
    spaced by an even share of the gap rather than by eye; the straight strands could take a
    slight bow where there is room for one; and where a fan is pinched the give is spread by
    a soft minimum, which is a smooth fudge rather than a considered allocation.
    """
    cut, intervals, height = nesting(diagram)

    parent = [None] * len(intervals)
    for k, (u, v) in enumerate(intervals):
        for j, (a, b) in enumerate(intervals):
            if j != k and a < u and v < b and (parent[k] is None
                                               or b - a < intervals[parent[k]][1] - intervals[parent[k]][0]):
                parent[k] = j

    out: list = [None] * len(intervals)
    drawn: list = [None] * len(intervals)
    boxes: list = [None] * len(intervals)
    for k in sorted(range(len(intervals)), key=lambda k: -(intervals[k][1] - intervals[k][0])):
        arc = diagram.arcs[k]
        one, two = arc.a.side, arc.b.side
        pa, pb = position(diagram, arc.a), position(diagram, arc.b)
        if OPPOSITE[one] == two:
            bow = spacing(diagram)["bow"]
            if bow <= 0.0:
                out[k], drawn[k] = Stroke("line", pa, pb), [pa, pb]
            else:
                na, nb = INWARD[one], INWARD[two]
                out[k] = Stroke("curve", pa, pb, (pa[0] + bow * na[0], pa[1] + bow * na[1]),
                                (pb[0] + bow * nb[0], pb[1] + bow * nb[1]))
                drawn[k] = out[k].points(16)
            boxes[k] = _box(drawn[k])
            continue

        na, nb = INWARD[one], INWARD[two]
        crowds = one != two
        if one == two:                              # the semicircle on its own feet
            reach_a = reach_b = 4.0 / 3.0 * math.dist(pa, pb) / 2.0
        else:                                       # the quarter ellipse about their corner
            corner = CORNER[frozenset((one, two))]
            across = max(abs(pa[0] - corner[0]), abs(pb[0] - corner[0]))
            up = max(abs(pa[1] - corner[1]), abs(pb[1] - corner[1]))
            flat_first = one in ("bottom", "top")
            reach_a = KAPPA * (up if flat_first else across)
            reach_b = KAPPA * (across if flat_first else up)

        # the apex is 3/8 of the way along the two control offsets put together
        vx = 3.0 / 8.0 * (reach_a * na[0] + reach_b * nb[0])
        vy = 3.0 / 8.0 * (reach_a * na[1] + reach_b * nb[1])
        want = math.hypot(vx, vy)
        if want < 1e-12:
            out[k], drawn[k] = Stroke("line", pa, pb), [pa, pb]
            boxes[k] = _box(drawn[k])
            continue
        dx, dy = vx / want, vy / want

        mid = ((pa[0] + pb[0]) / 2.0, (pa[1] + pb[1]) / 2.0)
        above = parent[k]
        gap = 0.9 if above is None else min(_ray_hit(mid, (dx, dy), drawn[above], 0.9), 0.9)
        allowed = gap * height[k] / (height[k] + 1.0)
        # A rainbow takes the room it wants outright: its size is fixed by its own feet, it
        # cannot over-reach, and a fan of them is already evenly stepped.  A corner arc is the
        # one that grows without bound as its generators move away from the corner, so it is
        # the one that runs into things, and it gives way early -- a *soft* minimum against
        # the room rather than a hard one.  A hard minimum squeezes nothing until it squeezes
        # everything: the fan stays at full size and then piles into a heap at the first arc
        # that meets the obstruction, which is exactly what it used to do.
        give = SOFTNESS if crowds else SOFTNESS_RAINBOW
        apex = (want ** -give + allowed ** -give) ** (-1.0 / give)
        share = apex / want

        def shaped(share: float) -> Stroke:
            return Stroke("curve", pa, pb,
                          (pa[0] + share * reach_a * na[0], pa[1] + share * reach_a * na[1]),
                          (pb[0] + share * reach_b * nb[0], pb[1] + share * reach_b * nb[1]))

        # The ray only asks how far it is to the parent straight ahead, and that is neither the
        # only direction an arc can meet something nor the only thing it can meet.  A rainbow
        # standing beside a straight strand that rises steeply out of the edge next to it
        # clears the strand at its apex and clips it with its flank -- and the two are not
        # nested at all, so no amount of care about parents would have compared them.  So the
        # estimate is checked against everything already drawn, and given up on a bit at a
        # time until the arc really is clear.  Outermost first, so what is already drawn is
        # everything with a longer span than this one.
        out[k] = shaped(share)
        for _ in range(16):
            here = out[k].points(10)
            box = _box(here)
            if not any(_overlapping(box, boxes[j]) and crossings_between([here, drawn[j]])
                       for j in range(len(drawn)) if drawn[j] is not None):
                break
            share *= 0.8
            out[k] = shaped(share)
        drawn[k] = out[k].points(10)
        boxes[k] = _box(drawn[k])
    return out


#: the stretches tried for each alpha curve, as (start, end) along it from z's corner
SPANS = ((0.0, 1.0), (0.0, 0.8), (0.0, 0.6), (0.2, 1.0), (0.4, 1.0))
#: past this many arcs a diagram is drawn evenly spaced: tuning costs a few strokes() each
TUNE_LIMIT = 160


def crowding(diagram: Diagram, samples: int = 24, quantile: float = 0.01) -> float:
    """How close beta comes to itself, as a fraction of the even spacing: 1 is no closer
    than neighbouring generators, and small means strands running together.

    Sampled, not solved: points along every stroke, each asked for the nearest point on any
    OTHER stroke, the copies in the eight neighbouring domains included so a seam is no
    edge.  Points near the boundary are left out, since there a stroke meets its own
    continuation and the nearest "other" stroke is itself.  The answer is a low quantile
    rather than the minimum, which is one unlucky pair of samples.
    """
    from collections import defaultdict
    cell = 0.02
    grid = defaultdict(list)
    curves = [[s.at(i / samples) for i in range(samples + 1)] for s in strokes(diagram)]
    for k, points in enumerate(curves):
        for i in (-1, 0, 1):
            for j in (-1, 0, 1):
                for x, y in points:
                    x, y = x + i, y + j
                    if -0.1 < x < 1.1 and -0.1 < y < 1.1:
                        grid[(int(math.floor(x / cell)), int(math.floor(y / cell)))].append(
                            (k, x, y))
    gaps = []
    for k, points in enumerate(curves):
        for x, y in points:
            if not (0.04 < x < 0.96 and 0.04 < y < 0.96):
                continue
            gx, gy = int(math.floor(x / cell)), int(math.floor(y / cell))
            best = 0.1
            for a in range(gx - 4, gx + 5):
                for b in range(gy - 4, gy + 5):
                    for j, qx, qy in grid.get((a, b), ()):
                        if j != k:
                            best = min(best, math.hypot(qx - x, qy - y))
            gaps.append(best)
    if not gaps:
        return 1.0
    gaps.sort()
    even = 1.0 / (max(diagram.x_count, diagram.y_count) + 1)
    return gaps[int(len(gaps) * quantile)] / even


def tune_spacing(diagram: Diagram) -> dict:
    """Spread each alpha curve's generators over whichever stretch of it draws best, and
    bow the strands across the domain if that helps.

    Even spacing along the whole edge is not always even spacing of beta.  Q(2,2,2) has
    thirteen arcs from the left edge to the top, in the wedge between that edge and a
    strand that leaves the bottom right beside the corner: the lower ones land where the
    wedge is almost shut, and ran together at a tenth of a spacing.  Gathering the y
    generators into the top three fifths of the edge lands them where there is room -- but
    then the fan's arcs leave the top square-on beside a strand leaving it at a slant, and
    pile up there instead, which is what the bow is for.  Neither helps much alone; the two
    together take :func:`crowding` from 0.25 of a spacing to 0.79.

    So: with the strands bowed, try each of ``SPANS`` for y and then for x, and keep
    whatever :func:`crowding` says is least crowded and still draws as clean strokes --
    unless nothing beats the plain layout.  It is remembered on the diagram.  Only pictures
    call this.  Moving generators along their curve and bending beta is an isotopy, so no
    disc changes, but the solver has no reason to pay for the search; the renderer
    re-attaches regions after tuning, so what is drawn is still exactly the embedding it
    measured.
    """
    if getattr(diagram, "_spacing", None) is not None:
        return diagram._spacing
    diagram._spacing = dict(UNIFORM)
    if len(diagram.arcs) > TUNE_LIMIT:
        return diagram._spacing
    plain = dict(UNIFORM)
    best, score = plain, (crowding(diagram) if stroked(diagram) else 0.0)
    current = dict(UNIFORM, bow=STRAND_BOW)
    for curve in ("y", "x"):
        base = dict(current)
        for span in SPANS:
            diagram._spacing = dict(base, **{curve: span})
            if not stroked(diagram):
                continue
            trial = crowding(diagram)
            if trial > score * 1.05:
                score, best = trial, dict(diagram._spacing)
                current = dict(best)
    diagram._spacing = best
    return best


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
                 tuple((a.a.side, a.a.index, a.b.side, a.b.index) for a in diagram.arcs),
                 tuple(sorted(spacing(diagram).items())))
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
