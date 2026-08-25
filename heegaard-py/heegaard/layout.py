"""Putting a diagram on the page, without assuming anything about its shape.

The solver needs coordinates only for the last step -- deciding which side of beta a basepoint
falls on -- and any embedding will do, because two embeddings of the same combinatorics are
isotopic and give the same answer.  So this routes arcs in the one way that always works
rather than the one that looks best.

A valid diagram's arcs form a NON-CROSSING chord diagram on the boundary of the domain (that
is what ``crossing_problems`` checks).  Nesting therefore gives a routing for free: an arc
whose chord is (a, b) travels parallel to the boundary along the stretch from a to b, at a
depth set by how many arcs are nested inside it.  Deeper arcs enclose shallower ones and never
touch them.  Straight lines are not assumed anywhere.

The domain is the unit square, so a copy of it is a unit cell of the grid the solver works on.
Generator k of a count of N sits at (k + 1/2)/N along its edge, which leaves the same half-gap
at both ends and so spaces evenly across the gluing seam.
"""

from __future__ import annotations

import math

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


def route(diagram: Diagram, samples: int = 24) -> list[list[tuple[float, float]]]:
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


def crossings_between(paths) -> list[tuple[int, int]]:
    """Any two arcs that meet.  Should be empty; a diagram that validates cannot produce one."""
    def hit(p1, p2, p3, p4) -> bool:
        def side(a, b, c):
            return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
        d1, d2 = side(p3, p4, p1), side(p3, p4, p2)
        d3, d4 = side(p1, p2, p3), side(p1, p2, p4)
        return ((d1 > 0) != (d2 > 0)) and ((d3 > 0) != (d4 > 0))

    bad = []
    for u in range(len(paths)):
        for v in range(u + 1, len(paths)):
            P, Q = paths[u], paths[v]
            if any(hit(P[i], P[i + 1], Q[j], Q[j + 1])
                   for i in range(len(P) - 1) for j in range(len(Q) - 1)):
                bad.append((u, v))
    return bad
