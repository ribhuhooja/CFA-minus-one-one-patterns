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
import { statSync } from 'node:fs';

let cached = null;
/** Is Inkscape on the PATH? Checked once. */
export function inkscapeAvailable() {
  if (cached !== null) return cached;
  const probe = spawnSync('inkscape', ['--version'], { encoding: 'utf8' });
  cached = probe.status === 0 ? (probe.stdout.trim().split('\n')[0] || 'inkscape') : false;
  return cached;
}

/**
 * @param {string} svgPath
 * @param {{pngPath?:string, dpi?:number, background?:string}} [options]
 * @returns {{ok:true, path:string, bytes:number} | {ok:false, why:string}}
 */
export function svgToPng(svgPath, options = {}) {
  const { pngPath = svgPath.replace(/\.svg$/i, '.png'), dpi = 110, background = 'white' } = options;
  if (!inkscapeAvailable())
    return { ok: false, why: 'inkscape is not on the PATH (brew install inkscape)' };

  const run = spawnSync('inkscape', [svgPath, '--export-type=png',
    `--export-filename=${pngPath}`, `--export-background=${background}`,
    `--export-dpi=${dpi}`], { encoding: 'utf8' });
  if (run.status !== 0)
    return { ok: false, why: (run.stderr || run.error?.message || 'inkscape failed').trim().split('\n')[0] };
  try {
    return { ok: true, path: pngPath, bytes: statSync(pngPath).size };
  } catch {
    return { ok: false, why: 'inkscape reported success but wrote no file' };
  }
}
