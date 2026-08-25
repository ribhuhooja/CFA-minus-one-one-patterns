/**
 * Counting discs.
 *
 * A disc is a piece of beta together with the grid path that closes it up: the solver finds
 * the path, this module walks over every piece worth trying and reads off what the disc
 * carries.
 *
 * WHICH PIECES.  Beta meets each generator once per circuit, so the nodes of one circuit of
 * the lifted track are exactly the generators, once each.  From each of them we run both
 * ways along beta, as far as the point where beta comes back to that same generator -- one
 * circuit in each direction.  Every disc with that source is somewhere in that range.
 *
 * REEB CHORDS.  At each lattice point of the path there is an incoming direction and an
 * outgoing one, and the six pairs that can occur are exactly the six moves the local rules
 * permit -- which is why there are exactly six chords to name.  A path of k+1 steps reads
 * off k chords, one per lattice point, in the order it walks them; a path with no lattice
 * point at all -- both ends on one edge -- carries none.
 *
 * The naming is fixed by asking the composites to compose.  Writing a chord as (in, out),
 * rho_12 should start where rho_1 starts and end where rho_2 ends, and likewise rho_23 and
 * rho_123.  That holds for exactly one of the two ways of assigning rho_1 and rho_3:
 *
 *      rho_1  = N -> W        rho_12  = N -> N   = (start of rho_1, end of rho_2)
 *      rho_2  = E -> N        rho_23  = E -> E   = (start of rho_2, end of rho_3)
 *      rho_3  = S -> E        rho_123 = N -> E   = (start of rho_1, end of rho_3)
 *
 * Swap rho_1 and rho_3 and none of the three composites lines up.  That swapped table is
 * kept as `dictated` because it is how the rule was handed over; `composed` is the default,
 * and it is the one that reproduces reference_Q222.csv.
 *
 * VALIDATING ONCE.  Everything §2 of the solver's spec asks of an arc -- clearance from the
 * lattice points, transversality, staying in the window, crossing rather than touching at a
 * vertex -- is a property of beta, not of the piece being solved, so it holds for every piece
 * as soon as it holds for the whole lifted track.  The one thing that is not inherited is
 * that both ends lie in the interior of a grid edge, and that is exactly what a node is.  So
 * the track is checked once, the nodes are checked once, and the 2C^2 solves that follow skip
 * §2 entirely.  Re-validating the same curve for every piece was three quarters of the work.
 *
 * EXTENDING RATHER THAN REBUILDING.  From one generator the enumeration wants the pieces of
 * length 1, 2, 3, ... in turn, and each is the previous one plus an arc -- so an
 * `ArcDescriptionBuilder` is fed one arc at a time instead of the whole piece being described
 * from scratch each round.  Both directions grow at the piece's own end (going backwards, the
 * piece is the reverse of a run of arcs, so extending it prepends an arc to the run and
 * therefore appends to the reversal), which is what lets a plain append serve for both.
 *
 * THE POWER OF U is how often the domain covers the basepoint w, which sits shut inside the
 * innermost rainbow.  On the torus that is a multiplicity; in the universal cover, where the
 * solver works, it is simply the number of lifts of w that the region encloses.  The
 * basepoint z is the one that may never be covered, and the solver already refuses any path
 * that covers it.
 */
import { boundingBox, windingNumber } from '../../grid-arc/src/geometry.js';
import { solve, validateArc, edgeContaining, ArcDescriptionBuilder } from '../../grid-arc/src/index.js';
import { tabulate, PieceBuilder } from './fast.js';
import { layout } from './layout.js';
import { liftBeta, subTrack, tileExtent } from './track.js';
import { scaling, gridSettingsFor } from './bridge.js';

/** The six turns a path can make, and the chord each one is. */
export const REEB_CONVENTIONS = Object.freeze({
  /** composites compose; reproduces reference_Q222.csv */
  composed: Object.freeze({
    'N>W': 'rho_1', 'E>N': 'rho_2', 'S>E': 'rho_3',
    'N>N': 'rho_12', 'E>E': 'rho_23', 'N>E': 'rho_123'
  }),
  /** rho_1 and rho_3 the other way round, as the rule was first written down */
  dictated: Object.freeze({
    'S>E': 'rho_1', 'E>N': 'rho_2', 'N>W': 'rho_3',
    'N>N': 'rho_12', 'E>E': 'rho_23', 'N>E': 'rho_123'
  })
});
export const REEB_CHORDS = REEB_CONVENTIONS.composed;

