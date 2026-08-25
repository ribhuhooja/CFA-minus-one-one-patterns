/** node discs.js [i] [m] [n] [--convention=composed] [--out=out/Qimn-discs.csv] */
import { mkdirSync, writeFileSync } from 'node:fs';
import { Q, enumerateDiscs, toCSV } from './src/index.js';

const positional = process.argv.slice(2).filter((a) => !a.startsWith('--')).map(Number);
const flag = (name, fallback) =>
  process.argv.find((a) => a.startsWith(`--${name}=`))?.split('=')[1] ?? fallback;
const [i = 2, m = 2, n = 2] = positional;
const convention = flag('convention', 'composed');
const format = flag('format', 'full');

const diagram = Q(i, m, n);
const started = Date.now();
const { discs, circuit, generators, tried } = enumerateDiscs(diagram, { convention });
const seconds = ((Date.now() - started) / 1000).toFixed(1);

const out = flag('out', `out/Q${i}${m}${n}-discs${format === 'reference' ? '-reference' : ''}.csv`);
mkdirSync(out.replace(/\/[^/]*$/, ''), { recursive: true });
writeFileSync(out, toCSV(discs, { format, sort: true }));

const byU = {};
for (const d of discs) byU[`U^${d.U}`] = (byU[`U^${d.U}`] ?? 0) + 1;
const bySource = new Map();
for (const d of discs) bySource.set(d.source, (bySource.get(d.source) ?? 0) + 1);

console.log(`${diagram.name} -> H(r=${diagram.notes.r}, s=${diagram.notes.s})`);
console.log(`  ${generators.length} generators, beta circuit ${circuit} arcs`);
console.log(`  tried ${tried} pieces of beta in ${seconds}s`);
console.log(`  ${discs.length} discs   ${JSON.stringify(byU)}   Reeb convention: ${convention}`);
console.log(`  discs per generator: min ${Math.min(...bySource.values())}, ` +
            `max ${Math.max(...bySource.values())}, ` +
            `${generators.length - bySource.size} generators with none`);
console.log(`  ${out}  (${format} layout)`);
