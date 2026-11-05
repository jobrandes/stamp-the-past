// Pure logic for the community-place test (no network, no storage), so it can be unit-tested with plain node.
// Test branch only. A submission is ONE place: the contributor gives a name, a one-liner and two photo links;
// the research (story, sources, quiz) is written later by Claude and committed to the repo.
export const MAX_PHOTO = 1200 * 1024;
export const UPLOAD_LICENSES = ['CC0', 'CC BY', 'CC BY-SA'];

const clean = (s) => String(s ?? '').replace(/[\u0000-\u0008\u000b\u000c\u000e-\u001f]/g, '').replace(/\s+/g, ' ').trim();
export const stripHtml = (s) => clean(String(s ?? '').replace(/<[^>]*>/g, ' ').replace(/&amp;/g, '&').replace(/&quot;/g, '"').replace(/&#0?39;/g, "'").replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&nbsp;/g, ' '));

// Only commons.wikimedia.org File: pages are accepted, so the license can be read from the source page itself.
export function parseSourceLink(raw) {
  let u;
  try { u = new URL(String(raw || '').trim()); } catch { return null; }
  if (u.protocol !== 'https:') return null;
  if (u.hostname === 'commons.wikimedia.org') {
    let t = null;
    if (u.pathname.startsWith('/wiki/')) { try { t = decodeURIComponent(u.pathname.slice(6)); } catch { return null; } }
    else if (u.searchParams.get('title')) t = u.searchParams.get('title');
    if (!t || !/^File:/i.test(t)) return null;
    t = t.replace(/_/g, ' ').replace(/^file:/i, 'File:');
    if (t.length > 250) return null;
    return { kind: 'commons', title: t, page: 'https://commons.wikimedia.org/wiki/' + encodeURIComponent(t.replace(/ /g, '_')).replace(/%3A/g, ':').replace(/%2F/g, '/') };
  }
  // Library of Congress item pages: /item/<id>/ or /pictures/item/<id>/ (read from the LoC JSON record, checked Nov 5 2026).
  if (u.hostname === 'www.loc.gov' || u.hostname === 'loc.gov') {
    const m = u.pathname.match(/^\/(?:pictures\/)?item\/([A-Za-z0-9._-]{3,40})\/?$/);
    if (!m) return null;
    return { kind: 'loc', id: m[1], page: 'https://www.loc.gov/item/' + m[1] + '/' };
  }
  return null;
}

// Library of Congress: accept ONLY when its own rights statement is a plain "No known restrictions" (the wording used on
// Detroit Publishing, FSA/OWI and similar records). Anything that says "may be restricted", "images copied from other sources",
// "publication may be restricted" or is missing is refused, so we never guess.
export function readLoc(json) {
  const it = json?.item;
  if (!it || typeof it !== 'object') return { ok: false, error: 'The Library of Congress has no record with that address.' };
  const rights = clean(Array.isArray(it.rights_advisory) ? it.rights_advisory.join(' ') : it.rights_advisory || (Array.isArray(it.rights_information) ? it.rights_information.join(' ') : it.rights_information));
  const fine = /^no known restrictions\b/i.test(rights) && !/copied from other sources|may be restricted|publication may be|not evaluated|restricted/i.test(rights.replace(/^no known restrictions/i, ''));
  if (!fine) return { ok: false, error: `The Library of Congress does not clearly say this photo is free to use (its rights note: "${rights.slice(0, 120) || 'not stated'}"). Please pick another photo.` };
  if (it.access_restricted === true) return { ok: false, error: 'That Library of Congress record has no downloadable photo (it may be a group of images). Open a single photo from it and paste that link.' };
  const imgs = (it.image_url || []).map((x) => String(x).split('#')[0]).filter((x) => /^https:\/\/tile\.loc\.gov\/.+\.jpe?g$/i.test(x));
  const thumb = imgs.find((x) => /r\.jpe?g$/i.test(x)) || imgs.filter((x) => !/150px/.test(x)).pop();
  if (!thumb) return { ok: false, error: 'That Library of Congress record has no photo we can use.' };
  const who = (it.contributor_names || []).map((n) => clean(n).replace(/,\s*(photographer|publisher|copyright claimant|creator|author|artist|printer|lithographer|engraver|delineator)\b.*$/i, '')).filter(Boolean)[0];
  const credit = (who ? who + ' (Library of Congress)' : 'Library of Congress').slice(0, 120);
  const year = (String(it.date || '') + ' ' + [].concat(it.created_published || []).join(' ')).match(/\b(1[5-9]\d\d|20\d\d)\b/)?.[0] || '';
  const desc = '';
  return { ok: true, meta: { license: 'Public domain', credit, year, title: stripHtml(it.title).slice(0, 160), desc, thumb, mime: 'image/jpeg' } };
}

// Map a Commons license string to one of our four labels, or null when it is not free enough.
export function normalizeLicense(s) {
  const t = clean(s).toLowerCase();
  if (!t) return null;
  if (/\b(nc|nd)\b|non-?commercial|no derivat|fair use|all rights|copyrighted/.test(t)) return null;
  if (/^cc0|cc zero|cc-zero/.test(t)) return 'CC0';
  if (/public domain|^pd\b|pd-|no known copyright/.test(t)) return 'Public domain';
  if (/^cc[ -]by[ -]sa/.test(t)) return 'CC BY-SA';
  if (/^cc[ -]by\b/.test(t)) return 'CC BY';
  return null;
}

// Turn a Commons API response into {ok, meta} or {ok:false, error}.
export function readCommons(json, title) {
  const pages = json?.query?.pages ? Object.values(json.query.pages) : [];
  const p = pages[0];
  if (!p || p.missing !== undefined || !p.imageinfo?.[0]) return { ok: false, error: 'Commons has no file with that name.' };
  const ii = p.imageinfo[0], x = ii.extmetadata || {};
  const license = normalizeLicense(x.LicenseShortName?.value);
  if (!license) return { ok: false, error: `That photo's license ("${clean(x.LicenseShortName?.value) || 'not stated'}") is not one we can use. We need public domain, CC0, CC BY or CC BY-SA.` };
  if (!/^image\/(jpeg|png)$/.test(ii.mime || '')) return { ok: false, error: 'That file is not a JPEG or PNG photo.' };
  const credit = stripHtml(x.Artist?.value || x.Credit?.value).slice(0, 120) || 'Unknown author';
  const year = (stripHtml(x.DateTimeOriginal?.value || x.DateTime?.value).match(/\b(1[5-9]\d\d|20\d\d)\b/) || [''])[0];
  return { ok: true, meta: { license, credit, year, title: title.replace(/^File:/, '').slice(0, 160), desc: stripHtml(x.ImageDescription?.value).slice(0, 300), thumb: ii.thumburl || ii.url, mime: ii.mime } };
}

export function isImageBytes(b) {
  if (!b || b.length < 1000 || b.length > MAX_PHOTO) return null;
  if (b[0] === 0xff && b[1] === 0xd8 && b[2] === 0xff) return 'image/jpeg';
  if (b[0] === 0x89 && b[1] === 0x50 && b[2] === 0x4e && b[3] === 0x47) return 'image/png';
  return null;
}
export function decodeJpegDataUrl(d) {
  if (typeof d !== 'string' || !/^data:image\/jpeg;base64,[A-Za-z0-9+/=]+$/.test(d)) return null;
  const b = Buffer.from(d.split(',')[1], 'base64');
  return isImageBytes(b) === 'image/jpeg' ? b : null;
}

// Validate the short form. Returns { errs, v }. Links are parsed here; photos are fetched by the handler.
export function validate(input) {
  const errs = [];
  const t = (s, min, max, label) => { const v = clean(s); if (v.length < min || v.length > max) errs.push(`${label}: ${min ? min + ' to ' : 'up to '}${max} characters`); return v; };
  const v = {
    city: t(input.city, 2, 60, 'Town or city'), state: t(input.state, 0, 30, 'State or region'),
    place: t(input.place, 3, 80, 'Name of the place'), oneLiner: t(input.oneLiner, 10, 300, 'One line about it'),
    nickname: t(input.nickname, 0, 30, 'Nickname'),
  };
  // At least one photo is needed. "Then" only = waits for a "now" photo. "Now" only = becomes a Story stop (no old photo yet).
  const hasThenUrl = clean(input.thenUrl), hasNowUrl = clean(input.nowUrl), hasUpload = !!input.nowPhoto;
  if (hasThenUrl) { v.then = parseSourceLink(input.thenUrl); if (!v.then) errs.push('"Then" photo: paste the link to its File: page on commons.wikimedia.org, or its item page on loc.gov, or leave it empty.'); }
  if (hasNowUrl) { v.now = parseSourceLink(input.nowUrl); if (!v.now) errs.push('"Now" photo: paste a commons.wikimedia.org File: page link or a loc.gov item link, or upload your own instead.'); }
  else if (hasUpload) {
    v.nowUpload = input.nowPhoto;
    if (!decodeJpegDataUrl(input.nowPhoto)) errs.push('"Now" photo: that upload could not be read. Try another photo.');
    v.nowLicense = 'CC BY-SA'; // every uploaded photo is shared under CC BY-SA 4.0, credited to the contributor (no choice)
    v.nowCredit = t(input.nowCredit, 2, 120, 'Your photo credit');
    v.nowYear = t(input.nowYear, 4, 4, 'Year your photo was taken');
    if (!/^(19\d\d|20\d\d)$/.test(v.nowYear) || +v.nowYear > new Date().getFullYear()) errs.push('Year your photo was taken: use a real year such as 2026.');
    if (input.nowOwn !== true) errs.push('Tick "I took this photo myself" for an uploaded photo.');
  }
  if (!hasThenUrl && !hasNowUrl && !hasUpload) errs.push('Add at least one photo: an old one, a recent one, or both.');
  if (input.confirm !== true) errs.push('Please tick the box that confirms the photos are free to use and the facts are not your private information.');
  return { errs, v };
}
