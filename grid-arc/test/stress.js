/**
 * The uniqueness study.  node test/stress.js [count] [seed]
 *
 * Per randomly generated valid arc:
 *   U1  at most one path satisfies (P1)-(P4)
 *   U2  Appendix A pruning does not change the solution set
 *   U3  ... nor does the extra strict rule
 *   U4  every returned path re-validates
 *   U5  the winding number is -1 everywhere inside D (adaptive dense sampling)
 *   U6  the Appendix A walk is deterministic: never more than one open step
 *   U7  W/S steps out of a lattice point occur only as the final partial edge
 *   U8  the cell set C matches a dense resampling of the arc
 *   U9  widening the search space finds no extra solutions (the §6 lemma)
 *   U10 strategy:'walk' and strategy:'search' return the same solution set
 */
import { writeFileSync } from 'node:fs';
import {
  solve, checkPath, signedArea, windingNumber, boundingBox, distancePointSegment
} from '../src/index.js';
import { makeRandom, randomArc } from '../src/random.js';

const COUNT = Number(process.argv[2] ?? 5000);
const SEED = Number(process.argv[3] ?? 20260824);
const rnd = makeRandom(SEED);

const CHECKS = {
  U1: 'at most one solution per arc',
  U2: 'rules-on solution set == rules-off',
  U3: 'strict-rules solution set == rules-off',
  U4: 'every returned path re-validates',
  U5: 'winding is -1 throughout D',
  U6: 'the Appendix A walk is deterministic',
  U7: 'W/S steps from a lattice point only as the final partial edge',
  U8: 'cell set C matches a dense resampling of the arc',
  U9: 'widening the search space finds no extra solutions (§6 lemma)',
  U10: "strategy 'walk' agrees with strategy 'search'"
};
const failures = Object.fromEntries(Object.keys(CHECKS).map((k) => [k, []]));
const stat = {
  arcs: 0, solved: 0, modes: {}, lengths: {}, firstStepSW: 0,
  lemmaChecked: 0, lemmaSkipped: 0, openStepsRulesOn: {}, openStepsGeometryOnly: {},
  rulesRemovedABranch: 0, decisions: 0, candidatesPerArc: {}
};

const signature = (result) =>
  result.solutions
    .map((s) => s.points.map((p) => `${p[0].toFixed(6)},${p[1].toFixed(6)}`).join(' '))
    .sort().join(' | ');

/** Dense winding scan; the sample spacing adapts so that sliver regions are not missed. */
function windingScan(polygon) {
  const [x0, y0, x1, y1] = boundingBox(polygon);
  const h = Math.max(1e-4, Math.min(0.05, Math.sqrt(Math.abs(signedArea(polygon))) / 8));
  const onCurve = Math.min(1e-3, h / 10);
  let sawInterior = false;
  for (let x = x0 + h / 2; x < x1; x += h)
    for (let y = y0 + h / 2; y < y1; y += h) {
      const p = [x, y];
      let touching = false;
      for (let i = 0; i < polygon.length && !touching; i++)
        if (distancePointSegment(p, polygon[i], polygon[(i + 1) % polygon.length]) < onCurve) touching = true;
      if (touching) continue;
      const w = windingNumber(polygon, p);
      if (w === -1) sawInterior = true;
      else if (w !== 0) return { ok: false, bad: { p, w } };
    }
  return { ok: sawInterior, bad: sawInterior ? null : 'no interior point with winding -1' };
}

