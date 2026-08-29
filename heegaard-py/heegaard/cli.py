"""Command line: build a diagram, or solve one.

    python3 -m heegaard generate 2 2 2 -o Q222.csv     # a Q(i,m,n) diagram
    python3 -m heegaard pattern                        # what else can be built
    python3 -m heegaard pattern twin-rainbow -o t.csv  # ... build one by name
    python3 -m heegaard solve Q222.csv -o discs.csv    # its discs
    python3 -m heegaard solve Q222.csv                 # ... to stdout
    cat Q222.csv | python3 -m heegaard solve           # ... or from stdin
    python3 -m heegaard draw Q222.csv                  # svg: domain, cover, discs
    python3 -m heegaard draw Q222.csv --discs=d.csv    # ... reusing a solved disc table

`generate` is Q(i,m,n) and stays that way; `pattern` reaches the whole catalogue in
`heegaard.patterns`, of which Q is one entry.

`solve` knows nothing about Q(i,m,n): it reads whatever diagram the file describes.  That is
the whole coupling between this and anything else -- a generator upstream and a visualiser
downstream need only agree on the two formats.
"""

from __future__ import annotations

import argparse
import os
import sys
import time

from .diagram import DiagramError
from .format import (diagram_from_csv, diagram_to_csv, discs_from_csv, discs_to_cfa_csv,
                     discs_to_csv)
from .patterns import build, catalogue
from .render import render_cover, render_diagram, render_discs
from .qmn import Q
from .solver import enumerate_discs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="heegaard", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    generate = sub.add_parser("generate", help="write a Q(i,m,n) diagram")
    generate.add_argument("i", type=int)
    generate.add_argument("m", type=int)
    generate.add_argument("n", type=int)
    generate.add_argument("-o", "--out", default=None)

    pattern = sub.add_parser("pattern", help="write a named diagram from the catalogue")
    pattern.add_argument("name", nargs="?", default=None,
                         help="which pattern; omit to list them")
    pattern.add_argument("parameters", nargs="*", type=int,
                         help="its integer parameters, if it takes any")
    pattern.add_argument("-o", "--out", default=None)

    solve = sub.add_parser("solve", help="count the discs of a diagram")
    solve.add_argument("diagram", nargs="?", default=None, help="a diagram csv; stdin if absent")
    solve.add_argument("-o", "--out", default=None)
    solve.add_argument("--format", default="discs", choices=["discs", "cfa"],
                       help="the full disc table, or just the type-A structure it carries")

    draw = sub.add_parser("draw", help="svg of a diagram, its cover, and its discs")
    draw.add_argument("diagram", nargs="?", default=None, help="a diagram csv; stdin if absent")
    draw.add_argument("--discs", default=None,
                      help="a disc csv to draw; solved from the diagram if absent")
    draw.add_argument("--only", default="all",
                      choices=["all", "diagram", "cover", "discs"])
    draw.add_argument("--cell", type=float, default=None, help="pixels per copy of the domain")
    draw.add_argument("--tiles", type=int, default=3, help="copies per side in the cover")
    draw.add_argument("--limit", type=int, default=80,
                      help="how many discs to draw; 0 for all of them")
    draw.add_argument("--arrange", default="packed", choices=["packed", "insitu"])
    draw.add_argument("--no-labels", dest="labels", action="store_false")
    draw.add_argument("-o", "--out", default="out", help="directory for the svg files")

    args = parser.parse_args(argv)

    try:
        if args.command == "generate":
            diagram = Q(args.i, args.m, args.n)
            text = diagram_to_csv(diagram)
            _emit(text, args.out)
            print(f"{diagram}", file=sys.stderr)
            return 0

        if args.command == "pattern":
            if args.name is None:
                print(f"patterns:\n{catalogue()}", file=sys.stderr)
                return 0
            diagram = build(args.name, *args.parameters)
            _emit(diagram_to_csv(diagram), args.out)
            print(f"{diagram}", file=sys.stderr)
            return 0

        if args.command == "draw":
            return _draw(args)

        text = (open(args.diagram, encoding="utf-8").read() if args.diagram
                else sys.stdin.read())
        diagram = diagram_from_csv(text)
        started = time.perf_counter()
        discs = enumerate_discs(diagram)
        seconds = time.perf_counter() - started
        _emit(discs_to_csv(discs, diagram) if args.format == "discs"
              else discs_to_cfa_csv(discs, diagram), args.out)
        print(f"{diagram} -> {len(discs)} discs ({seconds:.2f}s)", file=sys.stderr)
        return 0
    except (DiagramError, ValueError, OSError) as exc:
        print(f"heegaard: {exc}", file=sys.stderr)
        return 1


def _stem(name: str) -> str:
    """A filename from a diagram name.  "Q(2,2,2)" -> "Q222", "twin-rainbow" unchanged."""
    kept = "".join(c if (c.isalnum() or c in "-_") else "" for c in name)
    return kept or "diagram"


def _draw(args) -> int:
    """Pictures, from the CSV and nothing else.

    Everything drawn is in the file: the arcs are the file's arcs, the routing is the one the
    solver uses, and the discs are either the file's discs or the ones this diagram bounds.
    No family is named, so a diagram nobody has a constructor for draws just as well.
    """
    text = (open(args.diagram, encoding="utf-8").read() if args.diagram
            else sys.stdin.read())
    diagram = diagram_from_csv(text)

    os.makedirs(args.out, exist_ok=True)
    stem = _stem(diagram.name)
    written = []

    def write(suffix: str, svg: str) -> None:
        path = os.path.join(args.out, f"{stem}{suffix}.svg")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(svg)
        written.append(path)

    note = str(diagram)
    if args.only in ("all", "diagram"):
        write("", render_diagram(diagram, cell=args.cell or 460))
    if args.only in ("all", "cover"):
        write("-cover", render_cover(diagram, tiles=args.tiles, cell=args.cell or 200))
    if args.only in ("all", "discs"):
        if args.discs:
            discs = discs_from_csv(open(args.discs, encoding="utf-8").read())
            note += f" -> {len(discs)} discs from {args.discs}"
        else:
            discs = enumerate_discs(diagram)
            note += f" -> {len(discs)} discs, solved here"
        write("-discs", render_discs(diagram, discs, cell=args.cell or 96,
                                     limit=args.limit or None, arrange=args.arrange,
                                     labels=args.labels))

    print(note, file=sys.stderr)
    for path in written:
        print(f"  {path}", file=sys.stderr)
    return 0


def _emit(text: str, out: str | None) -> None:
    if out:
        with open(out, "w", encoding="utf-8") as handle:
            handle.write(text)
    else:
        sys.stdout.write(text)


if __name__ == "__main__":
    raise SystemExit(main())
