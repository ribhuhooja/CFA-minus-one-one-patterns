/**
 * The conjectured arrow tables for Q(i, 2, 2), transcribed as given.
 *
 * Three groups -- 14 special arrows, a "snail" of 12i-7 arrows all labelled U, and 52i-25
 * arrows in families -- so 64i-18 in all.  Nothing here is computed from a diagram; this is
 * the prediction, kept separate so `enumerateDiscs` can be checked against it.
 *
 * Chord words are written the way the tables write them, rho_3 rho_2 rho_1 as "P3P2P1",
 * which is the order the path walks them under the `composed` naming.
 *
 * For Q(i, 2, 2):  r = 4i-1,  s = 8i-2,  maxx = 16i-3,  maxy = 8i-4.
 */

/** "" for U^0, "U" for U^1, "U^k" beyond. */
export const uPrefix = (U) => (U === 0 ? '' : U === 1 ? 'U' : `U^${U}`);
/** The reference tables' single-column form, e.g. U^2P23. */
export const annotation = (U, word) => `${uPrefix(U)}${word}`;

/**
 * @param {number} i
 * @returns {{source:string, target:string, U:number, word:string, group:string}[]}
 */
export function conjecturedArrows(i) {
  if (!Number.isInteger(i) || i < 1) throw new Error(`the tables are stated for i >= 1, got ${i}`);
  const out = [];
  const arrow = (group, source, U, word, target) => out.push({ source, target, U, word, group });
  const x = (k) => `x_${k}`, y = (k) => `y_${k}`;

  // ---- special arrows (14) ------------------------------------------------
  arrow('special', x(12 * i + 1), 2, '',            x(12 * i - 2));
  arrow('special', x(12 * i + 1), 2, 'P23',         x(12 * i - 2));
  arrow('special', y(4 * i - 1),  1, 'P1',          x(12 * i - 2));
  arrow('special', y(4 * i - 1),  1, 'P12P1',       x(12 * i - 3));
  arrow('special', y(4 * i),      2, 'P1',          x(12 * i - 3));
  arrow('special', y(4 * i),      2, 'P3',          x(12 * i - 2));
  arrow('special', x(12 * i),     2, 'P23P2P12P1',  x(12 * i - 4));
  arrow('special', y(4 * i - 3),  2, 'P123P2P12P1', x(12 * i - 4));
  arrow('special', y(4 * i - 4),  2, 'P123',        x(12 * i - 2));
  arrow('special', y(4 * i - 2),  0, 'P12P1',       x(12 * i - 2));
  arrow('special', y(4 * i - 2),  0, 'P12P12P1',    x(12 * i - 3));
  arrow('special', x(12 * i - 1), 0, 'P2P1',        x(12 * i - 2));
  arrow('special', x(12 * i - 1), 0, 'P2P12P1',     x(12 * i - 3));
  arrow('special', x(12 * i - 2), 0, 'P2P1',        x(12 * i - 3));

  // ---- the snail: 12i-7 arrows, all U ------------------------------------
  const snail = (source, target) => arrow('snail', source, 1, '', target);
  snail(x(12 * i), x(12 * i - 1));
  for (let k = 0; k <= i - 1; k++) {
    snail(x(4 * k),     x(4 * k + 3));
    snail(x(4 * k + 1), x(4 * k + 2));
    snail(y(4 * k),     y(4 * k + 3));
    snail(y(4 * k + 1), y(4 * k + 2));
  }
  for (let k = 0; k <= i - 2; k++) {
    snail(x(4 * i + 4 + 4 * k),  x(4 * i + 1 + 4 * k));
    snail(x(4 * i + 3 + 4 * k),  x(4 * i + 2 + 4 * k));
    snail(x(8 * i + 1 + 4 * k),  x(8 * i + 4 + 4 * k));
    snail(x(8 * i + 2 + 4 * k),  x(8 * i + 3 + 4 * k));
    snail(x(12 * i + 5 + 4 * k), x(12 * i + 2 + 4 * k));
    snail(x(12 * i + 4 + 4 * k), x(12 * i + 3 + 4 * k));
    snail(y(4 * i + 4 + 4 * k),  y(4 * i + 1 + 4 * k));
    snail(y(4 * i + 3 + 4 * k),  y(4 * i + 2 + 4 * k));
  }

  // ---- families: 52i-25 arrows -------------------------------------------
  const family = (source, U, word, target) => arrow('family', source, U, word, target);
  for (let j = 0; j <= 8 * i - 4; j++) family(y(j), 1, 'P3P2P1',      x(j));
  for (let j = 0; j <= 4 * i - 1; j++) family(y(j), 2, 'P3P2P12P1',   x(8 * i - 3 + j));
  for (let j = 0; j <= 4 * i - 1; j++) family(x(j), 1, 'P2P1',        x(8 * i - 3 + j));
  for (let j = 0; j <= 4 * i - 2; j++) family(y(j), 0, 'P1',          x(16 * i - 3 - j));
  for (let j = 0; j <= 4 * i - 3; j++) family(y(j), 0, 'P12',         y(8 * i - 4 - j));
  for (let j = 0; j <= 4 * i - 3; j++) family(y(j), 1, 'P123P2P1',    x(8 * i - 4 - j));
  for (let j = 0; j <= 4 * i - 5; j++) family(y(j), 1, 'P123',        x(4 + j));
  for (let j = 0; j <= 4 * i - 3; j++) family(x(16 * i - 3 - j), 0, 'P2',       y(8 * i - 4 - j));
  for (let j = 0; j <= 4 * i - 3; j++) family(x(16 * i - 3 - j), 1, 'P23P2P1',  x(8 * i - 4 - j));
  for (let j = 0; j <= 4 * i - 5; j++) family(x(16 * i - 3 - j), 1, 'P23',      x(4 + j));
  for (let j = 0; j <= 4 * i - 2; j++) family(x(4 * i + j), 1, '',    x(12 * i - 3 - j));
  for (let j = 0; j <= 4 * i - 5; j++) family(y(8 * i - 4 - j), 1, 'P3', x(4 + j));

  return out;
}

/** How many arrows the tables claim: 14 + (12i-7) + (52i-25). */
export const conjecturedCount = (i) => 64 * i - 18;
