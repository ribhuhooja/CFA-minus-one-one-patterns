"""The three text formats.

CSV body, one header row, no quoting -- no field ever contains a comma.  Metadata above it as
``# key: value`` lines, which ``pandas.read_csv(f, comment='#')`` ignores; the one ``#`` line
with no colon in it is the format name and version.  The full specification is in CLAUDE.md.

``read_cfa`` accepts a ``heegaard-discs 1`` file as well as a ``bordered-cfa 1`` one, because
the disc format's first four columns ARE the CFA format and the other two are provenance the
algebra has no use for.  That is the whole interface between disc finding and algebra: a file
with four columns in it.
"""

from __future__ import annotations

from .chain import AlgebraError, Complex
from .cfk import CFK
from .structures import CFA, CFD
from .torus import parse_word, write_word

CFA_FORMAT = "bordered-cfa 1"
CFD_FORMAT = "bordered-cfd 1"
COMPLEX_FORMAT = "bordered-complex 1"
DISCS_FORMAT = "heegaard-discs 1"


def _split(text: str, expected):
    """Metadata, column names, and body rows."""
    info: dict[str, str] = {}
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
        else:
            key, value = (p.strip() for p in stripped.split(":", 1))
            info[key] = value
    found = info.get("format")
    if found and found not in expected:
        raise AlgebraError(f'this file says "{found}", expected {" or ".join(expected)}')
    if not body:
        raise AlgebraError("the file has no table in it")
    columns = [c.strip() for c in body.pop(0).split(",")]
    return info, columns, [[v.strip() for v in line.split(",")] for line in body]


def _need(columns, wanted, what):
    for column in wanted:
        if column not in columns:
            raise AlgebraError(f'the {what} table has no "{column}" column')
    return {name: k for k, name in enumerate(columns)}


def _list(info, key):
    value = info.get(key, "").strip()
    return [g for g in value.replace(" ", ",").split(",") if g]


def _count(info, n, what):
    if "count" in info and int(info["count"]) != n:
        raise AlgebraError(f'the file says {info["count"]} {what} but has {n}')


# ---------------------------------------------------------------- type A

def read_cfa(text: str, name: str | None = None) -> CFA:
    info, columns, rows = _split(text, (CFA_FORMAT, DISCS_FORMAT))
    at = _need(columns, ("source", "target", "U", "chords"), "CFA")
    _count(info, len(rows), "operations")

    declared = {g: 0 for g in _list(info, "iota0")}
    declared.update({g: 1 for g in _list(info, "iota1")})
    parsed = []
    for k, f in enumerate(rows, start=1):
        try:
            parsed.append((f[at["source"]], f[at["target"]], int(f[at["U"]]),
                           parse_word(f[at["chords"]] if at["chords"] < len(f) else "")))
        except (ValueError, IndexError) as exc:
            raise AlgebraError(f"row {k}: {exc}") from None

    return CFA.build(name or info.get("name") or info.get("diagram") or "cfa", parsed,
                     idempotent=declared or None)


def write_cfa(cfa: CFA) -> str:
    lines = [f"# {CFA_FORMAT}", f"# name: {cfa.name}",
             f"# iota0: {','.join(cfa.in_idempotent(0))}",
             f"# iota1: {','.join(cfa.in_idempotent(1))}",
             f"# count: {len(cfa.operations)}",
             "source,target,U,chords"]
    lines += [f"{op.source},{op.target},{op.power},{op.spelled()}" for op in cfa.operations]
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------- type D

def read_cfd(text: str, name: str | None = None) -> CFD:
    info, columns, rows = _split(text, (CFD_FORMAT,))
    at = _need(columns, ("source", "target", "chord"), "CFD")
    _count(info, len(rows), "arrows")

    declared = {g: 0 for g in _list(info, "iota0")}
    declared.update({g: 1 for g in _list(info, "iota1")})
    parsed = []
    for k, f in enumerate(rows, start=1):
        word = parse_word(f[at["chord"]] if at["chord"] < len(f) else "")
        if len(word) > 1:
            raise AlgebraError(f"row {k}: {f[at['chord']]!r} is more than one chord; a "
                               f"type-D arrow carries exactly one")
        parsed.append((f[at["source"]], f[at["target"]], word[0] if word else None))

    d = CFD.build(name or info.get("name") or "cfd", parsed, idempotent=declared or None)
    if "tau" in info:
        d.notes["tau"] = int(info["tau"])
    return d


def write_cfd(cfd: CFD) -> str:
    lines = [f"# {CFD_FORMAT}", f"# name: {cfd.name}"]
    if "tau" in cfd.notes:
        lines.append(f"# tau: {cfd.notes['tau']}")
    lines += [f"# iota0: {','.join(cfd.in_idempotent(0))}",
              f"# iota1: {','.join(cfd.in_idempotent(1))}",
              f"# count: {len(cfd.arrows)}",
              "source,target,chord"]
    lines += [f"{a.source},{a.target},{a.spelled()}" for a in cfd.arrows]
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------- complexes and CFK

def read_complex(text: str, name: str | None = None) -> Complex:
    info, columns, rows = _split(text, (COMPLEX_FORMAT,))
    at = _need(columns, ("source", "target", "U"), "complex")
    _count(info, len(rows), "arrows")
    terms = [(f[at["source"]], f[at["target"]], int(f[at["U"]])) for f in rows]
    generators = _list(info, "generators") or [g for t in terms for g in t[:2]]
    c = Complex.build(name or info.get("name") or "complex", generators, terms)
    if "alexander" in info:
        c.notes["alexander"] = _grading(info["alexander"])
    for key in ("cfa", "cfd"):
        if key in info:
            c.notes[key] = info[key]
    return c


def read_cfk(text: str, name: str | None = None) -> CFK:
    c = read_complex(text, name)
    return CFK.build(c.name, c.generators, [(a.source, a.target, a.power) for a in c.arrows],
                     alexander=c.notes.get("alexander"))


def _grading(value: str) -> dict[str, int]:
    out = {}
    for piece in value.replace(",", " ").split():
        generator, _, number = piece.partition("=")
        out[generator.strip()] = int(number)
    return out


def write_complex(c: Complex, alexander: dict | None = None) -> str:
    lines = [f"# {COMPLEX_FORMAT}", f"# name: {c.name}",
             f"# generators: {','.join(c.generators)}"]
    grading = alexander if alexander is not None else c.notes.get("alexander")
    if grading:
        lines.append("# alexander: " + ",".join(f"{g}={grading[g]}" for g in c.generators))
    for key in ("cfa", "cfd"):
        if key in c.notes:
            lines.append(f"# {key}: {c.notes[key]}")
    lines += [f"# count: {len(c.arrows)}", "source,target,U"]
    lines += [f"{a.source},{a.target},{a.power}" for a in c.arrows]
    return "\n".join(lines) + "\n"


def write_cfk(k: CFK) -> str:
    return write_complex(k.complex, k.alexander)
