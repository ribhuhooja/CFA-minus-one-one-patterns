"""satellite-floer: knot Floer homology of satellites with (1,1) patterns.

Build a pattern's bordered Heegaard diagram, count its discs, and pair the type-A structure
they give with a companion's type-D structure:

    satellite-floer pattern hrs 3 1 -o P.csv       # a pattern's diagram
    satellite-floer solve P.csv -o discs.csv       # the discs it bounds
    satellite-floer draw P.csv                     # pictures of both (svg)
    satellite-floer box discs.csv trefoil          # gCFK^- of the satellite
    satellite-floer check out.csv                  # d^2, and the rank at U = 1

Run any subcommand with -h for its options.
"""

from __future__ import annotations

import argparse
import sys

from . import __version__
from .bordered import cli as algebra
from .heegaard import cli as diagrams


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="satellite-floer", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True, metavar="command")
    diagrams.register(sub)
    algebra.register(sub)

    args = parser.parse_args(argv)
    half = diagrams if args.command in diagrams.COMMANDS else algebra
    try:
        return half.run(args)
    except diagrams.ERRORS + algebra.ERRORS + (ValueError, OSError) as exc:
        print(f"satellite-floer: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
