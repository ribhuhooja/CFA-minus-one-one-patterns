/**
 * heegaard — bordered Heegaard diagrams on the torus.
 *
 *   import { Q, layout, renderDiagram, renderUniversalCover } from './heegaard/src/index.js';
 *   const diagram = Q(2, 2, 2);            // -> H(r=7, s=14)
 *   const drawn = layout(diagram, { cell: 26 });
 *   writeFileSync('Q222.svg', renderDiagram(drawn));
 *
 * The combinatorics (diagram.js) know nothing about geometry; the geometry (layout.js)
 * knows nothing about SVG.  Mathematical coordinates throughout, y up.
 */
export { HeegaardDiagram, SIDES, GENERATOR_OF_SIDE, GLUED_SIDE, endpointKey, generatorName } from './diagram.js';
export { Q, parameters, FAMILIES } from './qmn.js';
export { layout, findArcCrossings, translatePath, DEFAULTS } from './layout.js';
export { renderDiagram, renderUniversalCover, COLOURS } from './render.js';
export { liftBeta, subTrack, nearestNode, tileExtent } from './track.js';
export { scaling, closestApproach, gridSettingsFor } from './bridge.js';
export {
  enumerateDiscs, reebChords, chordWord, multiplicity, uPrefix,
  REEB_CHORDS, REEB_CONVENTIONS, toCSV
} from './discs.js';
export { conjecturedArrows, conjecturedCount, annotation } from './conjectured.js';
export { discAtlas, packIntoSlots, sampleDiscs } from './atlas.js';
