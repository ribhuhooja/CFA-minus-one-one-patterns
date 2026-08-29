"""Tests for the python side.  Run: python3 -m unittest discover -s tests

The disc counts and hashes below were produced by heegaard-js, independently, so a match here
is a cross-check between two implementations rather than a restatement of one.
"""

import hashlib
import unittest
from math import gcd

from heegaard import (PATTERNS, Q, build, catalogue, diagram_from_csv, diagram_to_csv,
                      discs_from_csv, discs_to_cfa_csv, discs_to_csv, names, parameters)
from heegaard.format import CFA_FORMAT, IDEMPOTENT_OF_CURVE
from heegaard.diagram import Diagram, DiagramError
from heegaard.bridge import (conway, conway_of, equivalent, inverse, mirror, name,
                             normalise, parameters as bridge_parameters,
                             parameters_of_conway, readings, reduced, schubert,
                             schubert_of_conway)
from heegaard.chen import (H, chen_form, cut_height, is_connected,
                           main_region_winding, polyline, recut, sigma, wrapped)
from heegaard.layout import (crossings_between, nesting, route, route_radial,
                             stroked, strokes)
from heegaard.render import render_cover, render_diagram, render_discs
from heegaard.solver import attach_regions, enumerate_discs, reeb_chords

#: (i, m, n) -> (discs, sha256 of the disc csv), from heegaard-js
EXPECTED = {
    (1, 2, 2): 46, (2, 2, 2): 110, (1, 3, 2): 70, (1, 2, 4): 106,
    (3, 3, 3): 408, (2, 4, 3): 345, (4, 2, 2): 238,
}


class Parameters(unittest.TestCase):
    def test_q222(self):
        p = parameters(2, 2, 2)
        self.assertEqual((p.r, p.s, p.max_x, p.max_y), (7, 14, 29, 12))

    def test_identities(self):
        for i, m, n in [(2, 2, 2), (1, 1, 2), (3, 2, 2), (2, 3, 5)]:
            p = parameters(i, m, n)
            self.assertEqual(p.max_y, 4 * i * m - 2 * m)
            self.assertEqual(p.max_y, 2 * p.r - 2)
            self.assertEqual(p.max_x, 2 * p.r + p.s + m + n - 3)

    def test_n_at_least_two(self):
        for n in (0, 1):
            with self.assertRaises(ValueError):
                Q(2, 2, n)


class Validation(unittest.TestCase):
    def test_q_is_legal(self):
        for i in (1, 2, 3):
            for m in (2, 3):
                for n in (2, 3):
                    self.assertEqual(Q(i, m, n).problems(), [])

    def test_beta_is_one_curve(self):
        for params in [(1, 2, 2), (2, 3, 5), (3, 3, 3)]:
            self.assertEqual(len(Q(*params).components()), 1)

    def test_intersection_number(self):
        for params in [(1, 2, 2), (2, 2, 2), (1, 5, 5), (2, 4, 3)]:
            left_right, top_bottom = Q(*params).intersection_number()
            self.assertEqual((abs(left_right), top_bottom), (1, 0))

    def test_catches_a_doubled_slot(self):
        d = Diagram("bad", x_count=2, y_count=0)
        d.add_arc(0, "bottom", 0, "top")
        d.add_arc(0, "bottom", 1, "top")
        self.assertTrue(any("used by 2 arc ends" in p for p in d.problems()))

    def test_catches_crossing_arcs(self):
        d = Diagram("crossing", x_count=2, y_count=0)
        d.add_arc(0, "bottom", 1, "top")
        d.add_arc(1, "bottom", 0, "top")
        self.assertTrue(any("must cross" in p for p in d.problems()))

    def test_catches_a_split_beta(self):
        d = Diagram("split", x_count=2, y_count=0)
        d.add_arc(0, "bottom", 0, "top")
        d.add_arc(1, "bottom", 1, "top")
        self.assertTrue(any("components" in p for p in d.problems()))

    def test_catches_a_wrong_homology_class(self):
        d = Diagram("wrong", x_count=1, y_count=1)
        d.add_arc(0, "bottom", 0, "top")
        d.add_arc(0, "left", 0, "right")
        self.assertTrue(any("multiplicity" in p for p in d.problems()))

    def test_validate_raises(self):
        d = Diagram("empty", x_count=1, y_count=0)
        with self.assertRaises(DiagramError):
            d.validate()


DIAGRAMS = [(1, 2, 2), (2, 2, 2), (1, 3, 2), (1, 2, 4), (2, 3, 5), (3, 3, 3), (1, 5, 5),
            (4, 2, 2), (2, 4, 3)]


