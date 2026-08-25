/** node cli.js [i] [m] [n] [--cell=26] [--tiles=3] [--out=out] */
import { mkdirSync, writeFileSync } from 'node:fs';
import { Q, layout, findArcCrossings, renderDiagram, renderUniversalCover } from './src/index.js';

const positional = process.argv.slice(2).filter((a) => !a.startsWith('--')).map(Number);
const flag = (name, fallback) => {
  const hit = process.argv.find((a) => a.startsWith(`--${name}=`));
  return hit ? hit.split('=')[1] : fallback;
};
const [i = 2, m = 2, n = 2] = positional;
const cell = Number(flag('cell', 26));
const tiles = Number(flag('tiles', 3));
const dir = flag('out', 'out');

const diagram = Q(i, m, n);
const drawn = layout(diagram, { cell });
const crossings = findArcCrossings(drawn);

mkdirSync(dir, { recursive: true });
const stem = `Q${i}${m}${n}`;
writeFileSync(`${dir}/${stem}.svg`, renderDiagram(drawn));
writeFileSync(`${dir}/${stem}-cover.svg`, renderUniversalCover(layout(diagram, { cell: Math.max(10, cell * 0.62) }), { tiles }));

const { r, s, dependentStrands } = diagram.notes;
console.log(`${diagram.name} -> H(r=${r}, s=${s})`);
console.log(`  ${diagram.xCount} x-generators, ${diagram.yCount} y-generators, ${diagram.arcs.length} arcs`);
console.log(`  dependent strands: ${dependentStrands} (m+n-2)`);
console.log(`  beta components: ${diagram.components().length}`);
console.log(`  drawn arc crossings: ${crossings.length}`);
console.log(`  ${dir}/${stem}.svg   ${dir}/${stem}-cover.svg`);
