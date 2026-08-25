/**
 * The drawn arc: validation (§2), its crossings with the grid, and the cells it visits.
 *
 * `describeArc` is the one call most downstream code needs; it returns everything the
 * solver (and anything else, e.g. a disc-counting pipeline) knows about a curve before
 * any path search happens.
 */
import {
  TOL, sub, length, isNearInteger, isSimplePolyline, distancePointSegment
} from './geometry.js';
import {
  GRID, gridSettings, edgeContaining, edgeParameter, cellSideOfEdge, cellKey
} from './grid.js';

/** @typedef {{message:string, at:?number[]}} Problem */

/**
 * Validate a candidate arc against §2.  Never repairs; returns every problem it finds.
 *
 * `assumeSimple` skips the (2.1) self-intersection test, which is the only quadratic step
 * here.  Pass it ONLY when the arc is embedded by construction and you can say why -- the
 * lift of an embedded curve to a covering space, for instance.  A hand-drawn stroke is not
 * such a case.  Everything else is still checked.
 *
 * @param {number[][]} arc polyline from x_s to x_e
 * @param {Object} [settings]
 * @param {{assumeSimple?:boolean}} [options]
 * @returns {Problem[]} empty if the arc is legal input
 */
export function validateArc(arc, settings = GRID, { assumeSimple = false } = {}) {
  const problems = [];
  const report = (message, at = null) => problems.push({ message, at });

  if (!Array.isArray(arc) || arc.length < 2) {
    report('an arc needs at least two points');
    return problems;
  }
  for (const p of arc)
    if (!Array.isArray(p) || p.length !== 2 || !isFinite(p[0]) || !isFinite(p[1])) {
      report('the arc contains a non-finite point');
      return problems;
    }

  // (2.1) simple
  if (!assumeSimple) {
    const simple = isSimplePolyline(arc);
    if (!simple.ok) report(`the arc is not simple: ${simple.why}`, simple.at);
  }

  // (2.5) inside the working window
  for (const p of arc)
    if (p[0] < settings.windowMin - TOL.geom || p[0] > settings.windowMax + TOL.geom ||
        p[1] < settings.windowMin - TOL.geom || p[1] > settings.windowMax + TOL.geom) {
      report(`the arc leaves the working window (cells ${settings.windowMin}..${settings.windowMax - 1})`, p);
      break;
    }

  // (2.2) both endpoints in the interior of a grid edge
  for (const [p, name] of [[arc[0], 'x_s'], [arc.at(-1), 'x_e']]) {
    const onVertical = isNearInteger(p[0], 1e-9), onHorizontal = isNearInteger(p[1], 1e-9);
    if (!onVertical && !onHorizontal) report(`${name} does not lie on a grid edge`, p);
    else if (onVertical && onHorizontal)
      report(`${name} is a lattice point; endpoints must lie in the interior of an edge`, p);
  }

  // An interior vertex may sit on a grid line, but only if the arc genuinely crosses
  // there.  A tangential touch is a non-transversal meeting, banned by (2.4).
  for (let i = 1; i < arc.length - 1; i++) {
    const v = arc[i];
    for (const axis of [0, 1]) {
      if (!isNearInteger(v[axis], 1e-9)) continue;
      const k = Math.round(v[axis]);
      let before = 0, after = 0;
      for (let j = i - 1; j >= 0 && before === 0; j--) before = Math.sign(arc[j][axis] - k);
      for (let j = i + 1; j < arc.length && after === 0; j++) after = Math.sign(arc[j][axis] - k);
      if (before === 0 || after === 0 || before === after)
        report(`the arc touches the grid line ${axis ? 'y' : 'x'}=${k} tangentially at vertex ${i}` +
               ' instead of crossing it', v);
    }
  }

  // (2.3) clearance from every lattice point
  outer:
  for (let i = 0; i + 1 < arc.length; i++) {
    const a = arc[i], b = arc[i + 1];
    const x0 = Math.floor(Math.min(a[0], b[0])) - 1, x1 = Math.ceil(Math.max(a[0], b[0])) + 1;
    const y0 = Math.floor(Math.min(a[1], b[1])) - 1, y1 = Math.ceil(Math.max(a[1], b[1])) + 1;
    for (let x = x0; x <= x1; x++) for (let y = y0; y <= y1; y++) {
      const d = distancePointSegment([x, y], a, b);
      if (d < settings.minLatticeDistance - 1e-12) {
        report(`the arc passes within ${d.toFixed(4)} of lattice point (${x},${y}); ` +
               `the minimum is ${settings.minLatticeDistance}`, [x, y]);
        break outer;
      }
    }
  }

  // (2.4) transversality: no segment collinear with a grid line
  for (let i = 0; i + 1 < arc.length; i++) {
    const a = arc[i], d = sub(arc[i + 1], a), l = length(d);
    if (l < TOL.geom) { report('the arc has a zero-length segment', a); continue; }
    if (Math.abs(d[1]) / l < TOL.transverse && isNearInteger(a[1], 1e-6))
      report(`segment ${i} is collinear with the grid line y=${Math.round(a[1])}`, a);
    if (Math.abs(d[0]) / l < TOL.transverse && isNearInteger(a[0], 1e-6))
      report(`segment ${i} is collinear with the grid line x=${Math.round(a[0])}`, a);
  }
  return problems;
}

