/** Static server rooted at the repo, so the viewer can import from grid-arc too.
 *  node serve.js [port]   ->   http://localhost:8300/heegaard/ */
import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { extname, join, normalize } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('..', import.meta.url));
const port = Number(process.argv[2] ?? 8300);
const types = {
  '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8', '.svg': 'image/svg+xml; charset=utf-8',
  '.css': 'text/css; charset=utf-8'
};

createServer(async (req, res) => {
  const asked = decodeURIComponent(req.url.split('?')[0]);
  const rel = asked === '/' ? '/heegaard/index.html' : asked.endsWith('/') ? `${asked}index.html` : asked;
  const file = normalize(join(root, rel));
  if (!file.startsWith(root)) { res.writeHead(403).end('forbidden'); return; }
  try {
    const body = await readFile(file);
    res.writeHead(200, { 'content-type': types[extname(file)] ?? 'application/octet-stream' });
    res.end(body);
  } catch { res.writeHead(404).end('not found'); }
}).listen(port, () => console.log(`heegaard viewer: http://localhost:${port}/heegaard/`));
