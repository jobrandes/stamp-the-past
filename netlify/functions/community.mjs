// Community-place test backend. Works ONLY on non-production deploys (branch deploys / previews / local dev).
// Production answers 404, so merging this file into main cannot expose anything.
import { getStore } from '@netlify/blobs';
import { createHash, randomBytes, timingSafeEqual } from 'node:crypto';
import sharp from 'sharp';
import { validate, parseSourceLink, readCommons, readLoc, isImageBytes, decodeJpegDataUrl } from '../lib/community-core.mjs';

const json = (o, s = 200) => new Response(JSON.stringify(o), { status: s, headers: { 'content-type': 'application/json', 'cache-control': 'no-store' } });
const sha = (t) => createHash('sha256').update(t).digest('hex');
const UA = { 'user-agent': 'StampThePastTest/1.0 (https://stampthepast.com; community test)' };

// Decode and re-encode every photo on the server: rejects broken or oversized images and drops all metadata (EXIF, GPS, comments).
export async function cleanImage(buf) {
  try {
    return await sharp(buf, { limitInputPixels: 40_000_000, failOn: 'error' }).rotate().resize({ width: 1280, height: 1280, fit: 'inside', withoutEnlargement: true }).jpeg({ quality: 78 }).toBuffer();
  } catch { return null; }
}

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
    const clean = await cleanImage(buf);
    if (!clean) return { ok: false, error: 'That photo could not be read as an image. Try another photo.' };
    return { ok: true, meta: res.meta, buf: clean, type: 'image/jpeg' };
  } catch { return { ok: false, error: 'Could not download that photo from Commons. Try again in a minute.' }; }
}

async function locPhoto(link, fetchFn) {
  let j;
  try { const r = await fetchFn('https://www.loc.gov/item/' + link.id + '/?fo=json', { headers: UA }); if (!r.ok) throw new Error('x'); j = await r.json(); } catch { return { ok: false, error: 'Could not reach the Library of Congress just now (or that item does not exist). Check the link and try again in a minute.' }; }
  const res = readLoc(j);
  if (!res.ok) return res;
  try {
    const r = await fetchFn(res.meta.thumb, { headers: UA }); if (!r.ok) throw new Error('x');
    const buf = Buffer.from(await r.arrayBuffer()); const type = isImageBytes(buf);
    if (!type) return { ok: false, error: 'That photo could not be fetched at a small size. Try another photo.' };
    const clean = await cleanImage(buf);
    if (!clean) return { ok: false, error: 'That photo could not be read as an image. Try another photo.' };
    return { ok: true, meta: res.meta, buf: clean, type: 'image/jpeg' };
  } catch { return { ok: false, error: 'Could not download that photo from the Library of Congress. Try again in a minute.' }; }
}

