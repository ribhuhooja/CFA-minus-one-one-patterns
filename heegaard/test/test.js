/** node test/test.js — the Q family, its bookkeeping, and its picture. */
import {
  Q, parameters, layout, findArcCrossings, renderDiagram, renderUniversalCover,
  liftBeta, subTrack, tileExtent, scaling, gridSettingsFor, closestApproach,
  enumerateDiscs, reebChords, chordWord, REEB_CONVENTIONS, toCSV,
  conjecturedArrows, conjecturedCount, discAtlas, packIntoSlots,
  diagramToCSV, diagramFromCSV, discsToCSV, discsFromCSV, DIAGRAM_FORMAT
} from '../src/index.js';
import { boundingBox } from '../../grid-arc/src/geometry.js';
import { ArcDescriptionBuilder, describeArc } from '../../grid-arc/src/index.js';
import { HeegaardDiagram } from '../src/diagram.js';
import { solve } from '../../grid-arc/src/index.js';

let passed = 0, failed = 0;
const check = (name, ok, info) => {
  if (ok) { passed++; return true; }
  failed++; console.log(`  FAIL  ${name}${info ? `\n        ${info}` : ''}`);
  return false;
};

console.log('\n  H(r,s) from Q(i,m,n)');
{
  const p = parameters(2, 2, 2);
  check('Q(2,2,2) -> r = 7', p.r === 7, `got ${p.r}`);
  check('Q(2,2,2) -> s = 14', p.s === 14, `got ${p.s}`);
  check('Q(2,2,2) -> maxx = 29', p.maxx === 29, `got ${p.maxx}`);
  check('Q(2,2,2) -> maxy = 12', p.maxy === 12, `got ${p.maxy}`);
  for (const [i, m, n] of [[2, 2, 2], [1, 1, 2], [3, 2, 2], [2, 2, 5], [1, 2, 4]]) {
    const q = parameters(i, m, n);
    check(`Q(${i},${m},${n}): maxy = 4im-2m = 2r-2`, q.maxy === 4 * i * m - 2 * m && q.maxy === 2 * q.r - 2);
    check(`Q(${i},${m},${n}): maxx = 2r+s+m+n-3`, q.maxx === 2 * q.r + q.s + m + n - 3);
  }
}

console.log('\n  n >= 2 is required');
for (const n of [0, 1]) {
  let threw = false;
  try { Q(2, 2, n); } catch { threw = true; }
  check(`Q(2,2,${n}) is rejected`, threw);
}
check('Q(2,2,2) is accepted', (() => { try { Q(2, 2, 2); return true; } catch { return false; } })());

console.log('\n  the diagram is legal, and its picture is embedded');
{
  let cases = 0, connected = 0;
  for (let i = 1; i <= 4; i++) for (let m = 1; m <= 4; m++) for (let n = 2; n <= 5; n++) {
    const p = parameters(i, m, n);
    if (p.r < 1 || p.s < p.r) continue;
    cases++;
    const diagram = Q(i, m, n);
    const label = `Q(${i},${m},${n})`;
    check(`${label} validates`, diagram.validate().length === 0,
          JSON.stringify(diagram.validate().slice(0, 2)));
    check(`${label} has (maxx+1)+(maxy+1) arcs`,
          diagram.arcs.length === diagram.xCount + diagram.yCount);
    check(`${label} has m+n-2 dependent strands`,
          diagram.arcs.filter((a) => a.family === 'dependent').length === m + n - 2,
          `got ${diagram.arcs.filter((a) => a.family === 'dependent').length}`);
    const drawn = layout(diagram);
    check(`${label} draws without arc crossings`, findArcCrossings(drawn).length === 0);
    if (diagram.components().length === 1) connected++;
  }
  console.log(`        ${cases} parameter sets, beta connected in ${connected}`);
  check('beta is a single curve for every parameter set', connected === cases);
}

