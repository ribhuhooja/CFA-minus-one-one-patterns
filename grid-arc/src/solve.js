/**
 * The solver.  Give it an arc, get back every path satisfying (P1)-(P4), or a reason why
 * there is none.
 *
 * Three strategies, same answer:
 *   'walk'    THE DEFAULT.  The deterministic Appendix A walk produces at most one candidate,
 *             then the global check runs once.  Linear in the length of the path, no
 *             backtracking.  The local rules never miss a solution -- across every study run
 *             so far they have never discarded one -- and the global check is what decides,
 *             so the walk cannot return a wrong answer, only fail to find one.  Nothing has
 *             ever been found that it fails to find.
 *   'search'  exhaustive DFS over the §6 candidate graph, then the global check on each
 *             candidate.  Makes no use of Appendix A unless `useRules` is set.  The reference
 *             the walk is checked against, and the only strategy that fills in `trace`.
 *   'verify'  run both and report whether they agreed (`result.agreement`).
 */
import { describeArc } from './arc.js';
import { endpointConditions, crossingStrictlyBetween, partialEdgeSpans } from './endpoints.js';
import { shieldingContext } from './rules.js';
import { checkPath } from './constraints.js';
import { enumeratePaths, walkPath } from './search.js';
import { directionsAlong, latticeKey } from './grid.js';

/**
 * @typedef {Object} Solution
 * @property {number[][]} points        x_s, lattice points..., x_e
 * @property {string[]} directions      e.g. ['E','N','N','W']
 * @property {string} kind              'search'|'walk'|'single-lattice-point'|'same-edge'
 * @property {{polygon:number[][], area:number, forbiddenInside:Object[]}} region
 * @property {Object[]} decisions       empty unless `decisions:true`
 * @property {Object[]} failures        empty for solutions, populated for rejected candidates
 */

/**
 * @typedef {Object} Result
 * @property {'invalid'|'solved'|'no-solution'} status
 * @property {?string} reason
 * @property {import('./arc.js').Problem[]} problems
 * @property {import('./arc.js').ArcDescription} arc
 * @property {?import('./endpoints.js').Endpoints} endpoints
 * @property {Solution[]} solutions
 * @property {Solution[]} rejected      candidates that reached v_e but failed (P1)-(P4)
 * @property {?Object} blocker          the crossing that blocks a forced partial edge
 * @property {Object[]} trace           empty unless `trace:true`
 * @property {Object} stats
 */

const DEFAULTS = {
  strategy: 'walk',     // 'walk' | 'search' | 'verify' -- see the note above
  useRules: false,      // apply Appendix A while searching (ignored by 'walk', which is the rules)
  strictRule: false,    // add the extra rule from the original prompt
  decisions: false,     // record the per-lattice-point decision log
  trace: false,         // record the DFS trace, for stepping through the search
  maxSolutions: 1000,
  grid: undefined,      // override the grid constants (see gridSettings); undefined = defaults
  assumeSimple: false,  // skip the quadratic self-intersection test; see validateArc
  assumeValid: false,   // skip §2 entirely -- only for a sub-arc of an already-checked curve
  description: undefined, // a prebuilt ArcDescription, e.g. from an ArcDescriptionBuilder
  searchSpace: 'cells', // 'bbox' widens it, to test the §6 lemma
  bboxPad: 2,
  maxPathLength: undefined
};

/**
 * @param {number[][]} arc polyline from x_s to x_e, in mathematical coordinates
 * @param {Partial<typeof DEFAULTS>} [options]
 * @returns {Result}
 */
