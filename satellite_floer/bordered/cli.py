"""The algebra half of the command line: pair a pattern with a companion.

    satellite-floer knots                            # the catalogue
    satellite-floer cfk trefoil                      # a knot complex, as CSV
    satellite-floer cfd trefoil -o trefoil.csv       # its type-D structure
    satellite-floer cfd --cfk mine.csv               # ... from a CFK^- you wrote
    satellite-floer cfa Q121-discs.csv               # a disc table, as a CFA^-
    satellite-floer box Q121-discs.csv trefoil       # gCFK^- of the satellite
    satellite-floer box cfa.csv cfd.csv -o out.csv   # ... with both sides from files
    satellite-floer check out.csv                    # d^2, and the rank at U = 1

`box` takes its second argument as a file if one exists by that name and as a knot from the
catalogue otherwise, so ``box discs.csv t2 5`` works.  Nothing here has heard of a Heegaard
diagram: the left-hand side is a CSV with four columns in it, and where it came from is not
this subpackage's business.

``register`` adds these subcommands to the one parser in :mod:`satellite_floer.cli`, and
``run`` carries one out; errors are left to the caller to report.
"""

from __future__ import annotations

import os
import sys

from . import knots
from .box import box
from .cfk import CFK, cfd_from_cfk
from .chain import AlgebraError, Complex
from .format import (read_cfa, read_cfd, read_cfk, read_complex,
                     write_cfa, write_cfd, write_cfk, write_complex)
from .structures import CFA, CFD


COMMANDS = ("knots", "cfk", "cfd", "cfa", "box", "check")
ERRORS = (AlgebraError,)


def register(sub) -> None:
    """Add the algebra subcommands to ``sub``, an argparse subparsers object."""
    sub.add_parser("knots", help="list the knot catalogue")

    for name, help_text in (("cfk", "write a knot complex from the catalogue"),
                            ("cfd", "write the type-D structure of a knot complement")):
        p = sub.add_parser(name, help=help_text)
        p.add_argument("knot", nargs="?", default=None, help="a name from the catalogue")
        p.add_argument("parameters", nargs="*", type=int)
        p.add_argument("--cfk", default=None, help="read a CFK^- csv instead of naming a knot")
        p.add_argument("-o", "--out", default=None)

    cfa = sub.add_parser("cfa", help="read a disc table as a type-A structure")
    cfa.add_argument("discs", nargs="?", default=None, help="a disc or CFA csv; stdin if absent")
    cfa.add_argument("--name", default=None)
    cfa.add_argument("-o", "--out", default=None)

    b = sub.add_parser("box", help="the box tensor: gCFK^- of the satellite")
    b.add_argument("cfa", help="a disc csv or a CFA csv")
    b.add_argument("cfd", help="a CFD csv, or a knot from the catalogue")
    b.add_argument("parameters", nargs="*", type=int, help="the knot's parameters, if any")
    b.add_argument("--name", default=None)
    b.add_argument("-o", "--out", default=None)

    c = sub.add_parser("check", help="report on any file this package can read")
    c.add_argument("file", nargs="?", default=None)


def run(args) -> int:
    """Carry out one algebra subcommand."""
    if args.command == "knots":
        print(f"knots:\n{knots.catalogue()}", file=sys.stderr)
        return 0

    if args.command in ("cfk", "cfd"):
        k = read_cfk(_read(args.cfk)) if args.cfk else knots.cfk(args.knot, *args.parameters)
        if args.command == "cfk":
            _emit(write_cfk(k), args.out)
            print(f"{k}", file=sys.stderr)
        else:
            d = cfd_from_cfk(k).require_type_d()
            _emit(write_cfd(d), args.out)
            print(f"{k}\n{d}", file=sys.stderr)
        return 0

    if args.command == "cfa":
        a = read_cfa(_read(args.discs), args.name)
        _emit(write_cfa(a), args.out)
        print(_cfa_note(a), file=sys.stderr)
        return 0

    if args.command == "box":
        a = read_cfa(_read(args.cfa))
        d = (read_cfd(_read(args.cfd)) if os.path.exists(args.cfd)
             else knots.cfd(args.cfd, *args.parameters))
        c = box(a, d, args.name)
        _emit(write_complex(c), args.out)
        print(f"{a}\n{d}\n{_complex_note(c)}", file=sys.stderr)
        return 0

    text = _read(args.file)
    thing = _sniff(text)
    print(_note(thing), file=sys.stderr)
    return 0


def _sniff(text: str):
    """Read whichever of the formats this is."""
    head = next((l for l in text.splitlines()
                 if l.startswith("#") and ":" not in l), "").lstrip("# ").strip()
    if head.startswith("bordered-cfd"):
        return read_cfd(text)
    if head.startswith("bordered-complex"):
        c = read_complex(text)
        return CFK.build(c.name, c.generators,
                         [(a.source, a.target, a.power) for a in c.arrows],
                         alexander=c.notes["alexander"]) if "alexander" in c.notes else c
    return read_cfa(text)


def _note(thing) -> str:
    if isinstance(thing, CFA):
        return _cfa_note(thing)
    if isinstance(thing, CFD):
        return (f"{thing}\n  reduced: {thing.is_reduced()}"
                f"\n  type-D relation: {'holds' if not thing.d_squared() else 'FAILS'}")
    if isinstance(thing, CFK):
        return f"{thing}\n{_complex_note(thing.complex)}"
    return _complex_note(thing)


def _cfa_note(a: CFA) -> str:
    cancelled = a.notes.get("cancelled", 0)
    extra = f"\n  {cancelled} row(s) cancelled mod 2" if cancelled else ""
    return f"{a}{extra}"


def _complex_note(c: Complex) -> str:
    rank = c.homology_rank_at_U1()
    return (f"{c}\n  d^2 = 0: {c.is_a_complex()}"
            f"\n  dim H(C/(U-1)) = {rank}"
            f"{'' if rank == 1 else '   <- a knot complex must give 1'}")


def _read(path: str | None) -> str:
    return open(path, encoding="utf-8").read() if path else sys.stdin.read()


def _emit(text: str, out: str | None) -> None:
    if out:
        with open(out, "w", encoding="utf-8") as handle:
            handle.write(text)
    else:
        sys.stdout.write(text)

