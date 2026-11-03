#!/usr/bin/env python3
"""Community-city test branch: real function code on an in-memory store, real form, real app. Run via run_all when src/community.flag exists."""
import subprocess,time,json,sys,os,io,re
from playwright.sync_api import sync_playwright
from PIL import Image
R=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))+'/'
if not os.path.exists(R+'src/community.flag'): print('community: skipped (no flag)'); sys.exit(0)
PORT=8791
def jpg(c):
    b=io.BytesIO(); Image.new('RGB',(900,600),c).save(b,'JPEG',quality=80); p=f'/tmp/_cm_{c[0]}.jpg'; open(p,'wb').write(b.getvalue()); return p
def server(ctx):
    pr=subprocess.Popen(['node',R+'tests/community/server.mjs',R+'site',str(PORT)],env={**os.environ,'CTX':ctx},stdout=subprocess.PIPE); pr.stdout.readline(); return pr
errs=[]
def ok(c,m):
    if not c: errs.append(m)
sv=server('branch-deploy')
try:
  with sync_playwright() as pw:
    b=pw.chromium.launch(); pg=b.new_page(viewport={'width':390,'height':844}); pe=[]
    pg.add_init_script("try{localStorage.setItem('then-now-tour','1');localStorage.setItem('stp-dragged','1')}catch(e){}")
    pg.on('pageerror',lambda e:pe.append(str(e)))
    # 1. before anyone adds a city the app is unchanged
    pg.goto(f'http://localhost:{PORT}/play.html'); pg.wait_for_selector('#main')
    base=pg.evaluate("document.querySelectorAll('[data-a=city]').length")
    # 2. bad submissions are rejected with plain messages
    r=pg.evaluate("fetch('/api/community/submit',{method:'POST',body:JSON.stringify({city:'X',stops:[]})}).then(r=>r.json().then(j=>[r.status,j]))")
    ok(r[0]==400 and r[1]['errors'],'empty submit should be rejected: %r'%r)
    r=pg.evaluate("fetch('/api/community/submit',{method:'POST',body:JSON.stringify({city:'Xx',stops:[1,2,3,4].map(()=>({name:'<b>x</b>',story:'a',sources:[],then:{},now:{}}))})}).then(r=>r.json().then(j=>[r.status,j]))")
    ok(r[0]==400,'junk stops rejected')
    # 3. fill the real form
    pg.goto(f'http://localhost:{PORT}/contribute/'); pg.wait_for_selector('#city')
    ok(pg.evaluate("document.documentElement.scrollWidth<=innerWidth"),'contribute page sideways scroll at 390')
    pg.fill('#city','Testville'); pg.fill('#state','NV'); pg.fill('#nick','Dad')
    names=['Old Mill <script>alert(1)</script>','Town Hall','Depot','Library']
    for i in range(4):
        fs=pg.locator(f'fieldset[data-i="{i}"]')
        fs.locator('[data-f=name]').fill(names[i])
        fs.locator('[data-f=story]').fill(f'{names[i]} was built long ago by the people of Testville & friends. It served the town for decades.\n\nA second paragraph about its later life and what stands there today.')
        fs.locator('[data-f=ll]').fill(f'39.5{i}, -119.8{i}')
        fs.locator('[data-f=s1t]').fill('Local history'); fs.locator('[data-f=s1u]').fill('https://example.org/a%d'%i)
        fs.locator('[data-f=s2t]').fill('County archive'); fs.locator('[data-f=s2u]').fill('https://example.org/b%d'%i)
        th=fs.locator('.photo[data-era=then]'); nw=fs.locator('.photo[data-era=now]')
        th.locator('[data-f=file]').set_input_files(jpg((120,110,100))); th.locator('[data-f=credit]').fill('Some Archive'); th.locator('[data-f=year]').fill('1905'); th.locator('[data-f=license]').select_option('Public domain'); th.locator('[data-f=page]').fill('https://commons.wikimedia.org/wiki/File:Test%d.jpg'%i); th.locator('[data-f=caption]').fill('The old building in 1905')
        nw.locator('[data-f=file]').set_input_files(jpg((60,140,90))); nw.locator('[data-f=own]').check(); nw.locator('[data-f=credit]').fill('Dad'); nw.locator('[data-f=year]').fill('2026'); nw.locator('[data-f=license]').select_option('CC BY'); nw.locator('[data-f=caption]').fill('The same building today')
    # without the box ticked: rejected, message shown
    pg.click('#go'); pg.wait_for_selector('#errs:not([hidden])')
    ok('box' in pg.inner_text('#errs'),'confirm box message missing')
    pg.check('#confirm'); pg.click('#go'); pg.wait_for_selector('#done:not([hidden])')
    edit=pg.inner_text('#editlink'); ok(re.search(r'/contribute/\?edit=[a-f0-9]{32}$',edit) is not None,'edit link shape: '+edit)
    # 4. the app shows the city (test deploy only)
    pg.goto(f'http://localhost:{PORT}/play.html'); pg.wait_for_selector('#main')
    ok(pg.evaluate("document.querySelectorAll('[data-a=city]').length")>base,'community city should appear')
    html=pg.content()
    ok('<script>alert' not in html,'script injection survived')
    ok('Old Mill &lt;script&gt;' in html or 'Old Mill' in html,'name missing')
    # open the town, then stop 1
    pg.evaluate("Array.from(document.querySelectorAll('[data-a=city]')).find(function(e){return /^c[0-9a-f]{8}$/.test(e.getAttribute('data-c'));}).click()"); pg.wait_for_timeout(400)
    ok('Testville' in pg.inner_text('body'),'town screen did not open')
    ok(pg.evaluate("document.documentElement.scrollWidth<=innerWidth"),'town screen sideways scroll')
    ok('Community-added' in pg.inner_text('body'),'community label missing on town screen')
    pg.evaluate("document.querySelector('[data-a=open]').click()"); pg.wait_for_timeout(400)
    pg.click('[data-a=step][data-n="1"]'); pg.wait_for_timeout(300)
    pg.screenshot(path='/tmp/cm_q.png')
    ok('which of these is the name' in pg.inner_text('body').lower(),'placeholder question missing')
    # the right answer is the place name; pick each option until the stamp lands
    n=pg.evaluate("document.querySelectorAll('[data-a=pick]').length"); ok(n==4,'four options, got %d'%n)
    pg.evaluate("Array.from(document.querySelectorAll('[data-a=pick]')).find(function(b){return /^Old Mill/.test(b.innerText.trim());}).click()"); pg.wait_for_timeout(300)
    pg.wait_for_timeout(500); pg.screenshot(path='/tmp/cm_stamped.png')
    ok(pg.evaluate("JSON.parse(localStorage.getItem('then-now-v3')).p[Object.keys(JSON.parse(localStorage.getItem('then-now-v3')).p).find(function(k){return /^c[0-9a-f]{8}$/.test(k)})].done[0]")==1,'stamp did not save for the community town')
    for n_ in (2,3):
        nb=pg.query_selector('[data-a=step][data-n="%d"]'%n_)
        if nb: nb.click(); pg.wait_for_timeout(300)
    ok(pg.evaluate("document.querySelectorAll('a[href=\"undefined\"],a[href=\"\"]').length")==0,'a link points nowhere')
    pg.screenshot(path='/tmp/cm_last.png')
    ok('sources' in pg.inner_text('body').lower(),'sources step not reached')
    # save code unchanged by the extra town
    code=pg.evaluate("(function(){var n=0;try{return document.body.innerText.match(/TN3-[01-]+/)}catch(e){return null}})()")
    ok(not pe,'page errors: %r'%pe)
    # 5. edit link works and keeps photos
    pg.goto(f'http://localhost:{PORT}'+edit[edit.index('/contribute'):]); pg.wait_for_selector('#city')
    pg.wait_for_function("document.getElementById('city').value==='Testville'")
    pg.check('#confirm'); pg.click('#go'); pg.wait_for_selector('#done:not([hidden])')
    # 6. other widths on the app
    for w in (320,768,1280):
        pg.set_viewport_size({'width':w,'height':800}); pg.goto(f'http://localhost:{PORT}/play.html'); pg.wait_for_selector('#main')
        ok(pg.evaluate("document.documentElement.scrollWidth<=innerWidth"),f'play sideways scroll at {w}')
        pg.goto(f'http://localhost:{PORT}/contribute/'); ok(pg.evaluate("document.documentElement.scrollWidth<=innerWidth"),f'contribute sideways scroll at {w}')
    b.close()
  # 7. production context: feature is off
  sv.terminate(); sv=server('production')
  import urllib.request,urllib.error
  for u in ('/api/community/list','/api/community/submit'):
    try: urllib.request.urlopen(f'http://localhost:{PORT}{u}'); ok(False,'production should 404 '+u)
    except urllib.error.HTTPError as e: ok(e.code==404,'production status '+str(e.code))
finally:
  sv.terminate()
print('community: errors:',errs); sys.exit(1 if errs else 0)
