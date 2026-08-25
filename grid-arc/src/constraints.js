/**
 * §4: the global conditions (P1)-(P4) that decide whether a candidate path is a solution.
 *
 * Each check is exported on its own so other projects can reuse them piecemeal.  The one
 * that does real work is (P3): it is the only part of the algorithm that can answer
 * "no solution", because the local rules of Appendix A cannot see a forbidden point that
 * the path never passes near.
 */
import {
  signedArea, windingNumber, boundingBox, isSimplePolyline, distancePointSegment, TOL
} from './geometry.js';
import { GRID, forbiddenPoint, latticeKey } from './grid.js';

/** The Jordan curve bounding D: the arc forward, then the path backward. */
export function closedCurve(arc, path) {
  const polygon = arc.slice();
  for (let i = path.length - 2; i >= 1; i--) polygon.push(path[i]);
  return polygon;
}

/** (P1) the path is simple and visits no lattice point twice. */
export function checkSimple(path) {
  const simple = isSimplePolyline(path);
  if (!simple.ok) return [{ code: 'P1', detail: simple.why, at: simple.at }];
  const seen = new Set();
  for (let i = 1; i < path.length - 1; i++) {
    const key = latticeKey(path[i]);
    if (seen.has(key)) return [{ code: 'P1', detail: `lattice point ${key} visited twice`, at: path[i] }];
    seen.add(key);
  }
  return [];
}

/** (P2) path ∩ arc = {x_s, x_e}: the path may not touch any other crossing. */
export function checkDisjointFromArc(path, crossings) {
  for (const c of crossings) {
    if (c.kind !== 'interior') continue;
    for (let i = 0; i + 1 < path.length; i++)
      if (distancePointSegment(c.p, path[i], path[i + 1]) < TOL.onCurve)
        return [{ code: 'P2', detail: `the path uses a point of arc ∩ grid on edge ${c.edge}`, at: c.p }];
  }
  return [];
}

/** (P3) D contains no forbidden point.  Returns the offenders as well as the failure. */
export function checkForbiddenPoints(polygon, settings = GRID) {
  const [x0, y0, x1, y1] = boundingBox(polygon);
  const inside = [];
  for (let i = Math.floor(x0) - 1; i <= Math.ceil(x1) + 1; i++)
    for (let j = Math.floor(y0) - 1; j <= Math.ceil(y1) + 1; j++) {
      const f = forbiddenPoint(i, j, settings);
      if (windingNumber(polygon, f) !== 0) inside.push({ cell: [i, j], p: f });
    }
  return inside;
}

/**
 * (P4) every interior point of D has winding number -1.
 * The closed curve is simple whenever (P1) and (P2) hold, so its orientation is decided
 * exactly by the sign of its signed area — no sampling needed.
 */
export function checkOrientation(polygon) {
  const area = signedArea(polygon);
  return area < 0
    ? { failures: [], area }
    : { failures: [{ code: 'P4', detail: `the closed curve runs counter-clockwise (signed area ${area.toFixed(5)})`, at: null }], area };
}

/**
 * @typedef {Object} PathCheck
 * @property {boolean} ok
 * @property {{code:string, detail:string, at:?number[]}[]} failures
 * @property {number[][]} polygon    the Jordan curve bounding D
 * @property {number} area           signed; negative means correctly oriented
 * @property {{cell:number[], p:number[]}[]} forbiddenInside
 */

/**
 * Run (P1)-(P4) on a candidate path.
 * @param {number[][]} path              x_s, lattice points..., x_e
 * @param {import('./arc.js').ArcDescription} description
 * @returns {PathCheck}
 */
export function checkPath(path, description) {
  const failures = [
    ...checkSimple(path),
    ...checkDisjointFromArc(path, description.crossings)
  ];
  const polygon = closedCurve(description.arc, path);
  const { failures: orientationFailures, area } = checkOrientation(polygon);
  failures.push(...orientationFailures);

  const forbiddenInside = checkForbiddenPoints(polygon, description.settings ?? GRID);
  if (forbiddenInside.length)
    failures.push({
      code: 'P3',
      detail: `D contains ${forbiddenInside.length} forbidden point(s)`,
      at: forbiddenInside[0].p,
      forbidden: forbiddenInside
    });

  return { ok: failures.length === 0, failures, polygon, area, forbiddenInside };
}
