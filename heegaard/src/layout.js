/**
 * Geometry for a HeegaardDiagram: where the generators sit, and what shape each arc is.
 *
 * Mathematical coordinates, y increases upward, origin at the bottom-left corner of the
 * fundamental domain.  render.js is the only place that flips y for SVG.
 *
 * SPACING.  The domain is xCount by yCount cells of side `cell`, so the aspect ratio
 * reflects how many generators sit on each alpha curve.  Point k sits at (k + 1/2) cells
 * along its edge, which puts the same half-cell gap at both ends; across the gluing seam
 * the spacing is then uniform, so a universal cover looks like an even grid.
 *
 *   x_j on the bottom at ((j+1/2)c, 0)   and on the top at ((j+1/2)c, H)
 *   y_j on the left   at (0, H-(j+1/2)c) and on the right at (W, H-(j+1/2)c)
 *
 * y_0 sits next to the TOP-left corner, not the bottom.  That is forced, not chosen: in
 * the Q family the arc y_0 -- x_0 joins two slots that are adjacent on the boundary, so it
 * must hug a corner, and the corner it hugs is the top-left one.
 *
 * SHAPES.  In any one copy of the domain an arc is a single primitive: a straight segment if
 * its ends are on different edges, or a parabola bulging away from the edge if they are on
 * the same one, of height `bulge` x half-span.  That primitive -- `ends` and, for a bulge,
 * `control` -- is what the arc IS.  `path` is only a sampling of it, kept for the checks that
 * need points, and `samples` says how fine.  Drawing uses the primitive directly.
 *
 * The apex is always among the samples (it is t = 1/2, and the count is even), which is what
 * keeps a basepoint sitting under a bulge on the inside of the sampled polyline too.  Keeping bulge
 * below 1/2 keeps the slope at the foot of the bulge below one cell per cell, which is what
 * lets a nest of them sit underneath the diagonal strands that pass over it.
 *
 * THE BASEPOINT sits in the TOP-LEFT corner, which is exactly where the grid solver puts the
 * forbidden point of a cell.  It has to lie beyond the last beta arc that reaches into that
 * corner -- that is what "for small enough epsilon" means here -- so its offset is measured
 * from the picture rather than fixed: `cornerClearance` is how close any arc gets to the
 * corner along the diagonal, and the basepoint is placed at a fraction of that.  It is
 * reported as `epsilon` in units of the domain, so a cover of these domains is a unit grid
 * with a forbidden point at (k + epsilon, l + 1 - epsilon), which is the solver's convention.
 */
import { intersectSegments } from '../../grid-arc/src/geometry.js';
import { GENERATOR_OF_SIDE, generatorName } from './diagram.js';

export const DEFAULTS = { cell: 26, bulge: 0.45, samples: 16 };

/** Inward unit normal of each edge, in math coordinates. */
const INWARD = { bottom: [0, 1], top: [0, -1], left: [1, 0], right: [-1, 0] };

/**
 * @typedef {Object} Layout
 * @property {number} width, height, cell
 * @property {(e:Object)=>number[]} point         position of a boundary slot
 * @property {{arc:Object, index:number, family:string, shape:string, path:number[][], control:?number[]}[]} arcs
 * @property {{name:string, side:string, index:number, at:number[]}[]} generators
 */

