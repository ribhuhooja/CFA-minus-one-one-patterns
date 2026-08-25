/**
 * SVG for a laid-out diagram.  This is the only module that flips y: everything upstream
 * is in mathematical coordinates (y up), SVG is y down.
 *
 * Colours match the grid solver next door, so the two pictures read as the same object:
 * the alpha curves are the pale red grid, beta is drawn in pale blue.
 */

export const COLOURS = Object.freeze({
  grid: '#f0b9b9',          // the alpha curves — the same pale red as the grid solver
  gridStrong: '#e08a8a',    // the edges of the marked fundamental domain
  arc: '#7ea6ec',           // beta
  generatorX: '#2f3437',
  generatorY: '#2f3437',
  label: '#6b645d',
  ink: '#1d1a17',
  basepoint: '#b3261e'
});

const esc = (s) => String(s).replace(/[&<>]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c]));
const fmt = (v) => (Math.round(v * 100) / 100).toString();
const polyline = (points) => points.map(([x, y], k) => `${k ? 'L' : 'M'}${fmt(x)} ${fmt(y)}`).join(' ');

/**
 * An arc as one path command: a line, or the quadratic it actually is.  Both survive the
 * affine map into svg coordinates unchanged, so there is nothing to sample.
 */
function arcCommand(arc, to, dx = 0, dy = 0) {
  const shift = ([x, y]) => to([x + dx, y + dy]);
  const [a, b] = arc.ends.map(shift);
  if (arc.shape !== 'parabola') return `M${fmt(a[0])} ${fmt(a[1])}L${fmt(b[0])} ${fmt(b[1])}`;
  const c = shift(arc.control);
  return `M${fmt(a[0])} ${fmt(a[1])}Q${fmt(c[0])} ${fmt(c[1])} ${fmt(b[0])} ${fmt(b[1])}`;
}

/**
 * One fundamental domain.
 * @param {import('./layout.js').Layout} laidOut
 * @param {{labels?:boolean, caption?:string, basepoint?:boolean, margin?:number}} [options]
 */
export function renderDiagram(laidOut, options = {}) {
  const { labels = true, basepoint = true, caption = defaultCaption(laidOut) } = options;
  const { width, height, cell, arcs, generators } = laidOut;

  const pad = Math.max(26, cell * 1.1);
  const bottomPad = pad + (caption ? 34 : 0);
  const W = width + 2 * pad, H = height + pad + bottomPad;
  const X = (x) => pad + x;                       // math -> svg
  const Y = (y) => pad + (height - y);
  const to = (p) => [X(p[0]), Y(p[1])];

  const parts = [];
  parts.push(`<rect width="${fmt(W)}" height="${fmt(H)}" fill="#ffffff"/>`);

  // the alpha curves: the boundary of the fundamental domain
  parts.push(`<rect x="${fmt(X(0))}" y="${fmt(Y(height))}" width="${fmt(width)}" height="${fmt(height)}" ` +
             `fill="none" stroke="${COLOURS.grid}" stroke-width="2.5"/>`);

  // beta
  parts.push(`<g fill="none" stroke="${COLOURS.arc}" stroke-width="2" stroke-linecap="round">`);
  for (const a of arcs) parts.push(`<path d="${arcCommand(a, to)}"/>`);
  parts.push('</g>');

  // generators
  parts.push('<g>');
  for (const g of generators) {
    const [x, y] = to(g.at);
    parts.push(`<circle cx="${fmt(x)}" cy="${fmt(y)}" r="2.6" fill="${
      g.kind === 'x' ? COLOURS.generatorX : COLOURS.generatorY}"/>`);
  }
  parts.push('</g>');

  if (labels && cell >= 14) {
    const size = Math.min(10, Math.max(7, cell * 0.42));
    parts.push(`<g font-family="ui-monospace,Menlo,monospace" font-size="${fmt(size)}" fill="${COLOURS.label}">`);
    for (const g of generators) {
      const [x, y] = to(g.at);
      let dx = 0, dy = 0, anchor = 'middle';
      if (g.side === 'bottom') dy = size + 6;
      else if (g.side === 'top') dy = -7;
      else if (g.side === 'left') { dx = -6; dy = size * 0.36; anchor = 'end'; }
      else { dx = 6; dy = size * 0.36; anchor = 'start'; }
      parts.push(`<text x="${fmt(x + dx)}" y="${fmt(y + dy)}" text-anchor="${anchor}">${g.index}</text>`);
    }
    parts.push('</g>');
    parts.push(`<g font-family="ui-sans-serif,system-ui,sans-serif" font-size="10" fill="${COLOURS.label}">` +
      `<text x="${fmt(X(width) + 12)}" y="${fmt(Y(height) - 10)}" text-anchor="middle">x_j</text>` +
      `<text x="${fmt(X(0) - 12)}" y="${fmt(Y(height) - 10)}" text-anchor="middle">y_j</text></g>`);
  }

  if (basepoint) {
    const [x, y] = to(laidOut.basepoint.at);
    parts.push(`<circle cx="${fmt(x)}" cy="${fmt(y)}" r="3.4" fill="${COLOURS.basepoint}"/>`);
    parts.push(`<text x="${fmt(x + 8)}" y="${fmt(y + 13)}" ` +
               `font-family="ui-monospace,Menlo,monospace" font-size="10" ` +
               `fill="${COLOURS.basepoint}">z</text>`);
  }

  if (caption)
    parts.push(`<text x="${fmt(pad)}" y="${fmt(H - 14)}" font-family="ui-sans-serif,system-ui,sans-serif" ` +
               `font-size="12" fill="${COLOURS.ink}">${esc(caption)}</text>`);

  return svg(W, H, parts.join('\n  '), laidOut.diagram.name);
}