export function solve(arc, options = {}) {
  const opts = { ...DEFAULTS, ...options };
  const description = opts.description ?? describeArc(arc.map((p) => [p[0], p[1]]), opts);
  const points = description.arc;

  const result = {
    status: 'invalid', reason: null, problems: description.problems,
    arc: description, endpoints: null, solutions: [], rejected: [],
    blocker: null, trace: [], stats: {}
  };
  if (description.problems.length) return result;

  const endpoints = endpointConditions(points);
  result.endpoints = endpoints;

  // Building this walks every sub-arc, so leave it until something is actually going to be
  // searched: four fifths of all solves stop at the blocked-partial-edge test below.
  let shielding = null;
  const ctx = () => (shielding ??= shieldingContext(description));
  const ruleOptions = { strict: opts.strictRule };
  const spans = partialEdgeSpans(endpoints);
  const { crossings } = description;

  // §5: either forced partial edge being crossed rules out the general search.  It does not
  // rule out the same-edge candidate below, where x_e is itself the "blocking" crossing.
  // only the crossings on that one edge can possibly lie inside the span
  const onEdgeS = description.crossingsByEdge?.get(endpoints.edgeS) ?? crossings;
  const onEdgeE = description.crossingsByEdge?.get(endpoints.edgeE) ?? crossings;
  const blockedStart = crossingStrictlyBetween(endpoints.edgeS, ...spans.start, onEdgeS);
  const blockedEnd = crossingStrictlyBetween(endpoints.edgeE, ...spans.end, onEdgeE);
  if (blockedStart || blockedEnd) {
    result.blocker = blockedStart ?? blockedEnd;
    result.reason = blockedStart
      ? `the forced first partial edge (x_s → v_s, ${endpoints.first}) is crossed by the arc`
      : `the forced final partial edge (v_e → x_e, ${endpoints.last}) is crossed by the arc`;
  }

  const candidates = [...degenerateCandidates(endpoints, spans, onEdgeS)];

  let searchStats = { steps: 0, truncated: false };
  if (!blockedStart && !blockedEnd && latticeKey(endpoints.vs) !== latticeKey(endpoints.ve)) {
    const shared = { ctx: ctx(), ruleOptions, recordDecisions: opts.decisions,
                     maxPathLength: opts.maxPathLength };

    if (opts.strategy === 'walk' || opts.strategy === 'verify') {
      const walk = walkPath(description, endpoints, shared);
      result.walk = { status: walk.status, at: walk.at, options: walk.options };
      if (walk.lattice)
        candidates.push({
          points: [endpoints.xs, ...walk.lattice, endpoints.xe],
          kind: 'walk', decisions: walk.decisions
        });
      else if (!result.reason)
        result.reason = walk.status === 'stuck'
          ? `the Appendix A walk has no legal step at (${walk.at})`
          : `the Appendix A walk ended '${walk.status}'`;
    }

    if (opts.strategy === 'search' || opts.strategy === 'verify') {
      const enumerated = enumeratePaths(description, endpoints, {
        ...shared, useRules: opts.useRules, recordTrace: opts.trace, maxPaths: opts.maxSolutions * 4
      });
      searchStats = enumerated.stats;
      result.trace = enumerated.trace;
      for (const p of enumerated.paths)
        candidates.push({
          points: [endpoints.xs, ...p.lattice, endpoints.xe],
          kind: 'search', decisions: p.decisions
        });
    }
  }

  if (opts.strategy === 'verify') result.agreement = compareStrategies(candidates);

  for (const candidate of dedupe(candidates)) {
    const check = checkPath(candidate.points, description);
    const entry = {
      points: candidate.points,
      directions: directionsAlong(candidate.points),
      kind: candidate.kind,
      region: { polygon: check.polygon, area: check.area, forbiddenInside: check.forbiddenInside },
      decisions: candidate.decisions ?? [],
      failures: check.failures
    };
    (check.ok ? result.solutions : result.rejected).push(entry);
    if (result.solutions.length >= opts.maxSolutions) break;
  }

  result.stats = { ...searchStats, candidates: candidates.length };
  result.status = result.solutions.length ? 'solved' : 'no-solution';
  if (result.solutions.length) { result.reason = null; result.blocker = null; }
  else if (!result.reason)
    result.reason = candidates.length
      ? `all ${candidates.length} grid paths from v_s to v_e fail (P1)-(P4)`
      : 'no grid path from v_s to v_e exists in the candidate graph';
  return result;
}

/**
 * The two shapes §5 singles out, neither of which involves a search.  Both are validated
 * against (P1)-(P4) like any other candidate.
 */
function* degenerateCandidates(endpoints, spans, onStartEdge) {
  const { xs, xe, vs, ve, edgeS, edgeE, first } = endpoints;

  // x_s and x_e on the same edge, with the forced direction pointing from one to the other
  // and no lattice point in between: the sub-segment alone is a candidate.
  if (edgeS === edgeE) {
    const [tStart] = spans.start, tEnd = spans.end[1];
    const forward = (first === 'E' || first === 'N') ? 1 : -1;
    const noLatticeBetween = Math.floor(Math.min(tStart, tEnd)) === Math.floor(Math.max(tStart, tEnd));
    if ((tEnd - tStart) * forward > 0 && noLatticeBetween &&
        !crossingStrictlyBetween(edgeS, tStart, tEnd, onStartEdge))
      yield { points: [xs, xe], kind: 'same-edge', decisions: [] };
  }

  if (latticeKey(vs) === latticeKey(ve))
    yield { points: [xs, vs, xe], kind: 'single-lattice-point', decisions: [] };
}

const candidateKey = (c) => c.points.map((p) => `${p[0].toFixed(6)},${p[1].toFixed(6)}`).join(' ');

/** Two strategies can produce the same path; report it once, tagged with both. */
function dedupe(candidates) {
  const seen = new Map();
  for (const candidate of candidates) {
    const key = candidateKey(candidate);
    const existing = seen.get(key);
    if (!existing) { seen.set(key, { ...candidate }); continue; }
    if (!existing.kind.split('+').includes(candidate.kind)) existing.kind += `+${candidate.kind}`;
    if (!existing.decisions?.length && candidate.decisions?.length) existing.decisions = candidate.decisions;
  }
  return [...seen.values()];
}

/** Did the local walk and the exhaustive search reach the same candidates? */
function compareStrategies(candidates) {
  const fromWalk = new Set(candidates.filter((c) => c.kind === 'walk').map(candidateKey));
  const fromSearch = new Set(candidates.filter((c) => c.kind === 'search').map(candidateKey));
  if (!fromWalk.size && !fromSearch.size) return { compared: false, agree: true };
  // The search may legitimately reach candidates the walk prunes; those must all fail the
  // global check, which the caller sees.  Agreement means: the walk's answer, if any, is
  // one the search also found, and the walk did not miss a path the search alone accepted.
  const agree = [...fromWalk].every((k) => fromSearch.has(k));
  return { compared: true, agree, walk: [...fromWalk], search: [...fromSearch] };
}