const handle = (opts) => async (req, context) => {
  const getStoreFn = opts.getStoreFn || getStore, fetchFn = opts.fetchFn || fetch;
  const ctx = context.deploy?.context || 'dev';
  if (ctx === 'production') return json({ error: 'not found' }, 404);
  const store = getStoreFn({ name: 'community-' + ctx.replace(/[^a-z-]/g, ''), consistency: 'strong' });
  const url = new URL(req.url);
  const parts = url.pathname.replace(/^\/api\/community\/?/, '').split('/').filter(Boolean);
  const adminKey = (opts.adminKey ?? globalThis.Netlify?.env?.get?.('COMMUNITY_ADMIN_KEY') ?? '');
  const isAdmin = () => { const k = req.headers.get('x-admin-key') || ''; return adminKey.length >= 16 && k.length === adminKey.length && timingSafeEqual(Buffer.from(k), Buffer.from(adminKey)); };

  // Own-photo uploads are OFF unless COMMUNITY_UPLOADS=1 (no image scanning yet: links to Commons/LoC only).
  const uploadsOn = opts.uploads ?? (globalThis.Netlify?.env?.get?.('COMMUNITY_UPLOADS') === '1');
  if (req.method === 'GET' && parts[0] === 'config') return json({ uploads: !!uploadsOn });

  if (req.method === 'GET' && parts[0] === 'photo' && parts[1]) {
    const key = 'photo/' + parts[1].replace(/[^a-z0-9_]/gi, '');
    const e = await store.getWithMetadata(key, { type: 'arrayBuffer' });
    if (!e) return new Response('not found', { status: 404 });
    // Every submitted photo is HELD: only the admin key can see it until the place is approved (listed in status.json `added`).
    const admin = isAdmin();
    if (!admin) {
      let approved = false;
      try { const r = await fetchFn(new URL('/community/status.json', url.origin).href); if (r.ok) { const st = await r.json(); approved = (st.added || []).includes(key.split('/')[1].split('_')[0]); } } catch {}
      if (!approved) return new Response('not found', { status: 404 });
    }
    return new Response(e.data, { headers: { 'content-type': e.metadata?.type || 'image/jpeg', 'cache-control': admin ? 'private, no-store' : 'public, max-age=300' } });
  }

  // Add or replace photos from the private status link (e.g. a place that is "Waiting for a photo"). Puts the place back in the review queue.
  if (req.method === 'POST' && parts[0] === 'mine' && parts[1] && parts[2] === 'photo') {
    const id = parts[1].slice(0, 8).replace(/[^a-f0-9]/g, ''), token = parts[1].slice(8);
    const sub = await store.get('sub/' + id, { type: 'json' });
    if (!sub || sub.tokenHash !== sha(token)) return json({ error: 'That link is not valid.' }, 404);
    let body; try { body = await req.json(); } catch { return json({ errors: ['Could not read the form.'] }, 400); }
    if (!body || typeof body !== 'object' || Array.isArray(body)) return json({ errors: ['Could not read the form.'] }, 400);
    let st = { added: [], declined: {} };
    try { const r = await fetchFn(new URL('/community/status.json', url.origin).href); if (r.ok) st = await r.json(); } catch {}
    if ((st.added || []).includes(id)) return json({ errors: ['This place was already added, so its photos cannot be changed here.'] }, 400);
    if ((st.declined || {})[id]) return json({ errors: ['This place was not added, so it cannot be changed.'] }, 400);
    if (body.nowPhoto && !uploadsOn) return json({ errors: ['Photo uploads are turned off for now. Please link to a free photo on Wikimedia Commons instead.'] }, 400);
    const { errs, v } = validate({ city: sub.city, state: sub.state, place: sub.place, oneLiner: sub.oneLiner, nickname: sub.nickname || '', thenUrl: body.thenUrl, nowUrl: body.nowUrl, nowPhoto: body.nowPhoto, nowOwn: body.nowOwn, nowCredit: body.nowCredit, nowYear: body.nowYear, nowLicense: body.nowLicense, confirm: body.confirm });
    if (errs.length) return json({ errors: errs }, 400);
    const next = { ...sub };
    const { errors, photos } = await collectPhotos(v, id, next, fetchFn);
    if (errors.length) return json({ errors }, 400);
    for (const [k, b, type, own] of photos) await store.set(k, b, { metadata: own ? { type, own: true } : { type } });
    next.resubmitted = new Date().toISOString();
    await store.setJSON('sub/' + id, next);
    return json({ ok: true, status: 'received' });
  }

  if (req.method === 'GET' && parts[0] === 'mine' && parts[1]) {
    const id = parts[1].slice(0, 8).replace(/[^a-f0-9]/g, ''), token = parts[1].slice(8);
    const sub = await store.get('sub/' + id, { type: 'json' });
    if (!sub || sub.tokenHash !== sha(token)) return json({ error: 'That link is not valid.' }, 404);
    let status = 'received', note = '';
    try { const r = await fetchFn(new URL('/community/status.json', url.origin).href); if (r.ok) { const s = await r.json(); if ((s.added || []).includes(id)) status = 'added'; else if (s.waiting && s.waiting[id]) { status = 'waiting'; note = String(s.waiting[id]); } else if (s.declined && s.declined[id]) { status = 'declined'; note = String(s.declined[id]); } } } catch {}
    return json({ id, status, note, place: sub.place, city: sub.city, state: sub.state, created: sub.created, has: { then: !!sub.then, now: !!sub.now } });
  }

  // Reports: anyone may report a published place. Three reports hide it in the app until a person looks (hiding is reversible, nothing is deleted).
  // Only a count per place is stored: no reporter id, no text. The app lets one device report a place once.
  const HIDE_AT = 3;
  if (req.method === 'POST' && parts[0] === 'report' && parts[1]) {
    const id = parts[1].replace(/[^a-f0-9]/g, '').slice(0, 8);
    if (id.length !== 8) return json({ error: 'bad id' }, 400);
    let st = { added: [] };
    try { const r = await fetchFn(new URL('/community/status.json', url.origin).href); if (r.ok) st = await r.json(); } catch {}
    if (!(st.added || []).includes(id)) return json({ error: 'not a published place' }, 404);
    const cur = (await store.get('rep/' + id, { type: 'json' })) || { n: 0 };
    cur.n = Math.min((cur.n || 0) + 1, 1000); cur.last = new Date().toISOString();
    await store.setJSON('rep/' + id, cur);
    return json({ ok: true, hidden: cur.n >= HIDE_AT && !cur.cleared });
  }
  if (req.method === 'GET' && parts[0] === 'hidden') {
    const { blobs } = await store.list({ prefix: 'rep/' });
    const out = [];
    for (const b of blobs.slice(0, 200)) { const r = await store.get(b.key, { type: 'json' }); if (r && r.n >= HIDE_AT && !r.cleared) out.push(b.key.slice(4)); }
    return new Response(JSON.stringify({ hidden: out }), { headers: { 'content-type': 'application/json', 'cache-control': 'public, max-age=60' } });
  }
  // Admin only: put a hidden place back (a person looked and it is fine).
  if (req.method === 'POST' && parts[0] === 'unhide' && parts[1]) {
    if (!isAdmin()) return json({ error: 'not found' }, 404);
    const id = parts[1].replace(/[^a-f0-9]/g, '').slice(0, 8);
    const cur = (await store.get('rep/' + id, { type: 'json' })) || { n: 0 }; cur.cleared = true;
    await store.setJSON('rep/' + id, cur); return json({ ok: true });
  }

  // The inbox holds unreviewed free text and nicknames, so only the research run (admin key in the x-admin-key header) can read it.
  if (req.method === 'GET' && parts[0] === 'pending') {
    if (!isAdmin()) return json({ error: 'not found' }, 404);
    let st = { added: [], declined: {}, waiting: {} };
    try { const r = await fetchFn(new URL('/community/status.json', url.origin).href); if (r.ok) st = await r.json(); } catch {}
    const { blobs } = await store.list({ prefix: 'sub/' });
    const out = [];
    for (const b of blobs) {
      const s = await store.get(b.key, { type: 'json' }); if (!s) continue;
      if ((st.added || []).includes(s.id) || (st.declined || {})[s.id] || ((st.waiting || {})[s.id] && !s.resubmitted)) continue;
      const { tokenHash, ...pub } = s; out.push(pub);
    }
    return json({ pending: out });
  }

  if (isAdmin() && req.method === 'POST' && parts[0] === 'delete' && parts[1]) {
    const id = parts[1].replace(/[^a-f0-9]/g, '');
    for (const k of [`sub/${id}`, `photo/${id}_t`, `photo/${id}_n`]) await store.delete(k);
    return json({ ok: true, deleted: id });
  }

  if (req.method === 'POST' && parts[0] === 'submit') {
    let body;
    try { body = await req.json(); } catch { return json({ errors: ['Could not read the form.'] }, 400); }
    if (!body || typeof body !== 'object' || Array.isArray(body)) return json({ errors: ['Could not read the form.'] }, 400);
    if (body.hp) return json({ ok: true, id: 'ignored', status: 'ignored' });
    const { blobs } = await store.list({ prefix: 'sub/' });
    if (blobs.length >= 500) return json({ errors: ['The test inbox is full for now.'] }, 429);
    // Queue limit: only places still waiting for a decision count (not added or declined ones).
    let st = {};
    try { const r = await fetchFn(new URL('/community/status.json', url.origin).href); if (r.ok) st = await r.json(); } catch {}
    const handled = new Set([...(st.added || []), ...Object.keys(st.declined || {})]);
    const open = blobs.filter(b => !handled.has(b.key.slice(4))).length;
    if (open >= 60) return json({ errors: ['The review queue is full for now. Please try again in a few days.'] }, 429);
    if (body.nowPhoto && !uploadsOn) return json({ errors: ['Photo uploads are turned off for now. Please link to a free photo on Wikimedia Commons instead.'] }, 400);
    const { errs, v } = validate(body);
    if (errs.length) return json({ errors: errs }, 400);
    const id = randomBytes(4).toString('hex'), token = randomBytes(12).toString('hex');
    const sub = { id, city: v.city, state: v.state, place: v.place, oneLiner: v.oneLiner, nickname: v.nickname, created: new Date().toISOString(), tokenHash: sha(token) };
    const { errors, photos } = await collectPhotos(v, id, sub, fetchFn);
    if (errors.length) return json({ errors }, 400);
    for (const [k, b, type, own] of photos) await store.set(k, b, { metadata: own ? { type, own: true } : { type } });
    await store.setJSON('sub/' + id, sub);
    return json({ ok: true, id, status: 'received', edit: id + token });
  }

  return json({ error: 'not found' }, 404);
};