/**
 * @typedef {Object} Crossing
 * @property {number[]} p       the crossing point
 * @property {string} edge      edge key it lies on
 * @property {number} t         parameter along that edge, in (0,1)
 * @property {number} segment   index of the arc segment carrying it
 * @property {number} at        global parameter along the arc (segment + local t)
 * @property {'start'|'interior'|'end'} kind
 */

/**
 * X = arc ∩ grid, ordered along the arc.  Both endpoints are crossings by construction.
 * @returns {{crossings: Crossing[], problems: Problem[]}}
 */
export function findCrossings(arc) {
  const crossings = [], problems = [];
  const segments = arc.length - 1;

  for (let i = 0; i < segments; i++) {
    const a = arc[i], d = sub(arc[i + 1], a), l = length(d), hits = [];
    for (const axis of [0, 1]) {
      if (Math.abs(d[axis]) <= TOL.geom) continue;
      const lo = Math.min(a[axis], a[axis] + d[axis]), hi = Math.max(a[axis], a[axis] + d[axis]);
      for (let k = Math.ceil(lo - 1e-12); k <= Math.floor(hi + 1e-12); k++) {
        const t = (k - a[axis]) / d[axis];
        // half-open [0,1): a vertex on a grid line is counted once, by the segment leaving it
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
      crossings.push({
        p: h.p, edge, t: edgeParameter(edge, h.p),
        segment: i, at: i + h.t, kind: 'interior'
      });
    }
  }

  const last = arc.at(-1), lastEdge = edgeContaining(last, 1e-7);
  if (lastEdge)
    crossings.push({
      p: last, edge: lastEdge, t: edgeParameter(lastEdge, last),
      segment: segments - 1, at: segments, kind: 'end'
    });
  if (crossings.length) crossings[0].kind = 'start';

  return { crossings, problems };
}

/**
 * The cells whose interior the arc passes through, and the decomposition of the arc into
 * one sub-arc per cell visit.  Consecutive crossings bound exactly one sub-arc.
 * @returns {{cells: {i:number,j:number}[], subArcs: {cell:number[], entry:?string, exit:?string, from:number, to:number}[]}}
 */
export function decomposeIntoCells(arc, crossings) {
  const cells = new Map(), subArcs = [];
  const pointAt = (u) => {
    const i = Math.min(Math.floor(u), arc.length - 2), t = u - i;
    return [arc[i][0] + t * (arc[i + 1][0] - arc[i][0]), arc[i][1] + t * (arc[i + 1][1] - arc[i][1])];
  };
  for (let k = 0; k + 1 < crossings.length; k++) {
    const a = crossings[k], b = crossings[k + 1];
    const mid = pointAt((a.at + b.at) / 2);
    const i = Math.floor(mid[0]), j = Math.floor(mid[1]);
    cells.set(cellKey(i, j), { i, j });
    subArcs.push({
      cell: [i, j],
      entry: cellSideOfEdge(a.edge, i, j),
      exit: cellSideOfEdge(b.edge, i, j),
      from: a.at, to: b.at
    });
  }
  return { cells: [...cells.values()], subArcs };
}

/**
 * `assumeValid` skips §2 altogether.  Every check in it is a property of the CURVE, not of
 * the piece of it being solved: clearance from the lattice points, transversality, staying in
 * the window, crossing rather than touching at a vertex.  So a caller that has validated a
 * long curve once may solve any number of sub-arcs of it without paying for §2 again --
 * provided the two ends of each sub-arc are themselves in the interior of a grid edge, which
 * is (2.2) and the one thing that is not inherited.  `heegaard` checks exactly that.
 *
 * @typedef {Object} ArcDescription
 * @property {number[][]} arc
 * @property {Problem[]} problems     empty iff the arc is legal input
 * @property {Crossing[]} crossings
 * @property {{i:number,j:number}[]} cells       C, the cells the arc passes through
 * @property {Object[]} subArcs
 * @property {Set<string>} blockedEdges          edges the arc crosses; a path may not use them
 * @property {Set<string>} candidateEdges        §6: the only edges a path may use
 */

/**
 * Everything derivable from the arc alone.  Downstream modules take this, not the raw polyline.
 * @param {number[][]} arc
 * @param {{searchSpace?: 'cells'|'bbox', bboxPad?: number}} [options]
 *        `searchSpace:'bbox'` widens the candidate edge set to every edge near the arc,
 *        which exists only so the harness can test the §6 lemma empirically.
 * @returns {ArcDescription}
 */
export function describeArc(arc, options = {}) {
  const settings = options.settings ?? gridSettings(options.grid ?? {});
  const problems = options.assumeValid
    ? []
    : validateArc(arc, settings, { assumeSimple: options.assumeSimple });
  if (problems.length)
    return { arc, settings, problems, crossings: [], cells: [], subArcs: [],
             blockedEdges: new Set(), candidateEdges: new Set() };

  const { crossings, problems: crossingProblems } = findCrossings(arc);
  if (crossingProblems.length)
    return { arc, settings,
             problems: crossingProblems.map((p) => ({ ...p, message: `degenerate crossing: ${p.message}` })),
             crossings: [], cells: [], subArcs: [], blockedEdges: new Set(), candidateEdges: new Set() };

  const { cells, subArcs } = decomposeIntoCells(arc, crossings);
  const blockedEdges = new Set(crossings.map((c) => c.edge));
  const candidateEdges = buildCandidateEdges(arc, cells, options, settings);
  return { arc, settings, problems: [], crossings, cells, subArcs, blockedEdges, candidateEdges };
}

function buildCandidateEdges(arc, cells, { searchSpace = 'cells', bboxPad = 2 } = {}, settings = GRID) {
  const edges = new Set();
  if (searchSpace === 'bbox') {
    let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
    for (const p of arc) {
      x0 = Math.min(x0, p[0]); y0 = Math.min(y0, p[1]);
      x1 = Math.max(x1, p[0]); y1 = Math.max(y1, p[1]);
    }
    const i0 = Math.max(0, Math.floor(x0) - bboxPad), i1 = Math.min(settings.cells, Math.ceil(x1) + bboxPad);
    const j0 = Math.max(0, Math.floor(y0) - bboxPad), j1 = Math.min(settings.cells, Math.ceil(y1) + bboxPad);
    for (let i = i0; i <= i1; i++) for (let j = j0; j <= j1; j++) {
      if (i < i1) edges.add(`H:${i}:${j}`);
      if (j < j1) edges.add(`V:${i}:${j}`);
    }
    return edges;
  }
  // §6: D lies in the closure of the cells the arc visits, so every edge of the path is
  // an edge of one of those cells.
  for (const { i, j } of cells) {
    edges.add(`H:${i}:${j}`); edges.add(`H:${i}:${j + 1}`);
    edges.add(`V:${i}:${j}`); edges.add(`V:${i + 1}:${j}`);
  }
  return edges;
}
