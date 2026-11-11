"""Tests for the algebra, ``satellite_floer.bordered``.

The one fixture, ``twin-rainbow-cfa.csv``, was written by the diagram half's solver from
Q(1,2,1) = H(3,1) -- but it is checked in here as a file, and nothing in these tests imports
``satellite_floer.heegaard``, which is the point: the algebra's whole input is four columns
of CSV.  The tests that use both subpackages together are in ``test_together.py``.
"""

import os
import subprocess
import sys
import unittest

from satellite_floer import bordered
from satellite_floer.bordered import (CFA, CFD, CFK, AlgebraError, Complex, box, knots,
                                      read_cfa, read_cfd, read_cfk, read_complex, torus,
                                      write_cfa, write_cfd, write_cfk, write_complex)
from satellite_floer.bordered.cfk import cfd_from_cfk, infer_alexander
from satellite_floer.bordered.knots import mirror

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURE = os.path.join(HERE, "twin-rainbow-cfa.csv")
#: the subpackage's own source, wherever it was imported from
SOURCE = os.path.dirname(os.path.abspath(bordered.__file__))

#: the four test knots, and what Levine's theorem must give for each
#: name -> (generators, tau, dim iota_0, dim iota_1)
KNOTS = {"unknot": (1, 0, 1, 0), "trefoil": (3, 1, 3, 4),
         "lh-trefoil": (3, -1, 3, 4), "figure-eight": (5, 0, 5, 4)}


def fixture() -> CFA:
    with open(FIXTURE, encoding="utf-8") as handle:
        return read_cfa(handle.read())


# ---------------------------------------------------------------- the algebra

class TorusAlgebra(unittest.TestCase):
    def test_idempotents_are_forced_by_the_endpoints(self):
        # rho_i = [i, i+1]; the arc through boundary points 1 and 3 is iota_0
        self.assertEqual([(torus.left(c), torus.right(c)) for c in
                          ("rho_1", "rho_2", "rho_3", "rho_12", "rho_23", "rho_123")],
                         [(0, 1), (1, 0), (0, 1), (0, 0), (1, 1), (0, 1)])

    def test_composites_compose(self):
        self.assertEqual(torus.multiply("rho_1", "rho_2"), "rho_12")
        self.assertEqual(torus.multiply("rho_2", "rho_3"), "rho_23")
        self.assertEqual(torus.multiply("rho_12", "rho_3"), "rho_123")
        self.assertEqual(torus.multiply("rho_1", "rho_23"), "rho_123")

    def test_the_rest_of_the_products_are_zero(self):
        for a, b in [("rho_2", "rho_1"), ("rho_1", "rho_3"), ("rho_3", "rho_1"),
                     ("rho_23", "rho_23"), ("rho_12", "rho_12"), ("rho_123", "rho_1")]:
            self.assertIsNone(torus.multiply(a, b), f"{a} {b}")

    def test_a_sequence_can_compose_where_the_product_is_zero(self):
        # (rho_2, rho_1) is a legal argument list and does occur in the disc tables, even
        # though rho_2 . rho_1 = 0 in the algebra.
        self.assertTrue(torus.composable(["rho_2", "rho_1"]))
        self.assertIsNone(torus.multiply("rho_2", "rho_1"))

    def test_the_P_delimits_so_words_are_unambiguous(self):
        self.assertEqual(torus.parse_word("P123"), ["rho_123"])
        self.assertEqual(torus.parse_word("P1P23"), ["rho_1", "rho_23"])
        self.assertEqual(torus.parse_word("P12P3"), ["rho_12", "rho_3"])
        self.assertEqual(torus.parse_word(""), [])

    def test_words_round_trip(self):
        for word in ("", "P1", "P123", "P1P23", "P12P3", "P3P2P1", "P23P2P1"):
            self.assertEqual(torus.write_word(torus.parse_word(word)), word)

    def test_rho_spelling_is_read_too(self):
        self.assertEqual(torus.parse_word("rho_1 rho_23"), ["rho_1", "rho_23"])

    def test_a_nonsense_chord_is_refused(self):
        with self.assertRaises(ValueError):
            torus.parse_word("P4")


# ---------------------------------------------------------------- complexes

