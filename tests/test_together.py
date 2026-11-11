"""The two subpackages used together: diagram -> discs -> CFA^- -> box.

These are the only tests that import both halves.  The halves do not import each other; they
meet here, in the top-level command line, and in a CSV of discs.
"""

import os
import subprocess
import sys
import tempfile
import unittest

from satellite_floer.bordered import box, knots, read_cfa, write_cfa
from satellite_floer.heegaard import build, discs_to_cfa_csv
from satellite_floer.heegaard.solver import enumerate_discs

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURE = os.path.join(HERE, "twin-rainbow-cfa.csv")
ROOT = os.path.join(HERE, os.pardir)


def cfa_of(r, s):
    diagram = build("hrs", r, s)
    return read_cfa(discs_to_cfa_csv(enumerate_discs(diagram), diagram))


class WholeCycle(unittest.TestCase):
    def test_H_r_s_through_to_the_satellite(self):
        # Q(i,m,n) = H(1 + 2im - m, n + 3m - 2mn + 4imn - 4im - 2)
        for i, m, n in [(1, 2, 1), (1, 2, 2), (1, 3, 2)]:
            r, s = 1 + 2 * i * m - m, n + 3 * m - 2 * m * n + 4 * i * m * n - 4 * i * m - 2
            a = cfa_of(r, s)
            for name in ("unknot", "trefoil", "figure-eight"):
                c = box(a, knots.cfd(name))
                self.assertTrue(c.is_a_complex(), (i, m, n, name))
                self.assertEqual(c.homology_rank_at_U1(), 1, (i, m, n, name))

    def test_the_fixture_is_what_the_solver_still_produces(self):
        a = cfa_of(3, 1)
        a.name = "twin-rainbow"          # H(3,1) is the same diagram under its other name
        with open(FIXTURE, encoding="utf-8") as handle:
            self.assertEqual(write_cfa(a), handle.read())

    def test_both_ways_of_writing_the_cfa_agree(self):
        diagram = build("twin-rainbow")
        theirs = discs_to_cfa_csv(enumerate_discs(diagram), diagram)
        self.assertEqual(write_cfa(read_cfa(theirs)), theirs)


class CommandLine(unittest.TestCase):
    """One command reaches both halves, and its errors come out the same way."""

    def run_it(self, *args, cwd=ROOT):
        return subprocess.run([sys.executable, "-m", "satellite_floer", *args],
                              cwd=cwd, capture_output=True, text=True,
                              env={**os.environ, "PYTHONPATH": os.path.abspath(ROOT)})

    def test_pattern_to_satellite_through_files(self):
        with tempfile.TemporaryDirectory() as work:
            for step in (["pattern", "hrs", "3", "1", "-o", "P.csv"],
                         ["solve", "P.csv", "-o", "discs.csv"],
                         ["box", "discs.csv", "trefoil", "-o", "out.csv"]):
                done = self.run_it(*step, cwd=work)
                self.assertEqual(done.returncode, 0, (step, done.stderr))
            done = self.run_it("check", "out.csv", cwd=work)
            self.assertIn("d^2 = 0: True", done.stderr)
            self.assertIn("dim H(C/(U-1)) = 1", done.stderr)

    def test_errors_from_either_half_are_one_line(self):
        for args, says in ((["pattern", "hrs", "2", "2"], "beta is not one curve"),
                           (["cfd", "not-a-knot"], "no knot called")):
            done = self.run_it(*args)
            self.assertEqual(done.returncode, 1, args)
            self.assertTrue(done.stderr.startswith("satellite-floer: "), done.stderr)
            self.assertIn(says, done.stderr)

    def test_version(self):
        from satellite_floer import __version__
        done = self.run_it("--version")
        self.assertEqual(done.stdout.strip(), f"satellite-floer {__version__}")


if __name__ == "__main__":
    unittest.main()
