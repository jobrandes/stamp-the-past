// Community-place test backend. Works ONLY on non-production deploys (branch deploys / previews / local dev).
// Production answers 404, so merging this file into main cannot expose anything.
import { getStore } from '@netlify/blobs';
import { createHash, randomBytes, timingSafeEqual } from 'node:crypto';
import { validate, parseSourceLink, readCommons, isImageBytes, decodeJpegDataUrl } from '../lib/community-core.mjs';

const json = (o, s = 200) => new Response(JSON.stringify(o), { status: s, headers: { 'content-type': 'application/json', 'cache-control': 'no-store' } });
const sha = (t) => createHash('sha256').update(t).digest('hex');
const UA = { 'user-agent': 'StampThePastTest/1.0 (https://stampthepast.com; community test)' };

async function commonsPhoto(link, fetchFn) {
  const api = 'https://commons.wikimedia.org/w/api.php?action=query&format=json&prop=imageinfo&iiprop=url%7Cmime%7Csize%7Cextmetadata&iiurlwidth=640&titles=' + encodeURIComponent(link.title);
  let j;
  try { const r = await fetchFn(api, { headers: UA }); if (!r.ok) throw new Error('x'); j = await r.json(); } catch { return { ok: false, error: 'Could not reach Wikimedia Commons just now. Try again in a minute.' }; }
  const res = readCommons(j, link.title);
  if (!res.ok) return res;
  try {
    const r = await fetchFn(res.meta.thumb, { headers: UA }); if (!r.ok) throw new Error('x');
    const buf = Buffer.from(await r.arrayBuffer()); const type = isImageBytes(buf);
    if (!type) return { ok: false, error: 'That photo could not be fetched at a small size. Try another photo.' };
    return { ok: true, meta: res.meta, buf, type };
  } catch { return { ok: false, error: 'Could not download that photo from Commons. Try again in a minute.' }; }
}