class Layout(unittest.TestCase):
    def test_arcs_are_embedded(self):
        for params in DIAGRAMS:
            with self.subTest(diagram=params):
                self.assertEqual(crossings_between(route(Q(*params))), [])
        self.assertEqual(crossings_between(route(build("twin-rainbow"))), [])

    def test_the_older_routing_is_embedded_too(self):
        """It is only kept as an independent check, so a couple of diagrams is enough."""
        for params in [(2, 2, 2), (2, 3, 5)]:
            with self.subTest(diagram=params):
                self.assertEqual(crossings_between(route_radial(Q(*params))), [])

    def test_arcs_stay_in_the_domain(self):
        for params in DIAGRAMS:
            for x, y in (p for path in route(Q(*params)) for p in path):
                self.assertGreaterEqual(min(x, y), -1e-9)
                self.assertLessEqual(max(x, y), 1 + 1e-9)

    def test_arcs_start_and_end_at_their_generators(self):
        from heegaard.layout import position
        for diagram in (build("twin-rainbow"), Q(2, 2, 2)):
            for arc, path in zip(diagram.arcs, route(diagram)):
                self.assertEqual(path[0], position(diagram, arc.a))
                self.assertEqual(path[-1], position(diagram, arc.b))

    def test_an_arc_is_one_stroke(self):
        """The drawing is geometry, not samples: one line or one curve per arc."""
        for params in DIAGRAMS:
            diagram = Q(*params)
            pieces = strokes(diagram)
            self.assertEqual(len(pieces), len(diagram.arcs))
            self.assertTrue(all(p.kind in ("line", "curve") for p in pieces))

    def test_strokes_start_and_end_at_their_generators(self):
        from heegaard.layout import position
        for diagram in (build("twin-rainbow"), Q(2, 2, 2)):
            for arc, piece in zip(diagram.arcs, strokes(diagram)):
                self.assertEqual(piece.a, position(diagram, arc.a))
                self.assertEqual(piece.b, position(diagram, arc.b))

    def test_strokes_stay_in_the_domain(self):
        for params in DIAGRAMS:
            for piece in strokes(Q(*params)):
                for i in range(9):
                    x, y = piece.at(i / 8)
                    self.assertGreaterEqual(min(x, y), -1e-6)
                    self.assertLessEqual(max(x, y), 1 + 1e-6)

    def test_the_fallback_is_taken_when_the_strokes_cross(self):
        """Strokes are used when they are clear and never when they are not.  A diagram that
        falls back still draws and still solves; only the picture is uglier."""
        for params in DIAGRAMS + [(0, 0, 0)]:
            diagram = build("twin-rainbow") if params == (0, 0, 0) else Q(*params)
            clear = not crossings_between([p.points(10) for p in strokes(diagram)])
            self.assertEqual(stroked(diagram), clear, diagram.name)
            self.assertEqual(crossings_between(route(diagram)), [], diagram.name)

    def test_the_hand_drawn_diagram_draws_as_strokes(self):
        """twin-rainbow is the one this was built for, so pin it: every arc one piece of
        geometry, and its bottom-to-top connector straight."""
        diagram = build("twin-rainbow")
        self.assertTrue(stroked(diagram))
        pieces = strokes(diagram)
        lines = [p for p in pieces if p.kind == "line"]
        self.assertEqual(len(lines), 1)
        straight = [a for a in diagram.arcs if a.family == "bottom-top"]
        self.assertEqual(len(straight), 1)

    def test_both_routings_give_the_same_discs(self):
        """Any embedding of the same combinatorics must do -- so this is a real check on
        the solver, not just on the drawing."""
        import heegaard.layout as layout
        for maker in (lambda: build("twin-rainbow"), lambda: Q(1, 2, 2), lambda: Q(2, 2, 2),
                      lambda: Q(1, 3, 2)):
            diagram = maker()
            original = layout.route
            try:
                answers = []
                for routing in (original, route_radial):
                    layout.route = routing
                    answers.append(discs_to_csv(enumerate_discs(maker()), diagram))
            finally:
                layout.route = original
            self.assertEqual(answers[0], answers[1], diagram.name)


class Formats(unittest.TestCase):
    def test_round_trip(self):
        for params in [(1, 2, 2), (2, 2, 2), (2, 3, 5)]:
            original = Q(*params)
            back = diagram_from_csv(diagram_to_csv(original))
            self.assertEqual([(str(a.a), str(a.b)) for a in original.arcs],
                             [(str(a.a), str(a.b)) for a in back.arcs])
            self.assertEqual((original.x_count, original.y_count),
                             (back.x_count, back.y_count))
            self.assertEqual(original.basepoints, back.basepoints)

    def test_body_is_plain_csv(self):
        text = diagram_to_csv(Q(2, 2, 2))
        body = [l for l in text.splitlines() if not l.startswith("#")]
        self.assertTrue(all(len(l.split(",")) == 5 for l in body))
        self.assertNotIn('"', text)

    def test_refuses_a_foreign_format(self):
        with self.assertRaises(DiagramError):
            diagram_from_csv("# heegaard-diagram 99\nside_a,index_a,side_b,index_b\ntop,0,bottom,0\n")


