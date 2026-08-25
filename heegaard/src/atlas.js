/**
 * Every disc of a diagram, drawn at once on a large universal cover.
 *
 * A disc translated by a lattice vector is another lift of the same disc, so the picture is
 * still an honest picture of the cover whichever copy each one is drawn in.  That is what
 * makes a catalogue possible: left where the enumeration found them the discs sit on top of
 * one another, so `arrange: 'packed'` (the default) slides each into a free slot instead.
 * `arrange: 'insitu'` leaves them where they were found.
 *
 * Colours mean nothing; they are there so that two discs lying close together can be told
 * apart, and are assigned greedily so neighbours differ.
 */
import { boundingBox } from '../../grid-arc/src/geometry.js';

/** Enough hues to keep neighbours apart; nothing is meant by any particular one. */
const PALETTE = [
  '#d1495b', '#2a9d8f', '#e9c46a', '#5f6caf', '#e76f51', '#4a7c59',
  '#9d4edd', '#0288a6', '#c1666b', '#7f9c3c', '#b5651d', '#3f6fb5'
];

/**
 * Cycle through the palette in the order the discs were placed, so that slots next to each
 * other differ, then fix up any two that ended the same colour and close enough to be read
 * as one shape.
 */
function assignColours(boxes, order, margin = 0.6) {
  const near = (p, q) =>
    p[0] - margin < q[2] && q[0] - margin < p[2] && p[1] - margin < q[3] && q[1] - margin < p[3];
  const colour = new Array(boxes.length).fill(-1);
  order.forEach((k, position) => {
    const taken = new Set();
    for (let j = 0; j < boxes.length; j++)
      if (j !== k && colour[j] >= 0 && near(boxes[k], boxes[j])) taken.add(colour[j]);
    let c = position % PALETTE.length;
    for (let tries = 0; tries < PALETTE.length && taken.has(c); tries++) c = (c + 1) % PALETTE.length;
    colour[k] = c;
  });
  return colour;
}
const area = (b) => (b[2] - b[0]) * (b[3] - b[1]);

/**
 * Slide each disc by a whole number of copies so that none overlaps another: shelf packing,
 * tallest first.  Integer shifts only, because only a lattice vector maps a disc to another
 * lift of itself.
 */
export function packIntoSlots(boxes, gap = 0, aspect = 1) {
  const sizes = boxes.map((b) => [Math.ceil(b[2]) - Math.floor(b[0]) + gap,
                                 Math.ceil(b[3]) - Math.floor(b[1]) + gap]);
  const totalArea = sizes.reduce((sum, [w, h]) => sum + w * h, 0);
  // a copy of the domain is `aspect` times as wide as it is tall, so a squarish picture
  // wants that many fewer columns
  const targetWidth = Math.max(...sizes.map(([w]) => w),
                               Math.ceil(Math.sqrt(totalArea / Math.max(aspect, 0.2))));

  const order = [...boxes.keys()].sort((a, b) => sizes[b][1] - sizes[a][1]);
  const shifts = new Array(boxes.length);
  let penX = 0, penY = 0, shelfHeight = 0;
  for (const k of order) {
    const [w, h] = sizes[k];
    if (penX + w > targetWidth && penX > 0) { penX = 0; penY += shelfHeight; shelfHeight = 0; }
    shifts[k] = [penX - Math.floor(boxes[k][0]), penY - Math.floor(boxes[k][1])];
    penX += w;
    shelfHeight = Math.max(shelfHeight, h);
  }
  return shifts;
}

const fmt = (v) => (Math.round(v * 100) / 100).toString();
const esc = (s) => String(s).replace(/[&<>]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c]));

/**
 * @param {Object} enumeration  the result of enumerateDiscs({ keepRegions: true })
 * @param {{caption?:string, alpha?:number, pad?:number}} [options]
 * @returns {string} SVG
 */
