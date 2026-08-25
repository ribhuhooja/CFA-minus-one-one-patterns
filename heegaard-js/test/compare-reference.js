/**
 * Diff the computed disc list against a reference table.
 *   node test/compare-reference.js [i] [m] [n] [path/to/reference.csv]
 *
 * The reference is whatever the conjecture currently says; this script does not assume it
 * is right.  It reports where the two agree and prints every row where they do not.
 */
import { readFileSync } from 'node:fs';
import { Q, enumerateDiscs, chordWord } from '../src/index.js';

const args = process.argv.slice(2);
const [i = 2, m = 2, n = 2] = args.filter((a) => /^\d+$/.test(a)).map(Number);
const path = args.find((a) => a.endsWith('.csv'))
  ?? '/Users/ribhu/dependent-region-shur/reference_Q222.csv';

const reference = readFileSync(path, 'utf8').replace(/\r/g, '').trim().split('\n').slice(1)
  .map((line) => {
    const f = line.split(',').map((x) => x.trim());
    return {
      source: f[0], target: f[1],
      U: f[3] === '' ? 0 : f[3] === 'U' ? 1 : Number(f[3].replace('U^', '')),
      word: f[4] ?? ''
    };
  });

const { discs } = enumerateDiscs(Q(i, m, n));

const bag = (rows, key) => {
  const counts = new Map();
  for (const row of rows) counts.set(key(row), (counts.get(key(row)) ?? 0) + 1);
  return counts;
};
function compare(name, mine, theirs) {
  const keys = new Set([...mine.keys(), ...theirs.keys()]);
  let matched = 0;
  const differing = [];
  for (const key of keys) {
    const a = mine.get(key) ?? 0, b = theirs.get(key) ?? 0;
    matched += Math.min(a, b);
    if (a !== b) differing.push({ key, mine: a, reference: b });
  }
  const total = Math.max(discs.length, reference.length);
  console.log(`  ${name.padEnd(38)} ${String(matched).padStart(4)} / ${total}` +
              (differing.length ? '' : '   exact'));
  return differing;
}

const sorted = (word) => (word ? word.split('P').filter(Boolean).map((x) => `P${x}`).sort().join('') : '');

console.log(`\n  Q(${i},${m},${n}) against ${path.split('/').pop()}`);
console.log(`  computed ${discs.length} discs, reference has ${reference.length}\n`);
compare('U power', bag(discs, (d) => `U^${d.U}`), bag(reference, (r) => `U^${r.U}`));
compare('chord word', bag(discs, (d) => chordWord(d.chords)), bag(reference, (r) => r.word));
compare('chord multiset (order ignored)',
        bag(discs, (d) => sorted(chordWord(d.chords))), bag(reference, (r) => sorted(r.word)));
compare('source and target', bag(discs, (d) => `${d.source}->${d.target}`),
        bag(reference, (r) => `${r.source}->${r.target}`));
const rows = compare('whole row',
  bag(discs, (d) => [d.source, d.target, d.U, chordWord(d.chords)].join(',')),
  bag(reference, (r) => [r.source, r.target, r.U, r.word].join(',')));

if (rows.length) {
  console.log(`\n  rows that differ (${rows.length}):`);
  for (const row of rows)
    console.log(`    ${row.mine ? 'computed only' : 'reference only'}   ${row.key}`);
}
console.log();