class Chords(unittest.TestCase):
    def test_composites_compose(self):
        from heegaard.solver import REEB
        turn = {chord: pair for pair, chord in REEB.items()}
        for whole, first, last in [("rho_12", "rho_1", "rho_2"), ("rho_23", "rho_2", "rho_3"),
                                   ("rho_123", "rho_1", "rho_3")]:
            self.assertEqual(turn[whole][0], turn[first][0])
            self.assertEqual(turn[whole][1], turn[last][1])

    def test_one_chord_per_lattice_point(self):
        self.assertEqual(len(reeb_chords(["S", "E", "N", "N", "W"])), 4)
        self.assertEqual(reeb_chords(["S"]), [])

    def test_rejects_an_impossible_turn(self):
        with self.assertRaises(ValueError):
            reeb_chords(["W", "N"])


class Patterns(unittest.TestCase):
    """The catalogue in heegaard.patterns.  Every entry must build something legal."""

    def test_every_pattern_builds_a_legal_diagram(self):
        for name, pattern in PATTERNS.items():
            sample = (1, 2, 2)[:len(pattern.parameters)]
            with self.subTest(pattern=name):
                diagram = build(name, *sample)
                self.assertEqual(diagram.problems(), [])
                self.assertIn("w", diagram.basepoints, f"{name} has nowhere to put w")

    def test_every_pattern_is_embedded(self):
        for name, pattern in PATTERNS.items():
            sample = (1, 2, 2)[:len(pattern.parameters)]
            with self.subTest(pattern=name):
                self.assertEqual(crossings_between(route(build(name, *sample))), [])

    def test_qimn_is_q(self):
        self.assertEqual(diagram_to_csv(build("qimn", 2, 2, 2)), diagram_to_csv(Q(2, 2, 2)))

    def test_catalogue_lists_everything(self):
        text = catalogue()
        self.assertEqual(names(), list(PATTERNS))
        for name in names():
            self.assertIn(name, text)

    def test_wrong_arity_is_refused(self):
        with self.assertRaises(ValueError):
            build("qimn", 2, 2)
        with self.assertRaises(ValueError):
            build("twin-rainbow", 1)

    def test_unknown_pattern_is_refused(self):
        with self.assertRaises(ValueError):
            build("no-such-pattern")


class TwinRainbow(unittest.TestCase):
    """The hand-drawn 8-x, 5-y diagram.  Its 25 discs were confirmed by heegaard-js."""

    def setUp(self):
        self.diagram = build("twin-rainbow")

    def test_shape(self):
        d = self.diagram
        self.assertEqual((d.x_count, d.y_count, len(d.arcs)), (8, 5, 13))
        self.assertEqual(len(d.components()), 1)
        self.assertEqual(d.intersection_number(), (-1, 0))

    def test_the_arcs_are_the_ones_dictated(self):
        expected = {
            ("bottom", 0, "bottom", 3), ("bottom", 1, "bottom", 2),
            ("left", 4, "bottom", 4),
            ("left", 0, "top", 0), ("left", 1, "top", 1),
            ("left", 2, "top", 2), ("left", 3, "top", 3),
            ("bottom", 5, "top", 4),
            ("top", 5, "right", 2), ("top", 6, "right", 1), ("top", 7, "right", 0),
            ("bottom", 6, "right", 3), ("bottom", 7, "right", 4),
        }
        self.assertEqual({(a.a.side, a.a.index, a.b.side, a.b.index)
                          for a in self.diagram.arcs}, expected)

    def test_w_is_in_the_innermost_rainbow(self):
        arc = self.diagram.arcs[self.diagram.basepoints["w"]]
        self.assertEqual((arc.a.index, arc.b.index), (1, 2))

    def test_disc_count_matches_the_js_solver(self):
        self.assertEqual(len(enumerate_discs(self.diagram)), 25)

    def test_it_is_Q_1_2_1(self):
        """It is Q(1,2,1) -- see QIsH.  What is true is only that no Q with n >= 2 fits it,
        which is all the constructor in qmn.py can make: maxy = 4 forces m=2, i=1, and then
        maxx = 6n+1 = 7 wants n = 1."""
        for i in range(1, 8):
            for m in range(1, 8):
                for n in range(2, 8):
                    p = parameters(i, m, n)
                    self.assertNotEqual((p.max_x, p.max_y), (7, 4), f"Q({i},{m},{n})")
        self.assertEqual(parameters(1, 2, 1).max_x, 7)
        self.assertEqual(parameters(1, 2, 1).max_y, 4)

    def test_round_trips_through_csv(self):
        original = self.diagram
        back = diagram_from_csv(diagram_to_csv(original))
        self.assertEqual(discs_to_csv(enumerate_discs(back), back),
                         discs_to_csv(enumerate_discs(original), original))


