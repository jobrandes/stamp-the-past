// Local stand-in for Netlify: serves site/ and runs the real community function against an in-memory store.
import http from 'node:http'; import fs from 'node:fs'; import path from 'node:path';
import { makeHandler } from '../../netlify/functions/community.mjs';
const mem = new Map();
const store = () => ({
  async list({ prefix }) { return { blobs: [...mem.keys()].filter((k) => k.startsWith(prefix)).map((key) => ({ key })) }; },
  async get(k, o) { if (!mem.has(k)) return null; const v = mem.get(k); if (o?.type === 'json') return JSON.parse(JSON.stringify(v)); if (o?.type === 'arrayBuffer') return v.buffer.slice(v.byteOffset, v.byteOffset + v.byteLength); return v; },
  async set(k, v) { mem.set(k, v); }, async setJSON(k, v) { mem.set(k, JSON.parse(JSON.stringify(v))); },
});
const handler = makeHandler(store);
const root = path.resolve(process.argv[2]); const ctxName = process.env.CTX || 'branch-deploy';
const types = { '.html': 'text/html', '.js': 'text/javascript', '.json': 'application/json', '.jpg': 'image/jpeg', '.png': 'image/png', '.css': 'text/css', '.woff2': 'font/woff2', '.webmanifest': 'application/json' };
http.createServer(async (req, res) => {
  const u = new URL(req.url, 'http://x');
  if (u.pathname.startsWith('/api/')) {
    const chunks = []; for await (const c of req) chunks.push(c);
    const r = await handler(new Request('http://x' + req.url, { method: req.method, body: chunks.length ? Buffer.concat(chunks) : undefined, headers: req.headers }), { deploy: { context: ctxName } });
    res.writeHead(r.status, Object.fromEntries(r.headers)); res.end(Buffer.from(await r.arrayBuffer())); return;
  }
  let f = path.join(root, decodeURIComponent(u.pathname)); if (!f.startsWith(root)) { res.writeHead(403).end(); return; }
  if (fs.existsSync(f) && fs.statSync(f).isDirectory()) f = path.join(f, 'index.html');
  if (!fs.existsSync(f)) { res.writeHead(404).end('nf'); return; }
  res.writeHead(200, { 'content-type': types[path.extname(f)] || 'application/octet-stream' }); fs.createReadStream(f).pipe(res);
}).listen(Number(process.argv[3] || 8765), () => console.log('ready'));