export function discAtlas(enumeration, options = {}) {
  const { laidOut, discs } = enumeration;
  const { alpha = 0.55, pad = 1, arrange = 'packed', gap = 0 } = options;
  const withRegion = discs.filter((d) => d.polygon);
  if (!withRegion.length) throw new Error('no regions kept; enumerate with { keepRegions: true }');

  const shifts = arrange === 'packed'
    ? packIntoSlots(withRegion.map((d) => boundingBox(d.polygon)), gap,
                    laidOut.width / laidOut.height)
    : withRegion.map(() => [0, 0]);
  const regions = withRegion.map((d, k) =>
    d.polygon.map(([u, v]) => [u + shifts[k][0], v + shifts[k][1]]));

  const boxes = regions.map(boundingBox);
  const placement = [...boxes.keys()].sort((a, b) =>
    boxes[a][1] - boxes[b][1] || boxes[a][0] - boxes[b][0]);
  const colour = assignColours(boxes, placement);

  const i0 = Math.floor(Math.min(...boxes.map((b) => b[0]))) - pad;
  const j0 = Math.floor(Math.min(...boxes.map((b) => b[1]))) - pad;
  const i1 = Math.ceil(Math.max(...boxes.map((b) => b[2]))) + pad;
  const j1 = Math.ceil(Math.max(...boxes.map((b) => b[3]))) + pad;

  const { width: W, height: H } = laidOut;
  const margin = 12;
  const total = [(i1 - i0) * W, (j1 - j0) * H];
  const svgW = total[0] + 2 * margin, svgH = total[1] + 2 * margin + 26;
  // unit-grid coordinates -> svg
  const to = ([u, v]) => [margin + (u - i0) * W, margin + total[1] - (v - j0) * H];

  const parts = [`<rect width="${fmt(svgW)}" height="${fmt(svgH)}" fill="#ffffff"/>`];

  // the alpha curves
  parts.push('<g stroke="#f0b9b9" stroke-width="1.4">');
  for (let i = i0; i <= i1; i++) {
    const a = to([i, j0]), b = to([i, j1]);
    parts.push(`<line x1="${fmt(a[0])}" y1="${fmt(a[1])}" x2="${fmt(b[0])}" y2="${fmt(b[1])}"/>`);
  }
  for (let j = j0; j <= j1; j++) {
    const a = to([i0, j]), b = to([i1, j]);
    parts.push(`<line x1="${fmt(a[0])}" y1="${fmt(a[1])}" x2="${fmt(b[0])}" y2="${fmt(b[1])}"/>`);
  }
  parts.push('</g>');

  // beta: draw one copy of the domain, then reuse it for the rest.  Every copy is the same
  // picture, so there is no reason to write it out hundreds of times.
  const tile = [];
  for (const arc of laidOut.arcs) {
    const shift = ([x, y]) => to([i0 + x / W, j0 + y / H]);
    const [a, b] = arc.ends.map(shift);
    if (arc.shape === 'parabola') {
      const c = shift(arc.control);
      tile.push(`<path d="M${fmt(a[0])} ${fmt(a[1])}Q${fmt(c[0])} ${fmt(c[1])} ${fmt(b[0])} ${fmt(b[1])}"/>`);
    } else {
      tile.push(`<path d="M${fmt(a[0])} ${fmt(a[1])}L${fmt(b[0])} ${fmt(b[1])}"/>`);
    }
  }
  parts.push(`<defs><g id="beta" fill="none" stroke="#7ea6ec" stroke-width="1.1">${tile.join('')}</g></defs>`);
  for (let i = i0; i < i1; i++) for (let j = j0; j < j1; j++)
    parts.push(`<use href="#beta" x="${fmt((i - i0) * W)}" y="${fmt(-(j - j0) * H)}"/>`);

  // the discs, biggest first so a small one sitting inside a big one still shows
  const order = [...withRegion.keys()].sort((a, b) => area(boxes[b]) - area(boxes[a]));
  for (const k of order) {
    const d = withRegion[k], hue = PALETTE[colour[k]];
    const points = regions[k].map(to).map(([x, y]) => `${fmt(x)},${fmt(y)}`).join(' ');
    parts.push(`<polygon points="${points}" fill="${hue}" fill-opacity="${alpha}" ` +
      `stroke="${hue}" stroke-width="1"><title>${esc(`${d.source} -> ${d.target}` +
      `  U^${d.U}  ${d.word || 'no chords'}`)}</title></polygon>`);
  }

  const caption = options.caption ?? `${laidOut.diagram.name}  ·  ${withRegion.length} discs, ` +
    `each in its own copy of the domain  ·  ${i1 - i0} x ${j1 - j0} copies shown  ` +
    `·  hover a disc for its label`;
  parts.push(`<text x="${fmt(margin)}" y="${fmt(svgH - 8)}" ` +
    `font-family="ui-sans-serif,system-ui,sans-serif" font-size="13" fill="#1d1a17">${esc(caption)}</text>`);

  return `<svg xmlns="http://www.w3.org/2000/svg" width="${fmt(svgW)}" height="${fmt(svgH)}" ` +
    `viewBox="0 0 ${fmt(svgW)} ${fmt(svgH)}" role="img">\n  <title>${esc(laidOut.diagram.name)} discs</title>\n  ` +
    `${parts.join('\n  ')}\n</svg>\n`;
}
