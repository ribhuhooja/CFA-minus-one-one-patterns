/**
 * Appendix A: the conjectured local rules.  NON-NORMATIVE.
 *
 * These constrain the next step purely from the incoming direction plus what the arc does
 * near the lattice point.  Correctness of the solver never depends on them: `solve` runs
 * the global (P1)-(P4) check on whatever comes out, and the harness asserts the answer is
 * the same with the rules on and off.
 *
 * IMPORTANT SCOPE.  The table governs steps *between lattice points* only.  It does not
 * govern the first partial edge (x_s -> v_s) or the final partial edge (v_e -> x_e); both
 * are fixed by §5 instead, and either of them may legitimately run S or W.
 */
import { edgeKey } from './grid.js';

/** Permitted next steps, keyed by the direction of arrival at the lattice point. */
export const STEP_TABLE = Object.freeze({
  W: Object.freeze([]),
  S: Object.freeze(['E']),
  E: Object.freeze(['E', 'N']),
  N: Object.freeze(['E', 'N', 'W'])
});

/**
 * Queries about the arc that the shielding rules need.  Built once per arc.
 * @param {import('./arc.js').ArcDescription} description
 */
export function shieldingContext(description) {
  const bySubArcCell = new Map();
  for (const s of description.subArcs) {
    const key = `${s.cell[0]},${s.cell[1]}`;
    if (!bySubArcCell.has(key)) bySubArcCell.set(key, []);
    bySubArcCell.get(key).push(s);
  }
  return {
    /** does the arc cross this edge at all? */
    crossesEdge: (key) => description.blockedEdges.has(key),
    /** does some sub-arc of the arc in C(i,j) join these two sides (in either order)? */
    cellJoinsSides: (i, j, a, b) => {
      const list = bySubArcCell.get(`${i},${j}`);
      if (!list) return false;
      return list.some((s) => (s.entry === a && s.exit === b) || (s.entry === b && s.exit === a));
    }
  };
}

/**
 * Would Appendix A permit stepping `to` out of lattice point `v`, having arrived along `from`?
 * @param {?string} from  null at a point with no incoming lattice step (never happens in practice)
 * @param {string} to
 * @param {number[]} v
 * @param {ReturnType<shieldingContext>} ctx
 * @param {{strict?: boolean}} [options] `strict` adds the extra rule stated in the original
 *        prompt but omitted from Appendix A of the refined spec.
 * @returns {{allowed: boolean, rule: ?string}}
 */
export function localVerdict(from, to, v, ctx, { strict = false } = {}) {
  if (from === null) return { allowed: true, rule: null };

  if (!STEP_TABLE[from].includes(to))
    return { allowed: false, rule: `table: arriving ${from} permits only {${STEP_TABLE[from].join(',')}}` };

  // Every rule below says the same thing: the arc must shield the step from the forbidden
  // point of the cell the step would otherwise expose.
  if (from === 'E' && to === 'E' && !ctx.crossesEdge(edgeKey(v, 'N')))
    return { allowed: false, rule: 'arriving E, step E needs the arc to cross the N edge at v' };

  if (from === 'N' && to === 'E' && !ctx.crossesEdge(edgeKey(v, 'N')))
    return { allowed: false, rule: 'arriving N, step E needs the arc to cross the N edge at v' };

  if (from === 'N' && to === 'N' &&
      !(ctx.cellJoinsSides(v[0] - 1, v[1], 'S', 'N') || ctx.cellJoinsSides(v[0] - 1, v[1], 'W', 'N')))
    return { allowed: false, rule: 'arriving N, step N needs an arc S-N or W-N in the cell NW of v' };

  if (from === 'N' && to === 'W' && !ctx.crossesEdge(edgeKey(v, 'W')))
    return { allowed: false, rule: 'arriving N, step W needs the arc to cross the W edge at v' };

  if (strict && from === 'S' && to === 'E' && !ctx.crossesEdge(edgeKey(v, 'N')))
    return { allowed: false, rule: 'strict: arriving S, step E needs the arc to cross the N edge at v' };

  return { allowed: true, rule: null };
}
