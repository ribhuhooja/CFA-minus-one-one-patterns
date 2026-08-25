/**
 * §3 and §5: what the arc's orientation forces at the two endpoints.
 *
 * Traversing the arc from x_s to x_e, the enclosed region D lies on the side that
 * rotateCW(velocity) points to.  Consequently the closed curve (arc forward, path
 * backward) runs clockwise, and the first and last steps of the path are determined by
 * which side of its edge the arc departs into / arrives from.
 */
import { sub } from './geometry.js';
import { edgeContaining, edgeParameter, parseEdgeKey } from './grid.js';

/**
 * @typedef {Object} Endpoints
 * @property {number[]} xs, xe
 * @property {string} edgeS, edgeE       edge keys carrying x_s and x_e
 * @property {'N'|'E'|'S'|'W'} first     forced first step of the path, out of x_s
 * @property {'N'|'E'|'S'|'W'} last      forced final step of the path, into x_e
 * @property {number[]} vs               far end of the first partial edge
 * @property {number[]} ve               lattice point the final partial edge leaves from
 * @property {string} departsInto        'above'|'below'|'east'|'west'
 * @property {string} arrivesFrom
 */

/**
 * The §5 tables, as data.  A horizontal edge is the S side of one cell and the N side of
 * another, so the only meaningful datum is edge orientation plus which side the arc occupies.
 */
export const FIRST_STEP = Object.freeze({
  'H/above': 'E', 'H/below': 'W', 'V/east': 'S', 'V/west': 'N'
});
export const LAST_STEP = Object.freeze({
  'H/above': 'E', 'H/below': 'W', 'V/east': 'S', 'V/west': 'N'
});

/** @param {number[][]} arc @returns {Endpoints} */
export function endpointConditions(arc) {
  const xs = arc[0], xe = arc.at(-1);
  const edgeS = edgeContaining(xs, 1e-9), edgeE = edgeContaining(xe, 1e-9);
  const horizontalS = parseEdgeKey(edgeS).axis === 'H';
  const horizontalE = parseEdgeKey(edgeE).axis === 'H';

  const outward = sub(arc[1], xs);                 // leaves x_s along this
  const departsInto = horizontalS ? (outward[1] > 0 ? 'above' : 'below')
                                  : (outward[0] > 0 ? 'east' : 'west');
  const first = FIRST_STEP[`${horizontalS ? 'H' : 'V'}/${departsInto}`];

  const inward = sub(arc.at(-2), xe);              // points back up the last segment
  const arrivesFrom = horizontalE ? (inward[1] > 0 ? 'above' : 'below')
                                  : (inward[0] > 0 ? 'east' : 'west');
  const last = LAST_STEP[`${horizontalE ? 'H' : 'V'}/${arrivesFrom}`];

  const vs = first === 'E' ? [Math.ceil(xs[0]), xs[1]]
           : first === 'W' ? [Math.floor(xs[0]), xs[1]]
           : first === 'N' ? [xs[0], Math.ceil(xs[1])]
           :                 [xs[0], Math.floor(xs[1])];
  const ve = last === 'E' ? [Math.floor(xe[0]), xe[1]]
           : last === 'W' ? [Math.ceil(xe[0]), xe[1]]
           : last === 'N' ? [xe[0], Math.floor(xe[1])]
           :                [xe[0], Math.ceil(xe[1])];

  return { xs, xe, edgeS, edgeE, first, last, vs, ve, departsInto, arrivesFrom };
}

/**
 * The first crossing strictly between two parameters on one edge, or null.
 * Used for the two partial end edges: the crossing sitting *at* x_s or x_e is at the
 * boundary of the interval and does not block it.
 */
export function crossingStrictlyBetween(edge, t0, t1, crossings) {
  const lo = Math.min(t0, t1) + 1e-9, hi = Math.max(t0, t1) - 1e-9;
  return crossings.find((c) => c.edge === edge && c.t > lo && c.t < hi) ?? null;
}

/** Parameters of x_s -> v_s and v_e -> x_e along their edges. */
export function partialEdgeSpans(endpoints) {
  return {
    start: [edgeParameter(endpoints.edgeS, endpoints.xs), edgeParameter(endpoints.edgeS, endpoints.vs)],
    end:   [edgeParameter(endpoints.edgeE, endpoints.ve), edgeParameter(endpoints.edgeE, endpoints.xe)]
  };
}
