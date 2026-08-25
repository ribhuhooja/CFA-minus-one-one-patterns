/**
 * Planar geometry primitives.  Pure, coordinate-system agnostic, no grid knowledge.
 *
 * Everything here works in mathematical coordinates (y increases upward), but nothing
 * in this module actually depends on that; it is the callers that fix the convention.
 */

export const TOL = {
  geom: 1e-9,        // "these two numbers are the same"
  onCurve: 1e-7,     // "this point lies on that segment"
  transverse: 1e-3   // minimum |sin| of a crossing angle before we call it degenerate
};

export const sub = (a, b) => [a[0] - b[0], a[1] - b[1]];
export const add = (a, b) => [a[0] + b[0], a[1] + b[1]];
export const scale = (a, k) => [a[0] * k, a[1] * k];
export const cross = (a, b) => a[0] * b[1] - a[1] * b[0];
export const dot = (a, b) => a[0] * b[0] + a[1] * b[1];
export const length = (a) => Math.hypot(a[0], a[1]);
export const distance = (a, b) => Math.hypot(a[0] - b[0], a[1] - b[1]);

/** Clockwise quarter turn.  Used to define which side of a curve the region lies on. */
export const rotateCW = (v) => [v[1], -v[0]];
/** Counter-clockwise quarter turn. */
export const rotateCCW = (v) => [-v[1], v[0]];

export const isNear = (a, b, tol = TOL.geom) => Math.abs(a - b) <= tol;
export const isNearInteger = (x, tol = TOL.geom) => isNear(x, Math.round(x), tol);

export function distancePointSegment(p, a, b) {
  const ab = sub(b, a), l2 = dot(ab, ab);
  if (l2 < TOL.geom * TOL.geom) return distance(p, a);
  const t = Math.max(0, Math.min(1, dot(sub(p, a), ab) / l2));
  return distance(p, add(a, scale(ab, t)));
}

/**
 * Segment/segment intersection, including endpoint contact and collinear overlap.
 * @returns {{type:'none'}|{type:'point',p:number[]}|{type:'overlap'}}
 */
export function intersectSegments(p1, p2, p3, p4) {
  const r = sub(p2, p1), s = sub(p4, p3), d = cross(r, s), qp = sub(p3, p1);
  if (Math.abs(d) < TOL.geom) {
    if (Math.abs(cross(qp, r)) > TOL.geom) return { type: 'none' };       // parallel, apart
    const rr = dot(r, r);
    if (rr < TOL.geom) return distance(p1, p3) < TOL.geom ? { type: 'point', p: p1 } : { type: 'none' };
    let t0 = dot(qp, r) / rr, t1 = t0 + dot(s, r) / rr;
    if (t0 > t1) [t0, t1] = [t1, t0];
    if (t1 < -TOL.geom || t0 > 1 + TOL.geom) return { type: 'none' };
    if (Math.min(t1, 1) - Math.max(t0, 0) < TOL.geom)
      return { type: 'point', p: add(p1, scale(r, Math.max(t0, 0))) };
    return { type: 'overlap' };
  }
  const t = cross(qp, s) / d, u = cross(qp, r) / d;
  if (t < -TOL.geom || t > 1 + TOL.geom || u < -TOL.geom || u > 1 + TOL.geom) return { type: 'none' };
  return { type: 'point', p: add(p1, scale(r, t)) };
}

/**
 * Is an open polyline simple?  Consecutive segments may meet only at their shared vertex.
 * @returns {{ok:true}|{ok:false, at:number[], why:string}}
 */
export function isSimplePolyline(points) {
  const n = points.length - 1;
  for (let i = 0; i < n; i++)
    if (distance(points[i], points[i + 1]) < TOL.geom)
      return { ok: false, at: points[i], why: 'zero-length segment' };
  for (let i = 0; i < n; i++) for (let j = i + 1; j < n; j++) {
    const hit = intersectSegments(points[i], points[i + 1], points[j], points[j + 1]);
    if (hit.type === 'none') continue;
    if (hit.type === 'overlap')
      return { ok: false, at: points[j], why: `segments ${i} and ${j} overlap` };
    if (j === i + 1) {
      if (distance(hit.p, points[j]) < 1e-9) continue;
      return { ok: false, at: hit.p, why: `consecutive segments ${i},${j} meet away from their vertex` };
    }
    return { ok: false, at: hit.p, why: `segments ${i} and ${j} intersect` };
  }
  return { ok: true };
}

/** Shoelace area of a closed polygon.  Positive = counter-clockwise. */
export function signedArea(polygon) {
  let s = 0;
  for (let i = 0; i < polygon.length; i++) {
    const a = polygon[i], b = polygon[(i + 1) % polygon.length];
    s += a[0] * b[1] - b[0] * a[1];
  }
  return s / 2;
}

/** Winding number of a closed polygon about a point.  Positive = counter-clockwise. */
export function windingNumber(polygon, p) {
  let wn = 0;
  for (let i = 0; i < polygon.length; i++) {
    const a = polygon[i], b = polygon[(i + 1) % polygon.length];
    if (a[1] <= p[1]) {
      if (b[1] > p[1] && cross(sub(b, a), sub(p, a)) > 0) wn++;
    } else if (b[1] <= p[1] && cross(sub(b, a), sub(p, a)) < 0) wn--;
  }
  return wn;
}

/** @returns {[number,number,number,number]} [xmin, ymin, xmax, ymax] */
export function boundingBox(points) {
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  for (const p of points) {
    if (p[0] < x0) x0 = p[0];
    if (p[1] < y0) y0 = p[1];
    if (p[0] > x1) x1 = p[0];
    if (p[1] > y1) y1 = p[1];
  }
  return [x0, y0, x1, y1];
}

/** Ramer-Douglas-Peucker simplification.  Endpoints are always preserved. */
export function simplify(points, tolerance) {
  if (points.length < 3) return points.slice();
  let index = -1, worst = 0;
  for (let i = 1; i < points.length - 1; i++) {
    const d = distancePointSegment(points[i], points[0], points[points.length - 1]);
    if (d > worst) { worst = d; index = i; }
  }
  if (worst <= tolerance) return [points[0], points[points.length - 1]];
  const head = simplify(points.slice(0, index + 1), tolerance);
  return head.slice(0, -1).concat(simplify(points.slice(index), tolerance));
}
