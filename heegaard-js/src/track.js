/**
 * Beta, lifted to the universal cover.
 *
 * On the torus beta is a closed curve; in the cover it is an embedded track running through
 * translated copies of the fundamental domain.  Following it is mechanical: traverse an arc
 * from the end you came in by to the other end, then cross the alpha curve there -- which
 * means stepping into the neighbouring copy of the domain and continuing from the glued
 * slot.  Leaving by the top puts you in the copy above, by the right in the copy to the
 * right, and so on.
 *
 * The track's NODES are exactly its crossings with the alpha curves, i.e. the lifts of the
 * generators.  They matter because a sub-arc of beta can only be fed to the grid solver if
 * both its ends lie on an alpha curve: the solver's red path runs along the grid, so it has
 * nowhere to start from in the middle of a cell.  So a usable piece of beta is a run of
 * consecutive arcs, node to node, and that is the unit this module deals in.
 */
import { GLUED_SIDE, endpointKey, generatorName } from './diagram.js';

/** Which copy of the domain you land in when you leave by a given side. */
const TILE_STEP = { top: [0, 1], bottom: [0, -1], right: [1, 0], left: [-1, 0] };

/**
 * @typedef {Object} Track
 * @property {{at:number[], generator:string, side:string, index:number, tile:number[], arclength:number}[]} nodes
 * @property {number[][][]} segments   segment k runs from node k to node k+1
 * @property {number[]} period         tile shift after one full circuit of beta (its homology class)
 * @property {number} circuit          arcs in one circuit
 */

/**
 * @param {import('./diagram.js').HeegaardDiagram} diagram
 * @param {import('./layout.js').Layout} laidOut
 * @param {{arcs?:number, startArc?:number, startTile?:number[]}} [options]
 * @returns {Track}
 */
export function liftBeta(diagram, laidOut, options = {}) {
  const { width, height } = laidOut;
  const circuit = diagram.components()[0].length;
  const { arcs: wanted = circuit * 4, startArc = 0, startTile = [0, 0] } = options;

  const at = new Map();                       // endpoint key -> which arc end it is
  diagram.arcs.forEach((arc, index) => {
    at.set(endpointKey(arc.a), { index, end: 'a' });
    at.set(endpointKey(arc.b), { index, end: 'b' });
  });

  const shift = (p, [k, l]) => [p[0] + k * width, p[1] + l * height];
  const nodes = [], segments = [];

  let entry = diagram.arcs[startArc].a;
  let tile = [...startTile];
  let arclength = 0;
  let period = null;
  const startKey = `${endpointKey(entry)}`;

  for (let step = 0; step < wanted; step++) {
    const here = at.get(endpointKey(entry));
    const arc = diagram.arcs[here.index];
    const exit = here.end === 'a' ? arc.b : arc.a;
    const raw = laidOut.arcs[here.index].path;
    const oriented = here.end === 'a' ? raw : [...raw].reverse();
    const points = oriented.map((p) => shift(p, tile));

    nodes.push({
      at: points[0], generator: generatorName(entry), side: entry.side,
      index: entry.index, tile: [...tile], arclength, arcIndex: here.index,
      family: arc.family ?? ''
    });
    segments.push(points);
    for (let k = 0; k + 1 < points.length; k++)
      arclength += Math.hypot(points[k + 1][0] - points[k][0], points[k + 1][1] - points[k][1]);

    const [dk, dl] = TILE_STEP[exit.side];
    tile = [tile[0] + dk, tile[1] + dl];
    entry = { side: GLUED_SIDE[exit.side], index: exit.index };
    if (step + 1 === circuit) period = [tile[0] - startTile[0], tile[1] - startTile[1]];
    if (endpointKey(entry) === startKey && period === null) period = [tile[0] - startTile[0], tile[1] - startTile[1]];
  }

  // one last node so that segment k always runs between node k and node k+1
  const last = at.get(endpointKey(entry));
  const lastArc = laidOut.arcs[last.index].path;
  nodes.push({
    at: shift(last.end === 'a' ? lastArc[0] : lastArc.at(-1), tile),
    generator: generatorName(entry), side: entry.side, index: entry.index,
    tile: [...tile], arclength, arcIndex: last.index, family: diagram.arcs[last.index].family ?? ''
  });

  return { nodes, segments, period: period ?? [0, 0], circuit, width, height };
}

/**
 * The piece of the track between two nodes, as one polyline running from `from` to `to`.
 * Going backwards is allowed and simply reverses the result.
 */
export function subTrack(track, from, to) {
  if (from === to) return null;
  const forward = to > from;
  const [lo, hi] = forward ? [from, to] : [to, from];
  const points = [];
  for (let k = lo; k < hi; k++)
    for (const p of track.segments[k])
      if (!points.length || p[0] !== points.at(-1)[0] || p[1] !== points.at(-1)[1]) points.push(p);
  return forward ? points : points.reverse();
}

/** The node nearest a point, searched over the whole track. */
export function nearestNode(track, target) {
  let best = 0, bestDistance = Infinity;
  track.nodes.forEach((node, k) => {
    const d = Math.hypot(node.at[0] - target[0], node.at[1] - target[1]);
    if (d < bestDistance) { bestDistance = d; best = k; }
  });
  return { index: best, distance: bestDistance };
}

/** Tile range the track occupies, expanded by `pad`. */
export function tileExtent(track, pad = 1) {
  let i0 = Infinity, j0 = Infinity, i1 = -Infinity, j1 = -Infinity;
  for (const node of track.nodes) {
    i0 = Math.min(i0, node.tile[0]); i1 = Math.max(i1, node.tile[0]);
    j0 = Math.min(j0, node.tile[1]); j1 = Math.max(j1, node.tile[1]);
  }
  return [i0 - pad, j0 - pad, i1 + pad + 1, j1 + pad + 1];
}
