/**
 * Finding candidate paths from v_s to v_e.  Two strategies:
 *
 *   enumeratePaths  exhaustive DFS over the candidate graph.  The reference: makes no use
 *                   of Appendix A unless asked, so it can contradict it.
 *   walkPath        the deterministic Appendix A walk.  O(path length), no backtracking.
 *
 * Neither decides anything: both hand their candidates to constraints.checkPath.
 */
import { DIRECTION_NAMES, edgeKey, stepFrom, latticeKey } from './grid.js';
import { localVerdict } from './rules.js';

const MAX_DFS_STEPS = 2_000_000;
const MAX_TRACE = 20_000;

/** @typedef {{dir:string, edge:string, blocked:boolean, revisit:boolean, allowed:boolean, rule:?string}} Option */
/** @typedef {{v:number[], from:?string, options:Option[], geometricCount:number, localCount:number, forced:boolean}} Decision */

/** What could happen at `v`, arriving along `from`, and why each option is or is not open. */
function optionsAt(v, from, { candidateEdges, blockedEdges }, visited, ctx, ruleOptions) {
  const options = [];
  for (const dir of DIRECTION_NAMES) {
    const edge = edgeKey(v, dir);
    if (!candidateEdges.has(edge)) continue;           // outside the §6 search space
    const blocked = blockedEdges.has(edge);
    const revisit = visited.has(latticeKey(stepFrom(v, dir)));
    const { allowed, rule } = localVerdict(from, dir, v, ctx, ruleOptions);
    options.push({ dir, edge, blocked, revisit, allowed, rule });
  }
  return options;
}

const geometricallyOpen = (o) => !o.blocked && !o.revisit;

function summarise(v, from, options, useRules) {
  const open = options.filter((o) => geometricallyOpen(o) && (!useRules || o.allowed));
  return {
    v: v.slice(), from, options,
    geometricCount: options.filter(geometricallyOpen).length,
    localCount: options.filter((o) => geometricallyOpen(o) && o.allowed).length,
    forced: open.length === 1,
    open: open.map((o) => o.dir)
  };
}

/**
 * All simple paths from v_s to v_e in the candidate graph.
 * @returns {{paths: {lattice:number[][], decisions:Decision[]}[], trace:Object[], stats:Object}}
 */
export function enumeratePaths(description, endpoints, {
  useRules = false, ruleOptions = {}, ctx, recordDecisions = false, recordTrace = false,
  maxPaths = 1000, maxPathLength
} = {}) {
  const paths = [], trace = [], stats = { steps: 0, truncated: false };
  const target = latticeKey(endpoints.ve);
  const limit = maxPathLength ?? 4 * description.cells.length + 8;

  const visited = new Set([latticeKey(endpoints.vs)]);
  const lattice = [endpoints.vs];
  const decisions = [];
  const push = (event) => { if (recordTrace && trace.length < MAX_TRACE) trace.push(event); };

  const visit = (v, from) => {
    if (paths.length >= maxPaths || stats.steps > MAX_DFS_STEPS) { stats.truncated = true; return; }
    stats.steps++;
    if (lattice.length > limit) return;

    const options = optionsAt(v, from, description, visited, ctx, ruleOptions);
    const decision = summarise(v, from, options, useRules);
    decisions.push(decision);

    for (const dir of decision.open) {
      const next = stepFrom(v, dir);
      push({ type: 'step', from: v.slice(), dir, to: next.slice(), depth: lattice.length });
      if (latticeKey(next) === target) {
        paths.push({
          lattice: [...lattice.map((p) => p.slice()), next.slice()],
          decisions: recordDecisions ? decisions.map(cloneDecision) : []
        });
        push({ type: 'reach', at: next.slice(), depth: lattice.length + 1 });
        continue;                                        // (P1): v_e is terminal
      }
      visited.add(latticeKey(next));
      lattice.push(next);
      visit(next, dir);
      lattice.pop();
      visited.delete(latticeKey(next));
      push({ type: 'backtrack', at: next.slice(), depth: lattice.length });
    }
    decisions.pop();
  };
  visit(endpoints.vs, endpoints.first);

  return { paths, trace, stats };
}

/**
 * The deterministic Appendix A walk: at each lattice point take the single open step.
 *
 * @returns {{lattice:?number[][], decisions:Decision[], status:'reached'|'stuck'|'ambiguous'|'overlong', at:?number[], options:?string[]}}
 *   'stuck'     no step is open -- with the conjecture, that means no solution exists
 *   'ambiguous' more than one step is open -- the conjecture has failed for this arc
 */
export function walkPath(description, endpoints, {
  ruleOptions = {}, ctx, recordDecisions = false, maxPathLength
} = {}) {
  const target = latticeKey(endpoints.ve);
  const limit = maxPathLength ?? 4 * description.cells.length + 8;
  const visited = new Set([latticeKey(endpoints.vs)]);
  const lattice = [endpoints.vs];
  const decisions = [];

  let v = endpoints.vs, from = endpoints.first;
  while (latticeKey(v) !== target) {
    if (lattice.length > limit)
      return { lattice: null, decisions, status: 'overlong', at: v, options: null };

    const options = optionsAt(v, from, description, visited, ctx, ruleOptions);
    const decision = summarise(v, from, options, true);
    if (recordDecisions) decisions.push(decision);

    if (decision.open.length === 0)
      return { lattice: null, decisions, status: 'stuck', at: v, options: [] };
    if (decision.open.length > 1)
      return { lattice: null, decisions, status: 'ambiguous', at: v, options: decision.open };

    from = decision.open[0];
    v = stepFrom(v, from);
    visited.add(latticeKey(v));
    lattice.push(v);
  }
  return { lattice, decisions, status: 'reached', at: null, options: null };
}

function cloneDecision(d) {
  return { ...d, v: d.v.slice(), options: d.options.map((o) => ({ ...o })) };
}