export const makeHandler = (opts = {}) => async (req, context) => {
  const getStoreFn = opts.getStoreFn || getStore, fetchFn = opts.fetchFn || fetch;
  const ctx = context.deploy?.context || 'dev';
  if (ctx === 'production') return json({ error: 'not found' }, 404);
  const store = getStoreFn({ name: 'community-' + ctx.replace(/[^a-z-]/g, ''), consistency: 'strong' });
  const url = new URL(req.url);
  const parts = url.pathname.replace(/^\/api\/community\/?/, '').split('/').filter(Boolean);
  const adminKey = (opts.adminKey ?? globalThis.Netlify?.env?.get?.('COMMUNITY_ADMIN_KEY') ?? '');
  const isAdmin = () => { const k = url.searchParams.get('key') || ''; return adminKey.length >= 16 && k.length === adminKey.length && timingSafeEqual(Buffer.from(k), Buffer.from(adminKey)); };

  // Own-photo uploads are OFF unless COMMUNITY_UPLOADS=1 (no image scanning yet: links to Commons/LoC only).
  const uploadsOn = opts.uploads ?? (globalThis.Netlify?.env?.get?.('COMMUNITY_UPLOADS') === '1');
  if (req.method === 'GET' && parts[0] === 'config') return json({ uploads: !!uploadsOn });

  if (req.method === 'GET' && parts[0] === 'photo' && parts[1]) {
    const key = 'photo/' + parts[1].replace(/[^a-z0-9_]/gi, '');
    const e = await store.getWithMetadata(key, { type: 'arrayBuffer' });
    if (!e) return new Response('not found', { status: 404 });
    return new Response(e.data, { headers: { 'content-type': e.metadata?.type || 'image/jpeg', 'cache-control': 'public, max-age=300' } });
  }

  if (req.method === 'GET' && parts[0] === 'mine' && parts[1]) {
    const id = parts[1].slice(0, 8).replace(/[^a-f0-9]/g, ''), token = parts[1].slice(8);
    const sub = await store.get('sub/' + id, { type: 'json' });
    if (!sub || sub.tokenHash !== sha(token)) return json({ error: 'That link is not valid.' }, 404);
    let status = 'received', note = '';
    try { const r = await fetchFn(new URL('/community/status.json', url.origin).href); if (r.ok) { const s = await r.json(); if ((s.added || []).includes(id)) status = 'added'; else if (s.waiting && s.waiting[id]) { status = 'waiting'; note = String(s.waiting[id]); } else if (s.declined && s.declined[id]) { status = 'declined'; note = String(s.declined[id]); } } } catch {}
    return json({ id, status, note, place: sub.place, city: sub.city, state: sub.state, created: sub.created });
  }

  // The inbox list holds no personal data (no names, emails, locations or edit links), so the daily research run can read it without a secret.
  if (req.method === 'GET' && parts[0] === 'pending') {
    let st = { added: [], declined: {}, waiting: {} };
    try { const r = await fetchFn(new URL('/community/status.json', url.origin).href); if (r.ok) st = await r.json(); } catch {}
    const { blobs } = await store.list({ prefix: 'sub/' });
    const out = [];
    for (const b of blobs) {
      const s = await store.get(b.key, { type: 'json' }); if (!s) continue;
      if ((st.added || []).includes(s.id) || (st.declined || {})[s.id] || (st.waiting || {})[s.id]) continue;
      const { tokenHash, ...pub } = s; out.push(pub);
    }
    return json({ pending: out });
  }

  if (isAdmin() && req.method === 'GET' && parts[0] === 'delete' && parts[1]) {
    const id = parts[1].replace(/[^a-f0-9]/g, '');
    for (const k of [`sub/${id}`, `photo/${id}_t`, `photo/${id}_n`]) await store.delete(k);
    return json({ ok: true, deleted: id });
  }

  if (req.method === 'POST' && parts[0] === 'submit') {
    let body;
    try { body = await req.json(); } catch { return json({ errors: ['Could not read the form.'] }, 400); }
    if (body.hp) return json({ ok: true, id: 'ignored', status: 'ignored' });
    const { blobs } = await store.list({ prefix: 'sub/' });
    if (blobs.length >= 60) return json({ errors: ['The test inbox is full for now.'] }, 429);
    if (body.nowPhoto && !uploadsOn) return json({ errors: ['Photo uploads are turned off for now. Please link to a free photo on Wikimedia Commons instead.'] }, 400);
    const { errs, v } = validate(body);
    if (errs.length) return json({ errors: errs }, 400);
    const id = randomBytes(4).toString('hex'), token = randomBytes(12).toString('hex');
    const photos = [];
    const sub = { id, city: v.city, state: v.state, place: v.place, oneLiner: v.oneLiner, nickname: v.nickname, created: new Date().toISOString(), tokenHash: sha(token) };
    const errors = [];
    // "then" photo
    if (v.then && v.then.kind === 'commons') {
      const r = await commonsPhoto(v.then, fetchFn);
      if (!r.ok) errors.push('"Then" photo: ' + r.error); else { sub.then = { kind: 'commons', page: v.then.page, license: r.meta.license, credit: r.meta.credit, year: r.meta.year, title: r.meta.title, desc: r.meta.desc, photo: true }; photos.push([`photo/${id}_t`, r.buf, r.type]); }
    }
    // "now" photo
    if (v.now) {
      if (v.now.kind === 'commons') {
        const r = await commonsPhoto(v.now, fetchFn);
        if (!r.ok) errors.push('"Now" photo: ' + r.error); else { sub.now = { kind: 'commons', page: v.now.page, license: r.meta.license, credit: r.meta.credit, year: r.meta.year, title: r.meta.title, desc: r.meta.desc, photo: true }; photos.push([`photo/${id}_n`, r.buf, r.type]); }
      }
    } else if (v.nowUpload) {
      const buf = decodeJpegDataUrl(v.nowUpload);
      sub.now = { kind: 'own', license: v.nowLicense, credit: v.nowCredit, year: v.nowYear, photo: true }; photos.push([`photo/${id}_n`, buf, 'image/jpeg']);
    }
    if (errors.length) return json({ errors }, 400);
    for (const [k, b, type] of photos) await store.set(k, b, { metadata: { type } });
    await store.setJSON('sub/' + id, sub);
    return json({ ok: true, id, status: 'received', edit: id + token });
  }

  return json({ error: 'not found' }, 404);
};

export default makeHandler();

export const config = { path: '/api/community/*', rateLimit: { windowLimit: 60, windowSize: 60, aggregateBy: ['ip', 'domain'] } };
