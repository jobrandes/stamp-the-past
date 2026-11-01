#!/usr/bin/env python3
"""Build the app from src/ into a single self-contained index.html.
Usage: python3 build.py            (writes ./index.html)
Adding a town: drop src/packs/<id>.json and add its id to src/packs/index.json."""
import json,base64,os
R=os.path.dirname(os.path.abspath(__file__))+'/'
def rd(p,mode='r'): return open(R+p,mode).read() if mode=='r' else open(R+p,'rb').read()
keys=json.loads(rd('src/photos/manifest.json'))
for k in keys: assert os.path.exists(R+f'src/photos/{k}.jpg'), f'photo file missing: {k}'
photos={k:f'photos/{k}.jpg' for k in keys}  # loaded on demand as files, not embedded
order=json.loads(rd('src/packs/index.json'))['order']
packs={k:json.loads(rd(f'src/packs/{k}.json')) for k in order}
# every photo a pack references must exist
for k,p in packs.items():
    for st in p['stops']:
        for era in ('then','now'):
            ph=st[era].get('ph')
            assert not ph or ph['k'] in photos, f'{k}/{st["id"]}/{era}: missing photo {ph["k"]}'
    assert not p.get('heroKey') or p['heroKey'] in photos, f'{k}: missing hero'
idx=json.loads(rd('src/packs/index.json'))
# Story stops live apart from the town packs (src/tours/*.json). Only stops whose access and safety were checked (access_check) ship.
tours=[]
for _f in sorted(os.listdir(R+'src/tours')) if os.path.isdir(R+'src/tours') else []:
    if not _f.endswith('.json'): continue
    _t=json.loads(rd('src/tours/'+_f)); _t['stops']=[s for s in _t['stops'] if s.get('access_check')]
    for s in _t['stops']:
        ph=s.get('ph'); assert not ph or ph['k'] in photos, f'tour {_t["id"]}/{s["id"]}: missing photo {ph["k"]}'
    if _t['stops']: tours.append(_t)
