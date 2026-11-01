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
    need('nearby stops' in t and 'find stops near me' in t and 'continue without location' in t,'ask screen offers both choices')
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
    need('photo pending' not in t and (pg.locator('#main img').count()==0 or ('photo:' in t and pg.locator('.nbfig a').count()>=1)),'a Story stop shows either no image, or a photo with its credit and license link (never a placeholder)')
    need(pg.locator('.nbsrc a').count()>=2 and all(h.startswith('https://') for h in pg.eval_on_selector_all('.nbsrc a','e=>e.map(x=>x.href)')),'Story card lists 2+ https sources')
    need('getting there' in t and 'official pages on 2026-10-31' in t,'Story card shows the access note and when it was checked')
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
    pg.click('[data-a=nbarea][data-t=reno-sparks]'); t=txt(pg).lower()
    need('town missions' in t and 'story stops' in t and 'not in any route order' in t,'place view lists missions and Story stops with no route claim')
    need(pg.locator('.nbrow[data-a=nbtown]').count()==8 and pg.locator('.nbrow[data-a=nbstory]').count()==12,'Reno and Sparks show 8 town stops and 12 Story stops')
    need(not re.search(r'about [\d.]+ (m|km)',t),'no distances are shown without location')
    pg.click('[data-a=nbnoloc]'); pg.click('[data-a=nbtowns]'); need(pg.locator('#missions').count()==1 and 'pick a mission' in txt(pg).lower(),'"Pick any other town" returns to the town list')
    # 6. location denied by the phone
    pg=new(allow=False); pg.click('[data-a=nbopen] >> nth=0'); pg.click('[data-a=nbloc]'); pg.wait_for_timeout(600)
    t=txt(pg).lower(); need('location is off for this app' in t and 'reno and sparks' in t,'denied location explains itself and offers places')
    pg.click('[data-a=nbarea][data-t=reno-sparks]'); need(pg.locator('.nbrow[data-a=nbstory]').count()==12,'Story stops still reachable after a denial')
    # 7. nothing nearby
    pg=new(lat=0.0,lon=0.0); pg.click('[data-a=nbopen] >> nth=0'); pg.click('[data-a=nbloc]'); pg.wait_for_selector('.card [data-a=nbnoloc]'); pg.wait_for_timeout(500)
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
            clr=pg.evaluate("(()=>{window.scrollTo(0,document.documentElement.scrollHeight);const n=document.querySelector('#bnav');if(!n||getComputedStyle(n).display==='none'||n.offsetParent===null&&getComputedStyle(n).position!=='fixed')return 99;const nt=n.getBoundingClientRect().top;let m=0;document.querySelectorAll('#main *').forEach(e=>{const r=e.getBoundingClientRect();if(r.height>0&&r.width>0&&getComputedStyle(e).visibility!=='hidden')m=Math.max(m,r.bottom)});return nt-m})()")
            need(clr>=8,f'rb07: {label} at {w}px: last content ends {clr}px above the bottom bar (needs 8+)')
        pg.click('[data-a=nbopen] >> nth=0'); check('ask screen')
        pg.click('[data-a=nbnoloc]'); check('place picker')
        pg.click('[data-a=nbarea][data-t=reno-sparks]'); check('place view')
        pg.locator('.nbrow[data-a=nbstory]').first.click(); check('Story card')
        pg.click('[data-a=nbback]'); pg.click('[data-a=nbnoloc]'); pg.click('[data-a=nbask]'); pg.click('[data-a=nbloc]'); pg.wait_for_selector('.nbrow'); check('nearby list')
    # 7. Explore history: per-town free reading list, apart from the four-stop mission
    for town,nstory in (('savannah',6),('reno',6),('sparks',6)):
        pg=new(allow=False,seed={'then-now-v3':{'city':town,'home':False,'p':{}}})
        need(pg.locator('.exprow').count()==1,f'{town}: town page has one Explore history row')
        need(pg.locator('.stops .stop').count()==4,f'{town}: the four-stop mission list is unchanged')
        PROG="(()=>{var o=JSON.parse(localStorage.getItem('then-now-v3')||'{}');return JSON.stringify(o.p)+'|'+(localStorage.getItem('stp-virt')||'')+'|'+(localStorage.getItem('stp-badges')||'')})()"
        pg.click('.exprow'); pg.wait_for_selector('.nbrow')
        before=pg.evaluate(PROG)  # taken after the app's first save fills in empty zeroes for a fresh seed
        t=txt(pg).lower()
        need(f'{nstory+4} places' not in t,'heading counts only story places')
        need(f'{nstory} places to read' in t,f'{town}: heading says {nstory} places to read')
        need(pg.locator('.nbrow[data-a=nbstory]').count()==nstory,f'{town}: {nstory} Story places listed')
        need(pg.locator('.nbrow[data-a=nbtown]').count()==4,f'{town}: the 4 missions are listed apart, under their own heading')
        need('missions: earn stamps' in t and 'places to explore' in t,f'{town}: explore and missions are labelled differently')
        need(pg.evaluate("window.__geo.get+window.__geo.watch")==0,f'{town}: exploring never asks for location')
        pg.locator('.nbrow[data-a=nbstory]').first.click(); need('getting there' in txt(pg).lower(),f'{town}: a place opens its story')
        pg.click('[data-a=nbvisit]'); pg.click('[data-a=nbback]')
        need(pg.locator('.nbrow[data-a=nbstory]').count()==nstory,f'{town}: back returns to the same town list')
        need(pg.evaluate(PROG)==before,f'{town}: exploring changes no mission progress, stamps or XP')
        pg.click('[data-a=nbcityback]'); pg.wait_for_selector('.stops .stop')
        need(pg.locator('.stops .stop').count()==4 and pg.locator('.exprow').count()==1,f'{town}: back returns to the mission page')
        pg.locator('.stops .stop').first.click(); need(pg.locator('.stophead').count()>=1,f'{town}: a mission stop still opens')
    pg=new(allow=False,seed={'then-now-v3':{'city':'boston','home':False,'p':{}}})
    need(pg.locator('.exprow').count()==0,'cities without Story places show no Explore history row')
    for w,h in ((320,568),(390,844),(768,1024),(1280,800)):
        pg=new(allow=False,w=w,h=h,seed={'then-now-v3':{'city':'savannah','home':False,'p':{}}})
        for label,act in (('town page',None),('explore list','.exprow'),('place card','.nbrow[data-a=nbstory]')):
            if act: pg.locator(act).first.click(); pg.wait_for_timeout(150)
            ow=pg.evaluate("document.documentElement.scrollWidth-document.documentElement.clientWidth")
            need(ow<=1,f'explore {label} at {w}px has no sideways scroll ({ow}px)')
            small=pg.evaluate("[...document.querySelectorAll('#main button, #main a.btn')].filter(e=>e.offsetParent!==null).map(e=>[Math.round(e.getBoundingClientRect().height),(e.textContent||'').trim().slice(0,24)]).filter(x=>x[0]<44)")
            need(not small,f'explore {label} at {w}px: touch targets under 44px high: {small}')
    # larger text
    pg=new(); pg.evaluate("document.documentElement.style.fontSize='32px'"); pg.click('[data-a=nbopen] >> nth=0'); pg.click('[data-a=nbloc]'); pg.wait_for_selector('.nbrow')
    need(pg.evaluate("document.documentElement.scrollWidth-document.documentElement.clientWidth")<=1,'nearby list fits at 200% text')
    def clr2(label):
        c=pg.evaluate("(()=>{window.scrollTo(0,document.documentElement.scrollHeight);const n=document.querySelector('#bnav');if(!n||getComputedStyle(n).display==='none')return 99;let m=0;document.querySelectorAll('#main *').forEach(e=>{const r=e.getBoundingClientRect();if(r.height>0&&r.width>0)m=Math.max(m,r.bottom)});return n.getBoundingClientRect().top-m})()")
        need(c>=8,f'rb07: {label} at 200% text: last content ends {c}px above the bottom bar')
    clr2('nearby list')
    pg.locator('.nbrow[data-a=nbstory]').first.click(); need(pg.evaluate("document.documentElement.scrollWidth-document.documentElement.clientWidth")<=1,'Story card fits at 200% text')
    clr2('Story card')
    # deep link: /play#explore-<town> opens that town's Explore history list directly, no location, no tour
    for k,nm in (('savannah','Savannah'),('reno','Reno'),('sparks','Sparks')):
        ctx=b.new_context(viewport={'width':390,'height':844},reduced_motion='reduce'); ctx.add_init_script(COUNT)
        pg=ctx.new_page(); pg.on('pageerror',lambda e:errs.append(str(e))); pg.goto(U+'#explore-'+k); pg.wait_for_timeout(500)
        t=txt(pg); need(nm.lower()+': ' in t.lower() and 'places to read' in t.lower(),'deep link #explore-'+k+' opens the Explore history list (got: '+t[:60].replace('\n',' ')+')')
        need(pg.locator('.nbrow[data-a=nbstory]').count()>=6,'deep link list shows its Story places')
        need(pg.locator('.tourmodal, #tour, [data-a=tournext]').count()==0,'deep link does not open the first-run tour')
        need(pg.evaluate("window.__geo.get+window.__geo.watch")==0,'deep link asks for no location')
        pg.locator('.nbrow[data-a=nbstory]').first.click(); pg.wait_for_timeout(200)
        need(pg.locator('.nbsrc a').count()>=2,'deep link story opens with sources')
        ctx.close()
    ctx=b.new_context(viewport={'width':390,'height':844},reduced_motion='reduce'); pg=ctx.new_page(); pg.goto(U+'#explore-nowhere'); pg.wait_for_timeout(400)
    need('places to read' not in txt(pg).lower(),'an unknown #explore- name falls back to the normal Home'); ctx.close()
    # 9. Also close by: expandable optional row on a town's mission card (built from the Explore data)
    for w,h in [(320,568),(390,844),(1280,900)]:
        pg=new(allow=False,w=w,h=h,seed={'then-now-v3':{'city':'reno','home':False,'p':{'reno':{'done':[0,0,0,0],'claims':[0,0,0,0,0,0,0,0]}}}}); pg.wait_for_timeout(400)
        d=pg.locator('details.alsonear')
        need(d.count()==1 and d.get_attribute('open') is None,'closeby (%dpx): Reno shows a collapsed "Also close by" row'%w)
        need('also close by' in d.inner_text().lower(),'closeby (%dpx): row is labelled'%w)
        d.locator('summary').click(); pg.wait_for_timeout(150)
        need(d.locator('.nbrow').count()>=3 and 'no stamps' in d.inner_text().lower(),'closeby (%dpx): expands to places and says no stamps'%w)
        need(pg.evaluate("document.documentElement.scrollWidth")<=w+1,'closeby (%dpx): no sideways scroll'%w)
        need(d.locator('summary').bounding_box()['height']>=44,'closeby (%dpx): summary is a 44px target'%w)
        if w==390:
            d.locator('.nbrow').first.click(); pg.wait_for_timeout(250)
            need(pg.locator('.nbsrc a').count()>=2 and pg.locator('.nbback').count()==1,'closeby: tapping a place opens its Story card with sources and a back link')
            need(pg.evaluate("(()=>{var o=JSON.parse(localStorage.getItem('then-now-v3')||'{}');var r=(o.p||{}).reno;return !r||r.done.every(function(x){return !x})})()"),'closeby: reading a place earns no stamp')
    pg=new(allow=False,seed={'then-now-v3':{'city':'tahoe','home':False,'p':{}}}); pg.wait_for_timeout(300)
    need(pg.locator('details.alsonear').count()==0,'closeby: a town with nothing within half a mile shows no row')
    b.close()
srv.terminate()
need(not errs,f'page errors: {errs[:3]}')
print('NEARBY: '+('OK' if not bad else 'FAILED'))
for m in bad: print(' -',m)
raise SystemExit(1 if bad else 0)
