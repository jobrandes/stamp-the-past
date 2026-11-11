#!/usr/bin/env python3
"""Slim Home (plan step 3): one start card, a Today row, two links. Everything else lives on Towns, Passport or the Menu.
Phone checks use the iPhone 17 size (402x874 at 3x, touch). Chromium emulates it; real Safari is not available in the cloud session.
SHOTS=<folder> saves screenshots to look at."""
import os,json,threading,functools,http.server,sys
from playwright.sync_api import sync_playwright
R=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))+'/'
src=open(R+'index.html').read()
open(R+'src/_slim.html','w').write('<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"></head><body>'+src+'</body></html>')
class _Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*a): pass
class _S(http.server.ThreadingHTTPServer):
    def handle_error(self,*a): pass
srv=_S(('127.0.0.1',0),functools.partial(_Q,directory=R)); threading.Thread(target=srv.serve_forever,daemon=True).start()
U='http://127.0.0.1:%d/src/_slim.html'%srv.server_address[1]
SHOTS=os.environ.get('SHOTS')
bad=[]
def need(c,m):
    if not c: bad.append(m)
def seed_js(seed):
    return "try{if(!sessionStorage.getItem('_s')){sessionStorage.setItem('_s','1');"+''.join("localStorage.setItem(%s,%s);"%(json.dumps(k),json.dumps(json.dumps(v))) for k,v in seed.items())+"}}catch(e){}"
