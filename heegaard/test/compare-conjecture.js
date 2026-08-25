/**
 * Check the computed discs of Q(i,2,2) against the conjectured arrow tables.
 *   node test/compare-conjecture.js [maxI]
 *
 * A row is (source, target, U, chord word).  Nothing is normalised away: the two lists have
 * to agree as multisets, row for row.
 */
import { Q, enumerateDiscs, chordWord } from '../src/index.js';
import { conjecturedArrows, conjecturedCount } from '../src/conjectured.js';

const maxI = Number(process.argv[2] ?? 3);
const row = (r) => [r.source, r.target, r.U, r.word].join(' | ');

let failures = 0;
console.log('\n  Q(i,2,2): computed discs against the conjectured tables\n');
for (let i = 1; i <= maxI; i++) {
  const started = Date.now();
  const computed = enumerateDiscs(Q(i, 2, 2)).discs
    .map((d) => ({ source: d.source, target: d.target, U: d.U, word: chordWord(d.chords) }));
  const conjectured = conjecturedArrows(i);

  const bag = (rows) => {
    const counts = new Map();
    for (const r of rows) counts.set(row(r), (counts.get(row(r)) ?? 0) + 1);
    return counts;
  };
  const mine = bag(computed), theirs = bag(conjectured);
  const keys = new Set([...mine.keys(), ...theirs.keys()]);
  let matched = 0;
  const differing = [];
  for (const key of keys) {
    const a = mine.get(key) ?? 0, b = theirs.get(key) ?? 0;
    matched += Math.min(a, b);
    if (a !== b) differing.push(`${a ? 'computed only  ' : 'conjecture only'}   ${key}`);
  }

  const seconds = ((Date.now() - started) / 1000).toFixed(1);
  const total = Math.max(computed.length, conjectured.length);
  console.log(`  i=${i}   computed ${String(computed.length).padStart(4)}   ` +
    `conjectured ${String(conjectured.length).padStart(4)} (64i-18 = ${conjecturedCount(i)})   ` +
    `rows matching ${String(matched).padStart(4)}/${total}   ${seconds}s   ` +
    (differing.length ? `${differing.length} DIFFER` : 'exact'));
  for (const line of differing.slice(0, 20)) console.log(`      ${line}`);
  if (differing.length) failures++;
}
console.log();
process.exit(failures ? 1 : 0);