class Discs(unittest.TestCase):
    def test_counts_match_the_js_solver(self):
        for params, expected in EXPECTED.items():
            self.assertEqual(len(enumerate_discs(Q(*params))), expected, f"Q{params}")

    def test_discs_are_well_formed(self):
        for disc in enumerate_discs(Q(2, 2, 2)):
            self.assertLess(disc.area, 0)                       # correctly oriented
            self.assertGreaterEqual(disc.U, 0)
            self.assertEqual(len(disc.chords), len(disc.directions) - 1)
            self.assertNotEqual(disc.offset, 0)

    def test_the_count_formula(self):
        for i, m, n in [(1, 2, 2), (2, 2, 2), (1, 3, 2), (3, 3, 3), (2, 4, 3)]:
            predicted = 2 * m * (n + 2) ** 2 * i - (m * (n * n + 2 * n + 5) - m * m - n * n)
            self.assertEqual(len(enumerate_discs(Q(i, m, n))), predicted)

    def test_solving_a_reloaded_diagram(self):
        original = Q(1, 3, 2)
        reloaded = diagram_from_csv(diagram_to_csv(original))
        self.assertEqual(discs_to_csv(enumerate_discs(reloaded), reloaded),
                         discs_to_csv(enumerate_discs(original), original))


class DiscFormat(unittest.TestCase):
    """Reading a disc table back, which is what lets a picture be drawn from a file."""

    def test_round_trip(self):
        for maker in (lambda: build("twin-rainbow"), lambda: Q(1, 2, 2)):
            diagram = maker()
            text = discs_to_csv(enumerate_discs(diagram), diagram)
            self.assertEqual(discs_to_csv(discs_from_csv(text), diagram), text)

    def test_chords_are_checked_against_the_path(self):
        diagram = build("twin-rainbow")
        text = discs_to_csv(enumerate_discs(diagram), diagram)
        head, _, rest = text.partition("source,target,U,chords,arcs,path\n")
        first, _, tail = rest.partition("\n")
        fields = first.split(",")
        fields[3] = "P999"                                   # a word the path does not spell
        with self.assertRaises(DiagramError):
            discs_from_csv(head + "source,target,U,chords,arcs,path\n"
                           + ",".join(fields) + "\n" + tail)

    def test_count_is_checked(self):
        diagram = build("twin-rainbow")
        text = discs_to_csv(enumerate_discs(diagram), diagram)
        with self.assertRaises(DiagramError):
            discs_from_csv(text.replace("# count: 25", "# count: 99"))


class Regions(unittest.TestCase):
    """A disc's polygon can be rebuilt from source, offset and path alone."""

    def test_replay_matches_the_solver(self):
        for maker in (lambda: build("twin-rainbow"), lambda: Q(1, 2, 2), lambda: Q(2, 2, 2)):
            diagram = maker()
            kept = enumerate_discs(diagram, keep_regions=True)
            bare = attach_regions(diagram, enumerate_discs(diagram))
            self.assertEqual([d.region for d in kept], [d.region for d in bare])
            self.assertEqual([d.area for d in kept], [d.area for d in bare])

    def test_replay_from_a_csv(self):
        diagram = build("twin-rainbow")
        kept = enumerate_discs(diagram, keep_regions=True)
        from_file = attach_regions(
            diagram, discs_from_csv(discs_to_csv(enumerate_discs(diagram), diagram)))
        key = lambda d: (d.source, d.target, d.U, d.word)
        self.assertEqual([d.region for d in sorted(kept, key=key)],
                         [d.region for d in sorted(from_file, key=key)])

    def test_a_disc_that_does_not_fit_the_diagram_is_refused(self):
        diagram = build("twin-rainbow")
        disc = enumerate_discs(diagram)[0]
        disc.target = "x_0" if disc.target != "x_0" else "x_1"
        with self.assertRaises(ValueError):
            attach_regions(diagram, [disc])


