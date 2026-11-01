#!/usr/bin/env python3
"""Nearby stops: location is only asked for on a tap, every fallback works, Story stops stay separate from progress,
nothing leaves the phone, and the screens fit every width."""
import os,json,re
from playwright.sync_api import sync_playwright
R=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))+'/'
import subprocess,time
# served over http like the real site (file:// pages can lose a localStorage write if reloaded straight away)
srv=subprocess.Popen(['python3','-m','http.server','8771','-d',R+'site'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); time.sleep(1)
U='http://localhost:8771/play.html'
bad=[];errs=[]
def need(c,m):
    if not c: bad.append(m)
COUNT="window.__geo={get:0,watch:0};try{var g=navigator.geolocation,og=g.getCurrentPosition.bind(g),ow=g.watchPosition.bind(g);g.getCurrentPosition=function(){window.__geo.get++;return og.apply(null,arguments)};g.watchPosition=function(){window.__geo.watch++;return ow.apply(null,arguments)}}catch(e){}"
RENO=(39.5247,-119.8124)
with sync_playwright() as p:
    b=p.chromium.launch()
    def new(lat=RENO[0],lon=RENO[1],allow=True,seed=None,w=390,h=844,geook=False):
        kw=dict(viewport={'width':w,'height':h},reduced_motion='reduce')
        if allow: kw.update(geolocation={'latitude':lat,'longitude':lon,'accuracy':20},permissions=['geolocation'])
        ctx=b.new_context(**kw)
        ctx.add_init_script("try{localStorage.setItem('then-now-tour','1');"+("localStorage.setItem('stp-geo-ok','1');" if geook else '')+"}catch(e){}"+COUNT)
        if seed:
            js="try{if(!sessionStorage.getItem('_s')){sessionStorage.setItem('_s','1');"+''.join("localStorage.setItem(%s,%s);"%(json.dumps(k),json.dumps(json.dumps(v))) for k,v in seed.items())+"}}catch(e){}"
            ctx.add_init_script(js)
        reqs=[]
        ctx.on('request',lambda r:reqs.append(r.url))
        pg=ctx.new_page(); pg.on('pageerror',lambda e:errs.append(str(e))); pg.goto(U); pg.reqs=reqs
        return pg
    def txt(pg): return pg.inner_text('#main')
    # 1. entry points on Home (first run and returning) and in the Towns tab
    pg=new(); need(pg.locator('[data-a=nbopen]').count()>=2,'first-run Home has the Nearby card and the Towns row')
    first_hero=pg.evaluate("(()=>{var a=document.querySelector('.home-hero'),c=document.querySelector('.nbcard');return a&&c&&(a.compareDocumentPosition(c)&Node.DOCUMENT_POSITION_FOLLOWING)>0})()")
    need(first_hero,'first-run Home keeps the hero above the Nearby card')
    pg=new(seed={'then-now-v3':{'city':'reno','home':True,'p':{'reno':{'done':[1,0,0,0],'claims':[0,0,0,0,0,0,0,0]}}}})
    need(pg.locator('.nbcard [data-a=nbopen]').count()==1,'returning Home has the Nearby card')
    need(pg.evaluate("window.__geo.get+window.__geo.watch")==0,'no location request just from loading Home')
    # 2. nothing is asked until the tap
    pg.click('.nbcard [data-a=nbopen]'); pg.wait_for_timeout(200)
    t=txt(pg).lower()
    need('closest stops' in t and 'find stops near me' in t and 'continue without location' in t,'ask screen offers both choices')
    need('stays on this phone' in t and 'only while the app is open' in t,'ask screen explains why location is needed')
    need(pg.evaluate("window.__geo.get+window.__geo.watch")==0,'opening the screen does not request location')
    need(pg.evaluate("document.activeElement&&document.activeElement.id")=='stopTitle','focus moves to the screen title')
    # 3. with location: list is nearest-first, at most 5, honest wording, states shown
    pg.click('[data-a=nbloc]'); pg.wait_for_selector('.nbrow',timeout=5000)
    rows=pg.locator('.nbrow'); n=rows.count(); need(1<=n<=5,f'nearby list shows 1 to 5 stops (got {n})')
    t=txt(pg).lower()
    need('straight-line' in t and 'not as a route' in t and 'not walking distances' in t,'list says distances are straight-line and not a route')
    need('story stop' in t and 'town mission' in t,'list mixes town missions and Story stops')
    need('not stamped' in t and 'not visited' in t,'list shows stamped and visited states')
    ds=[]
    for i in range(n):
        m=re.search(r'about ([\d.]+) (m|km)',rows.nth(i).inner_text()); 
        if m: ds.append(float(m.group(1))*(1000 if m.group(2)=='km' else 1))
    need(ds==sorted(ds) and len(ds)==n,f'list is nearest first ({ds})')
    need(pg.evaluate("window.__geo.get")>=1,'location was requested after the tap')
    # town stop opens the normal mission flow (stamp + XP unchanged)
    town=pg.locator('.nbrow[data-a=nbtown]').first; town.click(); pg.wait_for_timeout(200)
    tt=txt(pg).lower(); need('virginia street bridge' in tt and ('i am here' in tt or 'check in' in tt) and pg.locator('[data-a=pick]').count()+pg.locator('[data-a=step]').count()>=1,'town stop opens the normal mission flow')
    # 4. Story stop card
    pg=new(seed={'then-now-v3':{'city':'reno','home':True,'p':{'reno':{'done':[1,0,0,0],'claims':[0,0,0,0,0,0,0,0]}}}})
    prog=lambda: json.loads(pg.evaluate("localStorage.getItem('then-now-v3')"))['p']
    pg.click('.nbcard [data-a=nbopen]'); pg.click('[data-a=nbloc]'); pg.wait_for_selector('.nbrow')
    pg.locator('.nbrow[data-a=nbstory]').first.click(); pg.wait_for_timeout(200)
    t=txt(pg).lower()
    need(pg.locator('#main img').count()==0 and 'photo pending' not in t,'a Story stop with no photo shows no image and no placeholder')
    need(pg.locator('.nbsrc a').count()>=2 and all(h.startswith('https://') for h in pg.eval_on_selector_all('.nbsrc a','e=>e.map(x=>x.href)')),'Story card lists 2+ https sources')
    need('getting there' in t and 'checked 2026-10-31' in t,'Story card shows the access note and when it was checked')
    href=pg.get_attribute('.nbaccess a.btn','href'); need('travelmode=walking' in href and 'google.com/maps/dir' in href and 'destination=' in href,'directions link is a walking Maps link')
    need(pg.get_attribute('.nbaccess a.btn','target')=='_blank','Maps opens outside the app')
    need('opens in maps, outside this app' in t,'card says Maps opens outside the app')
    need('no stamp and no xp' in t and 'not part of your backup code' in t,'card says Visited is device-only, no stamp, no XP')
    need(pg.evaluate("document.activeElement&&document.activeElement.id")=='stopTitle','focus moves to the Story title')
    vb=pg.locator('[data-a=nbvisit]'); need(vb.get_attribute('aria-pressed')=='false' and 'mark visited' in vb.inner_text().lower(),'Mark visited starts off')
    before=prog()
    vb.click(); need(pg.locator('[data-a=nbvisit]').get_attribute('aria-pressed')=='true','Mark visited toggles on')
    after=prog()
    need(before==after,'marking a Story stop does not touch town progress or XP')
    pre=pg.evaluate("localStorage.getItem('stp-tour')")
    pg.reload(); pg.click('.nbcard [data-a=nbopen]'); pg.click('[data-a=nbloc]'); pg.wait_for_selector('.nbrow')
    pg.wait_for_timeout(300)
    need('visited' in txt(pg).lower() and pg.locator('.nbst.on').count()>=1,'Visited persists across reload '+txt(pg)[:200].replace(chr(10),'|')+' pre='+str(pre)+' post='+str(pg.evaluate("localStorage.getItem('stp-tour')")))
    # backup code unchanged by Visited
    pg.click('#bnav [data-t=pass]'); code1=pg.input_value('#codeOut')
    pg.click('#bnav [data-t=home]'); pg.click('.nbcard [data-a=nbopen]'); pg.click('[data-a=nbloc]'); pg.wait_for_selector('.nbrow')
    pg.locator('.nbrow[data-a=nbstory]').first.click(); pg.click('[data-a=nbvisit]')
    pg.click('#bnav [data-t=pass]'); need(pg.input_value('#codeOut')==code1,'Visited marks are not in the backup code')
    # 5. no location: choose a place first, no distances, no route order
    pg=new(allow=False); pg.click('[data-a=nbopen] >> nth=0'); pg.click('[data-a=nbnoloc]')
    t=txt(pg).lower(); need('reno and sparks' in t and 'pick any other town' in t,'no-location path offers places first')
    need(pg.evaluate("window.__geo.get+window.__geo.watch")==0,'continuing without location never asks for it')
    pg.click('[data-a=nbarea]'); t=txt(pg).lower()
    need('town missions' in t and 'story stops' in t and 'not in any route order' in t,'place view lists missions and Story stops with no route claim')
    need(pg.locator('.nbrow[data-a=nbtown]').count()==8 and pg.locator('.nbrow[data-a=nbstory]').count()==4,'Reno and Sparks show 8 town stops and 4 Story stops')
    need(not re.search(r'about [\d.]+ (m|km)',t),'no distances are shown without location')
    pg.click('[data-a=nbnoloc]'); pg.click('[data-a=nbtowns]'); need(pg.locator('#missions').count()==1 and 'pick a mission' in txt(pg).lower(),'"Pick any other town" returns to the town list')
    # 6. location denied by the phone
    pg=new(allow=False); pg.click('[data-a=nbopen] >> nth=0'); pg.click('[data-a=nbloc]'); pg.wait_for_timeout(600)
    t=txt(pg).lower(); need('location is off for this app' in t and 'reno and sparks' in t,'denied location explains itself and offers places')
    pg.click('[data-a=nbarea]'); need(pg.locator('.nbrow[data-a=nbstory]').count()==4,'Story stops still reachable after a denial')
    # 7. nothing nearby
    pg=new(lat=0.0,lon=0.0); pg.click('[data-a=nbopen] >> nth=0'); pg.click('[data-a=nbloc]'); pg.wait_for_selector('.card [data-a=nbnoloc]')
    need('no stops within about 25 miles' in txt(pg).lower(),'nothing nearby gets a clear message and a way out')
    # 8. nothing leaves the phone and the data is in the one built file
    pg=new(); pg.click('[data-a=nbopen] >> nth=0'); pg.click('[data-a=nbloc]'); pg.wait_for_selector('.nbrow'); pg.locator('.nbrow[data-a=nbstory]').first.click()
    ext=[u for u in pg.reqs if not u.startswith('http://localhost:8771/') and not u.startswith('data:') and not u.startswith('blob:')]
    need(not ext,f'no network requests during Nearby stops ({ext[:3]})')
    for f in ('site/play.html','index.html'):
        s2=open(R+f).read(); need('Lake Mansion' in s2 and 'Sparks Heritage Museum' in s2,f'{f} contains the Story stop data (works offline in the app)')
    # 9. layout and touch targets at every width, on every Nearby screen
    for (w,h) in ((320,640),(360,740),(375,667),(390,844),(768,1024),(1280,800)):
        pg=new(w=w,h=h)
        def check(label):
            ow=pg.evaluate("document.documentElement.scrollWidth-document.documentElement.clientWidth")
            need(ow<=1,f'{label} at {w}px has no sideways scroll ({ow}px)')
            small=pg.evaluate("[...document.querySelectorAll('#main button, #main a.btn')].filter(e=>e.offsetParent!==null).map(e=>[e.getBoundingClientRect().height,e.getBoundingClientRect().width,(e.textContent||'').trim().slice(0,24)]).filter(x=>x[0]<44)")
            need(not small,f'{label} at {w}px: touch targets under 44px high: {small}')
        pg.click('[data-a=nbopen] >> nth=0'); check('ask screen')
        pg.click('[data-a=nbnoloc]'); check('place picker')
        pg.click('[data-a=nbarea]'); check('place view')
        pg.locator('.nbrow[data-a=nbstory]').first.click(); check('Story card')
        pg.click('[data-a=nbback]'); pg.click('[data-a=nbnoloc]'); pg.click('[data-a=nbask]'); pg.click('[data-a=nbloc]'); pg.wait_for_selector('.nbrow'); check('nearby list')
    # larger text
    pg=new(); pg.evaluate("document.documentElement.style.fontSize='32px'"); pg.click('[data-a=nbopen] >> nth=0'); pg.click('[data-a=nbloc]'); pg.wait_for_selector('.nbrow')
    need(pg.evaluate("document.documentElement.scrollWidth-document.documentElement.clientWidth")<=1,'nearby list fits at 200% text')
    pg.locator('.nbrow[data-a=nbstory]').first.click(); need(pg.evaluate("document.documentElement.scrollWidth-document.documentElement.clientWidth")<=1,'Story card fits at 200% text')
    b.close()
srv.terminate()
need(not errs,f'page errors: {errs[:3]}')
print('NEARBY: '+('OK' if not bad else 'FAILED'))
for m in bad: print(' -',m)
raise SystemExit(1 if bad else 0)
