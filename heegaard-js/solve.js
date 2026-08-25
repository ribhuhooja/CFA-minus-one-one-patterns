/**
 * The solver as a filter: a diagram in, its discs out, both as CSV.
 *
 *   node solve.js diagram.csv                    # discs to stdout
 *   node solve.js diagram.csv --out=discs.csv
 *   cat diagram.csv | node solve.js              # or from stdin
 *
 * Nothing here knows what Q(i,m,n) is.  It reads whatever diagram the file describes, counts
 * the discs, and writes them.  That is the whole coupling between this and anything else --
 * a generator upstream and a visualiser downstream need only agree on these two formats, and
 * either can be replaced, in any language, without touching this.
 */
import { readFileSync, writeFileSync } from 'node:fs';
import { diagramFromCSV, discsToCSV, enumerateDiscs } from './src/index.js';

const args = process.argv.slice(2);
const flag = (name, fallback) =>
  args.find((a) => a.startsWith(`--${name}=`))?.split('=')[1] ?? fallback;
const input = args.find((a) => !a.startsWith('--'));
const out = flag('out', null);
const convention = flag('convention', 'composed');
const engine = flag('engine', 'heegaard');
const quiet = args.includes('--quiet') || !out;

const text = input ? readFileSync(input, 'utf8') : readFileSync(0, 'utf8');
const { diagram } = diagramFromCSV(text);

const started = Date.now();
const { discs, circuit, tried } = enumerateDiscs(diagram, { convention, engine });
const seconds = (Date.now() - started) / 1000;

const csv = discsToCSV(discs, { diagram, convention });
if (out) writeFileSync(out, csv); else process.stdout.write(csv);

if (!quiet || out) {
  const report = `${diagram.name}: ${diagram.xCount} x + ${diagram.yCount} y generators, ` +
    `${diagram.arcs.length} arcs -> ${discs.length} discs ` +
    `(${tried} pieces of beta, ${seconds.toFixed(2)}s)`;
  console.error(report);
}