class Render(unittest.TestCase):
    """The pictures.  Nothing here checks that they are pretty, only that they are honest."""

    def setUp(self):
        self.diagram = build("twin-rainbow")
        self.discs = enumerate_discs(self.diagram)

    def test_all_three_are_well_formed_svg(self):
        import xml.etree.ElementTree as ET
        for svg in (render_diagram(self.diagram), render_cover(self.diagram),
                    render_discs(self.diagram, self.discs)):
            root = ET.fromstring(svg)
            self.assertTrue(root.tag.endswith("svg"))
            self.assertGreater(float(root.get("width")), 0)

    def test_nothing_is_drawn_outside_the_canvas(self):
        """A caption longer than the picture is wide used to be sliced off the edge."""
        import re
        for svg in (render_diagram(self.diagram, cell=120),
                    render_cover(self.diagram, cell=40),
                    render_discs(self.diagram, self.discs, cell=30)):
            width = float(re.search(r'width="([0-9.]+)"', svg).group(1))
            for x in re.findall(r'<text x="(-?[0-9.]+)"', svg):
                self.assertLess(float(x), width)

    def test_the_picture_does_not_depend_on_disc_order(self):
        shuffled = list(reversed(self.discs))
        self.assertEqual(render_discs(self.diagram, self.discs),
                         render_discs(self.diagram, shuffled))

    def test_drawing_from_a_csv_matches_drawing_from_the_solver(self):
        text = discs_to_csv(self.discs, self.diagram)
        self.assertEqual(render_discs(self.diagram, discs_from_csv(text)),
                         render_discs(self.diagram, self.discs))

    def test_a_reloaded_diagram_draws_the_same_picture(self):
        back = diagram_from_csv(diagram_to_csv(self.diagram))
        self.assertEqual(render_diagram(back), render_diagram(self.diagram))
        self.assertEqual(render_cover(back), render_cover(self.diagram))

    def test_every_disc_is_drawn(self):
        svg = render_discs(self.diagram, self.discs, limit=None)
        self.assertEqual(svg.count("<polygon"), len(self.discs))

    def test_the_limit_is_respected(self):
        svg = render_discs(self.diagram, self.discs, limit=6)
        self.assertEqual(svg.count("<polygon"), 6)

    def test_a_name_with_punctuation_survives_into_the_title(self):
        svg = render_diagram(Q(1, 2, 2))
        self.assertIn("<title>Q(1,2,2)</title>", svg)

    def test_labels_can_be_turned_off(self):
        with_labels = render_discs(self.diagram, self.discs, labels=True)
        without = render_discs(self.diagram, self.discs, labels=False)
        self.assertIn("U^", with_labels)
        self.assertLess(without.count("<text"), with_labels.count("<text"))


def q_parameters(i, m, n):
    """The (r, s) that Q(i,m,n) is claimed to be H of."""
    return 1 + 2*i*m - m, n + 3*m - 2*m*n + 4*i*m*n - 4*i*m - 2


def arc_set(d):
    return sorted(tuple(sorted(((a.a.side, a.a.index), (a.b.side, a.b.index)))) for a in d.arcs)


class ChenForm(unittest.TestCase):
    """H(r, s) built on the annulus, before it is cut across."""

    CASES = [(r, s) for r in list(range(2, 9)) + list(range(-8, -1))
             for s in range(1, 12) if is_connected(r, s)]

    def test_the_sigma_formula_is_the_winding_of_the_main_region(self):
        """The closed form and walking the path have to agree, and nothing else says so."""
        for r in range(2, 12):
            for s in range(1, 21):
                with self.subTest(r=r, s=s):
                    self.assertEqual(sigma(r, s), -main_region_winding(r, s))

    def test_every_point_is_used_once_on_each_side(self):
        for r, s in self.CASES:
            form = chen_form(r, s)
            for side in ("left", "right"):
                used = sorted(i for sa, ia, sb, ib, _f, _ha, _hb in form.arcs
                              for s_, i in ((sa, ia), (sb, ib)) if s_ == side)
                self.assertEqual(used, list(range(form.M)), f"H({r},{s}) {side}")

    def test_the_arcs_stay_inside_the_domain_once_wrapped(self):
        for r, s in self.CASES[:40]:
            form = chen_form(r, s)
            for arc in form.arcs:
                for piece in wrapped(polyline(form, arc, 12), form.M):
                    for _x, h in piece:
                        self.assertGreaterEqual(h, -1e-9)
                        self.assertLessEqual(h, form.M + 1e-9)

    def test_the_drawing_is_embedded(self):
        """If two arcs crossed, the order of the crossings along the new cut would be wrong,
        and the diagram that came out would not be embedded either."""
        for r, s in self.CASES[:30]:
            paths = []
            form = chen_form(r, s)
            for arc in form.arcs:
                paths.extend(wrapped(polyline(form, arc, 24), form.M))
            scaled = [[(x, h / form.M) for x, h in piece] for piece in paths]
            self.assertEqual(crossings_between(scaled), [], f"H({r},{s})")

    def test_the_cut_meets_beta_twice_r_minus_one_times(self):
        for r, s in self.CASES:
            _, hits = recut(chen_form(r, s))
            self.assertEqual(len(hits), 2 * abs(r) - 1, f"H({r},{s})")

    def test_H_is_a_legal_diagram(self):
        for r, s in self.CASES:
            with self.subTest(r=r, s=s):
                d = H(r, s)
                self.assertEqual(d.problems(), [])
                self.assertEqual((d.x_count, d.y_count),
                                 (chen_form(r, s).M, 2 * abs(r) - 1))

    def test_a_disconnected_beta_is_refused(self):
        bad = next((r, s) for r in range(2, 12) for s in range(1, 12)
                   if not is_connected(r, s))
        with self.assertRaises(ValueError):
            H(*bad)

    def test_H_round_trips_through_csv(self):
        for r, s in [(3, 1), (3, 6), (5, 4), (-3, 6), (7, 14)]:
            original = H(r, s)
            back = diagram_from_csv(diagram_to_csv(original))
            self.assertEqual(arc_set(original), arc_set(back))
            self.assertEqual(discs_to_csv(enumerate_discs(back), back).splitlines()[6:],
                             discs_to_csv(enumerate_discs(original), original).splitlines()[6:])


