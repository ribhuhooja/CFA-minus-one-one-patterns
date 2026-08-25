/**
 * The grid: lattice points, edges, cells, forbidden points.
 *
 * CONVENTIONS
 *   - Mathematical coordinates, y increases upward.  Nothing here ever flips y.
 *   - Directions are absolute compass directions.  The words left/right/up/down are
 *     never used relative to a direction of travel, here or anywhere else in src/.
 *   - Cell C(i,j) = [i,i+1] x [j,j+1].
 *   - Edge keys: "H:i:j" is the segment (i,j)-(i+1,j);  "V:i:j" is (i,j)-(i,j+1).
 *   - The forbidden point of C(i,j) sits just inside its NORTH-WEST corner.
 */
import { isNearInteger } from './geometry.js';

/**
 * Defaults for a freehand curve on the unit grid.  Any solve may override them: an arc that
 * comes from somewhere other than a mouse -- a beta curve lifted from a Heegaard diagram,
 * say -- lives at a different scale and passes much closer to the lattice points, so it
 * needs a smaller `epsForbidden` and a smaller clearance.  The one invariant that must
 * hold, whatever the numbers, is
 *
 *     epsForbidden * sqrt(2)  <  minLatticeDistance
 *
 * i.e. the arc never comes closer to a lattice point than that point's own forbidden point
 * does.  `gridSettings` checks it.
 */
export const GRID = Object.freeze({
  cells: 20,                 // the window is cells 0..19
  windowMin: 2,              // the drawn arc must stay in cells 2..17, i.e. coordinates [2,18]
  windowMax: 18,
  epsForbidden: 1e-3,        // how far the forbidden point sits from its corner
  minLatticeDistance: 0.08,  // how far the arc must stay from every lattice point
  simplifyTolerance: 0.03    // RDP tolerance for a freehand stroke, in cells
});

/** Resolve a partial override against the defaults. */
export function gridSettings(overrides = {}) {
  const settings = { ...GRID, ...overrides };
  if (settings.epsForbidden * Math.SQRT2 >= settings.minLatticeDistance)
    throw new Error(
      `grid settings: epsForbidden*sqrt(2) = ${(settings.epsForbidden * Math.SQRT2).toPrecision(3)} ` +
      `must be below minLatticeDistance = ${settings.minLatticeDistance}; otherwise the arc may ` +
      'pass on the wrong side of a forbidden point');
  if (settings.windowMin >= settings.windowMax)
    throw new Error('grid settings: windowMin must be below windowMax');
  return Object.freeze(settings);
}

export const DIRECTIONS = Object.freeze({ N: [0, 1], E: [1, 0], S: [0, -1], W: [-1, 0] });
export const DIRECTION_NAMES = Object.freeze(['N', 'E', 'S', 'W']);
export const OPPOSITE = Object.freeze({ N: 'S', S: 'N', E: 'W', W: 'E' });

export const stepFrom = (v, d) => [v[0] + DIRECTIONS[d][0], v[1] + DIRECTIONS[d][1]];
export const latticeKey = (v) => `${v[0]},${v[1]}`;
export const cellKey = (i, j) => `${i},${j}`;

/** The edge leaving lattice point `v` in direction `d`. */
export function edgeKey(v, d) {
  const [x, y] = v;
  switch (d) {
    case 'E': return `H:${x}:${y}`;
    case 'W': return `H:${x - 1}:${y}`;
    case 'N': return `V:${x}:${y}`;
    default:  return `V:${x}:${y - 1}`;   // S
  }
}

export function parseEdgeKey(key) {
  const [axis, i, j] = key.split(':');
  return { axis, i: +i, j: +j };
}

export function edgeEndpoints(key) {
  const { axis, i, j } = parseEdgeKey(key);
  return axis === 'H' ? [[i, j], [i + 1, j]] : [[i, j], [i, j + 1]];
}

export function cellEdgeKeys(i, j) {
  return [`H:${i}:${j}`, `H:${i}:${j + 1}`, `V:${i}:${j}`, `V:${i + 1}:${j}`];
}

/** Which side of cell C(i,j) is this edge?  'S'|'N'|'W'|'E', or null if it is not a side. */
export function cellSideOfEdge(key, i, j) {
  const { axis, i: a, j: b } = parseEdgeKey(key);
  if (axis === 'H' && a === i && b === j) return 'S';
  if (axis === 'H' && a === i && b === j + 1) return 'N';
  if (axis === 'V' && a === i && b === j) return 'W';
  if (axis === 'V' && a === i + 1 && b === j) return 'E';
  return null;
}

/** Parameter in [0,1] of a point known to lie on `key`. */
export function edgeParameter(key, p) {
  const { axis, i, j } = parseEdgeKey(key);
  return axis === 'H' ? p[0] - i : p[1] - j;
}

/** The edge a point on a grid line belongs to; null at a lattice point or off the grid. */
export function edgeContaining(p, tol = 1e-9) {
  const onVertical = isNearInteger(p[0], tol), onHorizontal = isNearInteger(p[1], tol);
  if (onVertical && onHorizontal) return null;
  if (onVertical) return `V:${Math.round(p[0])}:${Math.floor(p[1])}`;
  if (onHorizontal) return `H:${Math.floor(p[0])}:${Math.round(p[1])}`;
  return null;
}

/** The forbidden point of C(i,j): just inside the NW corner (i, j+1). */
export const forbiddenPoint = (i, j, settings = GRID) =>
  [i + settings.epsForbidden, j + 1 - settings.epsForbidden];

/** The cell whose forbidden point sits at the given lattice corner, i.e. C(x, y-1). */
export const cellOwningCorner = (v) => [v[0], v[1] - 1];

/** Compass directions of the successive segments of an axis-aligned path. */
export function directionsAlong(points) {
  const out = [];
  for (let i = 0; i + 1 < points.length; i++) {
    const dx = points[i + 1][0] - points[i][0], dy = points[i + 1][1] - points[i][1];
    out.push(Math.abs(dx) > Math.abs(dy) ? (dx > 0 ? 'E' : 'W') : (dy > 0 ? 'N' : 'S'));
  }
  return out;
}