class Complexes(unittest.TestCase):
    def test_repeated_arrows_cancel(self):
        c = Complex.build("c", ["a", "b"], [("a", "b", 0), ("a", "b", 0)])
        self.assertEqual(c.arrows, [])

    def test_three_of_the_same_arrow_leave_one(self):
        c = Complex.build("c", ["a", "b"], [("a", "b", 1)] * 3)
        self.assertEqual(len(c.arrows), 1)

    def test_different_U_powers_do_not_cancel(self):
        c = Complex.build("c", ["a", "b"], [("a", "b", 0), ("a", "b", 1)])
        self.assertEqual(len(c.arrows), 2)

    def test_d_squared(self):
        good = Complex.build("good", list("abc"), [("a", "b", 0), ("a", "c", 1)])
        self.assertTrue(good.is_a_complex())
        bad = Complex.build("bad", list("abc"), [("a", "b", 0), ("b", "c", 0)])
        self.assertFalse(bad.is_a_complex())
        with self.assertRaises(AlgebraError):
            bad.require_complex()

    def test_rank_at_U1(self):
        # the trefoil complex: 3 generators, d b = a + U c, one rank of differential
        c = Complex.build("trefoil", list("abc"), [("b", "a", 0), ("b", "c", 1)])
        self.assertEqual(c.homology_rank_at_U1(), 1)

    def test_an_arrow_must_name_a_generator(self):
        with self.assertRaises(AlgebraError):
            Complex.build("c", ["a"], [("a", "b", 0)])

    def test_a_negative_power_is_not_a_coefficient(self):
        with self.assertRaises(AlgebraError):
            Complex.build("c", ["a", "b"], [("a", "b", -1)])


# ---------------------------------------------------------------- idempotent inference

class Idempotents(unittest.TestCase):
    def test_inferred_from_the_chords_alone(self):
        a = CFA.build("t", [("p", "q", 0, ("rho_1",)), ("q", "r", 0, ("rho_2",))])
        self.assertEqual(a.idempotent, {"p": 0, "q": 1, "r": 0})

    def test_an_empty_word_forces_the_two_ends_to_agree(self):
        a = CFA.build("t", [("p", "q", 1, ()), ("q", "r", 0, ("rho_1",))])
        self.assertEqual(a.idempotent, {"p": 0, "q": 0, "r": 1})

    def test_the_fixture_puts_y_in_iota_0_and_x_in_iota_1(self):
        # not a convention anyone chose: it is the only assignment the chord words admit
        a = fixture()
        self.assertEqual(a.in_idempotent(0), [f"y_{j}" for j in range(5)])
        self.assertEqual(a.in_idempotent(1), [f"x_{j}" for j in range(8)])

    def test_contradictory_chords_are_caught(self):
        with self.assertRaises(AlgebraError):
            CFA.build("t", [("p", "q", 0, ("rho_1",)), ("p", "r", 0, ("rho_2",))])

    def test_a_generator_no_chord_reaches_needs_declaring(self):
        # p -> q with no chords ties them together but pins neither, and the names give no
        # hint either, so there is nothing to infer from
        with self.assertRaises(AlgebraError):
            CFA.build("t", [("p", "q", 1, ())], hint=lambda g: None)
        # ... and declaring it is the way out
        self.assertEqual(CFA.build("t", [("p", "q", 1, ())],
                                   idempotent={"p": 1, "q": 1}).in_idempotent(1), ["p", "q"])

    def test_a_word_that_does_not_compose_is_refused(self):
        with self.assertRaises(AlgebraError):
            CFA.build("t", [("p", "q", 0, ("rho_1", "rho_1"))])


class TypeAReduction(unittest.TestCase):
    def test_identical_operations_cancel_mod_2(self):
        a = CFA.build("t", [("p", "q", 0, ("rho_1",))] * 2 + [("p", "r", 1, ("rho_1",))])
        self.assertEqual(len(a.operations), 1)
        self.assertEqual(a.notes["cancelled"], 1)

    def test_the_fixture_has_nothing_to_cancel(self):
        self.assertEqual(fixture().notes["cancelled"], 0)

    def test_the_fixture(self):
        a = fixture()
        self.assertEqual(len(a.operations), 25)
        self.assertEqual(a.max_word_length(), 3)


# ---------------------------------------------------------------- knot complexes

