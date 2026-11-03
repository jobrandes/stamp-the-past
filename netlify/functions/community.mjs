// Community-city test backend. Works ONLY on non-production deploys (branch deploys / previews / local dev).
// Production answers 404, so merging this file into main cannot expose anything.
import { getStore } from '@netlify/blobs';
import { createHash, randomBytes } from 'node:crypto';
import { validate, decodeJpeg, buildPack } from '../lib/community-core.mjs';

const json = (o, s = 200) => new Response(JSON.stringify(o), { status: s, headers: { 'content-type': 'application/json', 'cache-control': 'no-store' } });
const sha = (t) => createHash('sha256').update(t).digest('hex');

export const makeHandler = (getStoreFn) => async (req, context) => {
  const ctx = context.deploy?.context || 'dev';
  if (ctx === 'production') return json({ error: 'not found' }, 404);
  const store = getStoreFn({ name: 'community-' + ctx.replace(/[^a-z-]/g, ''), consistency: 'strong' });
  const path = new URL(req.url).pathname.replace(/^\/api\/community\/?/, '');
  const parts = path.split('/').filter(Boolean);

  if (req.method === 'GET' && parts[0] === 'list') {
    const { blobs } = await store.list({ prefix: 'sub/' });
    const packs = [], photos = {};
    for (const b of blobs) {
      const sub = await store.get(b.key, { type: 'json' });
      if (!sub || sub.hidden) continue;
      const r = buildPack(sub); packs.push(r.pack); Object.assign(photos, r.photos);
    }
    packs.sort((a, b) => a.name.localeCompare(b.name));
    return json({ packs, photos });
  }

  if (req.method === 'GET' && parts[0] === 'photo' && parts[1]) {
    const key = 'photo/' + parts[1].replace(/[^a-z0-9_]/gi, '');
    const data = await store.get(key, { type: 'arrayBuffer' });
    if (!data) return new Response('not found', { status: 404 });
    return new Response(data, { headers: { 'content-type': 'image/jpeg', 'cache-control': 'public, max-age=300' } });
  }

  if (req.method === 'GET' && parts[0] === 'mine' && parts[1]) {
    const id = parts[1].slice(0, 8).replace(/[^a-f0-9]/g, ''), token = parts[1].slice(8);
    const sub = await store.get('sub/' + id, { type: 'json' });
    if (!sub || sub.tokenHash !== sha(token)) return json({ error: 'That edit link is not valid.' }, 404);
    const { tokenHash, ...pub } = sub;
    return json({ sub: pub });
  }

  if (req.method === 'POST' && parts[0] === 'submit') {
    let body;
    try { body = await req.json(); } catch { return json({ errors: ['Could not read the form.'] }, 400); }
    if (body.hp) return json({ ok: true, id: 'ignored' }); // honeypot
    let existing = null, id, token;
    if (body.edit) {
      id = String(body.edit).slice(0, 8).replace(/[^a-f0-9]/g, ''); token = String(body.edit).slice(8);
      existing = await store.get('sub/' + id, { type: 'json' });
      if (!existing || existing.tokenHash !== sha(token)) return json({ errors: ['That edit link is not valid.'] }, 403);
    } else {
      const { blobs } = await store.list({ prefix: 'sub/' });
      if (blobs.length >= 25) return json({ errors: ['The test is full for now (25 cities).'] }, 429);
      id = randomBytes(4).toString('hex'); token = randomBytes(12).toString('hex');
    }
    const { errs, clean } = validate(body, existing);
    if (errs.length) return json({ errors: errs }, 400);
    const sub = { id, ...clean, nickname: clean.nickname, created: existing?.created || new Date().toISOString(), updated: new Date().toISOString(), tokenHash: existing?.tokenHash || sha(token) };
    // photos: decode and store; 'keep' reuses what is already stored. Strip everything but pixels by re-using the client's JPEG re-encode.
    const writes = [];
    for (let i = 0; i < 4; i++) for (const era of ['then', 'now']) {
      const p = sub.stops[i][era], key = `photo/${id}_${i + 1}${era === 'then' ? 't' : 'n'}`;
      if (p.photo === 'keep') { delete p.photo; continue; }
      const buf = decodeJpeg(p.photo);
      if (!buf) return json({ errors: [`Place ${i + 1} ${era} photo is not a usable JPEG under 900 KB.`] }, 400);
      writes.push([key, buf]); delete p.photo;
    }
    if (existing) for (let i = 0; i < 4; i++) for (const era of ['then', 'now']) { /* keep flags already removed above */ }
    for (const [k, b] of writes) await store.set(k, b, { metadata: { type: 'image/jpeg' } });
    await store.setJSON('sub/' + id, sub);
    return json({ ok: true, id, edit: id + token });
  }

  return json({ error: 'not found' }, 404);
};

export default makeHandler(getStore);

export const config = { path: '/api/community/*', rateLimit: { windowLimit: 60, windowSize: 60, aggregateBy: ['ip', 'domain'] } };
