/**
 * Text formats for a diagram and for the discs it bounds.
 *
 * These are the boundary of the project: a solver, a visualiser, a drawing app and a
 * generator only have to agree on these two files, and can then be written in any language
 * and replaced independently.  So the rules are deliberately dull.
 *
 *   - CSV body, one header row, comma separated, no quoting (no field ever contains a comma).
 *   - Metadata as `# key: value` lines above the body.  `pandas.read_csv(f, comment='#')`
 *     reads the body and ignores them; so does every other CSV reader worth using.
 *   - Combinatorics only.  A diagram is its arcs; where they are drawn is a rendering
 *     decision, recomputed from the combinatorics by `layout`.  `cell` is carried as a hint
 *     and nothing depends on it.
 *
 * A generator is `x_j` or `y_j`: `x` for the alpha curve the bottom and top edges glue into,
 * `y` for the one the left and right edges glue into.  An arc endpoint names the *edge* it
 * sits on -- bottom, top, left or right -- because bottom and top are the same alpha curve
 * but different sides of the domain, and a diagram has to say which.
 */
import { HeegaardDiagram, SIDES, GENERATOR_OF_SIDE } from './diagram.js';

export const DIAGRAM_FORMAT = 'heegaard-diagram 1';
export const DISCS_FORMAT = 'heegaard-discs 1';

const meta = (key, value) => `# ${key}: ${value}\n`;

/** Split a file into its `# key: value` metadata and its CSV body. */
function split(text, expected) {
  const info = {}, body = [];
  for (const raw of text.split('\n')) {
    const line = raw.trim();
    if (!line) continue;
    if (!line.startsWith('#')) { body.push(line); continue; }
    const stripped = line.slice(1).trim(), at = stripped.indexOf(':');
    if (at < 0) { info.format = stripped; continue; }
    const key = stripped.slice(0, at).trim(), value = stripped.slice(at + 1).trim();
    if (key === 'basepoint') (info.basepoints ??= []).push(value);
    else info[key] = value;
  }
  if (info.format && info.format !== expected)
    throw new Error(`this file says "${info.format}", expected "${expected}"`);
  if (!body.length) throw new Error('the file has no table in it');
  const columns = body.shift().split(',').map((c) => c.trim());
  return { info, columns, body, at: (name) => columns.indexOf(name) };
}

/** @param {HeegaardDiagram} diagram @param {{cell?:number}} [options] @returns {string} */
export function diagramToCSV(diagram, options = {}) {
  let out = `# ${DIAGRAM_FORMAT}\n`;
  out += meta('name', diagram.name);
  out += meta('x-generators', diagram.xCount);
  out += meta('y-generators', diagram.yCount);
  if (options.cell) out += meta('cell', options.cell);
  for (const [key, value] of Object.entries(diagram.notes ?? {})) out += meta(`note-${key}`, value);
  out += meta('basepoint', 'z corner');
  for (const b of diagram.basepoints ?? []) out += meta('basepoint', `${b.name} arc ${b.insideArc}`);

  out += 'side_a,index_a,side_b,index_b,family\n';
  for (const arc of diagram.arcs)
    out += `${arc.a.side},${arc.a.index},${arc.b.side},${arc.b.index},${arc.family ?? ''}\n`;
  return out;
}

/** @param {string} text @returns {{diagram: HeegaardDiagram, meta: Object}} */
export function diagramFromCSV(text) {
  const { info, body, at } = split(text, DIAGRAM_FORMAT);
  for (const column of ['side_a', 'index_a', 'side_b', 'index_b'])
    if (at(column) < 0) throw new Error(`the arc table has no "${column}" column`);

  const arcs = body.map((line, row) => {
    const f = line.split(',').map((v) => v.trim());
    const end = (side, index) => {
      if (!SIDES.includes(side)) throw new Error(`row ${row + 1}: "${side}" is not a side`);
      const k = Number(index);
      if (!Number.isInteger(k) || k < 0) throw new Error(`row ${row + 1}: "${index}" is not an index`);
      return { side, index: k };
    };
    const arc = { a: end(f[at('side_a')], f[at('index_a')]), b: end(f[at('side_b')], f[at('index_b')]) };
    const family = at('family') >= 0 ? f[at('family')] : '';
    return family ? { ...arc, family } : arc;
  });

  // counts may be stated; if not, take them from the arcs themselves
  const highest = (kind) => Math.max(-1, ...arcs.flatMap((a) => [a.a, a.b])
    .filter((e) => GENERATOR_OF_SIDE[e.side] === kind).map((e) => e.index));
  const xCount = Number(info['x-generators'] ?? highest('x') + 1);
  const yCount = Number(info['y-generators'] ?? highest('y') + 1);

  const basepoints = (info.basepoints ?? []).map((s) => s.split(/\s+/))
    .filter(([, where]) => where === 'arc')
    .map(([name, , index]) => ({ name, insideArc: Number(index) }));

  const notes = {};
  for (const [key, value] of Object.entries(info))
    if (key.startsWith('note-')) notes[key.slice(5)] = Number.isNaN(Number(value)) ? value : Number(value);

  const diagram = new HeegaardDiagram({ name: info.name ?? 'diagram', xCount, yCount, arcs, basepoints, notes });
  const problems = diagram.validate();
  if (problems.length)
    throw new Error('the diagram in this file is not legal:\n  ' +
      problems.slice(0, 4).map((p) => p.message).join('\n  '));
  return { diagram, meta: info };
}

/** @param {Object[]} discs @param {{diagram?:HeegaardDiagram, convention?:string, sort?:boolean}} [options] */
export function discsToCSV(discs, options = {}) {
  const { diagram, convention = 'composed', sort = true } = options;
  let out = `# ${DISCS_FORMAT}\n`;
  if (diagram) {
    out += meta('diagram', diagram.name);
    out += meta('x-generators', diagram.xCount);
    out += meta('y-generators', diagram.yCount);
  }
  out += meta('reeb-convention', convention);
  out += meta('count', discs.length);
  out += 'source,target,U,chords,arcs,path\n';
  const rows = sort ? [...discs].sort((a, b) =>
    a.source.localeCompare(b.source, 'en', { numeric: true }) ||
    a.target.localeCompare(b.target, 'en', { numeric: true }) ||
    a.U - b.U || a.word.localeCompare(b.word)) : discs;
  for (const d of rows)
    out += `${d.source},${d.target},${d.U},${d.word},${d.offset},${d.directions.join(' ')}\n`;
  return out;
}

/** @param {string} text @returns {{discs:Object[], meta:Object}} */
export function discsFromCSV(text) {
  const { info, body, at } = split(text, DISCS_FORMAT);
  const discs = body.map((line) => {
    const f = line.split(',').map((v) => v.trim());
    const word = at('chords') >= 0 ? (f[at('chords')] ?? '') : '';
    return {
      source: f[at('source')], target: f[at('target')], U: Number(f[at('U')]), word,
      chords: word ? word.split('P').filter(Boolean).map((c) => `rho_${c}`) : [],
      offset: at('arcs') >= 0 ? Number(f[at('arcs')]) : undefined,
      directions: at('path') >= 0 && f[at('path')] ? f[at('path')].split(/\s+/) : []
    };
  });
  return { discs, meta: info };
}
