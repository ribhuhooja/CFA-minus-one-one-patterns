/**
 * Re-run a fixed set of diagrams and check the disc lists have not moved.
 *   node test/regression.js
 *
 * The fixture in test/golden/discs.json was produced before any of the speed work; it holds
 * the number of discs and a hash of the disc list for each diagram, so any change to the
 * answers shows up here whatever caused it.
 */
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { Q, enumerateDiscs, toCSV } from '../src/index.js';

const golden = JSON.parse(readFileSync(new URL('./golden/discs.json', import.meta.url), 'utf8'));
let failed = 0;
console.log(`\n  ${golden.cases.length} diagrams against test/golden/discs.json (${golden.produced})\n`);
console.log('  diagram        gens   discs   time     result');
console.log('  ' + '-'.repeat(54));

const started = Date.now();
for (const expected of golden.cases) {
  const t0 = Date.now();
  const { discs, circuit } = enumerateDiscs(Q(expected.i, expected.m, expected.n));
  const seconds = ((Date.now() - t0) / 1000).toFixed(2);
  const hash = createHash('sha256')
    .update(toCSV(discs, { format: 'reference', sort: true })).digest('hex').slice(0, 16);

  const complaints = [];
  if (circuit !== expected.generators) complaints.push(`${circuit} generators, expected ${expected.generators}`);
  if (discs.length !== expected.discs) complaints.push(`${discs.length} discs, expected ${expected.discs}`);
  if (hash !== expected.sha256) complaints.push(`hash ${hash}, expected ${expected.sha256}`);
  if (complaints.length) failed++;

  console.log(`  Q(${expected.i},${expected.m},${expected.n})`.padEnd(15) +
    String(circuit).padStart(6) + String(discs.length).padStart(8) +
    `${seconds}s`.padStart(8) + '   ' + (complaints.length ? `FAIL  ${complaints.join('; ')}` : 'same'));
}
console.log('  ' + '-'.repeat(54));
console.log(`  ${golden.cases.length - failed} unchanged, ${failed} changed` +
            `   in ${((Date.now() - started) / 1000).toFixed(1)}s\n`);
process.exit(failed ? 1 : 0);
