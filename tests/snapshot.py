"""Regression snapshot: walks every town, stop and step and hashes what is rendered.
Usage: python3 tests/snapshot.py <index.html> <out.json>"""
import sys,json,hashlib,os
R=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))+'/'
from playwright.sync_api import sync_playwright
src=open(sys.argv[1]).read()
wrap=R+'src/_snap.html'
open(wrap,'w').write('<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"></head><body>'+src+'</body></html>')
def h(x): return hashlib.sha1(x.encode()).hexdigest()[:12]
out={};errs=[]
with sync_playwright() as p:
    b=p.chromium.launch(); cx=b.new_context(viewport={'width':390,'height':844},reduced_motion='reduce'); cx.add_init_script("try{localStorage.setItem('then-now-tour','1')}catch(e){}"); pg=cx.new_page()
    pg.on('pageerror',lambda e:errs.append(str(e)))
    pg.goto('file://'+wrap)
    pg.click('#missions .town:not(.soon) >> nth=0')
    for city in ('Reno','Virginia City'):
        pg.click('.city >> text='+city)
        out[city+':trail']=h(pg.inner_html('#main')+pg.inner_html('#hero'))
        seen_celeb=0
        for i in range(4):
            pg.evaluate("(()=>{var e=document.getElementById('bpop');if(e)e.remove()})()")
            pg.locator(f'.stop >> nth={i}').evaluate("e=>e.scrollIntoView({block:'center'})")
            pg.click(f'.stop >> nth={i}'); out[f'{city}:{i}:find']=h(pg.inner_html('#main'))
            pg.click('text=I am here')
            for k in range(4):
                pg.locator('.opt').nth(k).click()
                if pg.query_selector('.opt.right'): break
            out[f'{city}:{i}:checkin']=h(pg.inner_html('#main'))
            pg.click('text=Unlock the story'); out[f'{city}:{i}:unlock']=h(pg.inner_html('#main'))
            pg.click('text=sort fact from fiction'); out[f'{city}:{i}:fof']=h(pg.inner_html('#main'))
            for rep in range(8):
                if pg.locator('[data-a=fnext]').count(): pg.click('[data-a=fnext]')
                if pg.locator('.fcard').count()==0: break
                for k in range(3):
                    if pg.locator('.fcard').count()==0: break
                    pg.locator('.fbtn').nth(k).click()
            out[f'{city}:{i}:fofdone']=h(pg.inner_html('#main'))
            # the town celebration opens 1.4 s after the last stamp: wait it out so it can never land on top of the exit button
            pg.wait_for_timeout(1500)
            if pg.locator('#celeb').count(): seen_celeb=1; pg.click('text=Keep exploring')
            pg.click('.stophead [data-a=exit]')
        pg.wait_for_timeout(700); out[city+':celeb']=1 if (seen_celeb or pg.locator('#celeb').count()) else 0
        if pg.locator('#celeb').count(): pg.click('text=Keep exploring')
        for t in ('cards','rewards','trail'):
            pg.click('#tab-'+t); out[f'{city}:tab:{t}']=h(pg.inner_html('#main'))
        out[city+':hdr']=h(pg.inner_html('#hero')+pg.inner_html('#cities'))
    out['errors']=errs
    b.close()
json.dump(out,open(sys.argv[2],'w'),indent=1)
print(len(out),'checks;','errors:',errs)
