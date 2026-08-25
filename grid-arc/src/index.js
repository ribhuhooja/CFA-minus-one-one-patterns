/**
 * grid-arc — public API.
 *
 * Given a simple arc drawn on the unit grid, find the grid path from one endpoint to the
 * other whose enclosed region avoids every forbidden point, or report that none exists.
 *
 *   import { solve } from './src/index.js';
 *   const result = solve([[5.4, 5], [5.6, 5.5], [5.4, 6]], { strategy: 'walk' });
 *   result.status;                        // 'solved'
 *   result.solutions[0].directions;       // ['E', 'N', 'W']
 *   result.solutions[0].region.polygon;   // the Jordan curve bounding D
 *
 * Everything is pure: no DOM, no globals, no I/O.  Mathematical coordinates throughout
 * (y increases upward); any flip belongs to a rendering layer.
 */

export { solve } from './solve.js';

// the arc, before any path search
export { validateArc, findCrossings, decomposeIntoCells, describeArc } from './arc.js';
export { ArcDescriptionBuilder } from './incremental.js';

// what the arc's orientation forces at its ends
export {
  endpointConditions, crossingStrictlyBetween, partialEdgeSpans, FIRST_STEP, LAST_STEP
} from './endpoints.js';

// the conjectured local rules — never load-bearing, always optional
export { STEP_TABLE, shieldingContext, localVerdict } from './rules.js';

// the global conditions, individually reusable
export {
  closedCurve, checkSimple, checkDisjointFromArc, checkForbiddenPoints, checkOrientation, checkPath
} from './constraints.js';

// the two ways of producing candidates
export { enumeratePaths, walkPath } from './search.js';

// grid and geometry vocabulary
export {
  GRID, gridSettings, DIRECTIONS, DIRECTION_NAMES, OPPOSITE, stepFrom, latticeKey, cellKey,
  edgeKey, parseEdgeKey, edgeEndpoints, cellEdgeKeys, cellSideOfEdge, edgeParameter,
  edgeContaining, forbiddenPoint, cellOwningCorner, directionsAlong
} from './grid.js';
export {
  TOL, sub, add, scale, cross, dot, length, distance, rotateCW, rotateCCW,
  distancePointSegment, intersectSegments, isSimplePolyline,
  signedArea, windingNumber, boundingBox, simplify
} from './geometry.js';
