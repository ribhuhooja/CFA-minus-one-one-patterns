/**
 * The Q(i, m, n) family, as bordered Heegaard diagrams H(r, s).
 *
 *   r = 1 + 2im - m
 *   s = n + 3m - 2mn + 4imn - 4im - 2
 *   maxx = 2r + s + m + n - 3        x generators, indexed 0..maxx
 *   maxy = 4im - 2m = 2r - 2         y generators, indexed 0..maxy
 *
 * Six families of arcs.  Directionality is not meaningful: an arc just joins its two
 * endpoints.  The arrows below are only there to match how the families were dictated.
 *
 *   F1  left -> top      y_j -- x_j                      j = 0 .. maxy
 *   F2  bottom -> top    x_j -- x_{2r-1+j}               j = 0 .. s-r
 *   F3  bottom rainbow   x_{s-r+1+j} -- x_{s+r-j}        j = 0 .. r-1
 *   F4  dependent        x_{s+r+j} -- x_{s+r+1+j}        j = 0 .. m+n-3
 *   F5  right -> top     y_j -- x_{maxx-j}               j = 0 .. r-1
 *   F6  right -> bottom  y_{maxy-j} -- x_{maxx-j}        j = 0 .. r-2
 *
 * The basepoint w is shut inside the innermost rainbow, the arc x_s -- x_{s+1}: that lens is
 * a region of the diagram all on its own, and the multiplicity of a domain there is the power
 * of U it carries.  The other basepoint, z, sits in the top-left corner and is what the grid
 * solver calls the forbidden point; a domain may cover w freely but never z.
 *
 * F4's two ends were given only by index; which edge each sits on is forced, not chosen.
 * After F1, F2 and F5 the top edge is short of exactly the indices s+r .. s+r+m+n-3, and
 * after F2, F3 and F6 the bottom edge is short of exactly s+r+1 .. s+r+m+n-2.  So the
 * dependent arcs run from x_{s+r+j} on the TOP to x_{s+r+1+j} on the BOTTOM: m+n-2 strands
 * crossing the domain, each landing one index to the right of where it left.
 */
import { HeegaardDiagram } from './diagram.js';

/** H(r,s) and the two counts, from Q(i,m,n). */
export function parameters(i, m, n) {
  const r = 1 + 2 * i * m - m;
  const s = n + 3 * m - 2 * m * n + 4 * i * m * n - 4 * i * m - 2;
  return {
    i, m, n, r, s,
    maxx: 2 * r + s + m + n - 3,
    maxy: 2 * r - 2,
    dependentStrands: m + n - 2
  };
}

/**
 * @param {number} i @param {number} m @param {number} n
 * @returns {HeegaardDiagram}
 */
export function Q(i, m, n) {
  for (const [name, v] of [['i', i], ['m', m], ['n', n]])
    if (!Number.isInteger(v) || v < 0) throw new Error(`Q: ${name} must be a non-negative integer, got ${v}`);
  if (n < 2) throw new Error(`Q(${i},${m},${n}): this family of diagrams is only valid for n >= 2`);

  const p = parameters(i, m, n);
  const { r, s, maxx, maxy } = p;
  if (r < 1) throw new Error(`Q(${i},${m},${n}): r = ${r} must be positive`);
  if (s < r) throw new Error(`Q(${i},${m},${n}): s = ${s} must be at least r = ${r}`);
  if (maxy !== 4 * i * m - 2 * m) throw new Error(`Q(${i},${m},${n}): maxy disagrees with 4im-2m`);

  const arcs = [];
  const join = (sideA, indexA, sideB, indexB, family) =>
    arcs.push({ a: { side: sideA, index: indexA }, b: { side: sideB, index: indexB }, family });

  for (let j = 0; j <= maxy;    j++) join('left',   j,         'top',    j,           'left-top');
  for (let j = 0; j <= s - r;   j++) join('bottom', j,         'top',    2 * r - 1 + j, 'bottom-top');
  for (let j = 0; j <= r - 1;   j++) join('bottom', s - r + 1 + j, 'bottom', s + r - j, 'rainbow');
  for (let j = 0; j <= m + n - 3; j++) join('top',  s + r + j, 'bottom', s + r + 1 + j, 'dependent');
  for (let j = 0; j <= r - 1;   j++) join('right',  j,         'top',    maxx - j,    'right-top');
  for (let j = 0; j <= r - 2;   j++) join('right',  maxy - j,  'bottom', maxx - j,    'right-bottom');

  const dependent = arcs.filter((a) => a.family === 'dependent').length;
  if (dependent !== p.dependentStrands)
    throw new Error(`Q(${i},${m},${n}): built ${dependent} dependent strands, expected m+n-2 = ${p.dependentStrands}`);

  // the innermost rainbow is j = r-1, i.e. x_s -- x_{s+1}; w lives in the lens under it
  const innermost = arcs.findIndex((a) =>
    a.family === 'rainbow' && Math.abs(a.a.index - a.b.index) === 1);
  if (innermost < 0) throw new Error(`Q(${i},${m},${n}): no innermost rainbow to hold w`);

  const diagram = new HeegaardDiagram({
    name: `Q(${i},${m},${n})`,
    xCount: maxx + 1,
    yCount: maxy + 1,
    arcs,
    basepoints: [{ name: 'w', insideArc: innermost }],
    notes: p
  });

  const problems = diagram.validate();
  if (problems.length)
    throw new Error(`Q(${i},${m},${n}) is not a legal diagram:\n  ` +
      problems.map((x) => x.message).join('\n  '));
  return diagram;
}

/** Families in the order they are built, for legends. */
export const FAMILIES = Object.freeze([
  'left-top', 'bottom-top', 'rainbow', 'dependent', 'right-top', 'right-bottom'
]);
