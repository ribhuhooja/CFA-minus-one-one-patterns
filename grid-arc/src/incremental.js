/**
 * Building an ArcDescription by extending it, instead of from scratch each time.
 *
 * Solving every sub-arc of one curve -- which is what disc counting does -- asks for the
 * description of prefix after prefix of the same polyline.  Each one costs O(length) to
 * derive, so a curve of C arcs costs O(C^2) for its C prefixes, and the answer is the same
 * as the previous one plus a little.  Everything `describeArc` computes is monotone under
 * appending points:
 *
 *   - a crossing keeps its `segment` and `at`, because new points go on the END and leave
 *     earlier indices alone;
 *   - the cell set, the blocked edges and the candidate edges only ever grow;
 *   - the sub-arc list only ever grows.
 *
 * The one thing that is not simply appended is the final crossing.  `findCrossings` records
 * the last point of the arc explicitly, as `kind: 'end'`; extend the arc and that point stops
 * being the end and becomes an ordinary crossing, which the half-open [0,1) rule then picks
 * up again as t = 0 of the first new segment.  So the builder keeps the interior crossings
 * and re-derives the end marker on demand.
 *
 * The builder is not cleverer than `describeArc`, just lazier; `incrementalMatchesScratch`
 * in the test suite is what says they agree.
 */
import { GRID, cellKey, cellSideOfEdge, edgeContaining, edgeParameter } from './grid.js';
import { TOL, sub, length } from './geometry.js';

/** Crossings strictly inside the polyline, for segments [from, to). */
function crossingsOfSegments(arc, from, to) {
  const found = [], problems = [];
  for (let i = from; i < to; i++) {
    const a = arc[i], d = sub(arc[i + 1], a), l = length(d), hits = [];
    for (const axis of [0, 1]) {
      if (Math.abs(d[axis]) <= TOL.geom) continue;
      const lo = Math.min(a[axis], a[axis] + d[axis]), hi = Math.max(a[axis], a[axis] + d[axis]);
      for (let k = Math.ceil(lo - 1e-12); k <= Math.floor(hi + 1e-12); k++) {
        const t = (k - a[axis]) / d[axis];
        if (t < -1e-12 || t >= 1 - 1e-12) continue;
        if (Math.abs(d[axis]) / l < TOL.transverse)
          problems.push({ message: `near-tangential crossing of ${axis ? 'y' : 'x'}=${k}`, at: a });
        const tt = Math.max(t, 0);
        hits.push({ t: tt, p: [a[0] + tt * d[0], a[1] + tt * d[1]] });
      }
    }
    hits.sort((u, v) => u.t - v.t);
    for (const h of hits) {
      const edge = edgeContaining(h.p, 1e-7);
      if (!edge) { problems.push({ message: 'the arc meets a lattice point', at: h.p }); continue; }
      found.push({ p: h.p, edge, t: edgeParameter(edge, h.p), segment: i, at: i + h.t, kind: 'interior' });
    }
  }
  return { found, problems };
}

export class ArcDescriptionBuilder {
  /**
   * @param {Object} [settings] resolved grid settings; §2 is never re-run, so the caller must
   *        have validated the whole curve already (see `assumeValid` on describeArc).
   */
  constructor(settings = GRID) {
    this.settings = settings;
    this.arc = [];
    this.interior = [];          // crossings with t in [0,1); the end marker is added on demand
    this.problems = [];
    this.cells = new Map();
    this.subArcs = [];
    this.blockedEdges = new Set();
    this.byEdge = new Map();     // interior crossings only; the end marker is added on lookup
    this.candidateEdges = new Set();
    this.builtTo = 0;            // how many crossings the cells and sub-arcs account for
  }

  /**
   * Extend the arc.  The first point given must be the current last point (they are the same
   * point of the curve), except on the first call.
   */
  append(points) {
    if (!points.length) return this;
    const startSegment = Math.max(0, this.arc.length - 1);
    if (this.arc.length) {
      const last = this.arc.at(-1), first = points[0];
      if (Math.abs(last[0] - first[0]) > 1e-12 || Math.abs(last[1] - first[1]) > 1e-12)
        throw new Error('append: the new points must start where the arc currently ends');
      this.arc.push(...points.slice(1));
    } else {
      this.arc.push(...points);
    }

    const { found, problems } = crossingsOfSegments(this.arc, startSegment, this.arc.length - 1);
    this.interior.push(...found);
    for (const c of found) {
      const on = this.byEdge.get(c.edge);
      if (on) on.push(c); else this.byEdge.set(c.edge, [c]);
    }
    this.problems.push(...problems);
    this.#extendCells();
    return this;
  }

  /** The end marker: the last point of the arc, as `findCrossings` would record it. */
  #endCrossing() {
    const last = this.arc.at(-1), edge = edgeContaining(last, 1e-7);
    if (!edge) return null;
    return { p: last, edge, t: edgeParameter(edge, last),
             segment: this.arc.length - 2, at: this.arc.length - 1, kind: 'end' };
  }

  /** Cells and sub-arcs for whatever crossings are not yet accounted for. */
  #extendCells() {
    const all = this.#crossings();
    const pointAt = (u) => {
      const i = Math.min(Math.floor(u), this.arc.length - 2), t = u - i;
      return [this.arc[i][0] + t * (this.arc[i + 1][0] - this.arc[i][0]),
              this.arc[i][1] + t * (this.arc[i + 1][1] - this.arc[i][1])];
    };
    // the sub-arc ending at the old end marker is unchanged, so restart one crossing back
    for (let k = Math.max(0, this.builtTo - 1); k + 1 < all.length; k++) {
      const a = all[k], b = all[k + 1];
      const mid = pointAt((a.at + b.at) / 2);
      const i = Math.floor(mid[0]), j = Math.floor(mid[1]);
      this.cells.set(cellKey(i, j), { i, j });
      this.candidateEdges.add(`H:${i}:${j}`).add(`H:${i}:${j + 1}`)
                        .add(`V:${i}:${j}`).add(`V:${i + 1}:${j}`);
      this.subArcs[k] = { cell: [i, j], entry: cellSideOfEdge(a.edge, i, j),
                          exit: cellSideOfEdge(b.edge, i, j), from: a.at, to: b.at };
    }
    this.subArcs.length = Math.max(0, all.length - 1);
    for (const c of all) this.blockedEdges.add(c.edge);
    this.builtTo = all.length;
  }

  #crossings() {
    const end = this.#endCrossing();
    const all = end ? [...this.interior, end] : [...this.interior];
    if (all.length) all[0] = { ...all[0], kind: 'start' };
    return all;
  }

  /**
   * Look up the crossings on one edge.  The end marker is folded in here rather than kept in
   * the index, because it is the one crossing that changes every time the arc is extended.
   */
  #lookup() {
    const end = this.#endCrossing(), byEdge = this.byEdge;
    return {
      get(edge) {
        const on = byEdge.get(edge);
        if (end && end.edge === edge) return on ? [...on, end] : [end];
        return on;
      }
    };
  }

  /** An ArcDescription equal to `describeArc(this.arc, { assumeValid: true })`. */
  get description() {
    return {
      arc: this.arc,
      settings: this.settings,
      problems: this.problems,
      crossings: this.#crossings(),
      cells: [...this.cells.values()],
      subArcs: this.subArcs,
      blockedEdges: this.blockedEdges,
      crossingsByEdge: this.#lookup(),
      candidateEdges: this.candidateEdges
    };
  }
}
