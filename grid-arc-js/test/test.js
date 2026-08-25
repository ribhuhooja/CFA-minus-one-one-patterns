/**
 * Correctness harness.   node test/test.js [fuzzCount] [seed]
 * Built-in examples, JSON round-trip, and a fuzz pass with the §8 assertions.
 * `node test/stress.js` is the larger uniqueness study.
 */
import { writeFileSync } from 'node:fs';
import { solve, validateArc, checkPath } from '../src/index.js';
import { makeRandom, randomArc } from '../src/random.js';
import { EXAMPLES } from '../src/examples.js';

const FUZZ = Number(process.argv[2] ?? 2000);
const SEED = Number(process.argv[3] ?? 20260824);

let passed = 0, failed = 0;
const counterexamples = [];
function check(name, condition, info) {
  if (condition) { passed++; return true; }
  failed++;
  console.log(`  FAIL  ${name}${info ? `\n        ${info}` : ''}`);
  return false;
}
const signature = (r) => r.solutions
  .map((s) => s.points.map((p) => `${p[0].toFixed(6)},${p[1].toFixed(6)}`).join(' ')).sort().join('|');

console.log('\n  defaults');
check("the default strategy is the walk", solve(EXAMPLES[0].arc).solutions[0].kind.includes('walk'),
      solve(EXAMPLES[0].arc).solutions[0]?.kind);

console.log('\n  built-in examples');
for (const example of EXAMPLES) {
  const problems = validateArc(example.arc);
  if (!check(`"${example.name}" is valid input`, problems.length === 0, JSON.stringify(problems))) continue;
  const result = solve(example.arc, { strategy: 'search' });
  if (example.expect === null) {
    check(`"${example.name}" has no solution`, result.status === 'no-solution', `got ${result.status}`);
  } else if (check(`"${example.name}" solves`, result.status === 'solved', result.reason)) {
    check(`"${example.name}" path = ${example.expect}`,
          result.solutions[0].directions.join(' ') === example.expect,
          `got ${result.solutions[0].directions.join(' ')}`);
    check(`"${example.name}" is unique`, result.solutions.length === 1,
          `${result.solutions.length} solutions`);
  }
  const walked = solve(example.arc, { strategy: 'walk' });
  check(`"${example.name}" agrees under strategy 'walk'`, signature(walked) === signature(result),
        `${signature(walked)} vs ${signature(result)}`);
}

// §8 asks for these shapes to be represented
const solvedDirections = EXAMPLES.filter((e) => e.expect).map((e) => e.expect.split(' '));
check('an example ends with a W step', solvedDirections.some((d) => d.at(-1) === 'W'));
check('an example ends with an S step', solvedDirections.some((d) => d.at(-1) === 'S'));
check('an example is a same-edge path with no lattice point', solvedDirections.some((d) => d.length === 1));
check('an example has no solution', EXAMPLES.some((e) => e.expect === null));

console.log('\n  JSON round-trip');
{
  const example = EXAMPLES[2];
  const loaded = JSON.parse(JSON.stringify({ format: 'grid-arc', version: 2, arc: example.arc }));
  check('save/load preserves the solution',
        signature(solve(example.arc, { strategy: 'search' })) ===
        signature(solve(loaded.arc, { strategy: 'search' })));
}

console.log(`\n  fuzz (${FUZZ} random valid arcs, seed ${SEED})`);
{
  const rnd = makeRandom(SEED);
  let n = 0, solved = 0, multiple = 0, ruleMismatch = 0, walkMismatch = 0, invalid = 0, misoriented = 0;
  while (n < FUZZ) {
    const generated = randomArc(rnd, { maxCells: 2 + Math.floor(rnd() * 11) });
    if (!generated) continue;
    n++;
    const { arc } = generated;
    const plain = solve(arc, { strategy: 'search' });
    const ruled = solve(arc, { strategy: 'search', useRules: true });
    const walked = solve(arc, { strategy: 'walk' });

    if (plain.solutions.length > 1) { multiple++; counterexamples.push({ why: 'multiple solutions', arc }); }
    if (signature(plain) !== signature(ruled)) { ruleMismatch++; counterexamples.push({ why: 'rules changed the answer', arc }); }
    if (signature(plain) !== signature(walked)) { walkMismatch++; counterexamples.push({ why: 'walk disagrees with search', arc }); }
    if (plain.solutions.length) solved++;
    for (const s of plain.solutions) {
      if (!checkPath(s.points, plain.arc).ok) { invalid++; counterexamples.push({ why: 're-validation', arc }); }
      if (!(s.region.area < 0)) { misoriented++; counterexamples.push({ why: 'winding sign', arc }); }
    }
  }
  console.log(`        ${n} arcs, ${solved} solved, ${n - solved} with no solution`);
  check('every arc has at most one solution', multiple === 0, `${multiple} violations`);
  check('Appendix A pruning does not change the answer', ruleMismatch === 0, `${ruleMismatch} violations`);
  check("strategy 'walk' agrees with strategy 'search'", walkMismatch === 0, `${walkMismatch} violations`);
  check('every returned path re-validates', invalid === 0, `${invalid} violations`);
  check('every solution has winding -1 inside D', misoriented === 0, `${misoriented} violations`);
}

console.log(`\n  ${passed} passed, ${failed} failed\n`);
if (counterexamples.length) {
  writeFileSync(new URL('../counterexamples.json', import.meta.url),
                JSON.stringify(counterexamples.slice(0, 20), null, 2));
  console.log('  counterexamples.json written — load it in the UI\n');
}
process.exit(failed ? 1 : 0);
