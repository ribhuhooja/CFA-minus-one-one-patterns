/**
 * A bordered Heegaard diagram on the torus, as combinatorics only.
 *
 * THE PICTURE
 * -----------
 * The fundamental domain is a rectangle.  Its horizontal edges are glued to each other
 * and its vertical edges to each other, so the boundary carries two alpha curves:
 *
 *   alpha_x   the horizontal one   (bottom edge == top edge)
 *   alpha_y   the vertical one     (left edge == right edge)
 *
 * The beta curve is drawn inside the rectangle as a family of arcs.  Each arc ends on the
 * boundary, and every endpoint is an intersection of beta with an alpha curve, i.e. a
 * generator: `x_j` on the horizontal alpha, `y_j` on the vertical one.
 *
 * Because bottom == top, an index `j` names one point of alpha_x but TWO slots on the
 * boundary of the rectangle: `x_j` on the bottom and `x_j` on the top.  Beta passes
 * through the point once, so it occupies each slot exactly once; the two slots are the
 * two germs of beta at that intersection.  Same for `y_j` on left and right.  That is the
 * whole bookkeeping rule, and `validate` checks it.
 *
 * Nothing here is drawn or measured; see layout.js for geometry and render.js for SVG.
 */

/** @typedef {{side:'bottom'|'top'|'left'|'right', index:number}} Endpoint */
/** @typedef {{a:Endpoint, b:Endpoint, family?:string}} Arc */

export const SIDES = Object.freeze(['bottom', 'right', 'top', 'left']);
/** Which alpha curve a side's points live on. */
export const GENERATOR_OF_SIDE = Object.freeze({ bottom: 'x', top: 'x', left: 'y', right: 'y' });
/** The side a point is glued to under the torus identification. */
export const GLUED_SIDE = Object.freeze({ bottom: 'top', top: 'bottom', left: 'right', right: 'left' });

export const endpointKey = (e) => `${e.side}:${e.index}`;
export const generatorName = (e) => `${GENERATOR_OF_SIDE[e.side]}_${e.index}`;

export class HeegaardDiagram {
  /**
   * @param {Object} spec
   * @param {string} spec.name
   * @param {number} spec.xCount   number of x generators (indices 0..xCount-1)
   * @param {number} spec.yCount   number of y generators
   * @param {Arc[]} spec.arcs
   * @param {{name:string, insideArc:number}[]} [spec.basepoints]
   *        Basepoints other than the corner one, given by the arc they are shut inside.
   *        `layout` turns each into a position; `z` in the top-left corner is always there
   *        and is not listed here.
   * @param {Object} [spec.notes]  free-form provenance (e.g. the i,m,n it came from)
   */
  constructor({ name = 'diagram', xCount, yCount, arcs, basepoints = [], notes = {} }) {
    this.name = name;
    this.xCount = xCount;
    this.yCount = yCount;
    this.arcs = arcs.map((arc) => ({ ...arc, a: { ...arc.a }, b: { ...arc.b } }));
    this.basepoints = basepoints.map((b) => ({ ...b }));
    this.notes = notes;
  }

  get maxx() { return this.xCount - 1; }
  get maxy() { return this.yCount - 1; }
  /** Number of boundary slots: each x index twice, each y index twice. */
  get slotCount() { return 2 * this.xCount + 2 * this.yCount; }

  /**
   * Position of a boundary slot going counter-clockwise from the bottom-left corner:
   * bottom left-to-right, right bottom-to-top, top right-to-left, left top-to-bottom.
   */
  slot({ side, index }) {
    const N = this.xCount, M = this.yCount;
    switch (side) {
      case 'bottom': return index;
      case 'right':  return N + (this.maxy - index);
      case 'top':    return N + M + (this.maxx - index);
      case 'left':   return 2 * N + M + index;
      default: throw new Error(`unknown side ${side}`);
    }
  }

  /** Every arc as an ordered pair of boundary slots. */
  chords() {
    return this.arcs.map((arc) => {
      const p = this.slot(arc.a), q = this.slot(arc.b);
      return p < q ? [p, q] : [q, p];
    });
  }

  /**
   * Check the diagram is a legal one.
   * @returns {{message:string, at?:string}[]} empty if it is
   */
  validate() {
    const problems = [];
    const report = (message, at) => problems.push(at ? { message, at } : { message });

    for (const arc of this.arcs)
      for (const end of [arc.a, arc.b]) {
        if (!SIDES.includes(end.side)) report(`unknown side "${end.side}"`);
        const limit = GENERATOR_OF_SIDE[end.side] === 'x' ? this.xCount : this.yCount;
        if (!Number.isInteger(end.index) || end.index < 0 || end.index >= limit)
          report(`index ${end.index} out of range on the ${end.side} edge`, generatorName(end));
      }
    if (problems.length) return problems;

    // every boundary slot used exactly once
    const used = new Map();
    for (const arc of this.arcs)
      for (const end of [arc.a, arc.b]) {
        const key = endpointKey(end);
        if (used.has(key)) report(`slot ${key} is used by more than one arc end`, key);
        used.set(key, (used.get(key) ?? 0) + 1);
      }
    for (const side of SIDES) {
      const limit = GENERATOR_OF_SIDE[side] === 'x' ? this.xCount : this.yCount;
      for (let k = 0; k < limit; k++)
        if (!used.has(`${side}:${k}`)) report(`nothing meets the ${side} edge at ${side}:${k}`, `${side}:${k}`);
    }
    if (this.arcs.length !== this.xCount + this.yCount)
      report(`expected ${this.xCount + this.yCount} arcs, got ${this.arcs.length}`);
    if (problems.length) return problems;

    // beta is embedded: the chord diagram must be non-crossing
    const chords = this.chords();
    for (let u = 0; u < chords.length; u++)
      for (let v = u + 1; v < chords.length; v++) {
        const [a, b] = chords[u], [c, d] = chords[v];
        const inside = (t) => t > a && t < b;
        if (inside(c) !== inside(d))
          report(`arcs ${u} and ${v} must cross: chords (${a},${b}) and (${c},${d}) interleave`);
      }
    return problems;
  }

  /**
   * Trace beta through the torus identifications.
   * @returns {{arcs:number[], generators:string[], length:number}[]} one entry per component
   */
  components() {
    const byEndpoint = new Map();
    this.arcs.forEach((arc, index) => {
      byEndpoint.set(endpointKey(arc.a), { index, other: arc.b });
      byEndpoint.set(endpointKey(arc.b), { index, other: arc.a });
    });
    const glue = (e) => ({ side: GLUED_SIDE[e.side], index: e.index });

    const seen = new Set(), out = [];
    for (let start = 0; start < this.arcs.length; start++) {
      if (seen.has(start)) continue;
      const arcs = [], generators = [];
      let end = this.arcs[start].a;
      do {
        const step = byEndpoint.get(endpointKey(end));
        seen.add(step.index);
        arcs.push(step.index);
        generators.push(generatorName(step.other));
        end = glue(step.other);                       // cross the alpha curve, continue
      } while (!seen.has(byEndpoint.get(endpointKey(end)).index));
      out.push({ arcs, generators, length: arcs.length });
    }
    return out;
  }

  /** Arcs grouped by the pair of sides they join — useful for choosing how to draw them. */
  byShape() {
    const shape = (arc) => (arc.a.side === arc.b.side ? 'same'
      : GLUED_SIDE[arc.a.side] === arc.b.side ? 'through' : 'corner');
    const out = { same: [], through: [], corner: [] };
    this.arcs.forEach((arc, index) => out[shape(arc)].push(index));
    return out;
  }
}