class QIsH(unittest.TestCase):
    """Q(i,m,n) is H(1+2im-m, n+3m-2mn+4imn-4im-2)."""

    def test_the_arcs_are_the_same(self):
        """150 diagrams, the largest Q(6,6,6) = H(67,670) at 947 arcs.  Checked by hand up to
        Q(9,25,25) = H(426,20448), 22199 arcs, which is too slow to keep here."""
        for i in range(1, 7):
            for m in range(2, 7):
                for n in range(2, 7):
                    r, s = q_parameters(i, m, n)
                    with self.subTest(i=i, m=m, n=n, r=r, s=s):
                        self.assertEqual(arc_set(H(r, s)), arc_set(Q(i, m, n)))

    def test_a_large_one(self):
        i, m, n = 10, 10, 10
        r, s = q_parameters(i, m, n)
        self.assertEqual((r, s), (191, 3438))
        self.assertEqual(arc_set(H(r, s)), arc_set(Q(i, m, n)))

    def test_the_discs_are_the_same(self):
        for i, m, n in [(1, 2, 2), (2, 2, 2), (1, 3, 2), (2, 3, 3), (1, 4, 4)]:
            r, s = q_parameters(i, m, n)
            q, h = Q(i, m, n), H(r, s)
            with self.subTest(i=i, m=m, n=n):
                self.assertEqual(discs_to_csv(enumerate_discs(h), h).splitlines()[6:],
                                 discs_to_csv(enumerate_discs(q), q).splitlines()[6:])

    def test_the_dependent_count_is_m_plus_n_minus_two(self):
        for i in range(1, 5):
            for m in range(1, 5):
                for n in range(1, 5):
                    r, s = q_parameters(i, m, n)
                    if r < 1 or s < 1:
                        continue
                    with self.subTest(i=i, m=m, n=n):
                        self.assertEqual(abs(sigma(r, s)), m + n - 2)

    def test_twin_rainbow_is_Q_1_2_1(self):
        """The hand-drawn diagram is Q(1,2,1), which is H(3,1)."""
        self.assertEqual(q_parameters(1, 2, 1), (3, 1))
        tw, h = build("twin-rainbow"), H(3, 1)
        self.assertEqual(arc_set(tw), arc_set(h))
        self.assertEqual(discs_to_csv(enumerate_discs(h), h).splitlines()[6:],
                         discs_to_csv(enumerate_discs(tw), tw).splitlines()[6:])


