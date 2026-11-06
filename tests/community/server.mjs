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
  if (u.includes('/community/places.json')) { const f = path.join(root, 'community/places.json'); return fs.existsSync(f) ? new Response(fs.readFileSync(f), { status: 200 }) : new Response('nf', { status: 404 }); }
  if (u.includes('/community/status.json')) { const f = path.join(root, 'community/status.json'); return fs.existsSync(f) ? new Response(fs.readFileSync(f), { status: 200 }) : new Response('nf', { status: 404 }); }
  if (u.startsWith('https://commons.wikimedia.org/w/api.php')) {
    const t = decodeURIComponent(new URL(u).searchParams.get('titles'));
    const ii = (lic, name) => ({ query: { pages: { 1: { title: t, imageinfo: [{ thumburl: 'https://upload.wikimedia.org/fake/' + encodeURIComponent(name) + '.jpg', url: 'https://upload.wikimedia.org/x.jpg', mime: 'image/jpeg', extmetadata: { LicenseShortName: { value: lic }, Artist: { value: '<a href="x">Jane <b>Doe</b></a>' }, DateTimeOriginal: { value: '1908-05-01' }, ImageDescription: { value: 'An old <i>building</i>' } } }] } } } });
    if (t.includes('Missing')) return new Response(JSON.stringify({ query: { pages: { '-1': { title: t, missing: '' } } } }));
    if (t.includes('NC')) return new Response(JSON.stringify(ii('CC BY-NC 2.0', 'nc')));
    return new Response(JSON.stringify(ii('CC BY-SA 4.0', t)));
  }
  if (u.startsWith('https://www.loc.gov/item/')) {
    const id = u.split('/item/')[1].split('/')[0];
    if (id.includes('gone')) return new Response('nf', { status: 404 });
    const ra = id.includes('rstr') ? 'Publication may be restricted. For information see Rights and Restrictions.' : id.includes('copied') ? 'No known restrictions on images made by the U.S. Government; images copied from other sources may be restricted.' : 'No known restrictions on publication.';
    return new Response(JSON.stringify({ item: { title: 'Fake Depot, 1906', date: '1906-01-01', rights_advisory: ra, access_restricted: false, contributor_names: ['Detroit Publishing Co., publisher'], image_url: ['https://tile.loc.gov/fake/x_150px.jpg#h=1&w=1', 'https://tile.loc.gov/fake/xr.jpg#h=640&w=505'], description: ['A test depot.'] } }));
  }
  if (u.startsWith('https://tile.loc.gov/fake/')) return new Response(JPG, { status: 200 });
  if (u.startsWith('https://upload.wikimedia.org/fake/')) return new Response(JPG, { status: 200 });
  if (u.startsWith('https://en.wikipedia.org/w/api.php')) {
    const sp = new URL(u).searchParams;
    if (sp.get('generator') === 'search') {
      const q = sp.get('gsrsearch') || '';
      if (q.includes('Nowhere')) return new Response(JSON.stringify({ batchcomplete: '' }));
      const pg = q.includes('Unrelated') ? { 5: { index: 1, title: 'Bridge Over Water', fullurl: 'https://en.wikipedia.org/wiki/Bridge_Over_Water', extract: 'A bridge.' } }
        : { 7: { index: 1, title: 'Fake Depot', fullurl: 'https://en.wikipedia.org/wiki/Fake_Depot', extract: 'Fake Depot is a historic railroad depot in Reno, Nevada, built in 1906.', coordinates: [{ lat: 39.53, lon: -119.81 }] }, 8: { index: 2, title: 'Fake Depot (band)', fullurl: 'https://en.wikipedia.org/wiki/Fake_Depot_(band)', extract: 'A band.' } };
      return new Response(JSON.stringify({ query: { pages: pg } }));
    }
    if (sp.get('action') === 'parse') return new Response(JSON.stringify({ parse: { externallinks: ['https://www.nps.gov/fake/depot.htm', 'https://shop.example.com/x', 'https://en.wikipedia.org/wiki/Other', '//www.nevadaculture.gov/fake', 'http://insecure.gov/x'] } }));
  }
  if (u === 'https://www.nps.gov/fake/depot.htm') return new Response('<html><head><title>Fake Depot - NPS</title><style>.a{}</style></head><body><nav>menu</nav><p>The depot opened in 1906 &amp; closed in 1971.</p><script>x()</script></body></html>', { status: 200, headers: { 'content-type': 'text/html' } });
  if (u === 'https://www.example.gov/redirect') return new Response('', { status: 301, headers: { location: 'https://evil.example.com/x' } });
  if (u === 'https://www.example.gov/moved') return new Response('', { status: 301, headers: { location: 'https://www.nps.gov/fake/depot.htm' } });
  if (u === 'https://www.example.gov/file.pdf') return new Response('%PDF', { status: 200, headers: { 'content-type': 'application/pdf' } });
  if (u === 'https://www.example.gov/missing') return new Response('nf', { status: 404 });
  throw new Error('unexpected fetch ' + u);
};
const handler = makeHandler({ getStoreFn: store, fetchFn: fakeFetch, adminKey: 'testkey-testkey-1234', uploads: process.env.UPLOADS !== '0' });
const types = { '.html': 'text/html', '.js': 'text/javascript', '.json': 'application/json', '.jpg': 'image/jpeg', '.png': 'image/png', '.css': 'text/css', '.woff2': 'font/woff2', '.webmanifest': 'application/json' };
http.createServer(async (req, res) => {
  const u = new URL(req.url, 'http://x');
  if (u.pathname.startsWith('/__age/')) { const id = u.pathname.slice(7), k = 'sub/' + id, o = mem.get(k); if (o) { o.created = new Date(Date.now() - Number(u.searchParams.get('days')) * 86400000).toISOString(); } res.writeHead(o ? 200 : 404).end('ok'); return; }
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
