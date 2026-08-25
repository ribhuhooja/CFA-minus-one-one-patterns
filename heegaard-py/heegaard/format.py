"""The two text formats, matching heegaard-js byte for byte.

CSV body, one header row, no quoting -- no field ever contains a comma.  Metadata as
``# key: value`` lines above it, which ``pandas.read_csv(f, comment='#')`` ignores.
Combinatorics only: where an arc is drawn is a rendering decision made elsewhere.
"""

from __future__ import annotations

from .diagram import CURVE_OF_SIDE, Diagram, DiagramError, SIDES

DIAGRAM_FORMAT = "heegaard-diagram 1"
DISCS_FORMAT = "heegaard-discs 1"


def diagram_to_csv(diagram: Diagram, cell: int | None = None) -> str:
    lines = [f"# {DIAGRAM_FORMAT}",
             f"# name: {diagram.name}",
             f"# x-generators: {diagram.x_count}",
             f"# y-generators: {diagram.y_count}"]
    if cell:
        lines.append(f"# cell: {cell}")
    for key, value in diagram.notes.items():
        lines.append(f"# note-{key}: {value}")
    lines.append("# basepoint: z corner")
    for name, arc in diagram.basepoints.items():
        lines.append(f"# basepoint: {name} arc {arc}")
    lines.append("side_a,index_a,side_b,index_b,family")
    for arc in diagram.arcs:
        lines.append(f"{arc.a.side},{arc.a.index},{arc.b.side},{arc.b.index},{arc.family}")
    return "\n".join(lines) + "\n"


def _split(text: str, expected: str):
    info: dict = {}
    basepoints: list[str] = []
    body: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if not line.startswith("#"):
            body.append(line)
            continue
        stripped = line[1:].strip()
        if ":" not in stripped:
            info["format"] = stripped
            continue
        key, value = (part.strip() for part in stripped.split(":", 1))
        if key == "basepoint":
            basepoints.append(value)
        else:
            info[key] = value
    if info.get("format") and info["format"] != expected:
        raise DiagramError(f'this file says "{info["format"]}", expected "{expected}"')
    if not body:
        raise DiagramError("the file has no table in it")
    columns = [c.strip() for c in body.pop(0).split(",")]
    return info, basepoints, columns, body


def diagram_from_csv(text: str) -> Diagram:
    info, basepoints, columns, body = _split(text, DIAGRAM_FORMAT)
    for column in ("side_a", "index_a", "side_b", "index_b"):
        if column not in columns:
            raise DiagramError(f'the arc table has no "{column}" column')
    at = {name: k for k, name in enumerate(columns)}

    diagram = Diagram(name=info.get("name", "diagram"))
    for row, line in enumerate(body, start=1):
        f = [v.strip() for v in line.split(",")]
        try:
            diagram.add_arc(int(f[at["index_a"]]), f[at["side_a"]],
                            int(f[at["index_b"]]), f[at["side_b"]],
                            f[at["family"]] if "family" in at and at["family"] < len(f) else "")
        except ValueError as exc:
            raise DiagramError(f"row {row}: {exc}") from None

    if "x-generators" in info:
        diagram.x_count = max(diagram.x_count, int(info["x-generators"]))
    if "y-generators" in info:
        diagram.y_count = max(diagram.y_count, int(info["y-generators"]))

    for spec in basepoints:
        parts = spec.split()
        if len(parts) == 3 and parts[1] == "arc":
            diagram.set_basepoint(parts[0], int(parts[2]))

    diagram.notes = {k[5:]: _number(v) for k, v in info.items() if k.startswith("note-")}
    return diagram.validate()


def _number(value: str):
    try:
        return int(value)
    except ValueError:
        return value


def discs_to_csv(discs, diagram: Diagram | None = None,
                 convention: str = "composed", sort: bool = True) -> str:
    lines = [f"# {DISCS_FORMAT}"]
    if diagram is not None:
        lines += [f"# diagram: {diagram.name}",
                  f"# x-generators: {diagram.x_count}",
                  f"# y-generators: {diagram.y_count}"]
    lines += [f"# reeb-convention: {convention}", f"# count: {len(discs)}",
              "source,target,U,chords,arcs,path"]

    def key(d):
        return (_gen_key(d.source), _gen_key(d.target), d.U, d.word)

    for d in (sorted(discs, key=key) if sort else discs):
        lines.append(f"{d.source},{d.target},{d.U},{d.word},{d.offset},{' '.join(d.directions)}")
    return "\n".join(lines) + "\n"


def _gen_key(name: str) -> tuple[str, int]:
    """Sort x_2 before x_10, matching the JS numeric collation."""
    curve, _, index = name.partition("_")
    return (curve, int(index))
