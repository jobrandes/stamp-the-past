#!/usr/bin/env python3
"""Town requests: no search match offers 'ask us to add it', the bottom of the town list has the same link,
and the form opens as a town request with the search text pre-filled and nothing sent until Send."""
import os,subprocess,time
from playwright.sync_api import sync_playwright
R=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))+'/'
srv=subprocess.Popen(['python3','-m','http.server','8772','-d',R+'site'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); time.sleep(1)
bad=[]
def need(c,m):
    if not c: bad.append(m)
try:
    with sync_playwright() as p:
        b=p.chromium.launch(); ctx=b.new_context(viewport={'width':390,'height':844})
        ctx.add_init_script("try{localStorage.setItem('then-now-tour','1')}catch(e){}")
        posts=[]; ctx.on('request',lambda r: posts.append(r.url) if r.method=='POST' else None)
        pg=ctx.new_page(); pg.goto('http://localhost:8772/play.html'); pg.wait_for_timeout(700)
        pg.click('text=Pick a mission'); pg.wait_for_timeout(300)
        need(pg.locator('.reqline [data-a=reqtown]').count()==1,'bottom of the town list offers a town request')
        pg.fill('#townSearch','Tombstone'); pg.wait_for_timeout(300)
        need(pg.is_visible('#townNone [data-a=reqtown]'),'no match offers ask us to add it')
        pg.click('#townNone [data-a=reqtown]'); pg.wait_for_timeout(300)
        need('which town' in pg.inner_text('#report h2').lower(),'form is titled as a town request')
        need(pg.input_value('#repMsg').startswith('Tombstone'),'search text is pre-filled')
        need(pg.get_attribute('#report','data-where')=='Town request','only "Town request" is sent as the location')
        need(len(posts)==0,'nothing is sent before Send')
        # in-your-face banner on Home: one field, one tap, sends only on Send, 44px targets, no sideways scroll
        for w in (320,390,768,1280):
            pg.set_viewport_size({'width':w,'height':800}); pg.goto('http://localhost:8772/play.html'); pg.wait_for_timeout(600)
            need(pg.is_visible('.reqban'),f'banner visible on Home at {w}')
            need(pg.evaluate("document.documentElement.scrollWidth<=innerWidth"),f'banner sideways scroll at {w}')
            need(pg.evaluate("(function(){var a=document.querySelector('#reqBanIn').getBoundingClientRect(),b=document.querySelector('.reqban .btn').getBoundingClientRect();return a.height>=44&&b.height>=44})()"),f'banner targets 44px at {w}')
        pg.set_viewport_size({'width':390,'height':844}); pg.goto('http://localhost:8772/play.html'); pg.wait_for_timeout(600)
        n0=len(posts)
        pg.click('.reqban [data-a=reqban]'); pg.wait_for_timeout(200)
        need('town first' in pg.inner_text('#reqBanOut').lower() and len(posts)==n0,'empty banner request is refused, nothing sent')
        pg.fill('#reqBanIn','Tombstone, AZ'); pg.click('.reqban [data-a=reqban]'); pg.wait_for_timeout(500)
        need(len(posts)==n0+1,'banner sends exactly one request on Send')
        b.close()
finally:
    srv.terminate()
print('REQTOWN: '+('OK' if not bad else 'FAILED\n - '+'\n - '.join(bad)))
raise SystemExit(1 if bad else 0)