console.log('\n  a broken diagram is caught, not drawn');
{
  const bad = new HeegaardDiagram({
    name: 'crossing', xCount: 2, yCount: 0,
    arcs: [{ a: { side: 'bottom', index: 0 }, b: { side: 'top', index: 1 } },
           { a: { side: 'bottom', index: 1 }, b: { side: 'top', index: 0 } }]
  });
  check('interleaved chords are reported', bad.validate().some((p) => /must cross/.test(p.message)));
  const missing = new HeegaardDiagram({
    name: 'missing', xCount: 2, yCount: 0,
    arcs: [{ a: { side: 'bottom', index: 0 }, b: { side: 'top', index: 0 } }]
  });
  check('an unused slot is reported', missing.validate().some((p) => /nothing meets/.test(p.message)));
}

console.log('\n  the basepoint sits past the last arc in the top-left corner');
for (const [i, m, n] of [[2, 2, 2], [1, 1, 2], [3, 2, 2], [1, 2, 4]]) {
  const drawn = layout(Q(i, m, n));
  const { at, epsilon, cornerClearance } = drawn.basepoint;
  const label = `Q(${i},${m},${n})`;
  const reach = at[0] + (drawn.height - at[1]);
  check(`${label}: the basepoint is nearer the corner than any arc`, reach < cornerClearance,
        `basepoint at ${reach.toFixed(2)}, nearest arc at ${cornerClearance.toFixed(2)}`);
  check(`${label}: no arc enters the basepoint's corner triangle`,
        drawn.arcs.every((a) => a.path.every(([x, y]) => x + (drawn.height - y) > reach)));
  const normalised = [at[0] / drawn.width, at[1] / drawn.height];
  check(`${label}: normalised, the basepoint is (eps, 1-eps)`,
        Math.abs(normalised[0] - epsilon) < 1e-12 && Math.abs(normalised[1] - (1 - epsilon)) < 1e-12);
}

console.log('\n  beta lifts to the universal cover');
{
  const diagram = Q(2, 2, 2), drawn = layout(diagram);
  const track = liftBeta(diagram, drawn, { arcs: diagram.arcs.length * 3 });
  check('one node per arc, plus the far end', track.nodes.length === track.segments.length + 1);
  check('a circuit is the whole of beta', track.circuit === diagram.arcs.length);
  check('beta has a non-trivial homology class', track.period.some((v) => v !== 0),
        JSON.stringify(track.period));
  const forward = subTrack(track, 4, 11), backward = subTrack(track, 11, 4);
  check('going backwards reverses the same points',
        JSON.stringify(forward) === JSON.stringify([...backward].reverse()));
  check('a sub-arc starts and ends at its two nodes',
        JSON.stringify(forward[0]) === JSON.stringify(track.nodes[4].at) &&
        JSON.stringify(forward.at(-1)) === JSON.stringify(track.nodes[11].at));
  check('the extent covers every node',
        (() => { const [i0, j0, i1, j1] = tileExtent(track, 0);
          return track.nodes.every((v) => v.tile[0] >= i0 && v.tile[0] <= i1 && v.tile[1] >= j0 && v.tile[1] <= j1); })());
}

