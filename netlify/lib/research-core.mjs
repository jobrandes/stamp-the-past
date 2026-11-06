// Source-research helper for the daily community run. Pure functions with an injectable fetch, so tests need no network.
// It uses Wikipedia's official API (made for programs) and reads plain text from official pages only (.gov, .edu, Wikipedia).
const UA = { 'user-agent': 'StampThePastTest/1.0 (https://stampthepast.com; community research helper)' };
const clean = (s) => String(s ?? '').replace(/\s+/g, ' ').trim();
const toks = (s) => new Set(clean(s).toLowerCase().replace(/[^a-z0-9 ]/g, ' ').split(' ').filter((w) => w.length > 2 && !['the', 'and', 'of'].includes(w)));
export const FETCH_MAX_BYTES = 400 * 1024, TEXT_MAX = 6000;

// Which hosts may the helper read? Only official-looking ones. No IPs, no ports, https only.
export function checkFetchable(raw) {
  let u; try { u = new URL(String(raw)); } catch { return { ok: false, error: 'That is not a web address.' }; }
  if (u.protocol !== 'https:') return { ok: false, error: 'Only https addresses are allowed.' };
  if (u.username || u.password || u.port) return { ok: false, error: 'Addresses with logins or ports are not allowed.' };
  const h = u.hostname.toLowerCase();
  if (/^[\d.]+$/.test(h) || h.includes(':') || !h.includes('.')) return { ok: false, error: 'Only named websites are allowed.' };
  const okHost = h === 'en.wikipedia.org' || h.endsWith('.gov') || h.endsWith('.edu');
  if (!okHost) return { ok: false, error: 'Only Wikipedia, .gov and .edu pages can be read here. For other sites, record the place as "needs-sources".' };
  return { ok: true, url: u.toString(), host: h };
}

export function pageText(html) {
  const title = clean((/<title[^>]*>([\s\S]*?)<\/title>/i.exec(html) || [])[1] || '').replace(/&amp;/g, '&');
  const body = String(html).replace(/<(script|style|noscript|nav|footer|header|svg)[\s\S]*?<\/\1>/gi, ' ').replace(/<[^>]*>/g, ' ')
    .replace(/&nbsp;/g, ' ').replace(/&amp;/g, '&').replace(/&quot;/g, '"').replace(/&#39;|&rsquo;/g, "'").replace(/&[a-z#0-9]+;/gi, ' ');
  return { title, text: clean(body).slice(0, TEXT_MAX) };
}

export async function readPage(raw, fetchFn) {
  const c = checkFetchable(raw); if (!c.ok) return c;
  let r;
  try { r = await fetchFn(c.url, { headers: UA, redirect: 'manual', signal: AbortSignal.timeout(8000) }); } catch { return { ok: false, error: 'The page could not be reached.' }; }
  if (r.status >= 300 && r.status < 400) {
    const loc = r.headers.get('location') || ''; let to = ''; try { to = new URL(loc, c.url).toString(); } catch { /* ignore */ }
    const c2 = to && checkFetchable(to); return { ok: false, error: 'The page redirects' + (c2 && c2.ok ? '. Try this address instead: ' + c2.url : ' to a site that is not allowed.') };
  }
  if (!r.ok) return { ok: false, error: 'The site answered ' + r.status + '.' };
  const type = (r.headers.get('content-type') || '').toLowerCase();
  if (!/text\/html|text\/plain|application\/xhtml/.test(type)) return { ok: false, error: 'That address is not a text page.' };
  const buf = Buffer.from(await r.arrayBuffer());
  if (buf.length > FETCH_MAX_BYTES) return { ok: false, error: 'The page is too large to read here.' };
  const { title, text } = pageText(buf.toString('utf8'));
  return { ok: true, url: c.url, title, text };
}

// Wikipedia: search + intro + coordinates in one call, then the article's reference links.
export async function wikiLookup(place, city, state, fetchFn) {
  const q = clean([place, city, state].filter(Boolean).join(' '));
  const api = 'https://en.wikipedia.org/w/api.php?action=query&format=json&generator=search&gsrlimit=3&prop=extracts%7Ccoordinates%7Cinfo&exintro=1&explaintext=1&exsentences=8&inprop=url&gsrsearch=' + encodeURIComponent(q);
  let j; try { const r = await fetchFn(api, { headers: UA, signal: AbortSignal.timeout(8000) }); if (!r.ok) throw 0; j = await r.json(); } catch { return { ok: false, error: 'Wikipedia could not be reached.' }; }
  const pages = Object.values((j.query || {}).pages || {}).sort((a, b) => (a.index || 9) - (b.index || 9));
  const want = toks(place), cityT = toks(city);
  const cands = [];
  for (const p of pages) {
    const have = toks(p.title); let hit = 0; want.forEach((w) => { if (have.has(w)) hit++; });
    const ratio = want.size ? hit / want.size : 0;
    const ext = clean(p.extract || ''); const cityHit = [...cityT].some((w) => ext.toLowerCase().includes(w) || have.has(w));
    const geo = p.coordinates && p.coordinates[0] ? [Number(p.coordinates[0].lat), Number(p.coordinates[0].lon)] : null;
    cands.push({ title: p.title, url: p.fullurl, summary: ext, geo, match: ratio >= 0.6 && (cityHit || !cityT.size) ? 'strong' : ratio >= 0.5 ? 'possible' : 'weak' });
  }
  const top = cands.find((c) => c.match !== 'weak');
  if (top) {
    const refsApi = 'https://en.wikipedia.org/w/api.php?action=parse&format=json&prop=externallinks&redirects=1&page=' + encodeURIComponent(top.title);
    try {
      const r = await fetchFn(refsApi, { headers: UA, signal: AbortSignal.timeout(8000) }); const k = await r.json();
      const seen = new Set(); top.links = [];
      for (const l of (k.parse || {}).externallinks || []) {
        const c = checkFetchable(String(l).replace(/^\/\//, 'https://'));
        if (c.ok && !c.host.endsWith('wikipedia.org') && !seen.has(c.url) && top.links.length < 12) { seen.add(c.url); top.links.push(c.url); }
      }
    } catch { top.links = []; }
  }
  return { ok: true, query: q, candidates: cands, best: top ? top.title : null };
}
