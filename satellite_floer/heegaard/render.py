"""SVG for a diagram, its universal cover, and the discs it bounds.

Everything here takes a :class:`~heegaard.diagram.Diagram` and a list of discs and nothing
else, which is the point: a diagram read out of a CSV draws exactly as well as one built by
a constructor, because there is nothing in a picture that is not in the file.  No family is
named anywhere below, and no arc is assumed to be straight.

Where the arcs go is decided by :mod:`heegaard.layout`, the same routing the solver uses to
settle its winding numbers.  So the picture is not an illustration of the answer -- it is the
embedding the answer was computed in, and a disc drawn here is the polygon that was tested.

This is the only module that flips y: everything upstream is mathematical (y up), SVG is y
down.  Colours are the ones heegaard-js draws with, so the two read as the same object: the
alpha curves are the pale red grid, beta is pale blue.
"""

from __future__ import annotations

import math

from .diagram import Diagram
from .layout import position, route, stroked, strokes, tune_spacing

COLOURS = {
    "grid": "#f0b9b9",          # the alpha curves
    "grid_strong": "#e08a8a",   # the edges of the marked fundamental domain
    "arc": "#7ea6ec",           # beta
    "generator": "#2f3437",
    "label": "#6b645d",
    "ink": "#1d1a17",
    "basepoint": "#b3261e",
    "paper": "#ffffff",
}

#: enough hues to keep neighbouring discs apart; nothing is meant by any particular one
PALETTE = ["#d1495b", "#2a9d8f", "#e9c46a", "#5f6caf", "#e76f51", "#4a7c59",
           "#9d4edd", "#0288a6", "#c1666b", "#7f9c3c", "#b5651d", "#3f6fb5"]


def _fmt(v: float) -> str:
    return f"{round(float(v), 2):g}"


def _esc(text) -> str:
    return (str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def _path_d(points) -> str:
    return " ".join(f"{'L' if k else 'M'}{_fmt(x)} {_fmt(y)}" for k, (x, y) in enumerate(points))


def _text_width(text: str, size: float) -> float:
    """Roughly how wide a run of text will render.

    There is no font metric available without a dependency, so this is an estimate, and it
    errs wide on purpose: the cost of guessing high is a little white space at the right, and
    the cost of guessing low is a caption sliced off the edge of the picture.
    """
    return len(text) * size * 0.56


def beta_paths(diagram: Diagram, to) -> list[str]:
    """The ``d`` of each arc of beta, in svg coordinates.

    One command per arc when the strokes are clear -- a line or a quadratic, which is what
    they are, with no points sampled off them.  ``to`` is affine, so a control point maps
    like any other and the curve survives the transform exactly.  When a diagram's strokes
    are not clear the fallback polyline is drawn instead, which is the only case where this
    emits a run of points.
    """
    if not stroked(diagram):
        return [_path_d([to(q) for q in path]) for path in route(diagram)]

    out = []
    for stroke in strokes(diagram):
        a, b = to(stroke.a), to(stroke.b)
        head = f"M{_fmt(a[0])} {_fmt(a[1])}"
        if stroke.kind == "line":
            out.append(f"{head}L{_fmt(b[0])} {_fmt(b[1])}")
        else:
            ca, cb = to(stroke.ca), to(stroke.cb)
            out.append(f"{head}C{_fmt(ca[0])} {_fmt(ca[1])} {_fmt(cb[0])} {_fmt(cb[1])} "
                       f"{_fmt(b[0])} {_fmt(b[1])}")
    return out


def _svg(width: float, height: float, body: str, title: str) -> str:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{_fmt(width)}" '
            f'height="{_fmt(height)}" viewBox="0 0 {_fmt(width)} {_fmt(height)}" role="img">\n'
            f"  <title>{_esc(title)}</title>\n  {body}\n</svg>\n")


def _basepoints(diagram: Diagram):
    """Where the solver actually puts z and w, so the picture agrees with the computation.

    A diagram with no w is drawable -- it just has no U powers, and the solver would refuse
    it -- so a missing basepoint is not an error here.
    """
    from .solver import _basepoints as solver_basepoints
    try:
        z_eps, w_point = solver_basepoints(diagram)
        return (z_eps, 1.0 - z_eps), w_point
    except ValueError:
        return None, None


def caption_for(diagram: Diagram, extra: str = "") -> str:
    notes = diagram.notes or {}
    bits = [diagram.name]
    if "r" in notes:
        bits.append(f"H(r={notes['r']}, s={notes['s']})")
    bits += [f"{diagram.x_count} x-generators, {diagram.y_count} y-generators",
             f"{len(diagram.arcs)} arcs"]
    components = len(diagram.components())
    bits.append("beta connected" if components == 1
                else f"beta has {components} components")
    if extra:
        bits.append(extra)
    return "  ·  ".join(bits)


# ------------------------------------------------------------------ one fundamental domain

