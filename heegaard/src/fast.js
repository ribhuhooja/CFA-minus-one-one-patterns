/**
 * A solver that knows it is looking at a Heegaard diagram.
 *
 * The general solver takes an arbitrary curve and rediscovers where it meets the grid by
 * root-finding along every segment.  For a piece of beta none of that is unknown:
 *
 *   - beta meets the alpha curves exactly at the generators, so a piece of k arcs has exactly
 *     k+1 crossings and they are the track's nodes.  (Checked 480/480 against the general
 *     solver before this module was written.)
 *   - which alpha edge a crossing lies on, and where along it, follows from the generator's
 *     side and index -- no geometry.
 *   - after normalising, one copy of the fundamental domain IS one unit cell of the grid, so
 *     every arc of the diagram lies in exactly one cell: its own tile.
 *
 * So the description of a piece is a slice of precomputed tables, and §2 validation has
 * nothing to check.  What is left geometric is the final (P1)-(P4) test on a completed
 * candidate, which still needs the polyline; that runs for a small minority of pieces and is
 * deliberately left alone here so this stays comparable to the general solver.
 */
import { GLUED_SIDE } from './diagram.js';

/** Which side of the unit cell a generator on this side of the domain sits on. */
const CELL_SIDE = { bottom: 'S', top: 'N', left: 'W', right: 'E' };

/**
 * Everything about the lifted track that can be worked out once.
 * @param {import('./diagram.js').HeegaardDiagram} diagram
 * @param {import('./track.js').Track} track
 */
export function tabulate(diagram, track) {
  const { xCount, yCount } = diagram;

  // per node: the alpha edge it lies on, where along it, and the point itself
  const nodes = track.nodes.map((node) => {
    const [a, b] = node.tile;
    const along = (node.index + 0.5);
    switch (node.side) {
      case 'bottom': return { edge: `H:${a}:${b}`,     t: along / xCount, p: [a + along / xCount, b] };
      case 'top':    return { edge: `H:${a}:${b + 1}`, t: along / xCount, p: [a + along / xCount, b + 1] };
      case 'left':   return { edge: `V:${a}:${b}`,     t: 1 - along / yCount, p: [a, b + 1 - along / yCount] };
      default:       return { edge: `V:${a + 1}:${b}`, t: 1 - along / yCount, p: [a + 1, b + 1 - along / yCount] };
    }
  });

  // per segment: the cell it lies in (its tile) and which sides it enters and leaves by
  const segments = track.segments.map((_, k) => {
    const [i, j] = track.nodes[k].tile;
    return {
      cell: { i, j },
      edges: [`H:${i}:${j}`, `H:${i}:${j + 1}`, `V:${i}:${j}`, `V:${i + 1}:${j}`],
      entry: CELL_SIDE[track.nodes[k].side],
      exit: CELL_SIDE[GLUED_SIDE[track.nodes[k + 1].side]]
    };
  });

  return { nodes, segments };
}

/**
 * Build up the description of a piece of beta one arc at a time.  Same shape as
 * grid-arc's ArcDescription, so `solve({ description })` takes it unchanged.
 */
export class PieceBuilder {
  /**
   * @param {ReturnType<tabulate>} tables
   * @param {Object} settings resolved grid settings
   * @param {(k:number)=>number[][]} pointsOf  the polyline of track segment k, already normalised
   */
  constructor(tables, settings, pointsOf) {
    this.tables = tables;
    this.settings = settings;
    this.pointsOf = pointsOf;
    this.reset();
  }

  reset(startNode = 0, direction = 1) {
    this.startNode = startNode;
    this.direction = direction;
    this.steps = 0;
    this.arc = [];
    this.cells = new Map();
    this.blockedEdges = new Set();
    this.byEdge = new Map();
    this.candidateEdges = new Set();
    this.crossings = [];
    this.cellList = [];
    this.subArcs = [];
    this.#addCrossing(startNode, 'start');
    return this;
  }

  #addCrossing(node, kind) {
    const info = this.tables.nodes[node];
    const record = { p: info.p, edge: info.edge, t: info.t, segment: this.steps, at: this.steps, kind };
    this.crossings.push(record);
    this.blockedEdges.add(info.edge);
    const on = this.byEdge.get(info.edge);
    if (on) on.push(record); else this.byEdge.set(info.edge, [record]);
    return record;
  }

  /** Extend the piece by one arc of beta. */
  extend() {
    const segment = this.direction > 0 ? this.startNode + this.steps
                                       : this.startNode - this.steps - 1;
    if (segment < 0 || segment >= this.tables.segments.length) return false;

    const points = this.pointsOf(segment, this.direction);
    if (this.arc.length) this.arc.push(...points.slice(1)); else this.arc.push(...points);

    const info = this.tables.segments[segment];
    const cellKey = `${info.cell.i},${info.cell.j}`;
    if (!this.cells.has(cellKey)) {
      this.cells.set(cellKey, info.cell);
      this.cellList.push(info.cell);
      for (const edge of info.edges) this.candidateEdges.add(edge);
    }
    const [entry, exit] = this.direction > 0 ? [info.entry, info.exit] : [info.exit, info.entry];
    this.subArcs.push({ cell: [info.cell.i, info.cell.j], entry, exit,
                        from: this.steps, to: this.steps + 1 });

    this.steps++;
    const far = this.direction > 0 ? this.startNode + this.steps : this.startNode - this.steps;
    // the crossing that was the end is now interior; the new far node is the end
    if (this.crossings.length > 1) this.crossings.at(-1).kind = 'interior';
    this.#addCrossing(far, 'end');
    return true;
  }

  get description() {
    return {
      arc: this.arc,
      settings: this.settings,
      problems: [],
      crossings: this.crossings,
      cells: this.cellList,
      subArcs: this.subArcs,
      blockedEdges: this.blockedEdges,
      crossingsByEdge: this.byEdge,
      candidateEdges: this.candidateEdges
    };
  }
}
