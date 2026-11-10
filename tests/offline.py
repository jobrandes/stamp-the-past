"""Offline check: serve site/, let the service worker install, go offline, reload, and play."""
import subprocess,sys,time,os,json
from playwright.sync_api import sync_playwright
R=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
srv=subprocess.Popen([sys.executable,'-m','http.server','8765','--directory',R+'/site'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
bad=[]
try:
    time.sleep(1)
    with sync_playwright() as p:
        b=p.chromium.launch(); ctx=b.new_context(viewport={'width':390,'height':800}); ctx.add_init_script("try{localStorage.setItem('then-now-tour','1')}catch(e){}"); pg=ctx.new_page()
        errs=[]; pg.on('pageerror',lambda e: errs.append(str(e)))
        pg.goto('http://localhost:8765/play.html'); 
        ok=pg.evaluate("navigator.serviceWorker.ready.then(()=>true)")
        pg.wait_for_timeout(1500); pg.reload(); pg.wait_for_timeout(800)
        if not pg.evaluate("!!navigator.serviceWorker.controller"): bad.append('service worker is not controlling the page')
        ctx.set_offline(True)
        pg.reload(); pg.wait_for_timeout(800)
        if not pg.locator('#startBox, .stat').count(): bad.append('offline reload did not show Home')
        pg.click('#bnav [data-t=towns]'); pg.click('.town >> nth=0'); pg.click('.stop >> nth=0'); pg.click('text=I am here')
        if pg.locator('.opt').count()<4: bad.append('offline: check-in question did not load')
        if not pg.evaluate("document.querySelector('link[rel=manifest]')!==null"): bad.append('manifest link missing')
        bad+=['page error: '+e for e in errs]
        b.close()
finally:
    srv.terminate()
print('OFFLINE: '+('OK' if not bad else 'FAILED'))
for x in bad: print(' -',x)
sys.exit(1 if bad else 0)
