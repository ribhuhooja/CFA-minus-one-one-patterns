"""Redraw the user's six hand-drawn Q(i,2,2) sheets from the computed disc table.

    python3 figures/qi22.py [-o out/qi22] [--i 2] [--j 3] [--k 0]

Each family on a sheet is drawn at one concrete member -- Q(i,2,2) with the given i, j, k;
j = 3 is the largest at which every j-family on the sheets exists when i = 2, and the
families hugging an edge (rho_1, rho_12, rho_2 between the ends of the fans) grow with j, so
it is the one where those are most visible --
placed in the cell of the 4 x 5 grid where the user drew it, coloured by kind as the user
coloured them; ``--key`` numbers the discs and adds a key in the user's own notation.  The U power and chords in the key are the computed disc's, not transcribed.
No caption: that is left to whoever places the figure.
"""

import argparse
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from satellite_floer.heegaard.qmn import Q                # noqa: E402
from satellite_floer.heegaard.render import render_atlas  # noqa: E402
from satellite_floer.heegaard.solver import enumerate_discs# noqa: E402
from qi22_spec import GROUPS, SHEETS            # noqa: E402

#: the user's colours, as fills pale enough for beta to read through
GROUP_COLOURS = {"o": "#f9b98a", "g": "#a8e6a0", "p": "#f5a8d4"}


def evaluate(name: str, i: int, j: int, k: int) -> str:
    """``x_{8i-3+j}`` at i, j, k, as the generator it names."""
    curve, _, index = name.partition("_")
    expression = re.sub(r"(\d)([ijk])", r"\1*\2", index.strip("{}"))
    return f"{curve}_{eval(expression, {}, {'i': i, 'j': j, 'k': k})}"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-o", "--out", default="out/qi22")
    parser.add_argument("--i", type=int, default=2)
    parser.add_argument("--j", type=int, default=3)
    parser.add_argument("--k", type=int, default=0)
    parser.add_argument("--key", action="store_true",
                        help="put the key beside each grid; off, since the sheets are set "
                             "side by side in the paper and a key there is unreadably small")
    args = parser.parse_args(argv)

    diagram = Q(args.i, 2, 2)
    table = enumerate_discs(diagram)
    os.makedirs(args.out, exist_ok=True)
    for number, (sheet, groups) in enumerate(zip(SHEETS, GROUPS), 1):
        discs, centres, names = [], [], []
        for entry in sheet:
            source, target, centre = entry[:3]
            s, t = (evaluate(n, args.i, args.j, args.k) for n in (source, target))
            hits = [d for d in table if (d.source, d.target) == (s, t)]
            if len(entry) > 3:
                hits = [d for d in hits if f"U{d.U}{d.word}" == entry[3]]
            if len(hits) != 1:
                raise SystemExit(f"sheet {number}: {source} -> {target} is {s} -> {t}, "
                                 f"which is {len(hits)} discs of {diagram.name}, not one")
            discs.append(hits[0])
            centres.append(centre)
            names.append((source, target))
        svg = render_atlas(diagram, discs, columns=4, rows=5, centres=centres, names=names,
                           caption=False, key=args.key, numbers=args.key,
                           colours=[GROUP_COLOURS[g] for g in groups])
        path = os.path.join(args.out, f"Qi22-sheet-{number}.svg")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(svg)
        print(path, file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