class KnotComplexes(unittest.TestCase):
    def test_the_catalogue_is_all_legal(self):
        for name in knots.names():
            k = knots.cfk(name, *([5] if knots.KNOTS[name].parameters else []))
            self.assertTrue(k.complex.is_a_complex(), name)
            self.assertEqual(k.complex.homology_rank_at_U1(), 1, name)

    def test_sizes_and_tau(self):
        for name, (n, tau, _, _) in KNOTS.items():
            k = knots.cfk(name)
            self.assertEqual(len(k.generators), n, name)
            self.assertEqual(k.tau(), tau, name)

    def test_the_trefoil_with_d_b_equals_a_plus_Uc_is_right_handed(self):
        k = knots.cfk("trefoil")
        self.assertEqual(k.alexander, {"a": -1, "b": 0, "c": 1})
        self.assertEqual(k.tau(), 1)
        self.assertEqual(k.survivors(), ("c", "a"))     # xi_0 vertically, eta_0 horizontally

    def test_tau_agrees_with_itself_both_ways(self):
        for name in ("unknot", "trefoil", "lh-trefoil", "figure-eight"):
            k = knots.cfk(name)
            xi, eta = k.survivors()
            self.assertEqual(k.alexander[xi], -k.alexander[eta], name)

    def test_mirroring_flips_tau_and_keeps_the_arrow_lengths(self):
        for name in ("trefoil", "figure-eight"):
            k = knots.cfk(name)
            m = mirror(k)
            self.assertEqual(m.tau(), -k.tau(), name)
            self.assertEqual(sorted(a.length for a in m.vertical()),
                             sorted(a.length for a in k.vertical()), name)
            self.assertEqual(sorted(a.length for a in m.horizontal()),
                             sorted(a.length for a in k.horizontal()), name)

    def test_t2_is_a_staircase_with_tau_equal_to_the_genus(self):
        for q in (3, 5, 7, 9):
            k = knots.cfk("t2", q)
            self.assertEqual(len(k.generators), q)
            self.assertEqual(k.tau(), (q - 1) // 2)
        self.assertEqual(knots.cfk("t2", -5).tau(), -2)

    def test_t2_3_is_the_trefoil(self):
        a, b = knots.cfk("t2", 3), knots.cfk("trefoil")
        self.assertEqual(sorted(a.alexander.values()), sorted(b.alexander.values()))
        self.assertEqual(a.tau(), b.tau())

    def test_an_unsimplified_basis_is_refused(self):
        # x is the source of two vertical arrows, so the pairing is not a matching
        with self.assertRaises(AlgebraError):
            CFK.build("bad", list("xyz"), [("x", "y", 0), ("x", "z", 0)],
                      alexander={"x": 1, "y": 0, "z": 0})

    def test_a_differential_may_not_raise_the_alexander_grading(self):
        with self.assertRaises(AlgebraError):
            CFK.build("bad", ["x", "y"], [("x", "y", 0)], alexander={"x": 0, "y": 1})

    def test_a_horizontal_arrow_must_raise_it_by_its_U_power(self):
        with self.assertRaises(AlgebraError):
            CFK.build("bad", ["x", "y"], [("x", "y", 1)], alexander={"x": 0, "y": 5})


class AlexanderInference(unittest.TestCase):
    def test_it_recovers_what_the_catalogue_declares(self):
        for name in ("unknot", "trefoil", "lh-trefoil", "figure-eight"):
            k = knots.cfk(name)
            self.assertEqual(infer_alexander(k.complex), k.alexander, name)

    def test_it_recovers_the_staircases(self):
        for q in (3, 5, 7):
            k = knots.cfk("t2", q)
            self.assertEqual(infer_alexander(k.complex), k.alexander, q)

    def test_it_refuses_an_unbalanced_complex(self):
        with self.assertRaises(AlgebraError):
            infer_alexander(Complex.build("c", ["a", "b"], [("a", "b", 0)]))


# ---------------------------------------------------------------- Levine Theorem 2.6

class TypeDFromKnot(unittest.TestCase):
    def test_the_unknot_is_one_generator_with_a_rho_12_self_loop(self):
        d = knots.cfd("unknot")
        self.assertEqual(len(d.generators), 1)
        self.assertEqual(len(d.arrows), 1)
        arrow = d.arrows[0]
        self.assertEqual(arrow.source, arrow.target)
        # rho_12 and not rho_23: the lone generator is xi_0 = eta_0, which is in iota_0, and
        # rho_12 is the only chord running iota_0 to iota_0
        self.assertEqual(arrow.chord, "rho_12")

    def test_the_sizes_the_theorem_predicts(self):
        for name, (_, tau, n0, n1) in KNOTS.items():
            d = knots.cfd(name)
            self.assertEqual(len(d.in_idempotent(0)), n0, name)
            self.assertEqual(len(d.in_idempotent(1)), n1, name)

    def test_iota_1_counts_the_arrow_lengths_plus_the_unstable_chain(self):
        for name in ("trefoil", "figure-eight", "lh-trefoil"):
            k = knots.cfk(name)
            want = (sum(a.length for a in k.vertical())
                    + sum(a.length for a in k.horizontal()) + 2 * abs(k.tau()))
            self.assertEqual(len(cfd_from_cfk(k).in_idempotent(1)), want, name)

    def test_the_type_d_relation_holds_across_the_catalogue(self):
        for name in knots.names():
            d = knots.cfd(name, *([7] if knots.KNOTS[name].parameters else []))
            self.assertEqual(d.d_squared(), [], name)
            self.assertTrue(d.is_reduced(), name)

    def test_every_chord_respects_the_idempotents(self):
        for name in knots.names():
            d = knots.cfd(name, *([5] if knots.KNOTS[name].parameters else []))
            for a in d.arrows:
                self.assertEqual(torus.left(a.chord), d.idempotent[a.source])
                self.assertEqual(torus.right(a.chord), d.idempotent[a.target])

    def test_the_unstable_chain_takes_the_shape_tau_dictates(self):
        out = {(a.source, a.chord) for a in knots.cfd("trefoil").arrows}
        self.assertIn(("a", "rho_3"), out)          # tau > 0: eta_0 -D3-> mu_1
        self.assertIn(("c", "rho_1"), out)          # ... and xi_0 -D1-> mu_s
        out = {(a.source, a.chord) for a in knots.cfd("lh-trefoil").arrows}
        self.assertIn(("c", "rho_123"), out)        # tau < 0: xi_0 -D123-> mu_1


# ---------------------------------------------------------------- the box tensor

class BoxTensor(unittest.TestCase):
    def test_it_pairs_only_within_an_idempotent(self):
        a, d = fixture(), knots.cfd("trefoil")
        c = box(a, d)
        want = (len(a.in_idempotent(0)) * len(d.in_idempotent(0))
                + len(a.in_idempotent(1)) * len(d.in_idempotent(1)))
        self.assertEqual(len(c.generators), want)

    def test_the_result_is_a_complex_with_free_homology_of_rank_one(self):
        a = fixture()
        for name in ("unknot", "trefoil", "lh-trefoil", "figure-eight"):
            c = box(a, knots.cfd(name))
            self.assertTrue(c.is_a_complex(), name)
            self.assertEqual(c.homology_rank_at_U1(), 1, name)

    def test_boxing_with_the_unknot_keeps_only_the_iota_0_part(self):
        a = fixture()
        c = box(a, knots.cfd("unknot"))
        self.assertEqual(len(c.generators), len(a.in_idempotent(0)))

    def test_a_word_is_a_sequence_and_not_a_product(self):
        # m_3(p, rho_1, rho_2) needs a TWO-arrow path; a single rho_12 arrow will not do
        pair_word = CFA.build("pair", [("p", "q", 0, ("rho_1", "rho_2"))])
        composite = CFA.build("composite", [("p", "q", 0, ("rho_12",))])
        one_step = CFD.build("one", [("e", "f", "rho_12")])
        two_step = CFD.build("two", [("e", "g", "rho_1"), ("g", "f", "rho_2")])

        self.assertEqual(box(pair_word, one_step).arrows, [])
        self.assertEqual(len(box(pair_word, two_step).arrows), 1)
        self.assertEqual(len(box(composite, one_step).arrows), 1)
        self.assertEqual(box(composite, two_step).arrows, [])

    def test_the_empty_word_pairs_with_the_empty_path(self):
        a = CFA.build("a", [("p", "q", 2, ())], idempotent={"p": 0, "q": 0})
        d = CFD.build("d", [("e", "e", "rho_12")])
        c = box(a, d)
        self.assertEqual([(x.source, x.target, x.power) for x in c.arrows],
                         [("p*e", "q*e", 2)])

    def test_two_paths_spelling_the_same_word_cancel(self):
        a = CFA.build("a", [("p", "q", 0, ("rho_1",))])
        d = CFD.build("d", [("e", "f", "rho_1"), ("e", "f", "rho_1")])
        self.assertEqual(d.arrows, [])                       # they cancelled already
        d2 = CFD.build("d2", [("e", "f", "rho_1"), ("e", "g", "rho_1")])
        self.assertEqual(len(box(a, d2).arrows), 2)

    def test_the_row_order_of_the_input_does_not_matter(self):
        with open(FIXTURE, encoding="utf-8") as handle:
            lines = handle.read().rstrip("\n").split("\n")
        head = [l for l in lines if l.startswith("#") or l.startswith("source")]
        body = [l for l in lines if l not in head]
        shuffled = read_cfa("\n".join(head + list(reversed(body))) + "\n")
        self.assertEqual(write_complex(box(fixture(), knots.cfd("figure-eight"))),
                         write_complex(box(shuffled, knots.cfd("figure-eight"))))

    def test_an_unreduced_type_d_is_refused_rather_than_guessed_at(self):
        a = fixture()
        d = CFD.build("unreduced", [("e", "f", None)], idempotent={"e": 0, "f": 0})
        with self.assertRaises(AlgebraError):
            box(a, d)


# ---------------------------------------------------------------- the formats

class Formats(unittest.TestCase):
    def test_cfa_round_trip(self):
        text = write_cfa(fixture())
        self.assertEqual(write_cfa(read_cfa(text)), text)

    def test_a_disc_csv_reads_as_a_cfa(self):
        # the disc format's extra columns are provenance and must simply be ignored
        discs = ("# heegaard-discs 1\n# diagram: t\n# count: 2\n"
                 "source,target,U,chords,arcs,path\n"
                 "y_0,x_7,0,P1,-1,N W\nx_0,x_3,1,,1,E\n")
        a = read_cfa(discs)
        self.assertEqual(len(a.operations), 2)
        self.assertEqual(a.idempotent, {"x_0": 1, "x_3": 1, "x_7": 1, "y_0": 0})

    def test_cfd_round_trip(self):
        for name in ("unknot", "trefoil", "figure-eight"):
            text = write_cfd(knots.cfd(name))
            self.assertEqual(write_cfd(read_cfd(text)), text, name)

    def test_cfk_round_trip_carries_the_grading(self):
        for name in ("trefoil", "figure-eight", "lh-trefoil"):
            k = knots.cfk(name)
            back = read_cfk(write_cfk(k))
            self.assertEqual(back.alexander, k.alexander, name)
            self.assertEqual(back.tau(), k.tau(), name)

    def test_complex_round_trip(self):
        text = write_complex(box(fixture(), knots.cfd("trefoil")))
        self.assertEqual(write_complex(read_complex(text)), text)

    def test_the_wrong_format_name_is_caught(self):
        with self.assertRaises(AlgebraError):
            read_cfd(write_cfa(fixture()))

    def test_a_miscounted_file_is_caught(self):
        with self.assertRaises(AlgebraError):
            read_cfd("# bordered-cfd 1\n# count: 9\nsource,target,chord\na,b,P1\n")

    def test_a_type_d_arrow_carries_one_chord(self):
        with self.assertRaises(AlgebraError):
            read_cfd("# bordered-cfd 1\nsource,target,chord\na,b,P1P2\n")


# ---------------------------------------------------------------- independence

class Independence(unittest.TestCase):
    def test_this_package_imports_nothing_from_heegaard(self):
        for name in os.listdir(SOURCE):
            if not name.endswith(".py"):
                continue
            with open(os.path.join(SOURCE, name),
                      encoding="utf-8") as handle:
                text = handle.read()
            self.assertNotIn("heegaard", text.replace("heegaard-py", "").replace(
                "heegaard-discs", "").replace("Heegaard", ""), name)

    def test_no_third_party_imports(self):
        for name in os.listdir(SOURCE):
            if not name.endswith(".py"):
                continue
            with open(os.path.join(SOURCE, name),
                      encoding="utf-8") as handle:
                for line in handle:
                    if line.startswith("import ") or line.startswith("from "):
                        head = line.split()[1].split(".")[0]
                        self.assertIn(head, {"", "argparse", "collections", "dataclasses",
                                             "itertools", "os", "sys", "typing",
                                             "__future__"}, f"{name}: {line.strip()}")


class CommandLine(unittest.TestCase):
    def run_it(self, *args):
        return subprocess.run([sys.executable, "-m", "satellite_floer", *args],
                              cwd=os.path.join(HERE, os.pardir),
                              capture_output=True, text=True)

    def test_knots_lists_the_catalogue(self):
        out = self.run_it("knots")
        self.assertEqual(out.returncode, 0)
        self.assertIn("figure-eight", out.stderr)

    def test_box_takes_a_knot_by_name(self):
        out = self.run_it("box", FIXTURE, "trefoil")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("bordered-complex 1", out.stdout)
        self.assertIn("d^2 = 0: True", out.stderr)

    def test_box_takes_the_torus_knot_parameters(self):
        out = self.run_it("box", FIXTURE, "t2", "5")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("dim H(C/(U-1)) = 1", out.stderr)

    def test_a_bad_knot_name_fails_cleanly(self):
        out = self.run_it("box", FIXTURE, "not-a-knot")
        self.assertEqual(out.returncode, 1)
        self.assertIn("no knot called", out.stderr)


if __name__ == "__main__":
    unittest.main()
