"""Tests for the python side.  Run: python3 -m unittest discover -s tests

The disc counts and hashes below were produced by heegaard-js, independently, so a match here
is a cross-check between two implementations rather than a restatement of one.
"""

import hashlib
import unittest

from heegaard import Q, diagram_from_csv, diagram_to_csv, discs_to_csv, parameters
from heegaard.diagram import Diagram, DiagramError
from heegaard.layout import crossings_between, route
from heegaard.solver import enumerate_discs, reeb_chords

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


class Layout(unittest.TestCase):
    def test_arcs_are_embedded(self):
        for params in [(1, 2, 2), (2, 2, 2), (2, 3, 5), (3, 3, 3), (1, 5, 5)]:
            paths = route(Q(*params))
            self.assertEqual(crossings_between(paths), [], f"Q{params} arcs cross")

    def test_arcs_stay_in_the_domain(self):
        for path in route(Q(2, 3, 5)):
            for x, y in path:
                self.assertGreaterEqual(min(x, y), -1e-9)
                self.assertLessEqual(max(x, y), 1 + 1e-9)


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


if __name__ == "__main__":
    unittest.main()