console.log('\n  pieces of beta are legal input to the grid solver');
{
  const diagram = Q(2, 2, 2), drawn = layout(diagram);
  const probe = liftBeta(diagram, drawn, { arcs: diagram.arcs.length * 2 });
  const first = tileExtent(probe, 1);
  const track = liftBeta(diagram, drawn, {
    arcs: diagram.arcs.length * 2, startTile: [1 - first[0], 1 - first[1]] });
  const extent = tileExtent(track, 1);
  const { settings } = gridSettingsFor(drawn, { extent });
  const scale = scaling(drawn);

  check('the basepoint is nearer its corner than beta ever gets to a lattice point',
        settings.epsForbidden * Math.SQRT2 < settings.minLatticeDistance);
  check('beta clears the lattice points by more than the solver demands',
        closestApproach(drawn).distance > settings.minLatticeDistance);

  let tried = 0, invalid = 0, solved = 0, disagreed = 0;
  for (let a = 0; a < track.nodes.length; a++)
    for (let b = a + 1; b < Math.min(a + 9, track.nodes.length); b++) {
      const piece = subTrack(track, a, b);
      if (!piece) continue;
      tried++;
      const arc = scale.pathToGrid(piece);
      const searched = solve(arc, { grid: settings, strategy: 'search' });
      const walked = solve(arc, { grid: settings, strategy: 'walk' });
      if (searched.status === 'invalid') invalid++;
      if (searched.status === 'solved') solved++;
      const key = (r) => r.solutions.map((x) => x.directions.join('')).sort().join('|');
      if (key(searched) !== key(walked)) disagreed++;
    }
  console.log(`        ${tried} pieces of beta, ${solved} bound a disc`);
  check('no piece of beta is rejected as invalid input', invalid === 0, `${invalid} rejected`);
  check('some pieces bound a disc', solved > 0);
  check("strategy 'walk' agrees with 'search' on beta too", disagreed === 0, `${disagreed} disagreed`);
}

console.log('\n  Reeb chords');
{
  const { composed, dictated } = REEB_CONVENTIONS;
  const turnOf = (table, chord) => Object.entries(table).find(([, v]) => v === chord)[0].split('>');
  // rho_12 must start where rho_1 starts and end where rho_2 ends, and likewise the others
  const composes = (table) => [['rho_12', 'rho_1', 'rho_2'], ['rho_23', 'rho_2', 'rho_3'],
                               ['rho_123', 'rho_1', 'rho_3']].every(([whole, first, last]) => {
    const [wIn, wOut] = turnOf(table, whole);
    return wIn === turnOf(table, first)[0] && wOut === turnOf(table, last)[1];
  });
  check('the default convention makes the composites compose', composes(composed));
  check('the dictated one does not, which is why it is not the default', !composes(dictated));
  check('the six turns are exactly the six permitted moves',
        new Set(Object.keys(composed)).size === 6 &&
        Object.keys(composed).every((t) => ['S>E', 'E>E', 'E>N', 'N>E', 'N>N', 'N>W'].includes(t)));
  check('a path reads off one chord per lattice point',
        reebChords(['S', 'E', 'N', 'N', 'W']).length === 4);
  check('S E N W reads P3P2P1', chordWord(reebChords(['S', 'E', 'N', 'W'])) === 'P3P2P1',
        chordWord(reebChords(['S', 'E', 'N', 'W'])));
  check('a path with no lattice point carries no chords', reebChords(['S']).length === 0);
  let threw = false;
  try { reebChords(['W', 'N']); } catch { threw = true; }
  check('a turn that cannot occur is rejected', threw);
}

console.log('\n  enumerating discs');
{
  const diagram = Q(1, 1, 2);
  const { discs, circuit, generators, tried } = enumerateDiscs(diagram);
  console.log(`        Q(1,1,2): ${tried} pieces tried, ${discs.length} discs`);
  check('every generator is a start point exactly once',
        generators.length === circuit && new Set(generators).size === circuit);
  check('some discs are found', discs.length > 0);
  const names = new Set(diagram.arcs.flatMap((a) => [a.a, a.b])
    .map((e) => `${e.side === 'left' || e.side === 'right' ? 'y' : 'x'}_${e.index}`));
  check('every source and target is a generator of the diagram',
        discs.every((d) => names.has(d.source) && names.has(d.target)));
  check('U is a non-negative integer', discs.every((d) => Number.isInteger(d.U) && d.U >= 0));
  check('the domain is correctly oriented', discs.every((d) => d.area < 0));
  check('chords match the path, one per lattice point',
        discs.every((d) => d.chords.length === d.directions.length - 1));
  check('the two ends never coincide', discs.every((d) => d.offset !== 0));
  const searched = enumerateDiscs(diagram, { strategy: 'search' });
  const walked = enumerateDiscs(diagram, { strategy: 'walk' });
  const key = (list) => list.map((d) => [d.source, d.target, d.offset, d.U, d.word].join('|')).sort().join('\n');
  check("strategy 'walk' finds the same discs as 'search'", key(searched.discs) === key(walked.discs));
}

