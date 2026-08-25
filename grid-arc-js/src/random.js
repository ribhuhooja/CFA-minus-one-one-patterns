/**
 * Random valid arcs, for fuzzing.  Three generators, all filtered through validateArc,
 * so anything returned is legal input by §2.
 *
 *   'walk'     self-avoiding walk on cells, routed entry -> interior point -> exit
 *   'revisit'  the same but allowed to re-enter a cell (most attempts self-intersect
 *              and are rejected, which is fine and cheap)
 *   'smooth'   a Catmull-Rom curve through random control points, clipped between two of
 *              its grid crossings
 */
import { simplify } from './geometry.js';
import { GRID, OPPOSITE } from './grid.js';
import { validateArc } from './arc.js';

/** Small deterministic PRNG, so every run is reproducible from its seed. */
export function makeRandom(seed) {
  let a = seed | 0;
  return function random() {
    a = (a + 0x6D2B79F5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const LO = 3, HI = 16;                       // generate inside the window, with room to spare
const pick = (rnd, xs) => xs[Math.floor(rnd() * xs.length)];
const jitter = (rnd, r) => (rnd() - 0.5) * 2 * r;

const STEPS = [[1, 0], [-1, 0], [0, 1], [0, -1]];
const SIDE_OF_STEP = { '1,0': 'E', '-1,0': 'W', '0,1': 'N', '0,-1': 'S' };

/** A point in the interior of one side of C(i,j), away from both corners. */
function sidePoint(rnd, i, j, side) {
  const t = 0.18 + 0.64 * rnd();
  switch (side) {
    case 'S': return [i + t, j];
    case 'N': return [i + t, j + 1];
    case 'W': return [i, j + t];
    default:  return [i + 1, j + t];
  }
}

export function cellWalk(rnd, { maxCells = 6, allowRevisit = false } = {}) {
  const steps = 1 + Math.floor(rnd() * maxCells);
  let i = LO + 1 + Math.floor(rnd() * (HI - LO - 2));
  let j = LO + 1 + Math.floor(rnd() * (HI - LO - 2));
  const cells = [[i, j]], seen = new Set([`${i},${j}`]), moves = [];

  for (let k = 0; k < steps; k++) {
    const options = STEPS.filter(([dx, dy]) => {
      const x = i + dx, y = j + dy;
      if (x < LO || x > HI || y < LO || y > HI) return false;
      if (!allowRevisit && seen.has(`${x},${y}`)) return false;
      const last = moves.at(-1);
      return !(last && dx === -last[0] && dy === -last[1]);
    });
    if (!options.length) break;
    const move = pick(rnd, options);
    moves.push(move); i += move[0]; j += move[1];
    cells.push([i, j]); seen.add(`${i},${j}`);
  }

  const points = [];
  const firstExit = moves.length ? SIDE_OF_STEP[moves[0].join(',')] : null;
  points.push(sidePoint(rnd, ...cells[0], pick(rnd, ['N', 'S', 'E', 'W'].filter((s) => s !== firstExit))));
  cells.forEach(([ci, cj], k) => {
    points.push([ci + 0.5 + jitter(rnd, 0.22), cj + 0.5 + jitter(rnd, 0.22)]);
    if (k < moves.length) points.push(sidePoint(rnd, ci, cj, SIDE_OF_STEP[moves[k].join(',')]));
  });
  const lastEntry = moves.length ? OPPOSITE[SIDE_OF_STEP[moves.at(-1).join(',')]] : null;
  points.push(sidePoint(rnd, ...cells.at(-1), pick(rnd, ['N', 'S', 'E', 'W'].filter((s) => s !== lastEntry))));
  return points;
}

export function catmullRom(control, samplesPerSegment) {
  const p = [control[0], ...control, control.at(-1)], out = [];
  for (let i = 1; i + 2 < p.length; i++) {
    const [p0, p1, p2, p3] = [p[i - 1], p[i], p[i + 1], p[i + 2]];
    for (let s = 0; s < samplesPerSegment; s++) {
      const t = s / samplesPerSegment, t2 = t * t, t3 = t2 * t;
      out.push([0, 1].map((a) => 0.5 * (2 * p1[a] + (-p0[a] + p2[a]) * t +
        (2 * p0[a] - 5 * p1[a] + 4 * p2[a] - p3[a]) * t2 +
        (-p0[a] + 3 * p1[a] - 3 * p2[a] + p3[a]) * t3)));
    }
  }
  out.push(control.at(-1));
  return out;
}

/** Every grid crossing along a polyline, in order. */
function gridCrossings(points) {
  const hits = [];
  for (let i = 0; i + 1 < points.length; i++) {
    const a = points[i], b = points[i + 1], local = [];
    for (const axis of [0, 1]) {
      if (Math.abs(b[axis] - a[axis]) <= 1e-12) continue;
      for (let k = Math.ceil(Math.min(a[axis], b[axis])); k <= Math.floor(Math.max(a[axis], b[axis])); k++) {
        const t = (k - a[axis]) / (b[axis] - a[axis]);
        if (t < 0 || t >= 1) continue;
        local.push({ i, t, p: [a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])] });
      }
    }
    local.sort((u, v) => u.t - v.t);
    hits.push(...local);
  }
  return hits;
}

export function smoothCurve(rnd) {
  const n = 3 + Math.floor(rnd() * 4), control = [];
  let x = LO + 1 + rnd() * (HI - LO - 2), y = LO + 1 + rnd() * (HI - LO - 2);
  for (let i = 0; i < n; i++) {
    control.push([x, y]);
    x = Math.max(LO + 0.3, Math.min(HI + 0.7, x + jitter(rnd, 2.2)));
    y = Math.max(LO + 0.3, Math.min(HI + 0.7, y + jitter(rnd, 2.2)));
  }
  const sampled = catmullRom(control, 24);
  const hits = gridCrossings(sampled);
  if (hits.length < 2) return null;
  const a = Math.floor(rnd() * (hits.length - 1));
  const b = a + 1 + Math.floor(rnd() * Math.min(10, hits.length - 1 - a));
  return [hits[a].p, ...sampled.slice(hits[a].i + 1, hits[b].i + 1), hits[b].p];
}

/**
 * One random arc that passes validation, or null (the caller just tries again).
 * @returns {?{arc:number[][], mode:string}}
 */
export function randomArc(rnd, { mode, maxCells } = {}) {
  const chosen = mode ?? pick(rnd, ['walk', 'walk', 'revisit', 'smooth', 'smooth']);
  const raw = chosen === 'smooth'
    ? smoothCurve(rnd)
    : cellWalk(rnd, { maxCells, allowRevisit: chosen === 'revisit' });
  if (!raw || raw.length < 2) return null;
  const arc = simplify(raw, GRID.simplifyTolerance);
  if (arc.length < 2 || validateArc(arc).length) return null;
  return { arc, mode: chosen };
}