class TwoBridge(unittest.TestCase):
    """b(p, q), C(a_1, ..., a_n) and H(r, s) are three names for one pattern."""

    PAIRS = [(r, s) for r in list(range(1, 16)) + list(range(-15, 0))
             for s in range(1, 26)]
    LINKS = [(p, q) for p in range(4, 120, 2) for q in range(1, p)
             if gcd(p, q) == 1 and q % 2]

    def test_the_worked_example(self):
        self.assertEqual(schubert(3, 1), (14, 5))
        self.assertEqual(conway(14, 5), (2, 1, 4))
        self.assertEqual(schubert_of_conway(2, 1, 4), (14, 5))
        self.assertEqual(parameters_of_conway(2, 1, 4), (3, 1))
        self.assertEqual(name(3, 1), "H(3,1) = b(14,5) = C(2,1,4)")

    def test_p_is_even_so_the_link_has_two_components(self):
        self.assertTrue(all(schubert(r, s)[0] % 2 == 0 for r, s in self.PAIRS))

    def test_q_is_coprime_to_p(self):
        for r, s in self.PAIRS:
            p, q = schubert(r, s)
            self.assertEqual(gcd(p, abs(q)) == 1, is_connected(r, s), f"H({r},{s})")

    def test_q_already_lies_in_the_standard_range(self):
        """|q| < p/2 comes out of the formulas without asking: |q| = 2|r|-1 and
        p/2 = s + 2|r|, so the condition is only s > -1."""
        for r, s in self.PAIRS:
            p, q = schubert(r, s)
            self.assertLess(abs(q), p / 2, f"H({r},{s}) -> b({p},{q})")
            self.assertEqual(reduced(p, q), q)

    def test_reduced_lands_in_the_range_and_keeps_the_class(self):
        for p, q in self.LINKS:
            for shift in (-2, -1, 0, 1, 2):
                out = reduced(p, q + shift * p)
                self.assertLess(abs(out), p / 2 + 1)
                self.assertEqual(out % p, q % p)

    def test_schubert_and_back(self):
        for r, s in self.PAIRS:
            self.assertEqual(bridge_parameters(*schubert(r, s)), (r, s))

    def test_conway_and_back(self):
        for r, s in self.PAIRS:
            if is_connected(r, s):
                self.assertEqual(schubert_of_conway(*conway_of(r, s)), schubert(r, s))

    def test_conway_round_trips_on_every_small_link(self):
        for p, q in self.LINKS:
            terms = conway(p, q)
            self.assertEqual(schubert_of_conway(*terms), (p, reduced(p, q)))
            self.assertEqual(conway(*schubert_of_conway(*terms)), terms)

    # ------------------------------------------------------------------ mirror

    def test_the_mirror_is_q_negated(self):
        for p, q in self.LINKS:
            self.assertEqual(mirror(p, q), (p, reduced(p, -q)))
            self.assertEqual(mirror(*mirror(p, q)), (p, reduced(p, q)))

    def test_the_mirror_negates_every_conway_term(self):
        for p, q in self.LINKS:
            self.assertEqual(conway(*mirror(p, q)), tuple(-a for a in conway(p, q)))

    def test_flipping_r_is_the_mirror(self):
        """Reflecting the Chen form gives b(p, -q), which is what it should."""
        for r, s in self.PAIRS:
            self.assertEqual(schubert(-r, s), mirror(*schubert(r, s)))

    # ------------------------------------------------------------------ Schubert's theorem

    def test_equivalence_is_an_equivalence(self):
        sample = self.LINKS[:120]
        for p, q in sample:
            self.assertTrue(equivalent(p, q, p, q))
            for p2, q2 in sample:
                self.assertEqual(equivalent(p, q, p2, q2), equivalent(p2, q2, p, q))
        for p, q in sample[:40]:
            self.assertTrue(equivalent(p, q, *inverse(p, q)))

    def test_different_p_is_never_the_same_link(self):
        self.assertFalse(equivalent(14, 5, 16, 5))

    def test_inverse_reverses_the_conway_word_up_to_the_mirror(self):
        """C of q^-1 is C of q backwards, and mirrored exactly when the two reduce to
        opposite signs.  4000 links, no exceptions."""
        for p, q in self.LINKS:
            forward = conway(p, q)
            back = conway(*inverse(p, q))
            same_sign = reduced(p, q) * reduced(p, pow(q, -1, p)) > 0
            expected = tuple(reversed(forward))
            if not same_sign:
                expected = tuple(-a for a in expected)
            self.assertEqual(back, expected, f"b({p},{q})")

    def test_readings_finds_the_diagram_back(self):
        for r, s in self.PAIRS:
            self.assertIn((r, s), readings(*schubert(r, s)))

    def test_what_is_refused(self):
        with self.assertRaises(ValueError):
            schubert(0, 3)                       # r must not be zero
        with self.assertRaises(ValueError):
            schubert(3, 0)                       # s must be positive
        with self.assertRaises(ValueError):
            bridge_parameters(15, 5)             # p odd: not two components
        with self.assertRaises(ValueError):
            bridge_parameters(14, 4)             # q even
        with self.assertRaises(ValueError):
            bridge_parameters(8, 5)              # s would come out negative
        with self.assertRaises(ValueError):
            conway(14, 7)                        # gcd is 7, not a link
        with self.assertRaises(ValueError):
            schubert_of_conway()                 # nothing to expand

    def test_it_narrows_nothing(self):
        """The rest of the package still takes any diagram at all -- this module only names
        the ones that happen to be unknot patterns."""
        import heegaard.diagram as diagram
        import heegaard.solver as solver
        for module in (diagram, solver):
            with open(module.__file__, encoding="utf-8") as handle:
                self.assertNotIn("bridge", handle.read())