/**
 * The universal cover: the domain tiled by translations, with the alpha curves as the grid.
 * @param {{tiles?:number|[number,number], markCentre?:boolean, caption?:string}} [options]
 */
export function renderUniversalCover(laidOut, options = {}) {
  const { width, height, cell, arcs } = laidOut;
  const [tx, ty] = Array.isArray(options.tiles ?? 3) ? options.tiles : [options.tiles ?? 3, options.tiles ?? 3];
  const { markCentre = true, dots = true, caption = defaultCaption(laidOut, `universal cover, ${tx} x ${ty} domains`) } = options;

  const pad = Math.max(18, cell * 0.7);
  const bottomPad = pad + (caption ? 34 : 0);
  const total = [width * tx, height * ty];
  const W = total[0] + 2 * pad, H = total[1] + pad + bottomPad;
  const X = (x) => pad + x;
  const Y = (y) => pad + (total[1] - y);
  const to = (p) => [X(p[0]), Y(p[1])];

  const parts = [`<rect width="${fmt(W)}" height="${fmt(H)}" fill="#ffffff"/>`];

  // the alpha curves, lifted: one line per translate of each edge
  parts.push(`<g stroke="${COLOURS.grid}" stroke-width="2">`);
  for (let k = 0; k <= tx; k++)
    parts.push(`<line x1="${fmt(X(k * width))}" y1="${fmt(Y(0))}" x2="${fmt(X(k * width))}" y2="${fmt(Y(total[1]))}"/>`);
  for (let l = 0; l <= ty; l++)
    parts.push(`<line x1="${fmt(X(0))}" y1="${fmt(Y(l * height))}" x2="${fmt(X(total[0]))}" y2="${fmt(Y(l * height))}"/>`);
  parts.push('</g>');

  // beta, lifted
  parts.push(`<g fill="none" stroke="${COLOURS.arc}" stroke-width="2" stroke-linecap="round">`);
  for (let k = 0; k < tx; k++) for (let l = 0; l < ty; l++)
    for (const a of arcs)
      parts.push(`<path d="${arcCommand(a, to, k * width, l * height)}"/>`);
  parts.push('</g>');

  if (dots && cell >= 12) {
    parts.push(`<g fill="${COLOURS.generatorX}">`);
    for (let k = 0; k < tx; k++) for (let l = 0; l < ty; l++)
      for (const g of laidOut.generators) {
        const [x, y] = to([g.at[0] + k * width, g.at[1] + l * height]);
        parts.push(`<circle cx="${fmt(x)}" cy="${fmt(y)}" r="1.9"/>`);
      }
    parts.push('</g>');
  }

  if (options.basepoints !== false) {
    parts.push(`<g fill="${COLOURS.basepoint}">`);
    for (let k = 0; k < tx; k++) for (let l = 0; l < ty; l++) {
      const [x, y] = to([k * width + laidOut.basepoint.at[0], l * height + laidOut.basepoint.at[1]]);
      parts.push(`<circle cx="${fmt(x)}" cy="${fmt(y)}" r="2.6"/>`);
    }
    parts.push('</g>');
  }

  if (markCentre) {
    const cx = Math.floor(tx / 2) * width, cy = Math.floor(ty / 2) * height;
    parts.push(`<rect x="${fmt(X(cx))}" y="${fmt(Y(cy + height))}" width="${fmt(width)}" height="${fmt(height)}" ` +
               `fill="none" stroke="${COLOURS.gridStrong}" stroke-width="3"/>`);
  }

  if (caption)
    parts.push(`<text x="${fmt(pad)}" y="${fmt(H - 14)}" font-family="ui-sans-serif,system-ui,sans-serif" ` +
               `font-size="12" fill="${COLOURS.ink}">${esc(caption)}</text>`);

  return svg(W, H, parts.join('\n  '), `${laidOut.diagram.name} universal cover`);
}

function defaultCaption(laidOut, extra) {
  const d = laidOut.diagram, note = d.notes ?? {};
  const bits = [d.name];
  if (note.r !== undefined) bits.push(`H(r=${note.r}, s=${note.s})`);
  bits.push(`${d.xCount} x-generators, ${d.yCount} y-generators`, `${d.arcs.length} arcs`);
  if (note.dependentStrands !== undefined) bits.push(`m+n-2 = ${note.dependentStrands} dependent strands`);
  const components = d.components().length;
  bits.push(components === 1 ? 'beta connected' : `beta has ${components} components`);
  if (extra) bits.push(extra);
  return bits.join('  ·  ');
}

function svg(W, H, body, title) {
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${fmt(W)}" height="${fmt(H)}" ` +
    `viewBox="0 0 ${fmt(W)} ${fmt(H)}" role="img">\n  <title>${esc(title)}</title>\n  ${body}\n</svg>\n`;
}
