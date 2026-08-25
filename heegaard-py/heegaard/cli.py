"""Command line: build a diagram, or solve one.

    python3 -m heegaard generate 2 2 2 -o Q222.csv     # a Q(i,m,n) diagram
    python3 -m heegaard solve Q222.csv -o discs.csv    # its discs
    python3 -m heegaard solve Q222.csv                 # ... to stdout
    cat Q222.csv | python3 -m heegaard solve           # ... or from stdin

`solve` knows nothing about Q(i,m,n): it reads whatever diagram the file describes.  That is
the whole coupling between this and anything else -- a generator upstream and a visualiser
downstream need only agree on the two formats.
"""

from __future__ import annotations

import argparse
import sys
import time

from .diagram import DiagramError
from .format import diagram_from_csv, diagram_to_csv, discs_to_csv
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

    solve = sub.add_parser("solve", help="count the discs of a diagram")
    solve.add_argument("diagram", nargs="?", default=None, help="a diagram csv; stdin if absent")
    solve.add_argument("-o", "--out", default=None)

    args = parser.parse_args(argv)

    try:
        if args.command == "generate":
            diagram = Q(args.i, args.m, args.n)
            text = diagram_to_csv(diagram)
            _emit(text, args.out)
            print(f"{diagram}", file=sys.stderr)
            return 0

        text = (open(args.diagram, encoding="utf-8").read() if args.diagram
                else sys.stdin.read())
        diagram = diagram_from_csv(text)
        started = time.perf_counter()
        discs = enumerate_discs(diagram)
        seconds = time.perf_counter() - started
        _emit(discs_to_csv(discs, diagram), args.out)
        print(f"{diagram} -> {len(discs)} discs ({seconds:.2f}s)", file=sys.stderr)
        return 0
    except (DiagramError, ValueError, OSError) as exc:
        print(f"heegaard: {exc}", file=sys.stderr)
        return 1


def _emit(text: str, out: str | None) -> None:
    if out:
        with open(out, "w", encoding="utf-8") as handle:
            handle.write(text)
    else:
        sys.stdout.write(text)


if __name__ == "__main__":
    raise SystemExit(main())
