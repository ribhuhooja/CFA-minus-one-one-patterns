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
from .layout import position, route, stroked, strokes

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