console.log('\n  Q(i,2,2) against the conjectured arrow tables');
{
  for (const i of [1, 2, 3, 4]) {
    const arrows = conjecturedArrows(i);
    check(`i=${i}: the tables hold 64i-18 = ${conjecturedCount(i)} arrows`,
          arrows.length === conjecturedCount(i), `got ${arrows.length}`);
    const group = (name) => arrows.filter((a) => a.group === name).length;
    check(`i=${i}: 14 special, ${12 * i - 7} snail, ${52 * i - 25} family`,
          group('special') === 14 && group('snail') === 12 * i - 7 && group('family') === 52 * i - 25,
          `${group('special')}/${group('snail')}/${group('family')}`);
  }
  // the real check: the computed discs are the conjectured arrows, row for row
  for (const i of [1, 2]) {
    const computed = enumerateDiscs(Q(i, 2, 2)).discs
      .map((d) => [d.source, d.target, d.U, chordWord(d.chords)].join('|')).sort();
    const conjectured = conjecturedArrows(i)
      .map((a) => [a.source, a.target, a.U, a.word].join('|')).sort();
    check(`Q(${i},2,2): every disc is a conjectured arrow and back`,
          computed.length === conjectured.length &&
          computed.every((row, k) => row === conjectured[k]),
          `computed ${computed.length}, conjectured ${conjectured.length}`);
  }
}

console.log('\n  CSV output');
{
  const { discs } = enumerateDiscs(Q(1, 2, 2));
  const full = toCSV(discs), reference = toCSV(discs, { format: 'reference', sort: true });
  check('the full layout heads with its columns',
        full.split('\n')[0] === 'source,target,U,chords,offset,path');
  check('the reference layout matches the reference tables',
        reference.split('\n')[0] === 'source,target,annotation,U,P');
  check('one row per disc, plus the header',
        full.trim().split('\n').length === discs.length + 1 &&
        reference.trim().split('\n').length === discs.length + 1);
  check('U^0 is written as an empty column, U^1 as U',
        reference.includes(',U,U,') || reference.includes(',,,'),
        reference.split('\n')[1]);
  check('sorting is stable and total',
        toCSV(discs, { format: 'reference', sort: true }) === reference);
}

console.log('\n  extending a description equals rebuilding it');
{
  // The whole speed-up rests on this: appending an arc to a piece of beta must give exactly
  // what describing the longer piece from scratch gives.  Checked over every prefix, both
  // directions, on real tracks.
  const summarise = (d) => JSON.stringify({
    crossings: d.crossings.map((c) =>
      [c.p[0].toFixed(9), c.p[1].toFixed(9), c.edge, c.t.toFixed(9), c.segment, c.at.toFixed(9), c.kind]),
    cells: [...d.cells].map((c) => `${c.i},${c.j}`).sort(),
    subArcs: d.subArcs.map((a) => [a.cell.join(','), a.entry, a.exit, a.from.toFixed(9), a.to.toFixed(9)]),
    blocked: [...d.blockedEdges].sort(),
    candidate: [...d.candidateEdges].sort()
  });

  let prefixes = 0, disagreed = 0, lookupsChecked = 0, lookupsWrong = 0;
  for (const params of [[1, 2, 2], [2, 2, 2], [1, 3, 2], [2, 3, 5]]) {
    const diagram = Q(...params), circuit = diagram.components()[0].length;
    const drawn = layout(diagram, { cell: 26, samples: 4 });
    const probe = liftBeta(diagram, drawn, { arcs: circuit * 3 + 1 });
    const [i0, j0] = tileExtent(probe, 1);
    const track = liftBeta(diagram, drawn, { arcs: circuit * 3 + 1, startTile: [1 - i0, 1 - j0] });
    const { settings } = gridSettingsFor(drawn, { extent: tileExtent(track, 1) });
    const scale = scaling(drawn);

    for (const direction of [1, -1]) {
      const builder = new ArcDescriptionBuilder(settings);
      for (let step = 1; step <= Math.min(circuit, 40); step++) {
        const piece = scale.pathToGrid(subTrack(track, circuit, circuit + direction * step));
        builder.append(builder.arc.length ? piece.slice(builder.arc.length - 1) : piece);
        const scratch = describeArc(piece, { grid: settings, assumeValid: true });
        prefixes++;
        if (summarise(builder.description) !== summarise(scratch)) disagreed++;
        // and the by-edge index must answer what a scan of the crossings would
        const lookup = builder.description.crossingsByEdge;
        for (const edge of new Set(scratch.crossings.map((c) => c.edge))) {
          lookupsChecked++;
          const byIndex = (lookup.get(edge) ?? []).length;
          const byScan = scratch.crossings.filter((c) => c.edge === edge).length;
          if (byIndex !== byScan) lookupsWrong++;
        }
      }
    }
  }
  console.log(`        ${prefixes} prefixes, ${lookupsChecked} edge lookups`);
  check('an extended description equals one built from scratch', disagreed === 0,
        `${disagreed} of ${prefixes} disagreed`);
  check('the by-edge index answers what a scan would', lookupsWrong === 0,
        `${lookupsWrong} of ${lookupsChecked} wrong`);

  let threw = false;
  try { new ArcDescriptionBuilder().append([[3, 3.5], [3.5, 4]]).append([[9, 9.5], [9.5, 10]]); }
  catch { threw = true; }
  check('appending points that do not join on is refused', threw);
}

