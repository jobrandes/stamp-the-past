// Local stand-in for Netlify: serves a site root and runs the real community function against an in-memory store
// and a fake Wikimedia Commons. Usage: node server.mjs <root> <port>
import http from 'node:http'; import fs from 'node:fs'; import path from 'node:path';
import { makeHandler } from '../../netlify/functions/community.mjs';
const mem = new Map(); const meta = new Map();
const store = () => ({
  async list({ prefix }) { return { blobs: [...mem.keys()].filter((k) => k.startsWith(prefix)).map((key) => ({ key })) }; },
  async get(k, o) { if (!mem.has(k)) return null; const v = mem.get(k); if (o?.type === 'json') return JSON.parse(JSON.stringify(v)); return v; },
  async getWithMetadata(k, o) { if (!mem.has(k)) return null; const v = mem.get(k); return { data: v.buffer.slice(v.byteOffset, v.byteOffset + v.byteLength), metadata: meta.get(k) || {} }; },
  async set(k, v, o) { mem.set(k, v); meta.set(k, o?.metadata); }, async setJSON(k, v) { mem.set(k, JSON.parse(JSON.stringify(v))); }, async delete(k) { mem.delete(k); },
});
const root = path.resolve(process.argv[2]); const ctxName = process.env.CTX || 'branch-deploy';
const JPG = fs.readFileSync(process.env.FAKE_JPG);
const fakeFetch = async (u) => {
  u = String(u);
  if (u.includes('/community/status.json')) { const f = path.join(root, 'community/status.json'); return fs.existsSync(f) ? new Response(fs.readFileSync(f), { status: 200 }) : new Response('nf', { status: 404 }); }
  if (u.startsWith('https://commons.wikimedia.org/w/api.php')) {
    const t = decodeURIComponent(new URL(u).searchParams.get('titles'));
    const ii = (lic, name) => ({ query: { pages: { 1: { title: t, imageinfo: [{ thumburl: 'https://upload.wikimedia.org/fake/' + encodeURIComponent(name) + '.jpg', url: 'https://upload.wikimedia.org/x.jpg', mime: 'image/jpeg', extmetadata: { LicenseShortName: { value: lic }, Artist: { value: '<a href="x">Jane <b>Doe</b></a>' }, DateTimeOriginal: { value: '1908-05-01' }, ImageDescription: { value: 'An old <i>building</i>' } } }] } } } });
    if (t.includes('Missing')) return new Response(JSON.stringify({ query: { pages: { '-1': { title: t, missing: '' } } } }));
    if (t.includes('NC')) return new Response(JSON.stringify(ii('CC BY-NC 2.0', 'nc')));
    return new Response(JSON.stringify(ii('CC BY-SA 4.0', t)));
  }
  if (u.startsWith('https://upload.wikimedia.org/fake/')) return new Response(JPG, { status: 200 });
  throw new Error('unexpected fetch ' + u);
};
const handler = makeHandler({ getStoreFn: store, fetchFn: fakeFetch, adminKey: 'testkey-testkey-1234', uploads: process.env.UPLOADS !== '0' });
const types = { '.html': 'text/html', '.js': 'text/javascript', '.json': 'application/json', '.jpg': 'image/jpeg', '.png': 'image/png', '.css': 'text/css', '.woff2': 'font/woff2', '.webmanifest': 'application/json' };
http.createServer(async (req, res) => {
  const u = new URL(req.url, 'http://x');
  if (u.pathname.startsWith('/api/')) {
    const chunks = []; for await (const c of req) chunks.push(c);
    const r = await handler(new Request('http://x' + req.url, { method: req.method, body: req.method === 'POST' ? Buffer.concat(chunks) : undefined, headers: req.headers }), { deploy: { context: ctxName } });
    res.writeHead(r.status, Object.fromEntries(r.headers)); res.end(Buffer.from(await r.arrayBuffer())); return;
  }
  let f = path.join(root, decodeURIComponent(u.pathname)); if (!f.startsWith(root)) { res.writeHead(403).end(); return; }
  if (fs.existsSync(f) && fs.statSync(f).isDirectory()) f = path.join(f, 'index.html');
  if (!fs.existsSync(f)) { res.writeHead(404).end('nf'); return; }
  res.writeHead(200, { 'content-type': types[path.extname(f)] || 'application/octet-stream', 'cache-control': 'no-store' }); fs.createReadStream(f).pipe(res);
}).listen(Number(process.argv[3] || 8765), () => console.log('ready'));
