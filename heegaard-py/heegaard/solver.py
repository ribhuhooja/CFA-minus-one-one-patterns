"""Counting the discs a diagram bounds.

The same algorithm as heegaard-js, and the same answers.  A disc is a piece of beta together
with the path along the alpha curves that closes it up, enclosing a region that covers no z.

WHICH PIECES.  Beta meets each generator once per circuit, so the nodes of one circuit of the
lifted curve are exactly the generators, once each.  From each of them we run both ways along
beta, out to where beta returns to that same generator -- one circuit each way.

WHAT IS COMBINATORIAL.  Nearly all of it.  Beta meets the alpha curves exactly at the
generators, so a piece of k arcs has k+1 crossings and they are the track's nodes; which alpha
edge each lies on, and where along it, follows from the generator's side and index; and one
copy of the domain IS one cell of the grid, so every arc lies in exactly one cell -- its tile.
The first and last steps of the path follow from which edge the end generators sit on.

WHAT IS NOT.  Deciding whether a completed path encloses a basepoint.  That is a winding
number, and it needs an embedding -- but any embedding will do, since two embeddings of the
same combinatorics are isotopic.  ``layout.route`` supplies one for any valid diagram without
assuming the arcs are straight or the diagram is from a family we know.

REEB CHORDS.  At each lattice point of the path there is an incoming direction and an outgoing
one, and the six pairs that can occur are exactly the six moves the local rules permit.  The
naming is fixed by asking the composites to compose: writing a chord as (in, out), rho_12
starts where rho_1 starts and ends where rho_2 ends, and likewise the others.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from .diagram import CURVE_OF_SIDE, Diagram, GLUED_SIDE, Endpoint
from .layout import position, route

DIRECTIONS = {"N": (0, 1), "E": (1, 0), "S": (0, -1), "W": (-1, 0)}
#: permitted next steps, by the direction of arrival
STEP_TABLE = {"W": (), "S": ("E",), "E": ("E", "N"), "N": ("E", "N", "W")}
REEB = {("N", "W"): "rho_1", ("E", "N"): "rho_2", ("S", "E"): "rho_3",
        ("N", "N"): "rho_12", ("E", "E"): "rho_23", ("N", "E"): "rho_123"}
#: the first step of the path, from the edge the start generator sits on
FIRST_STEP = {"bottom": "E", "top": "W", "left": "S", "right": "N"}
#: the last step into the end generator, likewise
LAST_STEP = {"bottom": "E", "top": "W", "left": "S", "right": "N"}
CELL_SIDE = {"bottom": "S", "top": "N", "left": "W", "right": "E"}
TILE_STEP = {"top": (0, 1), "bottom": (0, -1), "right": (1, 0), "left": (-1, 0)}


@dataclass
class Disc:
    source: str
    target: str
    offset: int
    directions: list[str]
    chords: list[str]
    U: int
    area: float
    #: the closed polygon it covers in the universal cover, if anyone asked for it
    region: list[tuple[float, float]] | None = None

    @property
    def word(self) -> str:
        return "".join(c.replace("rho_", "P") for c in self.chords)


def reeb_chords(directions: list[str]) -> list[str]:
    out = []
    for a, b in zip(directions, directions[1:]):
        chord = REEB.get((a, b))
        if chord is None:
            raise ValueError(f"the turn {a}->{b} has no Reeb chord; a path cannot contain it")
        out.append(chord)
    return out


# ---------------------------------------------------------------- the lifted curve

@dataclass
class Track:
    nodes: list[dict] = field(default_factory=list)      # side, index, tile, edge, t, point
    segments: list[list[tuple[float, float]]] = field(default_factory=list)
    cells: list[tuple[int, int]] = field(default_factory=list)
    entries: list[str] = field(default_factory=list)     # cell side each segment enters by
    exits: list[str] = field(default_factory=list)
    circuit: int = 0


def lift(diagram: Diagram, arcs: int, start_tile: tuple[int, int] = (0, 0)) -> Track:
    """Follow beta through the gluings, recording where each arc and node lands."""
    paths = route(diagram)
    by_end: dict[str, tuple[int, Endpoint]] = {}
    for k, arc in enumerate(diagram.arcs):
        by_end[str(arc.a)] = (k, arc.b)
        by_end[str(arc.b)] = (k, arc.a)

    track = Track(circuit=len(diagram.components()[0]))
    entry = diagram.arcs[0].a
    tile = start_tile

    def node_of(end: Endpoint, tile: tuple[int, int]) -> dict:
        a, b = tile
        count = diagram.x_count if end.curve == "x" else diagram.y_count
        along = (end.index + 0.5) / count
        if end.side == "bottom":
            edge, t, point = f"H:{a}:{b}", along, (a + along, float(b))
        elif end.side == "top":
            edge, t, point = f"H:{a}:{b + 1}", along, (a + along, float(b + 1))
        elif end.side == "left":
            edge, t, point = f"V:{a}:{b}", 1 - along, (float(a), b + 1 - along)
        else:
            edge, t, point = f"V:{a + 1}:{b}", 1 - along, (float(a + 1), b + 1 - along)
        return {"side": end.side, "index": end.index, "tile": tile, "edge": edge,
                "t": t, "point": point, "name": end.name}

    for _ in range(arcs):
        index, far = by_end[str(entry)]
        arc = diagram.arcs[index]
        raw = paths[index] if entry == arc.a else list(reversed(paths[index]))
        track.nodes.append(node_of(entry, tile))
        track.segments.append([(x + tile[0], y + tile[1]) for x, y in raw])
        track.cells.append(tile)
        track.entries.append(CELL_SIDE[entry.side])
        track.exits.append(CELL_SIDE[far.side])
        step = TILE_STEP[far.side]
        tile = (tile[0] + step[0], tile[1] + step[1])
        entry = far.glued
    track.nodes.append(node_of(entry, tile))
    return track


# ---------------------------------------------------------------- geometry, only at the end

def _winding(polygon, px: float, py: float) -> int:
    wn = 0
    for (ax, ay), (bx, by) in zip(polygon, polygon[1:] + polygon[:1]):
        if ay <= py:
            if by > py and (bx - ax) * (py - ay) - (by - ay) * (px - ax) > 0:
                wn += 1
        elif by <= py and (bx - ax) * (py - ay) - (by - ay) * (px - ax) < 0:
            wn -= 1
    return wn


def _signed_area(polygon) -> float:
    return sum(a[0] * b[1] - b[0] * a[1]
               for a, b in zip(polygon, polygon[1:] + polygon[:1])) / 2.0


def _edge_of(v: tuple[int, int], direction: str) -> str:
    x, y = v
    if direction == "E":
        return f"H:{x}:{y}"
    if direction == "W":
        return f"H:{x - 1}:{y}"
    if direction == "N":
        return f"V:{x}:{y}"
    return f"V:{x}:{y - 1}"


def _cell_edges(i: int, j: int):
    return (f"H:{i}:{j}", f"H:{i}:{j + 1}", f"V:{i}:{j}", f"V:{i + 1}:{j}")


def _side_of_cell(edge: str, i: int, j: int) -> str | None:
    axis, a, b = edge.split(":")
    a, b = int(a), int(b)
    if axis == "H" and a == i and b == j:
        return "S"
    if axis == "H" and a == i and b == j + 1:
        return "N"
    if axis == "V" and a == i and b == j:
        return "W"
    if axis == "V" and a == i + 1 and b == j:
        return "E"
    return None


@dataclass
class Piece:
    """The description of one run of arcs, built by extending, all from the tables."""
    track: Track
    start: int
    direction: int
    steps: int = 0
    points: list = field(default_factory=list)
    cells: dict = field(default_factory=dict)
    blocked: set = field(default_factory=set)
    by_edge: dict = field(default_factory=dict)
    candidate: set = field(default_factory=set)
    crossings: list = field(default_factory=list)
    sub_arcs: list = field(default_factory=list)

    def __post_init__(self):
        self._add(self.start, "start")

    def _add(self, node: int, kind: str):
        info = self.track.nodes[node]
        record = {"point": info["point"], "edge": info["edge"], "t": info["t"], "kind": kind}
        self.crossings.append(record)
        self.blocked.add(info["edge"])
        self.by_edge.setdefault(info["edge"], []).append(record)

    def extend(self) -> bool:
        segment = (self.start + self.steps if self.direction > 0
                   else self.start - self.steps - 1)
        if not 0 <= segment < len(self.track.segments):
            return False
        raw = self.track.segments[segment]
        points = raw if self.direction > 0 else list(reversed(raw))
        self.points.extend(points[1:] if self.points else points)

        i, j = self.track.cells[segment]
        if (i, j) not in self.cells:
            self.cells[(i, j)] = True
            self.candidate.update(_cell_edges(i, j))
        entry, exit_ = ((self.track.entries[segment], self.track.exits[segment])
                        if self.direction > 0
                        else (self.track.exits[segment], self.track.entries[segment]))
        self.sub_arcs.append(((i, j), entry, exit_))

        self.steps += 1
        far = self.start + self.steps if self.direction > 0 else self.start - self.steps
        if len(self.crossings) > 1:
            self.crossings[-1]["kind"] = "interior"
        self._add(far, "end")
        return True

    def joins_sides(self, i: int, j: int, one: str, two: str) -> bool:
        return any(cell == (i, j) and {entry, exit_} == {one, two}
                   for cell, entry, exit_ in self.sub_arcs)


def _local_ok(came: str, goes: str, v, piece: Piece) -> bool:
    """The conjectured local rules.  They never discard a genuine solution; only the global
    test decides, so these prune rather than judge."""
    if goes not in STEP_TABLE[came]:
        return False
    if came == "E" and goes == "E":
        return _edge_of(v, "N") in piece.blocked
    if came == "N" and goes == "E":
        return _edge_of(v, "N") in piece.blocked
    if came == "N" and goes == "N":
        return (piece.joins_sides(v[0] - 1, v[1], "S", "N")
                or piece.joins_sides(v[0] - 1, v[1], "W", "N"))
    if came == "N" and goes == "W":
        return _edge_of(v, "W") in piece.blocked
    return True


def _between(records, lo: float, hi: float):
    low, high = min(lo, hi) + 1e-9, max(lo, hi) - 1e-9
    return next((r for r in records if low < r["t"] < high), None)


def _lattice(point, direction: str, leaving: bool) -> tuple[int, int]:
    """The lattice point a path step runs to (leaving) or comes from (arriving)."""
    x, y = point
    if direction == "E":
        return (math.ceil(x) if leaving else math.floor(x), int(round(y)))
    if direction == "W":
        return (math.floor(x) if leaving else math.ceil(x), int(round(y)))
    if direction == "N":
        return (int(round(x)), math.ceil(y) if leaving else math.floor(y))
    return (int(round(x)), math.floor(y) if leaving else math.ceil(y))


def _solve_piece(piece: Piece, z_eps: float, w_point, max_path: int):
    """Find the disc this piece bounds, or None."""
    nodes = piece.track.nodes
    first_node = nodes[piece.start]
    last_node = nodes[piece.start + piece.direction * piece.steps]

    # A node is recorded as the ENTRY of the arc that follows it, so its side is the side of
    # that arc's tile.  Run beta backwards and it leaves through the opposite side instead,
    # and arrives at the far node without a gluing in between.
    if piece.direction > 0:
        first = FIRST_STEP[first_node["side"]]
        last = LAST_STEP[GLUED_SIDE[last_node["side"]]]
    else:
        first = FIRST_STEP[GLUED_SIDE[first_node["side"]]]
        last = LAST_STEP[last_node["side"]]
    xs, xe = first_node["point"], last_node["point"]
    edge_s, edge_e = first_node["edge"], last_node["edge"]

    vs, ve = _lattice(xs, first, True), _lattice(xe, last, False)
    t_vs = 1.0 if first in ("E", "N") else 0.0
    t_ve = 0.0 if last in ("E", "N") else 1.0
    on_s = piece.by_edge.get(edge_s, [])
    on_e = piece.by_edge.get(edge_e, [])
    blocked_start = _between(on_s, first_node["t"], t_vs)
    blocked_end = _between(on_e, t_ve, last_node["t"])

    candidates = []
    if edge_s == edge_e:                      # both ends on one alpha edge
        forward = 1 if first in ("E", "N") else -1
        ts, te = first_node["t"], last_node["t"]
        if (te - ts) * forward > 0 and not _between(on_s, ts, te):
            candidates.append([xs, xe])
    if not blocked_start and not blocked_end:
        if vs == ve:
            candidates.append([xs, (float(vs[0]), float(vs[1])), xe])
        else:
            walk = _walk(piece, vs, ve, first, max_path)
            if walk is not None:
                candidates.append([xs] + [(float(a), float(b)) for a, b in walk] + [xe])

    for path in candidates:
        disc = _check(path, piece, z_eps, w_point)
        if disc is not None:
            return disc
    return None


def _walk(piece: Piece, vs, ve, first: str, max_path: int):
    """Take the single step the local rules leave open, until v_e or nowhere."""
    visited, lattice, v, came = {vs}, [vs], vs, first
    while v != ve:
        if len(lattice) > max_path:
            return None
        open_steps = []
        for step, (dx, dy) in DIRECTIONS.items():
            edge = _edge_of(v, step)
            if edge not in piece.candidate or edge in piece.blocked:
                continue
            nxt = (v[0] + dx, v[1] + dy)
            if nxt in visited or not _local_ok(came, step, v, piece):
                continue
            open_steps.append((step, nxt))
        if len(open_steps) != 1:
            return None
        came, v = open_steps[0]
        visited.add(v)
        lattice.append(v)
    return lattice


def _check(path, piece: Piece, z_eps: float, w_point):
    """(P1)-(P4): simple, clear of beta, correctly oriented, covering no z."""
    if len(set(path)) != len(path):
        return None
    for a, b, c in zip(path, path[1:], path[2:]):
        if (a[0] - b[0], a[1] - b[1]) == (c[0] - b[0], c[1] - b[1]):
            return None                                   # doubles back
    for record in piece.crossings:
        if record["kind"] != "interior":
            continue
        px, py = record["point"]
        for (ax, ay), (bx, by) in zip(path, path[1:]):
            if min(ax, bx) - 1e-9 <= px <= max(ax, bx) + 1e-9 and \
               min(ay, by) - 1e-9 <= py <= max(ay, by) + 1e-9 and \
               abs((bx - ax) * (py - ay) - (by - ay) * (px - ax)) < 1e-9:
                return None

    polygon = list(piece.points) + list(reversed(path[1:-1]))
    area = _signed_area(polygon)
    if not area < 0:                                       # must run clockwise
        return None

    xs = [p[0] for p in polygon]
    ys = [p[1] for p in polygon]
    lo_i, hi_i = math.floor(min(xs)) - 1, math.ceil(max(xs)) + 1
    lo_j, hi_j = math.floor(min(ys)) - 1, math.ceil(max(ys)) + 1
    power = 0
    for i in range(lo_i, hi_i + 1):
        for j in range(lo_j, hi_j + 1):
            if _winding(polygon, i + z_eps, j + 1 - z_eps) != 0:
                return None                                # covers a z
            if _winding(polygon, i + w_point[0], j + w_point[1]) != 0:
                power += 1

    directions = []
    for (ax, ay), (bx, by) in zip(path, path[1:]):
        dx, dy = bx - ax, by - ay
        directions.append(("E" if dx > 0 else "W") if abs(dx) > abs(dy)
                          else ("N" if dy > 0 else "S"))
    return directions, power, area, polygon


def _basepoints(diagram: Diagram):
    """Where z and w go, measured off the drawing rather than assumed.

    z sits in the top-left corner of the domain, beyond the last arc that reaches into it --
    that is what "for small enough epsilon" means.  w is shut inside whichever arc the diagram
    says holds it, between that arc's chord and its apex.
    """
    paths = route(diagram)
    clearance = min(x + (1.0 - y) for path in paths for x, y in path)
    z_eps = 0.35 * clearance
    if 2 * z_eps >= clearance:
        raise ValueError("no room for z in the corner")

    nearest = min(math.dist((x, y), corner)
                  for path in paths for x, y in path
                  for corner in ((0, 0), (1, 0), (0, 1), (1, 1)))
    if z_eps * math.sqrt(2) >= nearest:
        raise ValueError(f"z sits {z_eps * math.sqrt(2):.4g} from its corner but beta passes "
                         f"within {nearest:.4g} of a lattice point")

    w_point = None
    for name, index in diagram.basepoints.items():
        if name != "w":
            continue
        path = paths[index]
        a, b = path[0], path[-1]
        apex = path[len(path) // 2]
        mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        w_point = (mid[0] + 0.45 * (apex[0] - mid[0]), mid[1] + 0.45 * (apex[1] - mid[1]))
    if w_point is None:
        raise ValueError(f"{diagram.name} has no w basepoint, so U powers are undefined")
    return z_eps, w_point


def lifted_track(diagram: Diagram) -> tuple[Track, int]:
    """Three circuits of beta, shifted so the middle one sits in positive tiles.

    The middle circuit is the one discs are enumerated from -- it has a whole circuit of
    room either side of it, which is as far as a disc can reach.  Anything that wants to
    rebuild a disc's geometry must lift the curve exactly this way, so this is shared rather
    than repeated.
    """
    circuit = len(diagram.components()[0])
    probe = lift(diagram, circuit * 3 + 1)
    lo_i = min(n["tile"][0] for n in probe.nodes) - 1
    lo_j = min(n["tile"][1] for n in probe.nodes) - 1
    return lift(diagram, circuit * 3 + 1, (1 - lo_i, 1 - lo_j)), circuit


def enumerate_discs(diagram: Diagram, keep_regions: bool = False) -> list[Disc]:
    """Every disc of the diagram.

    From each generator, run both ways along beta as far as the point where beta comes back to
    it -- one circuit each way.  Every disc with that source is somewhere in that range.

    ``keep_regions`` also hands back the polygon each disc covers in the universal cover.  It
    costs nothing to keep -- the check has already built it -- but it is a lot of points, so
    only a caller that means to draw them should ask.
    """
    diagram.validate()
    z_eps, w_point = _basepoints(diagram)
    track, circuit = lifted_track(diagram)
    max_path = 4 * len(diagram.arcs) + 8

    discs: list[Disc] = []
    for start in range(circuit, 2 * circuit):
        for direction in (1, -1):
            piece = Piece(track, start, direction)
            for step in range(1, circuit + 1):
                if not piece.extend():
                    break
                found = _solve_piece(piece, z_eps, w_point, max_path)
                if found is None:
                    continue
                directions, power, area, polygon = found
                discs.append(Disc(
                    source=track.nodes[start]["name"],
                    target=track.nodes[start + direction * step]["name"],
                    offset=direction * step, directions=directions,
                    chords=reeb_chords(directions), U=power, area=area,
                    region=list(polygon) if keep_regions else None))
    return discs


def _replay(directions: list[str], xs, xe) -> list[tuple[float, float]]:
    """Rebuild the alpha path of a disc from the directions the CSV recorded.

    The path is a start point on an alpha edge, then whole lattice points, then an end point
    on an alpha edge -- so one direction per step is enough to put it back.  The first step
    leaves ``xs`` for the lattice point ahead of it, the last arrives at ``xe``, and every
    step in between is one unit of the grid.
    """
    if len(directions) == 1:                      # both ends on one alpha edge
        return [xs, xe]
    v = _lattice(xs, directions[0], True)
    path = [xs, (float(v[0]), float(v[1]))]
    for step in directions[1:-1]:
        dx, dy = DIRECTIONS[step]
        v = (v[0] + dx, v[1] + dy)
        path.append((float(v[0]), float(v[1])))
    path.append(xe)
    return path


def attach_regions(diagram: Diagram, discs) -> list[Disc]:
    """Fill in ``region`` and ``area`` for discs that arrived without them.

    A disc read back from a CSV is source, target, offset and a list of directions, which is
    all the geometry there ever was: the offset says which run of arcs of beta it is, and the
    directions say how the alpha path closes it up.  So the polygon can be rebuilt exactly,
    and this is what lets a picture be drawn from a disc list someone else computed -- the JS
    solver, say -- without solving anything again.

    Raises if a disc does not describe a run of this diagram's beta, which makes it a check on
    the file as well as a way to draw it.
    """
    diagram.validate()
    track, circuit = lifted_track(diagram)
    start_of = {track.nodes[k]["name"]: k for k in range(circuit, 2 * circuit)}

    for disc in discs:
        if disc.region is not None:
            continue
        start = start_of.get(disc.source)
        if start is None:
            raise ValueError(f"{disc.source} is not a generator of {diagram.name}")
        if not disc.offset or abs(disc.offset) > circuit:
            raise ValueError(f"{disc.source}: an offset of {disc.offset} is not a run of "
                             f"beta, whose circuit is {circuit} arcs")
        piece = Piece(track, start, 1 if disc.offset > 0 else -1)
        for _ in range(abs(disc.offset)):
            if not piece.extend():
                raise ValueError(f"{disc.source}{disc.offset:+d} runs off the lifted curve")
        landed = track.nodes[start + disc.offset]
        if landed["name"] != disc.target:
            raise ValueError(f"{disc.source}{disc.offset:+d} arrives at {landed['name']}, "
                             f"but the disc says {disc.target}")

        path = _replay(disc.directions, track.nodes[start]["point"], landed["point"])
        disc.region = list(piece.points) + list(reversed(path[1:-1]))
        disc.area = _signed_area(disc.region)
    return discs