for (let i = 0; i < COUNT; i++) {
  const generated = randomArc(rnd, { maxCells: 2 + Math.floor(rnd() * 11) });
  if (!generated) { i--; continue; }
  const { arc, mode } = generated;
  stat.arcs++;
  stat.modes[mode] = (stat.modes[mode] ?? 0) + 1;

  const plain = solve(arc, { strategy: 'search', decisions: true });
  const ruled = solve(arc, { strategy: 'search', useRules: true, decisions: true });
  const strict = solve(arc, { strategy: 'search', useRules: true, strictRule: true });
  const walked = solve(arc, { strategy: 'walk' });

  if (plain.solutions.length > 1)
    failures.U1.push({ arc, count: plain.solutions.length,
                       paths: plain.solutions.map((s) => s.directions.join(' ')) });
  if (signature(plain) !== signature(ruled)) failures.U2.push({ arc });
  if (signature(plain) !== signature(strict)) failures.U3.push({ arc });
  if (signature(plain) !== signature(walked))
    failures.U10.push({ arc, search: signature(plain), walk: signature(walked) });

  if (plain.status === 'solved') stat.solved++;
  stat.candidatesPerArc[plain.stats.candidates] = (stat.candidatesPerArc[plain.stats.candidates] ?? 0) + 1;

  for (const solution of plain.solutions) {
    if (!checkPath(solution.points, plain.arc).ok)
      failures.U4.push({ arc, path: solution.directions.join(' ') });
    const scan = windingScan(solution.region.polygon);
    if (!scan.ok) failures.U5.push({ arc, path: solution.directions.join(' '), bad: scan.bad });

    const d = solution.directions;
    for (let k = 1; k + 1 < d.length; k++)
      if (d[k] === 'W' || d[k] === 'S') failures.U7.push({ arc, path: d.join(' '), at: k });
    if (d[0] === 'S' || d[0] === 'W') stat.firstStepSW++;
    stat.lengths[d.length] = (stat.lengths[d.length] ?? 0) + 1;

    for (const decision of solution.decisions) {
      stat.openStepsGeometryOnly[decision.geometricCount] =
        (stat.openStepsGeometryOnly[decision.geometricCount] ?? 0) + 1;
      stat.decisions++;
      if (decision.localCount < decision.geometricCount) stat.rulesRemovedABranch++;
    }
  }
  for (const solution of ruled.solutions)
    for (const decision of solution.decisions) {
      stat.openStepsRulesOn[decision.localCount] = (stat.openStepsRulesOn[decision.localCount] ?? 0) + 1;
      if (decision.localCount > 1)
        failures.U6.push({ arc, at: decision.v, from: decision.from, open: decision.open });
    }

  // U8: recompute C by dense resampling
  {
    const reference = new Set();
    for (let k = 0; k + 1 < arc.length; k++) {
      const a = arc[k], b = arc[k + 1];
      const steps = Math.max(2, Math.ceil(Math.hypot(b[0] - a[0], b[1] - a[1]) / 0.002));
      for (let q = 1; q < steps; q++) {
        const t = q / steps, x = a[0] + t * (b[0] - a[0]), y = a[1] + t * (b[1] - a[1]);
        if (Number.isInteger(x) || Number.isInteger(y)) continue;
        reference.add(`${Math.floor(x)},${Math.floor(y)}`);
      }
    }
    const found = new Set(plain.arc.cells.map((c) => `${c.i},${c.j}`));
    const missing = [...reference].filter((k) => !found.has(k));
    const extra = [...found].filter((k) => !reference.has(k));
    if (missing.length || extra.length) failures.U8.push({ arc, missing, extra });
  }

  // U9: the §6 lemma, on arcs small enough to enumerate exhaustively
  {
    const [x0, y0, x1, y1] = boundingBox(arc);
    if (x1 - x0 <= 4.5 && y1 - y0 <= 4.5) {
      stat.lemmaChecked++;
      const wide = solve(arc, { strategy: 'search', searchSpace: 'bbox', bboxPad: 1, maxPathLength: 12 });
      if (!wide.stats.truncated && signature(wide) !== signature(plain))
        failures.U9.push({ arc, cellSpace: signature(plain), bboxSpace: signature(wide) });
    } else stat.lemmaSkipped++;
  }
}

const line = (s = '') => console.log(s);
line();
line('  uniqueness stress test');
line('  ' + '-'.repeat(62));
line(`  arcs generated (valid)   : ${stat.arcs}   seed ${SEED}`);
line(`  generator mix            : ${JSON.stringify(stat.modes)}`);
line(`  solved / no solution     : ${stat.solved} / ${stat.arcs - stat.solved}`);
line(`  solution length histogram: ${JSON.stringify(stat.lengths)}`);
line(`  first partial edge S or W: ${stat.firstStepSW}  (allowed by §5)`);
line(`  §6-lemma cross-check on  : ${stat.lemmaChecked} arcs (${stat.lemmaSkipped} too large)`);
line(`  open steps, geometry only: ${JSON.stringify(stat.openStepsGeometryOnly)}`);
line(`  open steps, rules on     : ${JSON.stringify(stat.openStepsRulesOn)}`);
line(`  decisions where a rule removed a branch: ${stat.rulesRemovedABranch} of ${stat.decisions}`);
line(`  paths reaching v_e per arc: ${JSON.stringify(stat.candidatesPerArc)}`);
line();
let anyFailed = false;
for (const [key, description] of Object.entries(CHECKS)) {
  const n = failures[key].length;
  if (n) anyFailed = true;
  line(`  ${n ? 'FAIL' : 'pass'}  ${key.padEnd(4)}${description}${n ? `   (${n} counterexamples)` : ''}`);
}
line();
if (anyFailed) {
  const out = Object.fromEntries(
    Object.entries(failures).filter(([, v]) => v.length).map(([k, v]) => [k, v.slice(0, 20)]));
  writeFileSync(new URL('../counterexamples.json', import.meta.url), JSON.stringify(out, null, 2));
  line('  counterexamples.json written — load it in the UI');
  for (const [k, v] of Object.entries(out)) line(`  --- ${k} --- ${JSON.stringify(v[0]).slice(0, 320)}`);
}
process.exit(anyFailed ? 1 : 0);