const resolveConvention = (c) =>
  typeof c === 'string' ? (REEB_CONVENTIONS[c] ?? (() => { throw new Error(`no Reeb convention "${c}"`); })())
                        : (c ?? REEB_CHORDS);

/**
 * The chords a path carries, in the order it walks them.
 * @param {string[]} directions  as returned by the solver, e.g. ['S','E','N','N','W']
 * @param {string|Object} [convention] 'composed' (default) or 'dictated', or a table
 * @returns {string[]}
 */
export function reebChords(directions, convention) {
  const table = resolveConvention(convention);
  const chords = [];
  for (let k = 0; k + 1 < directions.length; k++) {
    const turn = `${directions[k]}>${directions[k + 1]}`;
    const chord = table[turn];
    if (!chord) throw new Error(`the turn ${turn} has no Reeb chord; the path should not contain it`);
    chords.push(chord);
  }
  return chords;
}

/** Short form, in the style of the reference tables: rho_12 rho_1 -> "P12P1". */
export const chordWord = (chords) => chords.map((c) => c.replace('rho_', 'P')).join('');

/** How many lifts of `point` (given inside the unit cell) the region encloses. */
export function multiplicity(polygon, point) {
  const [x0, y0, x1, y1] = boundingBox(polygon);
  let count = 0;
  for (let k = Math.floor(x0) - 1; k <= Math.ceil(x1) + 1; k++)
    for (let l = Math.floor(y0) - 1; l <= Math.ceil(y1) + 1; l++)
      if (windingNumber(polygon, [k + point[0], l + point[1]]) !== 0) count++;
  return count;
}

/**
 * @typedef {Object} Disc
 * @property {string} source, target      generator names
 * @property {number} offset              arcs travelled along beta, signed
 * @property {string[]} directions        the path, as compass steps
 * @property {string[]} chords            Reeb chords in the order the path walks them
 * @property {string} word                those chords as "P1P2..."
 * @property {string} wordReversed        the same, written the other way round
 * @property {number} U                   how often the domain covers w
 * @property {number} area                signed area of the closed curve; always negative
 * @property {number[][]} [polygon]       the region itself, in unit-grid coordinates;
 *                                        only present when `keepRegions` is asked for
 */

/**
 * Every disc of the diagram.
 * @param {import('./diagram.js').HeegaardDiagram} diagram
 * @param {{cell?:number, samples?:number, strategy?:string, convention?:string,
 *           engine?:'heegaard'|'generic', keepRegions?:boolean, onProgress?:Function}} [options]
 *        `engine` picks how a piece is described: 'heegaard' looks the answer up in tables
 *        precomputed from the diagram, 'generic' rediscovers it from the geometry as the
 *        general solver does.  They agree; the second is kept for cross-checking.
 * @returns {{discs:Disc[], circuit:number, generators:string[], settings:Object, laidOut:Object, track:Object, tried:number}}
 */
