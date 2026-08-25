/** node atlas.js [i] [m] [n] [--cell=12] [--out=out/Qimn-atlas.svg] */
import { mkdirSync, writeFileSync } from 'node:fs';
import { Q, enumerateDiscs } from './src/index.js';
import { discAtlas } from './src/atlas.js';

const positional = process.argv.slice(2).filter((a) => !a.startsWith('--')).map(Number);
const flag = (name, fallback) =>
  process.argv.find((a) => a.startsWith(`--${name}=`))?.split('=')[1] ?? fallback;
const [i = 1, m = 2, n = 2] = positional;
const cell = Number(flag('cell', 12));
const arrange = flag('arrange', 'packed');   // 'packed' | 'insitu'

const diagram = Q(i, m, n);
const enumeration = enumerateDiscs(diagram, { cell, samples: 16, keepRegions: true });
const svg = discAtlas(enumeration, { arrange });

const out = flag('out', `out/Q${i}${m}${n}-atlas.svg`);
mkdirSync(out.replace(/\/[^/]*$/, ''), { recursive: true });
writeFileSync(out, svg);
console.log(`${diagram.name}: ${enumeration.discs.length} discs -> ${out} ` +
            `(${(svg.length / 1024).toFixed(0)} KB, ${arrange})`);