def render_diagram(diagram: Diagram, cell: float = 460, labels: bool = True,
                   basepoints: bool = True, caption: str | None = None) -> str:
    """One copy of the domain: the alpha curves as its boundary, beta inside it."""
    tune_spacing(diagram)
    paths = route(diagram)
    text = caption_for(diagram) if caption is None else caption
    pad = max(30.0, cell * 0.11)
    bottom = pad + 34
    W = max(cell + 2 * pad, 2 * pad + _text_width(text, 12))
    H = cell + pad + bottom

    def to(p):
        return (pad + p[0] * cell, pad + (1.0 - p[1]) * cell)

    parts = [f'<rect width="{_fmt(W)}" height="{_fmt(H)}" fill="{COLOURS["paper"]}"/>',
             f'<rect x="{_fmt(pad)}" y="{_fmt(pad)}" width="{_fmt(cell)}" '
             f'height="{_fmt(cell)}" fill="none" stroke="{COLOURS["grid"]}" '
             f'stroke-width="2.5"/>']

    parts.append(f'<g fill="none" stroke="{COLOURS["arc"]}" stroke-width="2" '
                 f'stroke-linecap="round" stroke-linejoin="round">')
    for d in beta_paths(diagram, to):
        parts.append(f'<path d="{d}"/>')
    parts.append("</g>")

    parts.append(f'<g fill="{COLOURS["generator"]}">')
    for arc in diagram.arcs:
        for end in arc.ends():
            x, y = to(position(diagram, end))
            parts.append(f'<circle cx="{_fmt(x)}" cy="{_fmt(y)}" r="2.8"/>')
    parts.append("</g>")

    # a label per generator only while there is room for one; past that they overprint each
    # other into a grey smear and the picture is better off without them
    spacing = cell / max(diagram.x_count, diagram.y_count, 1)
    if labels and spacing >= 9.0:
        size = min(11.0, max(6.0, spacing * 0.62))
        parts.append(f'<g font-family="ui-monospace,Menlo,monospace" font-size="{_fmt(size)}" '
                     f'fill="{COLOURS["label"]}">')
        for arc in diagram.arcs:
            for end in arc.ends():
                x, y = to(position(diagram, end))
                if end.side == "bottom":
                    dx, dy, anchor = 0.0, size + 7, "middle"
                elif end.side == "top":
                    dx, dy, anchor = 0.0, -8.0, "middle"
                elif end.side == "left":
                    dx, dy, anchor = -7.0, size * 0.36, "end"
                else:
                    dx, dy, anchor = 7.0, size * 0.36, "start"
                parts.append(f'<text x="{_fmt(x + dx)}" y="{_fmt(y + dy)}" '
                             f'text-anchor="{anchor}">{end.index}</text>')
        parts.append("</g>")
        parts.append(f'<g font-family="ui-sans-serif,system-ui,sans-serif" font-size="11" '
                     f'fill="{COLOURS["label"]}">'
                     f'<text x="{_fmt(pad + cell + 14)}" y="{_fmt(pad - 12)}" '
                     f'text-anchor="middle">x_j</text>'
                     f'<text x="{_fmt(pad - 14)}" y="{_fmt(pad - 12)}" '
                     f'text-anchor="middle">y_j</text></g>')

    if basepoints:
        z_at, w_at = _basepoints(diagram)
        parts.append(f'<g fill="{COLOURS["basepoint"]}" '
                     f'font-family="ui-monospace,Menlo,monospace" font-size="11">')
        for point, name in ((z_at, "z"), (w_at, "w")):
            if point is None:
                continue
            x, y = to(point)
            parts.append(f'<circle cx="{_fmt(x)}" cy="{_fmt(y)}" r="3.6"/>'
                         f'<text x="{_fmt(x + 8)}" y="{_fmt(y + 13)}">{name}</text>')
        parts.append("</g>")

    if text:
        parts.append(f'<text x="{_fmt(pad)}" y="{_fmt(H - 14)}" '
                     f'font-family="ui-sans-serif,system-ui,sans-serif" font-size="12" '
                     f'fill="{COLOURS["ink"]}">{_esc(text)}</text>')
    return _svg(W, H, "\n  ".join(parts), diagram.name)


# ------------------------------------------------------------------ the universal cover