/** @param {import('./diagram.js').HeegaardDiagram} diagram */
export function layout(diagram, options = {}) {
  const { cell, bulge, samples } = { ...DEFAULTS, ...options };
  const width = diagram.xCount * cell;
  const height = diagram.yCount * cell;

  const point = ({ side, index }) => {
    const along = (index + 0.5) * cell;
    switch (side) {
      case 'bottom': return [along, 0];
      case 'top':    return [along, height];
      case 'left':   return [0, height - along];
      default:       return [width, height - along];      // right
    }
  };

  const arcs = diagram.arcs.map((arc, index) => {
    const a = point(arc.a), b = point(arc.b);
    if (arc.a.side !== arc.b.side)
      return { arc, index, family: arc.family ?? '', shape: 'segment',
               ends: [a, b], control: null, path: [a, b] };

    // both ends on one edge: a parabola bulging inward
    const [nx, ny] = INWARD[arc.a.side];
    const half = Math.hypot(b[0] - a[0], b[1] - a[1]) / 2;
    const rise = 2 * bulge * half;                        // control height; apex is half of it
    const control = [(a[0] + b[0]) / 2 + nx * rise, (a[1] + b[1]) / 2 + ny * rise];
    return {
      arc, index, family: arc.family ?? '', shape: 'parabola',
      ends: [a, b], control, path: sampleQuadratic(a, control, b, Math.max(2, 2 * Math.ceil(samples / 2)))
    };
  });

  // How close does beta get to the top-left corner, measured along the diagonal?  For a
  // straight arc the minimum of u + (H - v) is at an endpoint; parabolas are sampled.
  let cornerClearance = Infinity;
  for (const a of arcs)
    for (const [x, y] of a.path) cornerClearance = Math.min(cornerClearance, x + (height - y));
  const epsilon = (options.basepointFraction ?? 0.35) * cornerClearance / (width + height);
  const basepoint = { name: 'z', epsilon, at: [epsilon * width, height - epsilon * height], cornerClearance };

  // Basepoints shut inside a bulging arc: put them between the chord and the apex, which is
  // well inside the lens whatever the bulge.
  const named = new Map();
  for (const spec of diagram.basepoints ?? []) {
    const host = arcs[spec.insideArc];
    if (!host || host.shape !== 'parabola')
      throw new Error(`basepoint ${spec.name} needs an arc with both ends on one edge`);
    const [a, b] = host.ends, c = host.control;
    const apex = [(a[0] + 2 * c[0] + b[0]) / 4, (a[1] + 2 * c[1] + b[1]) / 4];
    const mid = [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2];
    const depth = options.basepointDepth ?? 0.45;
    named.set(spec.name, {
      name: spec.name, insideArc: spec.insideArc,
      at: [mid[0] + depth * (apex[0] - mid[0]), mid[1] + depth * (apex[1] - mid[1])]
    });
  }

  const generators = [];
  for (const arc of diagram.arcs)
    for (const end of [arc.a, arc.b])
      generators.push({ name: generatorName(end), kind: GENERATOR_OF_SIDE[end.side],
                        side: end.side, index: end.index, at: point(end) });

  named.set('z', basepoint);
  return { width, height, cell, point, arcs, generators, basepoint, basepoints: named, diagram };
}

function sampleQuadratic(a, c, b, samples) {
  const out = [];
  for (let k = 0; k <= samples; k++) {
    const t = k / samples, u = 1 - t;
    out.push([u * u * a[0] + 2 * u * t * c[0] + t * t * b[0],
              u * u * a[1] + 2 * u * t * c[1] + t * t * b[1]]);
  }
  return out;
}

/**
 * Do any two drawn arcs meet?  The combinatorial check in `validate` says beta is embedded;
 * this says the picture of it is too.  Every boundary slot belongs to one arc end, so any
 * intersection at all is a genuine one.
 * @returns {{a:number, b:number, at:number[]}[]}
 */
export function findArcCrossings(laidOut) {
  const hits = [];
  const { arcs } = laidOut;
  for (let u = 0; u < arcs.length; u++)
    for (let v = u + 1; v < arcs.length; v++) {
      const P = arcs[u].path, Q = arcs[v].path;
      outer:
      for (let p = 0; p + 1 < P.length; p++)
        for (let q = 0; q + 1 < Q.length; q++) {
          const hit = intersectSegments(P[p], P[p + 1], Q[q], Q[q + 1]);
          if (hit.type !== 'none') {
            hits.push({ a: u, b: v, at: hit.p ?? P[p] });
            break outer;
          }
        }
    }
  return hits;
}

/** Translate a laid-out arc into the copy of the domain at (dx, dy) tiles. */
export const translatePath = (path, dx, dy) => path.map(([x, y]) => [x + dx, y + dy]);
