/**
 * node atlas.js [i] [m] [n] [--cell=12] [--out=out/Qimn-atlas.svg] [--dpi=110] [--no-png]
 *
 * Writes the SVG, and a PNG beside it when Inkscape is installed.
 */
import { mkdirSync, writeFileSync } from 'node:fs';
import { Q, enumerateDiscs } from './src/index.js';
import { svgToPng } from './png.js';
import { discAtlas } from './src/atlas.js';

const positional = process.argv.slice(2).filter((a) => !a.startsWith('--')).map(Number);
const flag = (name, fallback) =>
  process.argv.find((a) => a.startsWith(`--${name}=`))?.split('=')[1] ?? fallback;
const [i = 1, m = 2, n = 2] = positional;
const cell = Number(flag('cell', 12));
const arrange = flag('arrange', 'packed');   // 'packed' | 'insitu'
const dpi = Number(flag('dpi', 110));
const wantPng = !process.argv.includes('--no-png');

const diagram = Q(i, m, n);
const enumeration = enumerateDiscs(diagram, { cell, samples: 16, keepRegions: true });
const svg = discAtlas(enumeration, { arrange });

const out = flag('out', `out/Q${i}${m}${n}-atlas.svg`);
mkdirSync(out.replace(/\/[^/]*$/, ''), { recursive: true });
writeFileSync(out, svg);
const kb = (bytes) => `${(bytes / 1024).toFixed(0)} KB`;
console.log(`${diagram.name}: ${enumeration.discs.length} discs -> ${out} (${kb(svg.length)}, ${arrange})`);

if (wantPng) {
  const png = svgToPng(out, { dpi });
  if (png.ok) console.log(`  and ${png.path} (${kb(png.bytes)}, ${dpi} dpi)`);
  else console.log(`  no png: ${png.why}`);
}
