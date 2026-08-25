/**
 * node atlas.js [i] [m] [n] [--cell=12] [--out=out/Qimn-atlas.svg]
 *                [--sample=80 | --all] [--dpi=110] [--max-px=40] [--no-png]
 *
 * By default it draws a sample: the largest disc of every distinct (chord word, U power),
 * then the largest ones left over.  --all draws every disc, which for a big diagram is a
 * canvas nobody can read.
 *
 * Writes the SVG, and a PNG beside it when Inkscape is installed.
 */
import { mkdirSync, writeFileSync } from 'node:fs';
import { Q, enumerateDiscs, sampleDiscs } from './src/index.js';
import { svgToPng } from './png.js';
import { discAtlas } from './src/atlas.js';

const positional = process.argv.slice(2).filter((a) => !a.startsWith('--')).map(Number);
const flag = (name, fallback) =>
  process.argv.find((a) => a.startsWith(`--${name}=`))?.split('=')[1] ?? fallback;
const [i = 1, m = 2, n = 2] = positional;
const cell = Number(flag('cell', 12));
const arrange = flag('arrange', 'packed');   // 'packed' | 'insitu'
const dpi = Number(flag('dpi', 110));
const maxMegapixels = Number(flag('max-px', 40));   // 0 disables the guard
const drawAll = process.argv.includes('--all');
const sampleSize = Number(flag('sample', 80));
const perClass = Number(flag('per-class', 1));
const wantPng = !process.argv.includes('--no-png');

const diagram = Q(i, m, n);
const enumeration = enumerateDiscs(diagram, { cell, samples: 16, keepRegions: true });

let caption, drawn = enumeration;
if (!drawAll) {
  const pick = sampleDiscs(enumeration.discs, { limit: sampleSize, perClass });
  drawn = { ...enumeration, discs: pick.chosen };
  caption = `${diagram.name}  ·  ${pick.shown} of ${pick.total} discs  ·  ` +
    `the largest of each of ${pick.classes} chord-and-U classes, then the largest left over` +
    `  ·  hover a disc for its label`;
}
const svg = discAtlas(drawn, { arrange, caption });

const out = flag('out', `out/Q${i}${m}${n}-atlas.svg`);
mkdirSync(out.replace(/\/[^/]*$/, ''), { recursive: true });
writeFileSync(out, svg);
const kb = (bytes) => `${(bytes / 1024).toFixed(0)} KB`;
console.log(`${diagram.name}: ${drawn.discs.length}` +
  (drawAll ? '' : ` of ${enumeration.discs.length}`) +
  ` discs -> ${out} (${kb(svg.length)}, ${arrange})`);

if (wantPng) {
  const png = svgToPng(out, { dpi, maxMegapixels });
  if (!png.ok) console.log(`  no png: ${png.why}`);
  else console.log(`  and ${png.path} (${kb(png.bytes)}, ${(png.pixels / 1e6).toFixed(1)} Mpx` +
    (png.capped ? `, dpi lowered to ${png.dpi.toFixed(0)} to stay under ${maxMegapixels} Mpx` : '') + ')');
}
