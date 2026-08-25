/**
 * The bridge to the grid solver next door.
 *
 * A universal cover of these domains IS the solver's grid: divide by (W, H) and every copy
 * of the fundamental domain becomes a unit cell, the alpha curves become the integer lines,
 * and the basepoint in a copy's top-left corner becomes that cell's forbidden point.  So a
 * piece of beta, normalised, is exactly the kind of arc the solver takes.
 *
 * The one thing that does not carry over is scale.  The solver's defaults are tuned for a
 * curve drawn by hand on a 20 x 20 grid, where staying 0.08 of a cell away from every
 * lattice point is easy.  Beta does not have that luxury: generator x_0 sits half a cell of
 * the *diagram* from the corner, which is a small fraction of a unit cell once normalised.
 * So the tolerances are measured off the diagram instead of assumed, subject to the rule
 * that beta must never come closer to a lattice point than the forbidden point does.
 */
import { distancePointSegment } from '../../grid-arc-js/src/geometry.js';
import { gridSettings } from '../../grid-arc-js/src/grid.js';

/** Normalised <-> cover coordinates. */
export function scaling(laidOut) {
  const { width, height } = laidOut;
  return {
    width, height,
    toGrid: ([x, y]) => [x / width, y / height],
    toCover: ([x, y]) => [x * width, y * height],
    pathToGrid: (points) => points.map(([x, y]) => [x / width, y / height]),
    pathToCover: (points) => points.map(([x, y]) => [x * width, y * height])
  };
}

/** How close beta gets to a lattice point, in normalised units. */
export function closestApproach(laidOut) {
  const { width, height } = laidOut;
  let best = Infinity, at = null;
  for (const arc of laidOut.arcs) {
    const path = arc.path.map(([x, y]) => [x / width, y / height]);
    for (let k = 0; k + 1 < path.length; k++)
      for (const corner of [[0, 0], [1, 0], [0, 1], [1, 1]]) {
        const d = distancePointSegment(corner, path[k], path[k + 1]);
        if (d < best) { best = d; at = { corner, arc: arc.index, family: arc.family }; }
      }
  }
  return { distance: best, at };
}

/**
 * Solver settings for this diagram.
 * @param {import('./layout.js').Layout} laidOut
 * @param {{extent?:number[], clearanceFraction?:number}} [options]
 *        `extent` is [i0, j0, i1, j1] in copies of the domain, so the window can be told
 *        how far the lifted curve is allowed to wander.
 */
export function gridSettingsFor(laidOut, options = {}) {
  const { extent = [0, 0, 20, 20], clearanceFraction = 0.6 } = options;
  const approach = closestApproach(laidOut);
  const epsForbidden = laidOut.basepoint.epsilon;
  const minLatticeDistance = clearanceFraction * approach.distance;

  if (epsForbidden * Math.SQRT2 >= minLatticeDistance)
    throw new Error(
      `this diagram is drawn too tight for the solver: the basepoint sits ` +
      `${(epsForbidden * Math.SQRT2).toPrecision(3)} from its corner but beta passes within ` +
      `${approach.distance.toPrecision(3)} of a lattice point. Raise the cell size or lower ` +
      'basepointFraction.');

  const lo = Math.min(extent[0], extent[1]), hi = Math.max(extent[2], extent[3]);
  return {
    settings: gridSettings({
      cells: hi, windowMin: lo, windowMax: hi,
      epsForbidden, minLatticeDistance
    }),
    approach
  };
}
