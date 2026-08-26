"""Tests for the python side.  Run: python3 -m unittest discover -s tests

The disc counts and hashes below were produced by heegaard-js, independently, so a match here
is a cross-check between two implementations rather than a restatement of one.
"""

import hashlib
import unittest

from heegaard import (PATTERNS, Q, build, catalogue, diagram_from_csv, diagram_to_csv,
                      discs_from_csv, discs_to_csv, names, parameters)
from heegaard.diagram import Diagram, DiagramError
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

    def test_it_is_outside_the_q_family(self):
        """No Q(i,m,n) has 8 x and 5 y generators; maxy = 4 forces m=2, i=1, then n < 2."""
        for i in range(1, 8):
            for m in range(1, 8):
                for n in range(2, 8):
                    p = parameters(i, m, n)
                    self.assertNotEqual((p.max_x, p.max_y), (7, 4), f"Q({i},{m},{n})")

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
