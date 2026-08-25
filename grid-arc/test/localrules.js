/**
 * Are the Appendix A rules enough on their own?   node test/localrules.js [count] [seed]
 *
 * Runs strategy:'walk' — the deterministic local walk, with the global (P1)-(P4) test used
 * only to accept or reject its single answer — and compares against the exhaustive search.
 *
 *   A  the walk produces nothing, and no solution exists          (local rules right)
 *   B  the walk produces a path and it is a genuine solution      (local rules right)
 *   C  the walk produces a path that fails the global check       (local rules WRONG)
 *   D  the walk produces nothing although a solution exists       (local rules WRONG)
 *
 * C is the interesting column: it measures what the local rules cannot see.
 */
import { solve, distancePointSegment } from '../src/index.js';
import { makeRandom, randomArc } from '../src/random.js';

const COUNT = Number(process.argv[2] ?? 8000);
const SEED = Number(process.argv[3] ?? 20260824);
const rnd = makeRandom(SEED);

const category = { A: 0, B: 0, C: 0, D: 0 };
const failureCodes = {}, cornerLocation = {}, wrongShape = {}, cornerDistance = {};
const walkStatus = {};

for (let i = 0; i < COUNT; i++) {
  const generated = randomArc(rnd, { maxCells: 2 + Math.floor(rnd() * 11) });
  if (!generated) { i--; continue; }
  const { arc } = generated;

  const walked = solve(arc, { strategy: 'walk' });
  const truth = solve(arc, { strategy: 'search' });
  if (walked.walk) walkStatus[walked.walk.status] = (walkStatus[walked.walk.status] ?? 0) + 1;

  const produced = walked.solutions.length + walked.rejected.length;
  if (produced === 0) {
    if (truth.solutions.length) category.D++; else category.A++;
    continue;
  }
  if (walked.solutions.length) { category.B++; continue; }

  category.C++;
  const wrong = walked.rejected[0];
  wrongShape[wrong.kind] = (wrongShape[wrong.kind] ?? 0) + 1;
  for (const f of wrong.failures) failureCodes[f.code] = (failureCodes[f.code] ?? 0) + 1;

  // Where does the forbidden point that the walk missed actually sit?
  for (const { cell } of wrong.region.forbiddenInside) {
    const corner = [cell[0], cell[1] + 1];           // the forbidden point hugs this lattice point
    const onPath = wrong.points.some((p) => p[0] === corner[0] && p[1] === corner[1]);
    const { vs, ve } = walked.endpoints;
    const where = !onPath ? 'off the path'
      : corner[0] === vs[0] && corner[1] === vs[1] ? 'at v_s'
      : corner[0] === ve[0] && corner[1] === ve[1] ? 'at v_e'
      : 'at an interior lattice point';
    cornerLocation[where] = (cornerLocation[where] ?? 0) + 1;
    if (!onPath) {
      let d = Infinity;
      for (let k = 0; k + 1 < wrong.points.length; k++)
        d = Math.min(d, distancePointSegment(corner, wrong.points[k], wrong.points[k + 1]));
      const bucket = wrong.kind === 'search' || wrong.kind === 'walk' ? `path, ${d.toFixed(1)} away` : wrong.kind;
      cornerDistance[bucket] = (cornerDistance[bucket] ?? 0) + 1;
    }
  }
}

const line = (s = '') => console.log(s);
line();
line(`  the Appendix A walk on its own, over ${COUNT} random arcs (seed ${SEED})`);
line('  ' + '-'.repeat(66));
line(`  A  walk produces nothing, no solution exists : ${String(category.A).padStart(5)}   right`);
line(`  B  walk produces the genuine solution        : ${String(category.B).padStart(5)}   right`);
line(`  C  walk produces an INVALID path             : ${String(category.C).padStart(5)}   WRONG`);
line(`  D  walk produces nothing, a solution exists  : ${String(category.D).padStart(5)}   WRONG`);
line();
line(`  how the walk ended            : ${JSON.stringify(walkStatus)}`);
line(`  what rejected its answer in C : ${JSON.stringify(failureCodes)}`);
line(`  shape of the wrong candidate  : ${JSON.stringify(wrongShape)}`);
line(`  the missed forbidden point is : ${JSON.stringify(cornerLocation)}`);
line(`  ...and when off the path      : ${JSON.stringify(cornerDistance)}`);
line();
line(category.D === 0
  ? '  D = 0: the local rules never kill a genuine solution.'
  : '  D > 0: the local rules DISCARD genuine solutions — the conjecture is false.');
line(category.C === 0
  ? '  C = 0: on this sample the local rules alone were a complete decision procedure.'
  : `  C > 0: the local rules cannot reject. The global (P3) test is doing real work in ${category.C} cases.`);