data={'boss':json.loads(rd('src/boss.json')),'right':json.loads(rd('src/right.json')),'order':order,'soon':idx.get('soon',[]),'packs':packs,'tours':tours}
js=rd('src/app.js').replace('__PHOTOS__',json.dumps(photos,ensure_ascii=False,separators=(',',':'))).replace('__DATA__',json.dumps(data,ensure_ascii=False,separators=(',',':')))
out=rd('src/head.html')+'<style>\n'+rd('src/styles.css')+'</style>'+rd('src/body.html')+'<script>\n'+js+'</script>'
open(R+'index.html','w').write(out)
print('built index.html',len(out)//1024,'KB;',len(photos),'photos;',len(packs),'towns')

# Standalone copy for static hosting (Netlify test site). Same content, wrapped in a full document.
os.makedirs(R+'site',exist_ok=True)
reset='<style>:root{color-scheme:light;padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}body{margin:0}img{max-width:100%}[hidden]{display:none!important}</style>'
full=('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><meta name="robots" content="noindex"><link rel="manifest" href="manifest.webmanifest"><link rel="apple-touch-icon" href="apple-touch-icon.png"><meta name="theme-color" content="#0e1d33"><meta name="apple-mobile-web-app-capable" content="yes"><meta name="apple-mobile-web-app-title" content="Stamp the Past">'
  +rd('src/head.html')+reset+'<style>\n'+rd('src/styles.css')+'</style></head><body>'+rd('src/body.html')+'<form name="report" method="POST" data-netlify="true" netlify-honeypot="bot-field" hidden><input name="form-name" value="report"><input name="bot-field"><input name="where"><input name="message"><input name="contact"></form><script>\n'+js+'</script></body></html>')
open(R+'site/play.html','w').write(full)
open(R+'site/_headers','w').write('/*\n  X-Content-Type-Options: nosniff\n  Referrer-Policy: strict-origin-when-cross-origin\n/play\n  X-Robots-Tag: noindex\n/play.html\n  X-Robots-Tag: noindex\n')

import shutil
for pg in ('privacy.html','support.html'):
    shutil.copy(R+'src/pages/'+pg,R+'site/'+pg)
shutil.rmtree(R+'site/photos',ignore_errors=True); os.makedirs(R+'site/photos')
for k in keys: shutil.copy(R+f'src/photos/{k}.jpg',R+f'site/photos/{k}.jpg')
shutil.rmtree(R+'site/fonts',ignore_errors=True); shutil.copytree(R+'src/fonts',R+'site/fonts')
print('copied pages and',len(keys),'photos and fonts')

# --- offline support for the static site ---
import hashlib
h=hashlib.sha1(full.encode()).hexdigest()[:10]
open(R+'site/sw.js','w').write(rd('src/sw.js').replace('__BUILD__',h))
open(R+'site/manifest.webmanifest','w').write(json.dumps({"name":"Stamp the Past","short_name":"Stamp the Past","start_url":"play.html","scope":"./","display":"standalone","background_color":"#0e1d33","theme_color":"#0e1d33","description":"Missions for real places.","icons":[{"src":"icon-192.png","sizes":"192x192","type":"image/png"},{"src":"icon-512.png","sizes":"512x512","type":"image/png"},{"src":"icon-maskable-512.png","sizes":"512x512","type":"image/png","purpose":"maskable"}]}))
for f in ('icon-192.png','icon-512.png','icon-maskable-512.png','apple-touch-icon.png'):
    shutil.copy(R+'src/assets/'+f,R+'site/'+f)
hd=open(R+'site/_headers').read()+'/sw.js\n  Cache-Control: no-cache\n/index.html\n  Cache-Control: no-cache\n'
open(R+'site/_headers','w').write(hd)
print('offline files written, build',h)

# --- landing page at the site root (the app itself lives at /play) ---
NEAR_ZONES={'America/New_York':'ny','America/Toronto':'buffalo','America/Detroit':'detroit','America/Chicago':'chicago','America/Indiana/Indianapolis':'indianapolis','America/Indianapolis':'indianapolis','America/Kentucky/Louisville':'louisville','America/Denver':'denver','America/Boise':'saltlake','America/Phoenix':'phoenix','America/Anchorage':'sitka','Pacific/Honolulu':'honolulu'}
near={}
for t in sorted(set(NEAR_ZONES.values())|{'ny'}):
    c=packs[t]; L=[]
    for st in c['stops']:
        ph=(st.get('now') or {}).get('ph')
        if ph and len(L)<4: L.append({'src':'photos/'+ph['k']+'.jpg','alt':(st['now'].get('label') or st['name'])+', '+c['name'],'by':ph.get('by',''),'lic':ph.get('lic','')})
    assert len(L)==4,t
    near[t]={'name':c['name'],'stamps':L}
land=rd('src/landing.html').replace('{{TOWNS}}',str(len(order))).replace('{{NEAR}}',json.dumps({'zones':NEAR_ZONES,'towns':near},ensure_ascii=False,separators=(',',':')))
assert '{{' not in land
open(R+'site/index.html','w').write(land)
open(R+'site/google7a48ffa7f434a573.html','w').write('google-site-verification: google7a48ffa7f434a573.html')
open(R+'site/robots.txt','w').write('User-agent: *\nAllow: /\nDisallow: /play\nSitemap: https://stampthepast.com/sitemap.xml\n')
open(R+'site/sitemap.xml','w').write('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join(f'<url><loc>https://stampthepast.com/{u}</loc></url>' for u in ('','privacy.html','support.html'))+'</urlset>')
print('landing page written,',len(land)//1024,'KB')

# --- crawlable town and stop pages (see seo.py) ---
import re as _re,sys
sys.path.insert(0,R)
import seo
_ts=_re.search(r'var TSTATE=(\{.*?\}), TFULL=(\{.*?\});',rd('src/app.js'))
seo_urls=seo.build(R,packs,order,json.loads(_ts.group(1)),json.loads(_ts.group(2)))
seo_urls.append(seo.daily_page(R,packs,order,json.loads(_ts.group(1))))
sm=['','privacy.html','support.html']
open(R+'site/sitemap.xml','w').write('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join(f'<url><loc>https://stampthepast.com/{u}</loc></url>' for u in sm)+''.join(f'<url><loc>https://stampthepast.com{u}</loc></url>' for u in seo_urls)+'</urlset>')
seo.test_pages(R)
print('seo pages:',len(seo_urls))
