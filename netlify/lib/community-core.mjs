// Pure logic for the community-city test (no network, no storage), so it can be unit-tested with plain node.
// Test branch only. Nothing here ships to the live site or the app.
export const THEN_HOSTS = ['commons.wikimedia.org', 'upload.wikimedia.org', 'loc.gov', 'www.loc.gov', 'tile.loc.gov', 'cdn.loc.gov'];
export const THEN_LICENSES = ['Public domain', 'CC0', 'CC BY', 'CC BY-SA'];
export const NOW_LICENSES = ['CC0', 'CC BY', 'CC BY-SA', 'Public domain'];
export const MAX_PHOTO = 900 * 1024;

const esc = (s) => String(s).replace(/[\u0000-\u0008\u000b\u000c\u000e-\u001f]/g, '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
const txt = (s, min, max, label, errs) => {
  const v = String(s ?? '').replace(/\s+/g, ' ').trim();
  if (v.length < min || v.length > max) errs.push(`${label}: ${min ? 'needs ' + min + ' to ' : 'up to '}${max} characters`);
  return v;
};
const url = (s, label, errs, hosts) => {
  try {
    const u = new URL(String(s || '').trim());
    if (u.protocol !== 'https:') throw new Error('x');
    if (hosts && !hosts.includes(u.hostname)) { errs.push(`${label}: must be a link on ${hosts.filter((h) => !h.startsWith('upload') && !h.startsWith('tile') && !h.startsWith('cdn') && !h.startsWith('www')).join(' or ')}`); return ''; }
    return u.href.slice(0, 400);
  } catch { errs.push(`${label}: needs a full https:// link`); return ''; }
};

export function isJpegDataUrl(d) { return typeof d === 'string' && /^data:image\/jpeg;base64,[A-Za-z0-9+/=]+$/.test(d); }
export function decodeJpeg(d) {
  const b = Buffer.from(d.split(',')[1], 'base64');
  if (b.length < 1000 || b.length > MAX_PHOTO || b[0] !== 0xff || b[1] !== 0xd8 || b[2] !== 0xff) return null;
  return b;
}

// Returns { errs:[], clean } where clean has plain-text (unescaped) fields and photo fields still as data URLs or 'keep'.
export function validate(input, existing) {
  const errs = [];
  const city = txt(input.city, 2, 60, 'City', errs);
  const state = txt(input.state, 0, 30, 'State or region', errs);
  const nick = txt(input.nickname, 0, 30, 'Nickname', errs);
  const stopsIn = Array.isArray(input.stops) ? input.stops : [];
  if (stopsIn.length !== 4) errs.push('Exactly four places are needed.');
  const stops = stopsIn.slice(0, 4).map((s, i) => {
    const w = `Place ${i + 1}`;
    const e = [];
    const name = txt(s.name, 3, 80, `${w} name`, e);
    const story = String(s.story ?? '').replace(/\r/g, '').split(/\n{2,}/).map((x) => x.replace(/\s+/g, ' ').trim()).filter(Boolean);
    const sl = story.join(' ').length;
    if (sl < 80 || sl > 1500 || story.length > 4) e.push(`${w} story: 80 to 1500 characters, up to 4 short paragraphs`);
    const address = txt(s.address, 0, 120, `${w} address`, e);
    let geo = null;
    if (s.lat !== '' && s.lat != null && s.lon !== '' && s.lon != null) {
      const la = Number(s.lat), lo = Number(s.lon);
      if (!(la >= -90 && la <= 90 && lo >= -180 && lo <= 180)) e.push(`${w}: latitude/longitude out of range`); else geo = [Math.round(la * 1e4) / 1e4, Math.round(lo * 1e4) / 1e4];
    }
    const srcIn = (Array.isArray(s.sources) ? s.sources : []).filter((x) => x && (x.u || x.t));
    if (srcIn.length < 2 || srcIn.length > 5) e.push(`${w}: give 2 to 5 sources`);
    const sources = srcIn.slice(0, 5).map((x, k) => ({ t: txt(x.t, 3, 100, `${w} source ${k + 1} title`, e), u: url(x.u, `${w} source ${k + 1}`, e) }));
    const eraErr = (era, T) => {
      const p = s[era] || {};
      const lab = `${w} ${era === 'then' ? '"Then"' : '"Now"'} photo`;
      const keep = p.photo === 'keep' && existing;
      if (!keep && !isJpegDataUrl(p.photo)) e.push(`${lab}: add a photo`);
      const o = { photo: keep ? 'keep' : p.photo };
      o.license = T.licenses.includes(p.license) ? p.license : (e.push(`${lab}: pick a license`), '');
      o.credit = txt(p.credit, 2, 120, `${lab} credit`, e);
      o.year = txt(p.year, 1, 12, `${lab} year`, e);
      o.caption = txt(p.caption, 3, 140, `${lab} caption`, e);
      o.own = !!p.own;
      if (era === 'then') o.page = url(p.page, `${lab} source page`, e, THEN_HOSTS);
      else if (o.own) { o.page = ''; } else o.page = url(p.page, `${lab} source page`, e, THEN_HOSTS);
      return o;
    };
    const then = eraErr('then', { licenses: THEN_LICENSES });
    const now = eraErr('now', { licenses: NOW_LICENSES });
    let q = null;
    if (s.q && (s.q.prompt || s.q.correct)) {
      const wrong = (Array.isArray(s.q.wrong) ? s.q.wrong : []).map((x) => String(x || '').replace(/\s+/g, ' ').trim()).filter(Boolean);
      const prompt = txt(s.q.prompt, 10, 200, `${w} question`, e), correct = txt(s.q.correct, 1, 80, `${w} right answer`, e), hint = txt(s.q.hint, 5, 160, `${w} hint`, e);
      const all = [correct, ...wrong.slice(0, 3)];
      if (wrong.length < 2 || new Set(all.map((x) => x.toLowerCase())).size !== all.length) e.push(`${w}: give 2 or 3 different wrong answers`);
      else if (hint.toLowerCase().includes(correct.toLowerCase())) e.push(`${w}: the hint must not contain the right answer`);
      else q = { prompt, correct, wrong: wrong.slice(0, 3), hint };
    }
    errs.push(...e);
    return { name, story, address, geo, sources, then, now, q };
  });
  const names = stops.map((s) => s.name.toLowerCase());
  if (new Set(names).size !== names.length) errs.push('The four places need four different names.');
  if (input.confirm !== true) errs.push('Please tick the box that says the photos and sources are yours to share.');
  return { errs, clean: { city, state, nickname: nick, stops } };
}

const firstSentence = (s, max) => { const m = s.match(/^.*?[.!?](?=\s|$)/); const f = (m ? m[0] : s); return f.length > max ? f.slice(0, max - 1).trimEnd() + '…' : f; };
const photoKey = (id, n, era) => `cm_${id}_${n}${era === 'then' ? 't' : 'n'}`;
export const photoUrl = (key) => `/api/community/photo/${key.slice(3)}`;

// sub = stored submission (plain text fields). Returns a full pack in the app's schema, plus the photo url map.
export function buildPack(sub) {
  const id = 'c' + sub.id;
  const esq = esc;
  const city = sub.city;
  const initials = (city.match(/[A-Za-z]/g) || ['C', 'M']).slice(0, 2).join('').toUpperCase().padEnd(2, 'X');
  const photos = {};
  const names = sub.stops.map((s) => s.name);
  const ccLink = (l) => ({ 'CC0': 'https://creativecommons.org/publicdomain/zero/1.0/', 'CC BY': 'https://creativecommons.org/licenses/by/4.0/', 'CC BY-SA': 'https://creativecommons.org/licenses/by-sa/4.0/', 'Public domain': 'https://creativecommons.org/publicdomain/mark/1.0/' }[l]);
  const ph = (p, key) => { const o = { k: key, by: esq(p.credit), lic: p.license, note: p.own ? 'Photo by the contributor' : 'resized' }; o.lu = ccLink(p.license); o.page = p.page || 'https://stampthepast.com/'; return o; };
  const stops = sub.stops.map((s, i) => {
    const n = i + 1, sid = 's' + n;
    const kt = photoKey(sub.id, n, 'then'), kn = photoKey(sub.id, n, 'now');
    photos[kt] = photoUrl(kt); photos[kn] = photoUrl(kn);
    const story = s.story.map(esq);
    const fact = esq(firstSentence(s.story[0], 150));
    const where = s.address ? ` at ${esq(s.address)}` : '';
    const opts = s.q ? [s.q.correct, ...s.q.wrong] : names.slice();
    const ansText = s.q ? s.q.correct : s.name;
    // rotate the right answer through slots deterministically so it is not always first
    const rot = (i + sub.id.charCodeAt(0)) % opts.length;
    const options = opts.slice(rot).concat(opts.slice(0, rot));
    const answer = options.indexOf(ansText);
    return {
      id: sid, name: esq(s.name), short: esq(s.name.length > 22 ? s.name.slice(0, 21).trimEnd() + '…' : s.name), badge: esq(s.name), tag: `Stop ${n} of 4`,
      teaser: esq(firstSentence(s.story[0], 120)), map: esq(s.address || `${s.name}, ${city}`),
      ...(s.geo ? { geo: [s.geo[0], s.geo[1], 300] } : {}),
      clue: `Find ${esq(s.name)}${where}. ${esq(firstSentence(s.story[0], 200))}`,
      safety: 'Stay on public paths and sidewalks, and cross at corners.', field: 'Community-added. Not yet walked or checked on site.',
      q: s.q ? { prompt: esq(s.q.prompt), options: options.map(esq), answer, hint: esq(s.q.hint), verify: 'Written by the contributor from their own sources. Check it on site.' }
        : { prompt: 'Which of these is the name of the place you are standing at?', options: options.map(esq), answer, hint: 'Look for a sign, plaque or the address in the clue.', verify: 'Placeholder question made from the four place names. A better one can be added.' },
      then: { ph: ph(s.then, kt), yr: esq(s.then.year), label: esq(s.then.caption), line: esq(s.then.caption), link: { t: 'Look for historic photos at the Library of Congress', u: 'https://www.loc.gov/pictures/search/?q=' + encodeURIComponent(city) } },
      now: { yr: esq(s.now.year), head: 'Today', label: esq(s.now.caption), line: esq(s.now.caption), ph: ph(s.now, kn) },
      story, fact, disputed: '', claims: [], sources: s.sources.map((x) => ({ t: esq(x.t), u: x.u })),
      card: { a: esq(s.then.year), b: esq(s.now.year), la: esq(s.then.caption).slice(0, 40), lb: esq(s.now.caption).slice(0, 40) },
      community: true,
    };
  });
  const k0 = photoKey(sub.id, 1, 'now');
  const pack = {
    id, name: esq(city), explorer: esq(city) + ' Explorer', initials, community: true,
    ranks: [[0, 'Newcomer'], [100, 'Visitor'], [250, 'Local Guide'], [450, 'Regular'], [600, esq(city) + ' Historian']],
    heroKey: k0, heroAlt: esq(sub.stops[0].now.caption), heroLi: '', heroCredit: 'Photo: ' + esq(sub.stops[0].now.credit) + ' · ' + sub.stops[0].now.license,
    mission: `Community-added by ${sub.nickname ? esq(sub.nickname) : 'a contributor'}. Find four places in ${esq(city)}. At each one, check in to earn its badge and unlock its story. Written from the contributor's own sources and not yet checked by us. Everything stays on this phone.`,
    afterDone: `All four badges earned. ${esq(city)} is stamped.`, safetyNote: '<li>Stay on public paths and sidewalks.</li>',
    badgeMap: Object.fromEntries(stops.map((s, i) => [s.id, [photoKey(sub.id, i + 1, 'now'), '50% 50%']])),
    level: 'Community', region: 'Community-added', stops,
  };
  return { pack, photos };
}
