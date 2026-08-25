/**
 * Rendering an SVG to PNG, if Inkscape happens to be installed.
 *
 * PNG rather than JPEG on purpose: these are line drawings -- flat colour, sharp edges, a lot
 * of white -- which is the worst case for a DCT codec.  Measured on these very files, JPEG at
 * quality 92 came out two to three times LARGER than PNG as well as lossier, because it
 * spends its bits on ringing around every grid line.
 *
 * Nothing else in the package shells out, and nothing depends on this working: if Inkscape is
 * missing the SVG is still written and the caller is told why there is no PNG.
 */
import { spawnSync } from 'node:child_process';
import { statSync, readFileSync } from 'node:fs';

/** SVG user units are px at 96 dpi, so anything above that scales the raster up. */
const SVG_DPI = 96;

/** The canvas size an SVG declares, in user units. */
export function svgSize(svgPath) {
  const head = readFileSync(svgPath, 'utf8').slice(0, 2048);
  const w = head.match(/\bwidth="([0-9.]+)"/), h = head.match(/\bheight="([0-9.]+)"/);
  return w && h ? { width: Number(w[1]), height: Number(h[1]) } : null;
}

let cached = null;
/** Is Inkscape on the PATH? Checked once. */
export function inkscapeAvailable() {
  if (cached !== null) return cached;
  const probe = spawnSync('inkscape', ['--version'], { encoding: 'utf8' });
  cached = probe.status === 0 ? (probe.stdout.trim().split('\n')[0] || 'inkscape') : false;
  return cached;
}

/**
 * The dpi is lowered as far as needed to keep the raster under `maxMegapixels`.  Without
 * that guard an atlas of a large diagram is a trap: the canvas grows with the number of discs
 * and the size of a domain, so Q(4,7,3) declares 157272 x 153302 user units, which at 110 dpi
 * asks for a 31 gigapixel image.  Rendering that does not fail, it just never finishes.
 *
 * @param {string} svgPath
 * @param {{pngPath?:string, dpi?:number, background?:string, maxMegapixels?:number}} [options]
 * @returns {{ok:true, path:string, bytes:number, dpi:number, pixels:number, capped:boolean}
 *          | {ok:false, why:string}}
 */
export function svgToPng(svgPath, options = {}) {
  const { pngPath = svgPath.replace(/\.svg$/i, '.png'), dpi: wanted = 110,
          background = 'white', maxMegapixels = 40 } = options;
  if (!inkscapeAvailable())
    return { ok: false, why: 'inkscape is not on the PATH (brew install inkscape)' };

  let dpi = wanted, capped = false, pixels = 0;
  const size = svgSize(svgPath);
  if (size) {
    const atWanted = size.width * size.height * (wanted / SVG_DPI) ** 2;
    if (maxMegapixels > 0 && atWanted > maxMegapixels * 1e6) {
      dpi = Math.max(1, SVG_DPI * Math.sqrt(maxMegapixels * 1e6 / (size.width * size.height)));
      capped = true;
    }
    pixels = size.width * size.height * (dpi / SVG_DPI) ** 2;
  }

  const run = spawnSync('inkscape', [svgPath, '--export-type=png',
    `--export-filename=${pngPath}`, `--export-background=${background}`,
    `--export-dpi=${dpi.toFixed(2)}`], { encoding: 'utf8' });
  if (run.status !== 0)
    return { ok: false, why: (run.stderr || run.error?.message || 'inkscape failed').trim().split('\n')[0] };
  try {
    return { ok: true, path: pngPath, bytes: statSync(pngPath).size, dpi, pixels, capped };
  } catch {
    return { ok: false, why: 'inkscape reported success but wrote no file' };
  }
}