console.log('\n  the Heegaard-aware engine agrees with the generic one');
{
  // The fast engine looks a piece's description up in tables instead of rediscovering it from
  // the geometry.  Everything downstream is shared, so the two must give the same discs.
  for (const params of [[1, 2, 2], [2, 2, 2], [1, 3, 2], [2, 3, 5]]) {
    const key = (list) => list
      .map((d) => [d.source, d.target, d.U, d.word, d.offset].join('|')).sort().join('\n');
    const generic = enumerateDiscs(Q(...params), { engine: 'generic' });
    const fast = enumerateDiscs(Q(...params), { engine: 'heegaard' });
    check(`Q(${params}): both engines find the same discs`, key(generic.discs) === key(fast.discs),
          `${generic.discs.length} vs ${fast.discs.length}`);
    check(`Q(${params}): and try the same number of pieces`, generic.tried === fast.tried);
  }
}

console.log('\n  the file formats');
{
  for (const params of [[1, 2, 2], [2, 2, 2], [2, 3, 5], [1, 5, 5]]) {
    const original = Q(...params);
    const { diagram } = diagramFromCSV(diagramToCSV(original, { cell: 26 }));
    const label = `Q(${params})`;
    check(`${label}: arcs survive the round trip`,
          JSON.stringify(original.arcs) === JSON.stringify(diagram.arcs));
    check(`${label}: counts and basepoints survive`,
          original.xCount === diagram.xCount && original.yCount === diagram.yCount &&
          JSON.stringify(original.basepoints) === JSON.stringify(diagram.basepoints));
    check(`${label}: the reloaded diagram bounds the same discs`,
          enumerateDiscs(diagram).discs.length === enumerateDiscs(original).discs.length);
  }

  const text = diagramToCSV(Q(2, 2, 2));
  check('the header names the format', text.startsWith(`# ${DIAGRAM_FORMAT}`));
  check('every metadata line is a comment',
        text.split('\n').filter((l) => l && !l.startsWith('#'))
            .every((l) => l.split(',').length === 5));
  check('no field needs quoting', !text.includes('"'));
  check('counts are inferred when not stated',
        diagramFromCSV(text.split('\n').filter((l) => !l.startsWith('# x-generators'))
          .join('\n')).diagram.xCount === 30);

  const refuses = (bad, why) => {
    let threw = false;
    try { diagramFromCSV(bad); } catch { threw = true; }
    check(`a file with ${why} is refused`, threw);
  };
  refuses('# heegaard-diagram 99\nside_a,index_a,side_b,index_b\ntop,0,bottom,0\n', 'the wrong version');
  refuses(`# ${DIAGRAM_FORMAT}\nside_a,index_a,side_b,index_b\nsideways,0,bottom,0\n`, 'a bad side');
  refuses(`# ${DIAGRAM_FORMAT}\nside_a,index_a,side_b,index_b\ntop,0,bottom,1\n`, 'arcs that do not close up');

  const discs = enumerateDiscs(Q(2, 2, 2)).discs;
  const back = discsFromCSV(discsToCSV(discs, { diagram: Q(2, 2, 2) })).discs;
  check('the disc list round trips', back.length === discs.length);
  const withChords = back.find((d) => d.chords.length);
  check('chords are parsed back into rho names',
        withChords && withChords.chords.every((c) => c.startsWith('rho_')),
        JSON.stringify(withChords?.chords));
  check('U powers and paths survive',
        back.every((d) => Number.isInteger(d.U) && Array.isArray(d.directions)));
}