STAMPED={'then-now-v3':{'city':'reno','home':1,'p':{'reno':{'done':[1,0,0,0],'claims':[1,1,0,0,0,0,0,0]}}}}
GEOASK="window._geoAsked=0;try{var g=navigator.geolocation;['getCurrentPosition','watchPosition'].forEach(function(n){var o=g[n].bind(g);g[n]=function(){window._geoAsked++;return o.apply(null,arguments)}})}catch(e){}"
errs=[]
with sync_playwright() as p:
    b=p.chromium.launch()
    def new(tz='America/New_York',seed=None,w=402,h=874,motion='reduce',scheme='light',geo=None):
        kw=dict(viewport={'width':w,'height':h},device_scale_factor=3 if w<700 else 1,has_touch=w<700,is_mobile=w<700,reduced_motion=motion,timezone_id=tz,color_scheme=scheme)
        if geo: kw['geolocation']={'latitude':geo[0],'longitude':geo[1],'accuracy':20}; kw['permissions']=['geolocation']
        ctx=b.new_context(**kw); ctx.add_init_script("try{localStorage.setItem('then-now-tour','1')}catch(e){}"); ctx.add_init_script(GEOASK)
        if geo: ctx.add_init_script("try{localStorage.setItem('stp-geo-ok','1');Object.defineProperty(navigator,'permissions',{value:undefined})}catch(e){}")
        if seed: ctx.add_init_script(seed_js(seed))
        pg=ctx.new_page(); pg.on('pageerror',lambda e:errs.append(str(e))); pg.goto(U); pg.wait_for_selector('#main'); pg.wait_for_timeout(250)
        return pg
    def shot(pg,name):
        if SHOTS: pg.wait_for_timeout(350); pg.screenshot(path=os.path.join(SHOTS,name+'.png'))
    def noscroll(pg,what):
        need(pg.evaluate("document.documentElement.scrollWidth<=window.innerWidth+1"),what+': no sideways scroll')
    def taps(pg,what):
        small=pg.evaluate("[...document.querySelectorAll('#main button,#main a,#main select')].filter(e=>e.checkVisibility()&&(e.getBoundingClientRect().height<43.5)).map(e=>(e.className||e.tagName)+':'+Math.round(e.getBoundingClientRect().height))")
        need(not small,what+': tap targets under 44px '+str(small[:5]))

    # ---- 1. new player, a time zone with a town: one start card ----
    pg=new(); t=pg.inner_text('#main').lower()
    need(pg.locator('#startBox [data-a=startplay]').count()==1,'East: start card has one Play button')
    need('try one from your couch' in t and 'brooklyn bridge' in t and 'stop 1 of 4' in t,'East: card names the stop, the couch and the dots')
    need(pg.locator('#main #missions').count()==0 and pg.locator('#townSearch').count()==0,'town list and search are not on Home')
    for gone in ['how it works','is that actually true','for parents','jump back in','trail of the week']:
        need(gone not in t,'Home no longer shows: '+gone)
    need(pg.locator('#startBox .f-now').count()==1 and pg.locator('#startBox .f-then').count()==1,'start photo has the old and the new picture')
    need('photo' in t or 'now:' in t,'start photo is credited')
    need(pg.evaluate("window._geoAsked")==0,'first load never asks for location')
    r=pg.evaluate("(()=>{var b=document.querySelector('#startBox .sc-go').getBoundingClientRect(),n=document.querySelector('#bnav').getBoundingClientRect();return [b.top,b.bottom,n.top,innerHeight]})()")
    need(r[0]>0 and r[1]<=r[2],'Play button is on the first screen, above the bottom bar %s'%r)
    need(pg.locator('.hlinks [data-a=gomissions]').count()==1 and pg.locator('.hlinks [data-a=reqtown]').count()==1,'two bottom links: browse towns, add your town')
    need('browse all 62 towns' in t,'browse link carries the town count')
    need(pg.evaluate("getComputedStyle(document.querySelector('#startBox .f-then')).animationName")=='none','Reduce Motion: the photo does not fade by itself')
    noscroll(pg,'East first-time'); taps(pg,'East first-time'); shot(pg,'1-new-east')
    # play from the couch -> the question, in preview mode
    pg.click('#startBox [data-a=startplay]'); pg.wait_for_timeout(400)
    need(pg.locator('#stopTitle').count()==1 and 'brooklyn' in pg.inner_text('#stopTitle').lower(),'Play opens the stop')
    need(pg.locator('.opt').count()>0,'Play lands on the question (explore from home)')
    shot(pg,'2-new-east-playing')
    # links
    pg=new(); pg.click('.hlinks [data-a=gomissions]'); pg.wait_for_timeout(250); need(pg.locator('#missions .town').count()>50,'Browse all towns opens the Towns page')
    pg=new(); pg.click('.hlinks [data-a=reqtown]'); pg.wait_for_timeout(250); need(pg.locator('#repWhere,#report,.report,dialog[open]').count()>0 or 'which town' in pg.inner_text('body').lower(),'Add your town opens the town request')

    # ---- 2. couch player comes back: next stop, dots filled ----
    pg=new(seed={'stp-virt':{'ny:bridge':1}}); t=pg.inner_text('#startBox').lower()
    need('you faded the past into today' in t and 'next: grand central' in t and 'stop 2 of 4' in t,'couch player sees the next stop: '+t[:120])
    need(pg.locator('#startBox .sc-dots i.on').count()==1,'one dot filled after one couch stop')
    shot(pg,'3-couch-next')

    # ---- 3. Pacific: ask, do not guess ----
    pg=new(tz='America/Los_Angeles'); t=pg.inner_text('#startBox').lower()
    need('where are you' in t and pg.locator('#startBox [data-a=startstate]').count()==4,'Pacific: asks, with four state buttons')
    need(pg.locator('#stSel option').count()>=51,'state list has every state')
    need(pg.locator('#startBox [data-a=startplay]').count()==0 and 'reno' not in t,'Pacific: no Reno default')
    need(pg.evaluate("window._geoAsked")==0,'Pacific: no location request')
    noscroll(pg,'Pacific ask'); taps(pg,'Pacific ask'); shot(pg,'4-pacific-ask')
    pg.click('#startBox [data-a=startstate][data-s=NV]'); pg.wait_for_timeout(250); t=pg.inner_text('#startBox').lower()
    need(pg.locator('#startBox [data-a=startplay]').count()==1 and 'reno' in t,'Nevada starts in Reno: '+t[:100])
    need('more in nevada' in t,'offers the other Nevada towns')
    shot(pg,'5-pacific-nevada')
    pg.reload(); pg.wait_for_selector('#startBox'); need('reno' in pg.inner_text('#startBox').lower(),'the state pick is remembered')
    pg.click('#startBox [data-a=startask]'); pg.wait_for_timeout(200); need(pg.locator('#startBox [data-a=starttown]').count()>1,'changing: lists the towns in the picked state')
    pg.click('#startBox [data-a=starttown][data-c=sparks]'); pg.wait_for_timeout(200); need('sparks' in pg.inner_text('#startBox').lower(),'picking a town in the state switches the card')
    # a state with no town says so plainly
    pg.click('#startBox [data-a=startask]'); pg.select_option('#stSel','ND'); pg.wait_for_timeout(250); t=pg.inner_text('#startBox').lower()
    need('no towns in north dakota yet' in t and 'closest is' in t and pg.locator('#startBox .sc-note [data-a=reqtown]').count()==1,'state with no town: says so, offers the closest and Add your town: '+t[:140])
    need(pg.locator('#startBox [data-a=startplay]').count()==1,'state with no town still has a Play button')
    noscroll(pg,'no-town state'); shot(pg,'6-no-town-state')

    # ---- 4. location already allowed: nearest stop, with distance ----
    pg=new(tz='America/Los_Angeles',geo=(39.5325,-119.81366)); pg.wait_for_timeout(1300); t=pg.inner_text('#startBox').lower()
    need('closest to you' in t and pg.locator('#startBox [data-a=startplay]').count()==1,'location on: card shows the closest stop: '+t[:120])
    shot(pg,'7-location-on')
    pg=new(tz='America/Los_Angeles',geo=(39.52812,-119.81366)); pg.wait_for_timeout(1300); t=pg.inner_text('#startBox').lower()
    need('you are here' in t and pg.locator('#startBox [data-a=neargo]').count()==1,'standing at a stop: card says You are here')
    need(pg.locator('.herebanner').count()==0,'standing at a stop on first-time Home: no second banner over the card')
    need(pg.locator('#todayBox .today').count()==1,'Today row appears once location names a town')
    shot(pg,'8-you-are-here')

    # ---- 5. returning player ----
    pg=new(seed=STAMPED); t=pg.inner_text('#main').lower()
    need(pg.locator('#startBox').count()==0 and pg.locator('.stat [data-a=nextstop]').count()==1,'returning: progress card with Next stop, no start card')
    need(pg.locator('.stat .f-now').count()==1,'returning: the progress card carries the next stop photo')
    need(pg.locator('#main #missions').count()==0,'returning: no town list on Home')
    need(pg.locator('.today').count()==1,'returning: Today row')
    need(pg.locator('.hlinks [data-a=trailweek]').count()==1 and pg.locator('.hlinks .hrow').count()==3,'returning: Trail of the week is one quiet row with the two links')
    need(pg.locator('#nearBox .rcard').count()==0,'returning without location: no nearby list')
    need('protect your stamps' not in t,'backup nudge is off Home')
    r=pg.evaluate("(()=>{var b=document.querySelector('.stat [data-a=nextstop]').getBoundingClientRect(),n=document.querySelector('#bnav').getBoundingClientRect();return [b.top,b.bottom,n.top]})()")
    need(r[0]>0 and r[1]<=r[2],'returning: Next stop is on the first screen %s'%r)
    noscroll(pg,'returning'); taps(pg,'returning'); shot(pg,'9-returning')
    pg.click('#bnav [data-t=pass]'); pg.wait_for_timeout(250); need('protect your stamps' in pg.inner_text('#main').lower(),'backup nudge lives on the Passport')
    pg=new(seed=STAMPED); pg.click('.hlinks [data-a=trailweek]'); pg.wait_for_timeout(250); need(pg.locator('#bt-trails[aria-selected=true]').count()==1,'Trail of the week row opens Trails')

    # ---- 5b. the Play button on the shared town and stop pages lands on the question, from the couch ----
    def deep(h,seed=None):
        ctx=b.new_context(viewport={'width':402,'height':874},device_scale_factor=3,has_touch=True,is_mobile=True,reduced_motion='reduce',timezone_id='America/Los_Angeles')
        if seed: ctx.add_init_script(seed_js(seed))
        pg=ctx.new_page(); pg.on('pageerror',lambda e:errs.append(str(e))); pg.goto(U+h); pg.wait_for_selector('#main'); pg.wait_for_timeout(500); return pg
    pg=deep('#play=boston:faneuil')
    need(pg.locator('#stopTitle').count()==1 and 'faneuil' in pg.inner_text('#stopTitle').lower() and pg.locator('.opt').count()>0,'#play= opens that stop on its question')
    need(pg.locator('.tour-card').count()==0,'#play= skips the first-run guide so nothing covers the question')
    need(pg.evaluate("document.documentElement.scrollWidth<=innerWidth"),'#play= no sideways scroll'); shot(pg,'10-page-play')
    ans=json.load(open(R+'src/packs/boston.json'))['stops'][1]['q']['answer']; pg.locator('.opt').nth(ans).click(); pg.wait_for_timeout(500)
    need('boston:faneuil' in pg.evaluate("localStorage.getItem('stp-virt')||''"),'a right answer from the page link earns a virtual stamp, not a real one')
    need(json.loads(pg.evaluate("localStorage.getItem('then-now-v3')||'{}'")).get('p',{}).get('boston',{}).get('done',[0,0,0,0])[1]==0,'the real stamp stays unearned')
    pg=deep('#play=reno:arch',seed=STAMPED); need(pg.locator('#stopTitle').count()==1 and pg.locator('.demo-banner').count()==0,'#play= on an already stamped stop opens it normally')
    pg=deep('#play=nowhere:nothing'); need(pg.locator('#startBox').count()==1,'#play= with unknown ids falls back to Home')
    # ---- 6. sizes, dark, motion ----
    for (w,h) in [(320,568),(360,740),(390,844),(402,874),(768,1024),(1024,768),(1280,800)]:
        for seed,nm in [(None,'new'),(STAMPED,'ret')]:
            for tz in ['America/New_York','America/Los_Angeles']:
                pg=new(tz=tz,seed=seed,w=w,h=h); noscroll(pg,'%s %s %dx%d'%(nm,tz,w,h))
                if w<700: taps(pg,'%s %s %dx%d'%(nm,tz,w,h))
                if SHOTS and tz=='America/New_York' and w in (320,1024): shot(pg,'size-%s-%d'%(nm,w))
    pg=new(scheme='dark'); shot(pg,'dark-new'); pg=new(scheme='dark',seed=STAMPED); shot(pg,'dark-returning'); pg=new(scheme='dark',tz='America/Los_Angeles'); shot(pg,'dark-pacific')
    pg=new(motion='no-preference'); need(pg.evaluate("getComputedStyle(document.querySelector('#startBox .f-then')).animationName")!='none','with motion allowed the photo fades by itself')
    pg.wait_for_timeout(4200); shot(pg,'fade-then')
    b.close()
need(not errs,'page errors: '+str(errs[:3]))
print('SLIM HOME: '+('OK' if not bad else 'FAILED\n - '+'\n - '.join(bad)))
sys.exit(1 if bad else 0)