// Reads the photos named in a validated submission into `sub` and returns the blobs to store.
async function collectPhotos(v, id, sub, fetchFn) {
  const photos = [], errors = [];
  // "then" photo
  if (v.then && (v.then.kind === 'commons' || v.then.kind === 'loc')) {
    const r = await (v.then.kind === 'loc' ? locPhoto : commonsPhoto)(v.then, fetchFn);
    if (!r.ok) errors.push('"Then" photo: ' + r.error); else { sub.then = { kind: v.then.kind, page: v.then.page, license: r.meta.license, credit: r.meta.credit, year: r.meta.year, title: r.meta.title, desc: r.meta.desc, photo: true }; photos.push([`photo/${id}_t`, r.buf, r.type]); }
  }
  // "now" photo
  if (v.now) {
    if (v.now.kind === 'commons' || v.now.kind === 'loc') {
      const r = await (v.now.kind === 'loc' ? locPhoto : commonsPhoto)(v.now, fetchFn);
      if (!r.ok) errors.push('"Now" photo: ' + r.error); else { sub.now = { kind: v.now.kind, page: v.now.page, license: r.meta.license, credit: r.meta.credit, year: r.meta.year, title: r.meta.title, desc: r.meta.desc, photo: true }; photos.push([`photo/${id}_n`, r.buf, r.type]); }
    }
  } else if (v.nowUpload) {
    const buf = await cleanImage(decodeJpegDataUrl(v.nowUpload));
    if (!buf) errors.push('"Now" photo: that upload could not be read as a photo. Try another one.');
    else sub.now = { kind: 'own', license: v.nowLicense, credit: v.nowCredit, year: v.nowYear, photo: true }; if (buf) photos.push([`photo/${id}_n`, buf, 'image/jpeg', true]);
  }
  return { errors, photos };
}

export const makeHandler = (opts = {}) => {
  const h = handle(opts);
  return async (req, context) => { try { return await h(req, context); } catch (e) { console.error('community error', e?.message); return json({ errors: ['Something went wrong. Please try again.'] }, 400); } };
};
export default makeHandler();

export const config = { path: '/api/community/*', rateLimit: { windowLimit: 60, windowSize: 60, aggregateBy: ['ip', 'domain'] } };