def render_cover(diagram: Diagram, tiles: int = 3, cell: float = 200,
                 mark_centre: bool = True, basepoints: bool = True,
                 caption: str | None = None) -> str:
    """The domain tiled by its translations, with the alpha curves as the grid.

    This is the picture the solver works in.  Beta closes up on the torus but not here: it
    runs off one edge and comes back on the next tile along, and a disc is a piece of that
    lifted curve closed up along the grid.
    """
    tune_spacing(diagram)
    tx, ty = (tiles, tiles) if isinstance(tiles, int) else tiles
    paths = route(diagram)
    text = (caption_for(diagram, f"universal cover, {tx} x {ty} domains")
            if caption is None else caption)
    pad = max(18.0, cell * 0.14)
    bottom = pad + 34
    total_w, total_h = cell * tx, cell * ty
    W = max(total_w + 2 * pad, 2 * pad + _text_width(text, 12))
    H = total_h + pad + bottom

    def to(p):
        return (pad + p[0] * cell, pad + total_h - p[1] * cell)

    parts = [f'<rect width="{_fmt(W)}" height="{_fmt(H)}" fill="{COLOURS["paper"]}"/>']

    parts.append(f'<g stroke="{COLOURS["grid"]}" stroke-width="2">')
    for k in range(tx + 1):
        a, b = to((k, 0)), to((k, ty))
        parts.append(f'<line x1="{_fmt(a[0])}" y1="{_fmt(a[1])}" '
                     f'x2="{_fmt(b[0])}" y2="{_fmt(b[1])}"/>')
    for l in range(ty + 1):
        a, b = to((0, l)), to((tx, l))
        parts.append(f'<line x1="{_fmt(a[0])}" y1="{_fmt(a[1])}" '
                     f'x2="{_fmt(b[0])}" y2="{_fmt(b[1])}"/>')
    parts.append("</g>")

    # one copy of beta, then reused: every tile is the same picture, so there is no reason
    # to write it out tiles*tiles times
    tile = "".join(f'<path d="{d}"/>'
                   for d in beta_paths(diagram, lambda q: to((q[0], q[1] + ty - 1))))
    parts.append(f'<defs><g id="beta" fill="none" stroke="{COLOURS["arc"]}" '
                 f'stroke-width="1.6" stroke-linecap="round" '
                 f'stroke-linejoin="round">{tile}</g></defs>')
    for k in range(tx):
        for l in range(ty):
            parts.append(f'<use href="#beta" x="{_fmt(k * cell)}" '
                         f'y="{_fmt((ty - 1 - l) * cell)}"/>')

    if cell >= 90:
        parts.append(f'<g fill="{COLOURS["generator"]}">')
        for k in range(tx):
            for l in range(ty):
                for arc in diagram.arcs:
                    for end in arc.ends():
                        px, py = position(diagram, end)
                        x, y = to((px + k, py + l))
                        parts.append(f'<circle cx="{_fmt(x)}" cy="{_fmt(y)}" r="1.9"/>')
        parts.append("</g>")

    if basepoints:
        z_at, w_at = _basepoints(diagram)
        parts.append(f'<g fill="{COLOURS["basepoint"]}">')
        for point in (z_at, w_at):
            if point is None:
                continue
            for k in range(tx):
                for l in range(ty):
                    x, y = to((point[0] + k, point[1] + l))
                    parts.append(f'<circle cx="{_fmt(x)}" cy="{_fmt(y)}" r="2.6"/>')
        parts.append("</g>")

    if mark_centre:
        a = to((tx // 2, ty // 2 + 1))
        parts.append(f'<rect x="{_fmt(a[0])}" y="{_fmt(a[1])}" width="{_fmt(cell)}" '
                     f'height="{_fmt(cell)}" fill="none" '
                     f'stroke="{COLOURS["grid_strong"]}" stroke-width="3"/>')

    if text:
        parts.append(f'<text x="{_fmt(pad)}" y="{_fmt(H - 14)}" '
                     f'font-family="ui-sans-serif,system-ui,sans-serif" font-size="12" '
                     f'fill="{COLOURS["ink"]}">{_esc(text)}</text>')
    return _svg(W, H, "\n  ".join(parts), f"{diagram.name} universal cover")


# ------------------------------------------------------------------ the discs

def _fresh(diagram: Diagram, discs):
    """Copies of the discs with no polygon yet, for the embedding the picture will use.

    A picture spreads the generators out first (:func:`~heegaard.layout.tune_spacing`), so a
    region the solver attached in its own even-spaced embedding is the same disc in a
    slightly different place.  Drawing it over the re-spaced beta would put its edges beside
    the strands rather than on them, so every disc is re-attached here instead.
    """
    from dataclasses import replace
    tune_spacing(diagram)
    return [replace(d, region=None) for d in discs]


def bounding_box(polygon):
    xs = [p[0] for p in polygon]
    ys = [p[1] for p in polygon]
    return (min(xs), min(ys), max(xs), max(ys))


def sample_discs(discs, limit: int = 80, per_class: int = 1):
    """Choose a readable handful rather than all of them.

    Two things make a disc worth drawing: being unlike the others, and being big enough to
    see.  So every (chord word, U power) class contributes its largest disc first -- the whole
    variety of the diagram, one specimen each -- and what budget is left goes to the largest
    discs still unpicked.  Area is signed and always negative, so ``abs`` is the size.
    """
    by_class: dict[str, list] = {}
    for d in discs:
        by_class.setdefault(f"{d.word}|{d.U}", []).append(d)
    for group in by_class.values():
        group.sort(key=lambda d: -abs(d.area))

    chosen, picked = [], set()
    groups = sorted(by_class.values(), key=lambda g: -abs(g[0].area))
    for rank in range(per_class):
        for group in groups:
            if rank < len(group) and len(chosen) < limit and id(group[rank]) not in picked:
                chosen.append(group[rank])
                picked.add(id(group[rank]))
    for d in sorted(discs, key=lambda d: -abs(d.area)):
        if len(chosen) >= limit:
            break
        if id(d) not in picked:
            chosen.append(d)
            picked.add(id(d))
    return chosen, len(by_class)


def pack_into_slots(boxes, gap: int = 0):
    """Slide each disc by a whole number of copies so that none overlaps another.

    Shelf packing, tallest first.  Integer shifts only, because only a lattice vector carries
    a disc to another lift of the same disc -- so every disc is still drawn where it honestly
    lives in the cover, just not on top of its neighbours.
    """
    sizes = [(math.ceil(b[2]) - math.floor(b[0]) + gap,
              math.ceil(b[3]) - math.floor(b[1]) + gap) for b in boxes]
    if not sizes:
        return []
    total = sum(w * h for w, h in sizes)
    target = max(max(w for w, _ in sizes), math.ceil(math.sqrt(total)))

    order = sorted(range(len(boxes)), key=lambda k: -sizes[k][1])
    shifts = [None] * len(boxes)
    pen_x = pen_y = shelf = 0
    for k in order:
        w, h = sizes[k]
        if pen_x + w > target and pen_x > 0:
            pen_x, pen_y, shelf = 0, pen_y + shelf, 0
        shifts[k] = (pen_x - math.floor(boxes[k][0]), pen_y - math.floor(boxes[k][1]))
        pen_x += w
        shelf = max(shelf, h)
    return shifts


def _assign_colours(boxes, order, margin: float = 0.6):
    """Greedy, so that two discs close enough to read as one shape are never the same hue."""
    def near(p, q):
        return (p[0] - margin < q[2] and q[0] - margin < p[2]
                and p[1] - margin < q[3] and q[1] - margin < p[3])

    colour = [-1] * len(boxes)
    for place, k in enumerate(order):
        taken = {colour[j] for j in range(len(boxes))
                 if j != k and colour[j] >= 0 and near(boxes[k], boxes[j])}
        c = place % len(PALETTE)
        for _ in range(len(PALETTE)):
            if c not in taken:
                break
            c = (c + 1) % len(PALETTE)
        colour[k] = c
    return colour


def render_discs(diagram: Diagram, discs, cell: float = 74, limit: int | None = 80,
                 arrange: str = "packed", alpha: float = 0.55, pad: int = 1,
                 labels: bool = True, caption: str | None = None) -> str:
    """Every disc at once, on a large universal cover.

    A disc translated by a lattice vector is another lift of the same disc, so the picture is
    an honest picture of the cover whichever copy each one is drawn in.  That is what makes a
    catalogue possible: left where the enumeration found them the discs sit on top of one
    another, so ``arrange="packed"`` slides each into a free slot instead.  ``"insitu"``
    leaves them where they were found, which is the truthful picture and usually unreadable.
    """
    from .format import _gen_key
    from .solver import attach_regions

    # canonical order first, so the picture depends on which discs there are and not on the
    # order they arrived in: a table solved here and the same table read back from a file --
    # or written by the JS solver -- must draw the same picture.
    discs = _fresh(diagram, discs)
    discs = sorted(discs, key=lambda d: (_gen_key(d.source), _gen_key(d.target), d.U, d.word))
    chosen, classes = (sample_discs(discs, limit) if limit and len(discs) > limit
                       else (list(discs), len({f"{d.word}|{d.U}" for d in discs})))
    attach_regions(diagram, chosen)
    if not chosen:
        raise ValueError(f"{diagram.name} bounds no discs, so there is nothing to draw")

    shifts = (pack_into_slots([bounding_box(d.region) for d in chosen])
              if arrange == "packed" else [(0, 0)] * len(chosen))
    regions = [[(x + sx, y + sy) for x, y in d.region]
               for d, (sx, sy) in zip(chosen, shifts)]
    boxes = [bounding_box(r) for r in regions]

    i0 = math.floor(min(b[0] for b in boxes)) - pad
    j0 = math.floor(min(b[1] for b in boxes)) - pad
    i1 = math.ceil(max(b[2] for b in boxes)) + pad
    j1 = math.ceil(max(b[3] for b in boxes)) + pad

    shown = (f"{len(chosen)} of {len(discs)} discs" if len(chosen) < len(discs)
             else f"all {len(discs)} discs")
    text = (f"{diagram.name}  ·  {shown} in {classes} (word, U) classes  ·  "
            f"{i1 - i0} x {j1 - j0} copies of the domain"
            if caption is None else caption)

    margin = 14.0
    total_w, total_h = (i1 - i0) * cell, (j1 - j0) * cell
    W = max(total_w + 2 * margin, 2 * margin + _text_width(text, 13))
    H = total_h + 2 * margin + 26

    def to(p):
        return (margin + (p[0] - i0) * cell, margin + total_h - (p[1] - j0) * cell)

    parts = [f'<rect width="{_fmt(W)}" height="{_fmt(H)}" fill="{COLOURS["paper"]}"/>']

    parts.append(f'<g stroke="{COLOURS["grid"]}" stroke-width="1.4">')
    for i in range(i0, i1 + 1):
        a, b = to((i, j0)), to((i, j1))
        parts.append(f'<line x1="{_fmt(a[0])}" y1="{_fmt(a[1])}" '
                     f'x2="{_fmt(b[0])}" y2="{_fmt(b[1])}"/>')
    for j in range(j0, j1 + 1):
        a, b = to((i0, j)), to((i1, j))
        parts.append(f'<line x1="{_fmt(a[0])}" y1="{_fmt(a[1])}" '
                     f'x2="{_fmt(b[0])}" y2="{_fmt(b[1])}"/>')
    parts.append("</g>")

    tile = "".join(f'<path d="{d}"/>'
                   for d in beta_paths(diagram, lambda q: to((q[0] + i0, q[1] + j1 - 1))))
    parts.append(f'<defs><g id="beta" fill="none" stroke="{COLOURS["arc"]}" '
                 f'stroke-width="1.1" stroke-linejoin="round">{tile}</g></defs>')
    for i in range(i0, i1):
        for j in range(j0, j1):
            parts.append(f'<use href="#beta" x="{_fmt((i - i0) * cell)}" '
                         f'y="{_fmt((j1 - 1 - j) * cell)}"/>')

    placement = sorted(range(len(boxes)), key=lambda k: (boxes[k][1], boxes[k][0]))
    colour = _assign_colours(boxes, placement)
    # biggest first, so a small disc sitting inside a big one still shows
    area_of = lambda b: (b[2] - b[0]) * (b[3] - b[1])
    for k in sorted(range(len(chosen)), key=lambda k: -area_of(boxes[k])):
        disc, hue = chosen[k], PALETTE[colour[k]]
        points = " ".join(f"{_fmt(x)},{_fmt(y)}" for x, y in map(to, regions[k]))
        label = f"{disc.source} -> {disc.target}  U^{disc.U}  {disc.word or 'no chords'}"
        parts.append(f'<polygon points="{points}" fill="{hue}" fill-opacity="{alpha}" '
                     f'stroke="{hue}" stroke-width="1">'
                     f'<title>{_esc(label)}</title></polygon>')

    size = cell * 0.125
    if labels and size >= 5.5:
        parts.append(f'<g font-family="ui-monospace,Menlo,monospace" '
                     f'font-size="{_fmt(size)}" fill="{COLOURS["ink"]}">')
        for k, disc in enumerate(chosen):
            x, y = to((math.floor(boxes[k][0]) + 0.05, math.floor(boxes[k][1]) + 0.04))
            head = f"{disc.source}\u2192{disc.target}"
            tail = f"U^{disc.U} {disc.word}" if disc.word else f"U^{disc.U}"
            parts.append(f'<text x="{_fmt(x)}" y="{_fmt(y - size - 1)}">{_esc(head)}</text>'
                         f'<text x="{_fmt(x)}" y="{_fmt(y)}">{_esc(tail)}</text>')
        parts.append("</g>")

    parts.append(f'<text x="{_fmt(margin)}" y="{_fmt(H - 8)}" '
                 f'font-family="ui-sans-serif,system-ui,sans-serif" font-size="13" '
                 f'fill="{COLOURS["ink"]}">{_esc(text)}</text>')
    return _svg(W, H, "\n  ".join(parts), f"{diagram.name} discs")


# ------------------------------------------------------------------ the atlas

def atlas_sheets(discs):
    """The discs split by what kind of operation each one is, for an atlas in a few sheets.

    The ``x`` generators are ``iota_1`` and the ``y`` are ``iota_0``, and the split is the one
    the idempotents suggest: the operations that start and end at ``x``, then everything else
    cut by length of chord word -- the differentials and ``m_2``, then the higher products.
    On Q(2,2,2) that is 42, 37 and 31 discs.
    """
    xx = [d for d in discs if d.source[0] == "x" and d.target[0] == "x"]
    rest = [d for d in discs if not (d.source[0] == "x" and d.target[0] == "x")]
    return [("x → x", xx),
            ("into or out of y, at most one chord", [d for d in rest if len(d.chords) <= 1]),
            ("into or out of y, two chords or more", [d for d in rest if len(d.chords) >= 2])]


def _raster(polygon, R: int):
    """The pixels of a polygon on a grid of ``R`` per copy of the domain, as row bitmasks.

    A pixel is in when its centre is, by the even-odd rule along each row.  Rows as Python
    ints, so that sliding a disc by a whole copy is a shift and a collision is an ``&``.
    Returns ``{row: mask}`` with bit ``k`` the pixel whose centre is at ``(k + 1/2) / R``.
    """
    rows: dict[int, int] = {}
    ys = [p[1] for p in polygon]
    edges = list(zip(polygon, polygon[1:] + polygon[:1]))
    for iy in range(math.floor(min(ys) * R), math.ceil(max(ys) * R) + 1):
        yc = (iy + 0.5) / R
        xs = sorted(a[0] + (yc - a[1]) * (b[0] - a[0]) / (b[1] - a[1])
                    for a, b in edges if (a[1] <= yc) != (b[1] <= yc))
        mask = 0
        for left, right in zip(xs[::2], xs[1::2]):
            k0, k1 = math.ceil(left * R - 0.5), math.floor(right * R - 0.5)
            if k1 >= k0:
                mask |= ((1 << (k1 - k0 + 1)) - 1) << k0
        if mask:
            rows[iy] = mask
    return rows


def _rows_shift(rows, dx: int, dy: int):
    return {y + dy: (m << dx if dx >= 0 else m >> -dx) for y, m in rows.items()}


def _deepest(rows):
    """A pixel as far inside as the mask goes, by eroding until nothing is left, and how
    many erosions that took -- which is roughly the radius, in pixels, of room for a label."""
    depth = 0
    while True:
        inner = {}
        for y, m in rows.items():
            e = m & (m << 1) & (m >> 1) & rows.get(y - 1, 0) & rows.get(y + 1, 0)
            if e:
                inner[y] = e
        if not inner:
            break
        rows, depth = inner, depth + 1
    ys = sorted(rows)
    y = ys[len(ys) // 2]
    bits = [k for k in range(rows[y].bit_length()) if rows[y] >> k & 1]
    return bits[len(bits) // 2], y, depth


def pack_tight(regions, columns: int, R: int = 48):
    """Slide each disc by a whole number of copies into a strip ``columns`` copies wide,
    as low as it will go without overlapping anything already placed.

    Unlike :func:`pack_into_slots` this tests the discs themselves and not their boxes, so a
    thin disc can sit in the crook of a fat one -- which is most of what makes an atlas
    dense.  Largest first, then the lowest row and leftmost column that is free.  Integer
    shifts only, so every disc is still a lift of itself.  Returns the shifts and the rasters
    at their final places.
    """
    rasters = [_raster(r, R) for r in regions]
    width = columns * R
    order = sorted(range(len(regions)), key=lambda k: -sum(bin(m).count("1")
                                                          for m in rasters[k].values()))
    occupied: dict[int, int] = {}
    shifts, placed = [None] * len(regions), [None] * len(regions)
    for k in order:
        rows = rasters[k]
        lo = min((m & -m).bit_length() - 1 for m in rows.values())
        hi = max(m.bit_length() for m in rows.values())
        bottom = min(rows)
        if hi - lo > width:
            raise ValueError(f"a disc is wider than {columns} copies of the domain")
        a_range = range(math.ceil(-lo / R), math.floor((width - hi) / R) + 1)
        b = math.ceil(-bottom / R)
        while shifts[k] is None:
            for a in a_range:
                if not any((m << (a * R) if a >= 0 else m >> (-a * R))
                           & occupied.get(y + b * R, 0) for y, m in rows.items()):
                    shifts[k] = (a, b)
                    break
            else:
                b += 1
        a, b = shifts[k]
        placed[k] = _rows_shift(rows, a * R, b * R)
        for y, m in placed[k].items():
            occupied[y] = occupied.get(y, 0) | m
    return shifts, placed


def _touching(p, q, reach: int = 3) -> bool:
    """Do two placed rasters come within ``reach`` pixels of each other?"""
    for y, m in p.items():
        grown = 0
        for s in range(reach + 1):
            grown |= (m << s) | (m >> s)
        for dy in range(-reach, reach + 1):
            if grown & q.get(y + dy, 0):
                return True
    return False


#: the look of a figure in a paper: Computer Modern, black ink, alpha in red, beta in blue.
#: Latin Modern and CMU are both Computer Modern as OpenType; neither is a system font, so
#: the svg names them and falls back to any serif.  TeX Live ships both (`kpsewhich lmroman10-regular.otf`).
ATLAS_FONT = "'Latin Modern Roman', 'LM Roman 10', 'CMU Serif', 'Computer Modern Serif', serif"
ATLAS_INK = {"alpha": "#d7372b", "beta": "#2b3bd1", "ink": "#000000", "paper": "#ffffff"}

#: pale enough that beta reads through every one of them; neighbours never share one
ATLAS_PALETTE = ["#f4a6a0", "#9fc5e8", "#b6d7a8", "#ffe599", "#d5a6e6", "#f9cb9c",
                 "#a2c4c9", "#ea9999", "#c9daf8", "#d9ead3", "#fff2cc", "#ead1dc",
                 "#b4a7d6", "#ffd966", "#93c47d", "#76a5af", "#e6b8af", "#cfe2f3",
                 "#f6b26b", "#8eb8e5", "#c27ba0", "#a4c2a5", "#e0c48c", "#bfbfbf"]


def _sub(base: str, y: float, low: str = "", high: str = "", size: float = 12.0,
         italic: bool = True) -> str:
    """``base`` with a subscript and/or superscript, as tspans on the baseline ``y``.

    Every piece carries an absolute ``y`` rather than a ``dy`` that is undone afterwards: the
    undoing would need a tspan of its own, Inkscape skips an empty one, and then every script
    leaves the rest of the line a little lower -- which reads as the line slanting."""
    small = _fmt(size * 0.7)
    style = ' font-style="italic"' if italic else ""
    out = f'<tspan y="{_fmt(y)}"{style}>{base}</tspan>'
    if low:
        out += f'<tspan y="{_fmt(y + size * 0.25)}" font-size="{small}">{_script(low)}</tspan>'
    if high:
        out += f'<tspan y="{_fmt(y - size * 0.4)}" font-size="{small}">{_script(high)}</tspan>'
    return out


def _script(text: str) -> str:
    """An index as TeX sets it: letters italic, digits upright, and a real minus sign.  So a
    family's index, ``8i-3+j``, reads as maths and not as a filename."""
    text = text.strip("{}")
    out = []
    for c in text:
        if c.isalpha():
            out.append(f'<tspan font-style="italic">{_esc(c)}</tspan>')
        else:
            out.append("\u2212" if c == "-" else _esc(c))
    return "".join(out)


def _plain(text: str, y: float) -> str:
    return f'<tspan y="{_fmt(y)}">{text}</tspan>'


#: Latin Modern Roman has no Greek; the rho is MATHEMATICAL ITALIC SMALL RHO from Latin
#: Modern Math, which is the glyph TeX's \\rho sets, falling back to an ordinary rho
_RHO = ("<tspan font-family=\"'Latin Modern Math', 'STIX Two Math', 'Cambria Math', serif\">"
        "\U0001D70C</tspan>")


def _generator(name: str, y: float, size: float) -> str:
    curve, _, index = name.partition("_")
    return _sub(_esc(curve), y, index, size=size) if index else _plain(_esc(name), y)


def _operation(disc, y: float, size: float, names=None) -> str:
    """The disc as the operation it is: ``m_{n+1}(x, rho_a, ...) = U^k y``.

    ``names`` replaces the source and target with other spellings of them -- a family's,
    say, ``("y_j", "x_{8i-3+j}")`` -- while the U power and the chords stay the disc's own.
    """
    source, target = names or (disc.source, disc.target)
    chords = [c.replace("rho_", "") for c in disc.chords]
    args = [_generator(source, y, size)] + [_sub(_RHO, y, c, size=size, italic=False)
                                            for c in chords]
    power = "" if disc.U == 0 else (_sub("U", y, high="" if disc.U == 1 else str(disc.U),
                                         size=size) + _plain("\u2009", y))
    # fixed-width spaces, as TeX would set them: SVG collapses an ordinary space at the edge
    # of a tspan, and every space here is at an edge
    return (_sub("m", y, str(len(chords) + 1), size=size) + _plain("(", y)
            + _plain(",\u2006", y).join(args) + _plain(")\u2004=\u2004", y)
            + power + _generator(target, y, size))


def _operation_width(disc, size: float, names=None) -> float:
    """An estimate of how wide :func:`_operation` sets, in the same spirit as _text_width."""
    source, target = names or (disc.source, disc.target)
    chars = 8 + len(source) + len(target) + 3 * len(disc.chords) \
        + sum(len(c) - 4 for c in disc.chords) * 0.7 + (2 if disc.U else 0)
    return chars * size * 0.5


def _italic_letters(text: str) -> str:
    """Set the one-letter words of a caption -- x, y, Q, U -- in italic, as maths."""
    import re
    return re.sub(r"(?<![\w(])([A-Za-z])(?![\w])",
                  lambda m: f'<tspan font-style="italic">{m.group(1)}</tspan>', _esc(text))


def _darker(hue: str, by: float = 0.55) -> str:
    """The same colour, darker: an outline for a fill."""
    r, g, b = (int(hue[i:i + 2], 16) for i in (1, 3, 5))
    return "#" + "".join(f"{round(c * by):02x}" for c in (r, g, b))


def _hue(colour) -> str:
    """A palette index, or a colour given outright."""
    return colour if isinstance(colour, str) else ATLAS_PALETTE[colour]


def render_atlas(diagram: Diagram, discs, columns: int = 5, cell: float = 220,
                 title: str | None = None, punctured: bool = True, alpha: float = 0.9,
                 key: bool = True, centres=None, rows: int | None = None, names=None,
                 caption: bool = True, colours=None, number: float = 14.0,
                 numbers: bool = True) -> str:
    """Discs packed edge to edge on a strip of the universal cover, one colour each.

    The dense counterpart of :func:`render_discs`: every disc is slid by a lattice vector
    (so it is still an honest lift) into the lowest free place in a strip ``columns`` copies
    wide, tested against the other discs' actual shapes rather than their boxes.  Each disc
    carries a number at its deepest point, and the key beside the strip says which operation
    it is.  Numbers follow (word, U, source, target), so the key reads grouped by kind.

    Drawn as a figure for a paper: Computer Modern, blue beta, red alpha, pale fills.  The
    cell is large on purpose -- Q(2,2,2) has thirty generators along one edge, and below
    about 200 pixels a side its strands run together into a solid band.

    ``punctured`` draws the boundary of the bordered diagram: the corner of the square is the
    puncture, so every lattice point of the cover is a hole.

    To lay a sheet out by hand instead, give ``centres``: for each disc, where its middle
    should land, in copies of the domain from the bottom-left of the sheet.  Each disc is
    moved by the lattice vector that brings its box's centre nearest there, the discs keep
    the order given and are numbered in it, and ``rows`` fixes the height.  ``names`` gives
    the key other spellings of each disc's source and target, and ``caption=False`` leaves
    the line under the picture to whoever is placing the figure.  ``colours`` gives each
    disc its fill outright -- to colour by kind rather than keep neighbours apart -- and
    ``number`` is the size of the numbers on the discs, which only mean anything beside a
    key -- ``numbers=False`` leaves them off.
    """
    from .format import _gen_key
    from .solver import attach_regions

    discs = _fresh(diagram, discs)
    if not discs:
        raise ValueError("no discs to draw")
    R = 48
    if centres is None:
        discs = sorted(discs, key=lambda d: (len(d.chords), d.word, d.U,
                                             _gen_key(d.source), _gen_key(d.target)))
        attach_regions(diagram, discs)
        shifts, placed = pack_tight([d.region for d in discs], columns, R)
    else:
        attach_regions(diagram, discs)
        shifts = []
        for disc, (cx, cy) in zip(discs, centres):
            box = bounding_box(disc.region)
            shifts.append((round(cx - (box[0] + box[2]) / 2), round(cy - (box[1] + box[3]) / 2)))
        placed = [_rows_shift(_raster(d.region, R), a * R, b * R)
                  for d, (a, b) in zip(discs, shifts)]
    regions = [[(x + a, y + b) for x, y in d.region] for d, (a, b) in zip(discs, shifts)]
    rows_used = rows or math.ceil(max(max(p) for p in placed) / R)
    names = names or [None] * len(discs)

    text = title or f"{diagram.name}, {len(discs)} discs"
    ink, size = ATLAS_INK, 15.0
    margin, foot = 20.0, (52.0 if caption else 0.0)
    total_w, total_h = columns * cell, rows_used * cell
    line, key_w = size * 1.55, 0.0
    if key:
        key_w = 60 + max(_operation_width(d, size, n) for d, n in zip(discs, names))
    W = total_w + 2 * margin + key_w
    H = max(total_h, line * (len(discs) + 1)) + 2 * margin + foot
    if caption:
        W = max(W, _text_width(text, 17) + 80 + 2 * margin)

    def to(p):
        return (margin + p[0] * cell, margin + total_h - p[1] * cell)

    parts = [f'<rect width="{_fmt(W)}" height="{_fmt(H)}" fill="{ink["paper"]}"/>',
             f'<clipPath id="strip"><rect x="{_fmt(margin)}" y="{_fmt(margin)}" '
             f'width="{_fmt(total_w)}" height="{_fmt(total_h)}"/></clipPath>',
             '<g clip-path="url(#strip)">']

    # colour: greedy over discs in order of size, never matching a disc it touches
    colour = [-1] * len(discs) if colours is None else list(colours)
    for k in (sorted(range(len(discs)), key=lambda k: -abs(discs[k].area))
              if colours is None else ()):
        taken = {colour[j] for j in range(len(discs))
                 if colour[j] >= 0 and _touching(placed[k], placed[j])}
        c = k % len(ATLAS_PALETTE)
        while c in taken and len(taken) < len(ATLAS_PALETTE):
            c = (c + 1) % len(ATLAS_PALETTE)
        colour[k] = c

    for k, disc in enumerate(discs):
        hue = _hue(colour[k])
        d = _path_d([to(p) for p in regions[k]]) + "Z"
        label = f"{disc.source} -> {disc.target}  U^{disc.U}  {disc.word or 'no chords'}"
        # coloured by kind, two discs of one colour can touch, and only an edge tells them
        # apart; coloured to keep neighbours apart, they never need one
        edge = ("none" if colours is None
                else f'{_darker(hue)}" stroke-width="1.4" stroke-linejoin="round')
        parts.append(f'<path d="{d}" fill="{hue}" fill-opacity="{alpha}" stroke="{edge}">'
                     f'<title>{k + 1}: {_esc(label)}</title></path>')

    tile = "".join(f'<path d="{d}"/>'
                   for d in beta_paths(diagram, lambda q: to((q[0], q[1] + rows_used - 1))))
    parts.append(f'<defs><g id="beta" fill="none" stroke="{ink["beta"]}" '
                 f'stroke-width="0.75" stroke-linecap="round" stroke-linejoin="round">'
                 f'{tile}</g></defs>')
    for i in range(columns):
        for j in range(rows_used):
            parts.append(f'<use href="#beta" x="{_fmt(i * cell)}" '
                         f'y="{_fmt((rows_used - 1 - j) * cell)}"/>')

    parts.append(f'<g stroke="{ink["alpha"]}" stroke-width="1.6">')
    for i in range(columns + 1):
        a, b = to((i, 0)), to((i, rows_used))
        parts.append(f'<line x1="{_fmt(a[0])}" y1="{_fmt(a[1])}" '
                     f'x2="{_fmt(b[0])}" y2="{_fmt(b[1])}"/>')
    for j in range(rows_used + 1):
        a, b = to((0, j)), to((columns, j))
        parts.append(f'<line x1="{_fmt(a[0])}" y1="{_fmt(a[1])}" '
                     f'x2="{_fmt(b[0])}" y2="{_fmt(b[1])}"/>')
    parts.append("</g>")

    _, w_at = _basepoints(diagram)
    if w_at is not None:
        parts.append(f'<g fill="{ink["ink"]}">')
        for i in range(columns):
            for j in range(rows_used):
                x, y = to((w_at[0] + i, w_at[1] + j))
                parts.append(f'<circle cx="{_fmt(x)}" cy="{_fmt(y)}" r="2"/>')
        parts.append("</g>")

    if punctured:
        rx, ry = cell * 0.028, cell * 0.04
        parts.append(f'<g fill="{ink["paper"]}" stroke="{ink["ink"]}" stroke-width="1">')
        for i in range(columns + 1):
            for j in range(rows_used + 1):
                x, y = to((i, j))
                parts.append(f'<ellipse cx="{_fmt(x)}" cy="{_fmt(y)}" rx="{_fmt(rx)}" '
                             f'ry="{_fmt(ry)}"/>')
        parts.append("</g>")
    parts.append("</g>")

    parts.append(f'<rect x="{_fmt(margin)}" y="{_fmt(margin)}" width="{_fmt(total_w)}" '
                 f'height="{_fmt(total_h)}" fill="none" stroke="{ink["alpha"]}" '
                 f'stroke-width="1.6"/>')

    parts.append(f'<g font-family="{ATLAS_FONT}" font-size="{_fmt(number)}" '
                 f'fill="{ink["ink"]}" text-anchor="middle" stroke="{ink["paper"]}" '
                 f'stroke-width="{_fmt(number * 0.2)}" stroke-linejoin="round" '
                 f'paint-order="stroke">')
    for k in range(len(discs) if numbers else 0):
        px, py, depth = _deepest(placed[k])
        if depth * cell / R >= number * 0.6:
            x, y = to(((px + 0.5) / R, (py + 0.5) / R))
            parts.append(f'<text x="{_fmt(x)}" y="{_fmt(y + number * 0.34)}">{k + 1}</text>')
        else:
            # too thin to hold its own number without hiding under it: put the number
            # beside the disc, off whichever end is not against the edge of the strip
            mask = placed[k]
            right = max(m.bit_length() for m in mask.values())
            if right < (columns - 0.15) * R:
                row = max(mask, key=lambda y: mask[y].bit_length())
                x, y = to((right / R, (row + 0.5) / R))
                x, anchor = x + 3, "start"
            else:
                left = min((m & -m).bit_length() - 1 for m in mask.values())
                row = next(y for y in sorted(mask) if (mask[y] & -mask[y]).bit_length() - 1
                           == left)
                x, y = to((left / R, (row + 0.5) / R))
                x, anchor = x - 3, "end"
            parts.append(f'<text x="{_fmt(x)}" y="{_fmt(y + number * 0.34)}" '
                         f'text-anchor="{anchor}">{k + 1}</text>')
    parts.append("</g>")

    if key:
        x0 = margin + total_w + 30
        parts.append(f'<g font-family="{ATLAS_FONT}" font-size="{_fmt(size)}" '
                     f'fill="{ink["ink"]}">')
        for k, disc in enumerate(discs):
            y = margin + line * (k + 0.8)
            hue = _hue(colour[k])
            parts.append(f'<rect x="{_fmt(x0)}" y="{_fmt(y - size * 0.72)}" '
                         f'width="{_fmt(size * 0.8)}" height="{_fmt(size * 0.8)}" '
                         f'fill="{hue}" stroke="{ink["ink"]}" stroke-width="0.5"/>'
                         f'<text x="{_fmt(x0 + 46)}" y="{_fmt(y)}" text-anchor="end">'
                         f'{k + 1}</text>'
                         f'<text x="{_fmt(x0 + 56)}" y="{_fmt(y)}">'
                         f'{_operation(disc, y, size, names[k])}</text>')
        parts.append("</g>")

    if caption:
        parts.append(f'<text x="{_fmt(margin)}" y="{_fmt(H - margin)}" font-family="{ATLAS_FONT}" '
                     f'font-size="17" fill="{ink["ink"]}">'
                     f'A<tspan font-size="13" letter-spacing="0.6">TLAS</tspan>. '
                     f'{_italic_letters(text)}</text>')
    return _svg(W, H, "\n  ".join(parts), text)


# ------------------------------------------------------------------ the Chen form

#: the families of a Chen form, and the colour each is drawn in
CHEN_COLOURS = {"rainbow-z": "#c1666b", "rainbow-w": "#2a9d8f", "strand": "#5f6caf",
                "dependent": "#b5651d", "dependent-turn": "#9d4edd"}


def render_chen(form, cut: bool = False, cell: float = 520,
                caption: str | None = None) -> str:
    """The Chen form: the torus cut along ``mu`` only, so an annulus.

    The two red edges are the same curve ``mu``, glued; the dashed edges are where the domain
    happens to be cut across, and beta does not touch them -- which is the whole point of this
    picture, and why it has no generators on that curve yet.

    With ``cut``, the line the fundamental region is about to be slid to is drawn across it,
    through ``z``, together with every place it meets beta.  Those meetings are the new
    generators, and they are numbered along the line, left to right, because that is the order
    they will appear in.
    """
    from .chen import basepoints, cut_height, polyline, recut, wrapped

    M = form.M
    pad = max(34.0, cell * 0.09)
    bottom = pad + 34
    W, H = cell + 2 * pad, cell + pad + bottom

    def to(x, h):
        return (pad + x * cell, pad + (h / M) * cell)

    parts = [f'<rect width="{_fmt(W)}" height="{_fmt(H)}" fill="{COLOURS["paper"]}"/>']
    # the two glued copies of mu, and the cut the domain currently has
    for x in (0.0, 1.0):
        a, b = to(x, 0), to(x, M)
        parts.append(f'<line x1="{_fmt(a[0])}" y1="{_fmt(a[1])}" x2="{_fmt(b[0])}" '
                     f'y2="{_fmt(b[1])}" stroke="{COLOURS["grid"]}" stroke-width="2.5"/>')
    for h in (0, M):
        a, b = to(0, h), to(1, h)
        parts.append(f'<line x1="{_fmt(a[0])}" y1="{_fmt(a[1])}" x2="{_fmt(b[0])}" '
                     f'y2="{_fmt(b[1])}" stroke="#c9c4bd" stroke-width="1.6" '
                     f'stroke-dasharray="6 5"/>')

    for arc in form.arcs:
        hue = CHEN_COLOURS.get(arc[4], COLOURS["arc"])
        for piece in wrapped(polyline(form, arc, 60), M):
            d = _path_d([to(x, h) for x, h in piece])
            parts.append(f'<path d="{d}" fill="none" stroke="{hue}" stroke-width="2" '
                         f'stroke-linecap="round"/>')

    parts.append(f'<g fill="{COLOURS["generator"]}">')
    for slot in range(M):
        for x in (0.0, 1.0):
            cx, cy = to(x, slot)
            parts.append(f'<circle cx="{_fmt(cx)}" cy="{_fmt(cy)}" r="2.6"/>')
    parts.append("</g>")

    if M <= 34:
        size = min(11.0, max(6.5, cell / M * 0.6))
        parts.append(f'<g font-family="ui-monospace,Menlo,monospace" font-size="{_fmt(size)}" '
                     f'fill="{COLOURS["label"]}">')
        for slot in range(M):
            x, y = to(0.0, slot)
            parts.append(f'<text x="{_fmt(x - 7)}" y="{_fmt(y + size * 0.36)}" '
                         f'text-anchor="end">{slot}</text>')
            x, y = to(1.0, slot)
            parts.append(f'<text x="{_fmt(x + 7)}" y="{_fmt(y + size * 0.36)}" '
                         f'text-anchor="start">{slot}</text>')
        parts.append("</g>")

    if cut:
        c = cut_height(form)
        a, b = to(-0.03, c), to(1.03, c)
        parts.append(f'<line x1="{_fmt(a[0])}" y1="{_fmt(a[1])}" x2="{_fmt(b[0])}" '
                     f'y2="{_fmt(b[1])}" stroke="{COLOURS["basepoint"]}" stroke-width="2" '
                     f'stroke-dasharray="7 4"/>')
        _, hits = recut(form)
        parts.append(f'<g font-family="ui-monospace,Menlo,monospace" font-size="10" '
                     f'fill="{COLOURS["basepoint"]}">')
        for hit in hits:
            x, y = to(hit["x"], c)
            parts.append(f'<circle cx="{_fmt(x)}" cy="{_fmt(y)}" r="4" '
                         f'fill="{COLOURS["basepoint"]}"/>')
            parts.append(f'<text x="{_fmt(x)}" y="{_fmt(y - 8)}" '
                         f'text-anchor="middle">{hit["index"]}</text>')
        parts.append("</g>")

    parts.append(f'<g fill="{COLOURS["basepoint"]}" '
                 f'font-family="ui-monospace,Menlo,monospace" font-size="12">')
    for name, (x, h) in basepoints(form).items():
        cx, cy = to(x, h)
        parts.append(f'<circle cx="{_fmt(cx)}" cy="{_fmt(cy)}" r="3.6"/>'
                     f'<text x="{_fmt(cx - 12)}" y="{_fmt(cy + 4)}" '
                     f'text-anchor="end">{name}</text>')
    parts.append("</g>")

    text = caption if caption is not None else (
        f"H({form.r},{form.s}) Chen form  ·  {form.M} points on mu  ·  "
        f"D = {form.D} dependent arcs  ·  sigma = {_chen_sigma(form)}")
    parts.append(f'<text x="{_fmt(pad)}" y="{_fmt(H - 14)}" '
                 f'font-family="ui-sans-serif,system-ui,sans-serif" font-size="12" '
                 f'fill="{COLOURS["ink"]}">{_esc(text)}</text>')
    return _svg(W, H, "\n  ".join(parts), f"H({form.r},{form.s}) Chen form")


def _chen_sigma(form) -> int:
    from .chen import sigma
    return sigma(form.r, form.s)
