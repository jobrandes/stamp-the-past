#!/usr/bin/env python3
"""Layout and behaviour checks at phone, tablet and desktop widths, light and dark.
Fails on: page errors, sideways scroll, broken images, tap targets under 40px on the key buttons."""
import sys,os
from playwright.sync_api import sync_playwright
R=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))+'/'
src=open(R+'index.html').read()
open(R+'src/_chk.html','w').write('<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"></head><body>'+src+'</body></html>')
bad=[];errs=[]
def need(c,m):
    if not c: bad.append(m)
with sync_playwright() as p:
    b=p.chromium.launch()
    for w,h,cs in [(360,740,'light'),(390,844,'dark'),(768,1024,'light'),(1280,900,'light'),(1280,900,'dark')]:
        cx=b.new_context(viewport={'width':w,'height':h},color_scheme=cs,reduced_motion='reduce',timezone_id='America/New_York'); cx.add_init_script("try{localStorage.setItem('then-now-tour','1')}catch(e){}"); pg=cx.new_page()
        pg.on('pageerror',lambda e:errs.append(str(e)))
        pg.goto('file://'+R+'src/_chk.html'); tag=f'{w}px/{cs}'
        pg.click('#bnav [data-t=towns]'); pg.click('#missions .town:not(.soon) >> nth=0')
        for city in ('Reno','Virginia City'):
            pg.click('.city >> text='+city)
            for step in range(4):
                pg.click('.stop >> nth=0')
                if step>=0: pg.click('text=I am here')
                for k in range(4):
                    pg.locator('.opt').nth(k).click()
                    if pg.query_selector('.opt.right'): break
                pg.click('text=Unlock the story')
                need(pg.evaluate('document.documentElement.scrollWidth')<=w,f'{tag} {city}: sideways scroll on unlock')
                need(pg.evaluate("[...document.images].every(i=>i.complete&&i.naturalWidth>0)"),f'{tag} {city}: broken image')
                pg.click('text=sort fact from fiction')
                need(pg.evaluate('document.documentElement.scrollWidth')<=w,f'{tag} {city}: sideways scroll on game')
                hts=pg.evaluate("[...document.querySelectorAll('.fbtn,#bar .btn:not(#barExit)')].map(e=>e.getBoundingClientRect().height)")
                need(all(x>=40 for x in hts),f'{tag} {city}: tap target under 40px {hts}')
                pg.click('.stophead [data-a=exit]'); break
            for t in ('cards','rewards','trail'):
                pg.click('#tab-'+t)
                need(pg.evaluate('document.documentElement.scrollWidth')<=w,f'{tag} {city}: sideways scroll on {t}')
        pg.context.close()
    b.close()
bad+= [f'page error: {e}' for e in errs]
print('LAYOUT: '+('OK' if not bad else 'FAILED'))
for x in bad: print(' -',x)
sys.exit(1 if bad else 0)