console.log('\n  the disc atlas');
{
  const enumeration = enumerateDiscs(Q(1, 2, 2), { cell: 11, samples: 16, keepRegions: true });
  check('regions are kept when asked for', enumeration.discs.every((d) => d.polygon));
  check('regions are dropped otherwise',
        enumerateDiscs(Q(1, 2, 2)).discs.every((d) => d.polygon === undefined));

  const boxes = enumeration.discs.map((d) => boundingBox(d.polygon));
  const shifts = packIntoSlots(boxes, 0, 2);
  check('every disc is slid by a whole number of copies',
        shifts.every(([dx, dy]) => Number.isInteger(dx) && Number.isInteger(dy)));
  const moved = boxes.map((b, k) => [b[0] + shifts[k][0], b[1] + shifts[k][1],
                                     b[2] + shifts[k][0], b[3] + shifts[k][1]]);
  let overlaps = 0;
  for (let a = 0; a < moved.length; a++) for (let b = a + 1; b < moved.length; b++) {
    const [p, q] = [moved[a], moved[b]];
    if (p[0] < q[2] - 1e-9 && q[0] < p[2] - 1e-9 && p[1] < q[3] - 1e-9 && q[1] < p[3] - 1e-9) overlaps++;
  }
  check('packed discs do not overlap', overlaps === 0, `${overlaps} overlapping pairs`);

  const svg = discAtlas(enumeration);
  check('the atlas is an svg', svg.startsWith('<svg') && svg.trimEnd().endsWith('</svg>'));
  check('one filled region per disc',
        (svg.match(/<polygon /g) ?? []).length === enumeration.discs.length,
        `${(svg.match(/<polygon /g) ?? []).length} polygons for ${enumeration.discs.length} discs`);
  check('beta is written once and reused',
        svg.includes('<defs>') && (svg.match(/<use /g) ?? []).length > 1);
  let threw = false;
  try { discAtlas(enumerateDiscs(Q(1, 2, 2))); } catch { threw = true; }
  check('an atlas without regions is refused', threw);
}

console.log('\n  rendering');
{
  const drawn = layout(Q(2, 2, 2));
  const single = renderDiagram(drawn), cover = renderUniversalCover(drawn, { tiles: 3 });
  for (const [name, svg] of [['diagram', single], ['universal cover', cover]]) {
    check(`${name} is an svg`, svg.startsWith('<svg') && svg.trimEnd().endsWith('</svg>'));
    check(`${name} uses the pale red grid`, svg.includes('#f0b9b9'));
    check(`${name} uses the pale blue arc colour`, svg.includes('#7ea6ec'));
  }
  check('the cover repeats every arc in every tile',
        (cover.match(/<path /g) ?? []).length === 43 * 9,
        `got ${(cover.match(/<path /g) ?? []).length}`);
}

console.log(`\n  ${passed} passed, ${failed} failed\n`);
process.exit(failed ? 1 : 0);
