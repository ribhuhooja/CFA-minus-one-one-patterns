"""The six hand-drawn sheets of Q(i,2,2) disc families, as data.

Each entry is one family, read off the user's sheets: the source and target in the user's
generic notation (i, j, k), and where on the sheet it was drawn -- the centre of the disc in
cells, columns from the left and rows from the BOTTOM of a 4 x 5 grid.  The U power and the
chord word are not written here: they come from the computed disc table, which is the
authority, and the family's formula only picks out which disc to draw.
"""

#: (source, target, centre) per sheet; indices are expressions in i, j, k
SHEETS = [
    [("y_j", "x_j", (0.5, 4.5)),
     ("y_j", "x_{8i-3+j}", (1.5, 4.0)),
     ("x_j", "x_{8i-3+j}", (2.56, 4.5)),
     ("y_j", "x_{16i-3-j}", (3.9, 4.85)),
     ("y_j", "y_{8i-4-j}", (3.9, 4.0)),
     ("y_j", "x_{8i-4-j}", (1.35, 2.36)),
     ("y_j", "x_{4+j}", (2.97, 2.6)),
     ("x_{16i-3-j}", "y_{8i-4-j}", (0.85, 1.15)),
     ("x_{16i-3-j}", "x_{8i-4-j}", (2.3, 0.5))],
    [("x_{4i+j}", "x_{12i-3-j}", (2.33, 4.08)),
     ("x_{16i-3-j}", "x_{4+j}", (1.04, 3.58)),
     ("y_{8i-4-j}", "x_{4+j}", (3.2, 3.58)),
     ("x_{12i+1}", "x_{12i-2}", (2.09, 1.82), "U2"),
     ("x_{12i+1}", "x_{12i-2}", (3.19, 1.63), "U2P23")],
    [("y_{4i-1}", "x_{12i-2}", (1.05, 3.28)),
     ("y_{4i-1}", "x_{12i-3}", (3.04, 3.68)),
     ("y_{4i}", "x_{12i-2}", (0.37, 1.64)),
     ("y_{4i}", "x_{12i-3}", (2.07, 1.82)),
     ("x_{12i}", "x_{12i-4}", (3.32, 1.01))],
    [("y_{4i-3}", "x_{12i-4}", (1.35, 3.85)),
     ("y_{4i-2}", "x_{12i-2}", (2.81, 4.36)),
     ("y_{4i-4}", "x_{12i-2}", (3.23, 3.47)),
     ("x_{12i-1}", "x_{12i-3}", (0.78, 1.0)),
     ("y_{4i-2}", "x_{12i-3}", (1.76, 1.81)),
     ("x_{12i-1}", "x_{12i-2}", (3.78, 1.51)),
     ("x_{12i-2}", "x_{12i-3}", (2.76, 0.5))],
    [("x_{12i}", "x_{12i-1}", (1.12, 3.28)),
     ("x_{4k}", "x_{4k+3}", (2.18, 3.54)),
     ("x_{4k+1}", "x_{4k+2}", (3.2, 3.55)),
     ("y_{4k}", "y_{4k+3}", (1.18, 1.45)),
     ("y_{4k+1}", "y_{4k+2}", (2.2, 1.45)),
     ("x_{4i+4+4k}", "x_{4i+1+4k}", (3.11, 1.42))],
    [("x_{4i+3+4k}", "x_{4i+2+4k}", (1.06, 3.47)),
     ("x_{8i+1+4k}", "x_{8i+4+4k}", (2.18, 3.54)),
     ("x_{8i+2+4k}", "x_{8i+3+4k}", (3.17, 3.53)),
     ("x_{12i+5+4k}", "x_{12i+2+4k}", (1.11, 2.43)),
     ("x_{12i+4+4k}", "x_{12i+3+4k}", (2.08, 2.47)),
     ("y_{4i+4+4k}", "y_{4i+1+4k}", (3.11, 2.43)),
     ("y_{4i+3+4k}", "y_{4i+2+4k}", (1.06, 1.48))],
]


#: which kind each family is, as the user coloured them by hand: o = a family in j (orange),
#: g = a special arrow (green), p = the snail (pink); one letter per entry of SHEETS
GROUPS = ["ooooooooo", "ooogg", "ggggg", "ggggggg", "pppppp", "ppppppp"]
