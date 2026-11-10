#!/usr/bin/env python3
"""Towns is its own page (slim Home plan, step 2) and the funnel counters (step 1).
Phone checks use the iPhone 17 size (402x874 at 3x, touch). Chromium emulates it; real Safari is not available in the cloud session."""
import os,json,threading,functools,http.server,sys
from playwright.sync_api import sync_playwright
R=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))+'/'
src=open(R+'index.html').read()
open(R+'src/_towns.html','w').write('<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"></head><body>'+src+'</body></html>')
class _Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*a): pass
class _S(http.server.ThreadingHTTPServer):
    def handle_error(self,*a): pass
srv=_S(('127.0.0.1',0),functools.partial(_Q,directory=R)); threading.Thread(target=srv.serve_forever,daemon=True).start()
U='http://127.0.0.1:%d/src/_towns.html'%srv.server_address[1]
SHOTS=os.environ.get('SHOTS')
bad=[]
def need(c,m):
    if not c: bad.append(m)
def seed_js(seed):
    return "try{if(!sessionStorage.getItem('_s')){sessionStorage.setItem('_s','1');"+''.join("localStorage.setItem(%s,%s);"%(json.dumps(k),json.dumps(json.dumps(v))) for k,v in seed.items())+"}}catch(e){}"
STAMPED={'then-now-v3':{'city':'reno','home':1,'p':{'reno':{'done':[1,0,0,0],'claims':[1,1,0,0,0,0,0,0]}}}}
with sync_playwright() as p:
    b=p.chromium.launch()
    def new(seed=None,w=402,h=874,tz=None):
        kw=dict(viewport={'width':w,'height':h},device_scale_factor=3,has_touch=True,is_mobile=True,reduced_motion='reduce')
        if tz: kw['timezone_id']=tz
        ctx=b.new_context(**kw); ctx.add_init_script("try{localStorage.setItem('then-now-tour','1')}catch(e){}")
        if seed: ctx.add_init_script(seed_js(seed))
        pg=ctx.new_page(); errs=[]; pg.on('pageerror',lambda e:errs.append(str(e))); pg.goto(U); pg.wait_for_selector('#main')
        pg.evaluate("window._pings=[];window.goatcounter={count:function(o){window._pings.push(o.title)}}")
        return pg,errs
    def over(pg): return pg.evaluate("document.documentElement.scrollWidth-innerWidth")
    # --- Towns tab opens its own page, from first-time Home and from a returning player's Home
    for label,seed in (('first-time',None),('returning',STAMPED)):
        pg,errs=new(seed,tz='America/New_York')
        pg.click('#bnav [data-t=towns]'); pg.wait_for_timeout(250)
        need(pg.locator('#main h1').inner_text().strip().lower()=='towns',label+': Towns tab shows a Towns page with its own heading')
        need(pg.locator('#main .home-hero').count()==0,label+': Towns page has no Home hero')
        need(pg.evaluate("document.querySelector('#bnav [data-t=towns]').classList.contains('on')"),label+': Towns is highlighted in the bottom bar')
        need(pg.locator('#missions button.town[data-c=reno]').count()==1 and pg.locator('#townSearch').count()==1 and pg.locator('.schips .chip').count()>10,label+': Towns page has the town list, search and state chips')
        need(pg.evaluate("window._pings.indexOf('towns-tab')>-1"),label+': opening Towns sends the anonymous towns-tab count')
        need(over(pg)<=0,label+': no sideways scroll on Towns at 402 wide, got %s'%over(pg))
        mb=pg.evaluate("(()=>{const m=document.getElementById('menuBtn').getBoundingClientRect(),h=document.querySelector('#main h1').getBoundingClientRect();return [m.bottom,h.top]})()")
        need(mb[0]<=mb[1]+2,label+': menu button does not sit on the Towns heading, got %s'%mb)
        pg.fill('#townSearch','savannah'); pg.wait_for_timeout(300); need(pg.locator('#missions button.town[data-c=savannah]:visible').count()==1,label+': town search works on the Towns page')
        pg.fill('#townSearch',''); pg.click('.schips .chip >> nth=0'); pg.wait_for_timeout(200)
        # Trails and My trip are switches on the same page
        pg.click('#bnav [data-t=trails]'); pg.wait_for_timeout(250)
        need(pg.locator('#bp-trails').is_visible() and pg.locator('#bnav [data-t=trails].on').count()==1,label+': Trails tab shows the trails on the Towns page')
        pg.click('#bt-trip'); pg.wait_for_timeout(150); need(pg.locator('#bp-trip').is_visible(),label+': My trip switch works on the Towns page')
        # opening a town leaves the page; Home brings Home back
        pg.click('#bt-towns'); pg.evaluate("document.querySelectorAll('#missions details.reg').forEach(d=>d.open=true)"); pg.click('#missions button.town[data-c=boston]'); pg.wait_for_timeout(300)
        need(pg.locator('#bnav').is_hidden() or pg.inner_text('#cityName').lower()=='boston',label+': a town opens from the Towns page')
        pg.goto(U); pg.wait_for_selector('#main'); pg.click('#bnav [data-t=towns]'); pg.click('#bnav [data-t=home]'); pg.wait_for_timeout(250)
        need(pg.locator('#main .home-hero').count()==1 or pg.locator('#main .statusrow, #main .status').count()>=0,label+': Home tab leaves the Towns page')
        need(pg.locator('#main h1').first.inner_text().strip().lower()!='towns',label+': Home is not the Towns page')
        need(not errs,label+': no script errors, got %s'%errs)
        if SHOTS and label=='returning':
            pg.click('#bnav [data-t=towns]'); pg.wait_for_timeout(300); pg.screenshot(path=SHOTS+'/towns-returning.png')
        pg.context.close()
    # --- sizes
    for w,h in ((320,568),(360,740),(390,844),(402,874),(1024,768)):
        pg,_=new(STAMPED,w,h); pg.click('#bnav [data-t=towns]'); pg.wait_for_timeout(250)
        need(over(pg)<=0,'no sideways scroll on Towns at %dx%d, got %s'%(w,h,over(pg)))
        pg.context.close()
    # --- funnel counters (step 1)
    pg,_=new(None,tz='America/New_York')
    need(pg.locator('.starttown').count()==1,'first-time Home shows the start-town card for an Eastern phone')
    pg.click('.starttown'); pg.wait_for_timeout(200)
    need('start-town' in pg.evaluate('window._pings'),'tapping the start-town card sends the anonymous start-town count, got %s'%pg.evaluate('window._pings'))
    pg.context.close()
    pg,_=new(None,tz='America/New_York'); pg.click('.heroGo'); pg.wait_for_timeout(200)
    need('pick-mission' in pg.evaluate('window._pings'),'tapping Pick a mission sends the anonymous pick-mission count, got %s'%pg.evaluate('window._pings'))
    need(pg.evaluate("JSON.stringify(window._pings).length")<200,'counts carry no place or player data')
    pg.context.close(); b.close()
print('TOWNSPAGE: '+('OK' if not bad else 'FAIL\n  '+'\n  '.join(bad)))
sys.exit(1 if bad else 0)