class AgainstTheJS(unittest.TestCase):
    """The cross-implementation check, which is the strongest one here.

    heegaard-js is a separate implementation with its own layout, so a byte-identical disc
    table is two programs agreeing rather than one restating itself.  It needs node and the
    sibling package, so it skips rather than fails when they are not there.
    """

    def _js(self, diagram):
        import os
        import shutil
        import subprocess
        root = os.path.join(os.path.dirname(__file__), "..", "..", "heegaard-js")
        if shutil.which("node") is None or not os.path.isdir(root):
            self.skipTest("heegaard-js or node is not here")
        done = subprocess.run(["node", "solve.js", "--quiet"], cwd=root,
                              input=diagram_to_csv(diagram), capture_output=True, text=True)
        if done.returncode != 0:
            self.skipTest(f"heegaard-js would not run: {done.stderr.strip()[:200]}")
        return done.stdout

    def test_disc_tables_are_byte_identical(self):
        for maker in (lambda: build("twin-rainbow"), lambda: Q(1, 2, 2), lambda: Q(2, 2, 2)):
            diagram = maker()
            with self.subTest(diagram=diagram.name):
                self.assertEqual(discs_to_csv(enumerate_discs(diagram), diagram),
                                 self._js(diagram))


if __name__ == "__main__":
    unittest.main()


class CfaExport(unittest.TestCase):
    """``--format=cfa``: the disc table projected onto the type-A structure it carries.

    This is the file the algebra reads, and the only thing that crosses between the two
    packages.  Nothing here imports ``bordered``; what is checked is that the projection is
    exactly the first four columns of the disc table and that the idempotent split is the one
    the chords force.
    """

    #: which idempotent each Reeb chord runs between, from A(T^2).  Repeated here rather than
    #: imported, so that a change on the algebra side has to be a deliberate change on both.
    ENDS = {"P1": (0, 1), "P2": (1, 0), "P3": (0, 1),
            "P12": (0, 0), "P23": (1, 1), "P123": (0, 1)}

    def chords(self, word):
        return ["P" + p for p in word.split("P") if p]

    def test_it_is_the_first_four_columns_of_the_disc_table(self):
        diagram = build("twin-rainbow")
        discs = enumerate_discs(diagram)
        full = [l for l in discs_to_csv(discs, diagram).splitlines() if not l.startswith("#")]
        thin = [l for l in discs_to_cfa_csv(discs, diagram).splitlines()
                if not l.startswith("#")]
        self.assertEqual(thin, [",".join(l.split(",")[:4]) for l in full])

    def test_the_header_declares_both_idempotents(self):
        diagram = build("twin-rainbow")
        text = discs_to_cfa_csv(enumerate_discs(diagram), diagram)
        self.assertIn(f"# {CFA_FORMAT}", text)
        self.assertIn("# iota0: y_0,y_1,y_2,y_3,y_4", text)
        self.assertIn("# iota1: x_0,x_1,x_2,x_3,x_4,x_5,x_6,x_7", text)

    def test_every_chord_word_composes_from_its_source_to_its_target(self):
        """The check that forces y into iota_0 and x into iota_1, on every diagram here.

        A word is a sequence, so what has to hold is that consecutive chords meet in the
        idempotents -- not that they multiply to something nonzero.  (P2P1 occurs, and
        rho_2 . rho_1 is zero.)
        """
        side = lambda name: IDEMPOTENT_OF_CURVE[name.partition("_")[0]]
        for diagram in [build("twin-rainbow"), Q(1, 2, 2), Q(2, 2, 2), Q(1, 3, 2)]:
            for disc in enumerate_discs(diagram):
                word = self.chords(disc.word)
                if not word:
                    self.assertEqual(side(disc.source), side(disc.target), str(diagram))
                    continue
                self.assertEqual(side(disc.source), self.ENDS[word[0]][0], str(diagram))
                self.assertEqual(side(disc.target), self.ENDS[word[-1]][1], str(diagram))
                for a, b in zip(word, word[1:]):
                    self.assertEqual(self.ENDS[a][1], self.ENDS[b][0], f"{disc.word}")

    def test_the_other_idempotent_assignment_would_fail(self):
        """Not a convention: swapping x and y breaks the very first chord."""
        diagram = build("twin-rainbow")
        swapped = {"y": 1, "x": 0}
        bad = 0
        for disc in enumerate_discs(diagram):
            word = self.chords(disc.word)
            if word and swapped[disc.source[0]] != self.ENDS[word[0]][0]:
                bad += 1
        self.assertGreater(bad, 0)