export function enumerateDiscs(diagram, options = {}) {
  const { cell = 26, samples = 4, strategy = 'walk', convention,
          engine = 'heegaard', keepRegions = false, onProgress } = options;
  // An arc is a primitive -- a segment or a parabola -- so it only has to be sampled finely
  // enough for the checks that need points.  The apex is always a sample, which is what keeps
  // a basepoint under a bulge on the right side of it.
  const laidOut = layout(diagram, { cell, samples });
  const circuit = diagram.components()[0].length;
  const span = circuit * 3 + 1;

  // lift, then lift again shifted so every copy the track visits has a non-negative index
  const probe = liftBeta(diagram, laidOut, { arcs: span });
  const [i0, j0] = tileExtent(probe, 1);
  const track = liftBeta(diagram, laidOut, { arcs: span, startTile: [1 - i0, 1 - j0] });
  const extent = tileExtent(track, 1);
  const { settings } = gridSettingsFor(laidOut, { extent });
  const scale = scaling(laidOut);

  const wSpot = laidOut.basepoints.get('w');
  if (!wSpot) throw new Error(`${diagram.name} has no w basepoint, so U powers are undefined`);
  const w = scale.toGrid(wSpot.at);

  // Check beta once, so that no piece of it has to be checked again (see above).
  const whole = scale.pathToGrid(subTrack(track, 0, track.segments.length));
  const problems = validateArc(whole, settings, { assumeSimple: true });
  if (problems.length)
    throw new Error(`${diagram.name}: the lifted beta curve is not legal input to the solver:\n  ` +
      problems.slice(0, 3).map((p) => p.message).join('\n  '));
  for (const node of track.nodes)
    if (!edgeContaining(scale.toGrid(node.at), 1e-9))
      throw new Error(`${diagram.name}: generator ${node.generator} does not lie in the interior ` +
        'of a grid edge, so pieces ending there cannot skip validation');

  // normalise every arc of the track once, rather than once per piece that contains it
  const gridSegments = track.segments.map((points) => scale.pathToGrid(points));
  const reversed = gridSegments.map((points) => [...points].reverse());

  const tables = engine === 'heegaard' ? tabulate(diagram, track) : null;
  const pointsOf = (k, direction) => (direction > 0 ? gridSegments[k] : reversed[k]);

  const discs = [];
  let tried = 0;
  for (let start = circuit; start < 2 * circuit; start++) {
    for (const direction of [1, -1]) {
      const builder = tables ? new PieceBuilder(tables, settings, pointsOf).reset(start, direction)
                             : new ArcDescriptionBuilder(settings);
      for (let step = 1; step <= circuit; step++) {
        const offset = direction * step;
        const segment = direction > 0 ? start + step - 1 : start - step;
        if (segment < 0 || segment >= gridSegments.length) break;
        if (tables) { if (!builder.extend()) break; }
        else builder.append(direction > 0 ? gridSegments[segment] : reversed[segment]);
        tried++;
        const result = solve(builder.arc, { description: builder.description, strategy });
        if (result.status !== 'solved') continue;
        for (const solution of result.solutions) {
          const chords = reebChords(solution.directions, convention);
          discs.push({
            source: track.nodes[start].generator,
            target: track.nodes[start + offset].generator,
            offset,
            directions: solution.directions,
            chords,
            word: chordWord(chords),
            wordReversed: chordWord([...chords].reverse()),
            U: multiplicity(solution.region.polygon, w),
            area: solution.region.area,
            ...(keepRegions ? { polygon: solution.region.polygon } : {})
          });
        }
      }
    }
    onProgress?.(start - circuit + 1, circuit);
  }

  const generators = [];
  for (let k = circuit; k < 2 * circuit; k++) generators.push(track.nodes[k].generator);
  return { discs, circuit, generators, settings, laidOut, track, tried };
}

/**
 * The disc list as CSV.
 *
 *   'full'       source,target,U,chords,offset,path   -- everything, including how far along
 *                beta the piece ran and the grid path that closed it
 *   'reference'  source,target,annotation,U,P         -- the layout the reference tables use,
 *                so the two can be diffed directly
 *
 * @param {Disc[]} discs
 * @param {{format?:'full'|'reference', reverse?:boolean, sort?:boolean}} [options]
 * @returns {string}
 */
export function toCSV(discs, { format = 'full', reverse = false, sort = false } = {}) {
  const word = (d) => (reverse ? d.wordReversed : d.word);
  const rows = sort
    ? [...discs].sort((a, b) =>
        a.source.localeCompare(b.source, 'en', { numeric: true }) ||
        a.target.localeCompare(b.target, 'en', { numeric: true }) ||
        a.U - b.U || word(a).localeCompare(word(b)))
    : discs;

  if (format === 'reference') {
    const lines = ['source,target,annotation,U,P'];
    for (const d of rows)
      lines.push([d.source, d.target, `${uPrefix(d.U)}${word(d)}`, uPrefix(d.U), word(d)].join(','));
    return `${lines.join('\n')}\n`;
  }
  const lines = ['source,target,U,chords,offset,path'];
  for (const d of rows)
    lines.push([d.source, d.target, d.U, word(d), d.offset, d.directions.join(' ')].join(','));
  return `${lines.join('\n')}\n`;
}

/** "" for U^0, "U" for U^1, "U^k" beyond -- how the reference tables write the U power. */
export const uPrefix = (U) => (U === 0 ? '' : U === 1 ? 'U' : `U^${U}`);
