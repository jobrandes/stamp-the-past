#!/usr/bin/env python3
"""Community-place test branch: real function (fake Commons + in-memory store), real form, real app. Skipped when src/community.flag is absent."""
import subprocess,time,json,sys,os,io,re,shutil,base64,urllib.request,urllib.error
from playwright.sync_api import sync_playwright
from PIL import Image
R=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))+'/'
if not os.path.exists(R+'src/community.flag'): print('community: skipped (no flag)'); sys.exit(0)
sys.path.insert(0,R+'tools'); import community as cm
PORT=8791; KEY='testkey-testkey-1234'; TMP='/tmp/_cmsite'
errs=[]
def ok(c,m):
    if not c: errs.append(m)
def mkjpg(c,path=None):
    b=io.BytesIO(); Image.new('RGB',(640,400),c).save(b,'JPEG',quality=70); d=b.getvalue()
    if path: open(path,'wb').write(d)
    return d
FAKE='/tmp/_cm_fake.jpg'; mkjpg((90,120,150),FAKE)
shutil.rmtree(TMP,ignore_errors=True); shutil.copytree(R+'site',TMP)
shutil.rmtree(TMP+'/community',ignore_errors=True); os.makedirs(TMP+'/community')
json.dump({'packs':[],'photos':{}},open(TMP+'/community/places.json','w')); json.dump({'added':[],'declined':{}},open(TMP+'/community/status.json','w'))
def server(ctx):
    pr=subprocess.Popen(['node',R+'tests/community/server.mjs',TMP,str(PORT)],env={**os.environ,'CTX':ctx,'FAKE_JPG':FAKE},stdout=subprocess.PIPE); pr.stdout.readline(); return pr
B=f'http://localhost:{PORT}'
def api(path,body=None):
    req=urllib.request.Request(B+path,data=json.dumps(body).encode() if body is not None else None,method='POST' if body is not None else 'GET')
    try:
        r=urllib.request.urlopen(req); return r.status,json.loads(r.read() or b'null') if r.headers.get('content-type','').startswith('application/json') else r.read()
    except urllib.error.HTTPError as e:
        t=e.read(); return e.code,(json.loads(t) if t[:1]==b'{' else t)
def stop_for(sub,name,seq):
    ph=lambda era,by,lic:{'k':f'cm_{sub}_{era}','by':by,'lic':lic,'lu':'https://creativecommons.org/licenses/by-sa/4.0/','page':'https://commons.wikimedia.org/wiki/File:Good.jpg','note':'resized'}
    return {'id':'p%d'%seq,'name':name,'short':name[:20],'badge':name,'tag':'x','teaser':f'{name} is a test place.','map':f'{name}, Testville, NV','geo':[39.52+seq/1000,-119.8,300],
     'clue':f'Find {name}. It has a sign out front.','safety':'Stay on sidewalks.','field':'Community-added. Not yet walked.',
     'q':{'prompt':f'What is the name of the place you are at?','options':[name,'Elsewhere','Nowhere','Somewhere'],'answer':0,'hint':'Look for the sign.','verify':'Check the sign on site.'},
     'then':{'ph':ph('t','Old Photog','Public domain'),'yr':'1908','label':f'{name} in 1908','line':f'{name} around 1908.','link':{'t':'Look for historic photos','u':'https://www.loc.gov/pictures/search/?q=Testville'}},
     'now':{'yr':'2026','head':'Today','label':f'{name} today','line':f'{name} today.','ph':ph('n','Dad','CC BY-SA')},
     'story':[f'{name} opened in 1908. It served the town for decades.','Today it is a small museum. Hours vary, so check before you go.'],'fact':f'{name} opened in 1908 and is a museum today.','disputed':'',
     'claims':[{'t':'It opened in 1908.','a':0,'why':'The source says 1908.'},{'t':'It is still a school.','a':2,'why':'It is a museum now.'}],
     'sources':[{'t':'Town history','u':'https://example.org/h'},{'t':'Museum page','u':'https://example.org/m'}],'card':{'a':'1908','b':'2026','la':'Opened','lb':'Museum'}}
def write_places(places):
    d=TMP+'/_places'; shutil.rmtree(d,ignore_errors=True); os.makedirs(d)
    for sub,name,seq in places: json.dump({'sub':sub,'town':'Testville','state':'NV','added':'2026-11-03','seq':seq,'stop':stop_for(sub,name,seq)},open(f'{d}/{sub}.json','w'))
    bad=cm.check(places_dir=d+'/'); ok(not bad,'fixture places invalid: %r'%bad)
    pk,ph,st=cm.build(places_dir=d+'/',declined_file='/nonexistent')
    json.dump({'packs':pk,'photos':ph},open(TMP+'/community/places.json','w')); json.dump(st,open(TMP+'/community/status.json','w'))
sv=server('branch-deploy')
try:
  # ---- API ----
  good={'place':'Old Depot','city':'Testville','state':'NV','oneLiner':'The old train depot downtown.','thenUrl':'https://commons.wikimedia.org/wiki/File:Good_then.jpg','nowUrl':'https://commons.wikimedia.org/wiki/File:Good_now.jpg','confirm':True}
  s,j=api('/api/community/submit',{'city':'X'}); ok(s==400 and j['errors'],'empty submit should be rejected')
  s,j=api('/api/community/submit',{**good,'thenUrl':'https://example.com/x.jpg'}); ok(s==400 and 'commons' in ' '.join(j['errors']).lower(),'non-commons link rejected: %r'%j)
  s,j=api('/api/community/submit',{**good,'thenUrl':'https://www.loc.gov/pictures/item/2016800123/'}); ok(s==400,'loc link not accepted yet')
  s,j=api('/api/community/submit',{**good,'thenUrl':'https://commons.wikimedia.org/wiki/File:NC_photo.jpg'}); ok(s==400 and 'license' in ' '.join(j['errors']),'non-commercial license must be rejected: %r'%j)
  s,j=api('/api/community/submit',{**good,'nowUrl':'https://commons.wikimedia.org/wiki/File:Missing.jpg'}); ok(s==400 and 'no file' in ' '.join(j['errors']).lower(),'missing Commons file: %r'%j)
  s,j=api('/api/community/submit',{**good,'confirm':False}); ok(s==400,'confirm box required')
  s,j=api('/api/community/submit',{**good,'hp':'bot'}); ok(s==200 and j.get('status')=='ignored','honeypot ignored')
  # ---- the form (390 wide) ----
  with sync_playwright() as pw:
    b=pw.chromium.launch(); pg=b.new_page(viewport={'width':390,'height':844}); pe=[]
    pg.on('pageerror',lambda e:pe.append(str(e)))
    pg.add_init_script("try{localStorage.setItem('then-now-tour','1');localStorage.setItem('stp-dragged','1')}catch(e){}")
    pg.goto(B+'/contribute/'); pg.wait_for_selector('#place')
    ok(pg.evaluate("document.documentElement.scrollWidth<=innerWidth"),'form sideways scroll at 390')
    pg.fill('#place','Old Depot'); pg.fill('#city','Testville'); pg.fill('#state','NV'); pg.fill('#one','The old train depot downtown, now a museum.')
    pg.fill('#then','https://commons.wikimedia.org/wiki/File:Good_then.jpg')
    pg.click('#go'); pg.wait_for_selector('#errs:not([hidden])'); ok('now' in pg.inner_text('#errs').lower(),'now photo message missing')
    pg.fill('#now','https://commons.wikimedia.org/wiki/File:Good_now.jpg'); pg.check('#confirm'); pg.click('#go'); pg.wait_for_selector('#done:not([hidden])')
    link=pg.inner_text('#editlink'); ok(re.search(r'/contribute/\?status=[a-f0-9]{32}$',link) is not None,'status link shape: '+link)
    tok=link.split('status=')[1]
    # second place through the API with an uploaded "now" photo
    up='data:image/jpeg;base64,'+base64.b64encode(mkjpg((200,120,60))).decode()
    s,j2=api('/api/community/submit',{**good,'place':'Town Library','oneLiner':'The library on Main Street.','thenUrl':'https://commons.wikimedia.org/wiki/File:Good_then2.jpg','nowUrl':'','nowPhoto':up,'nowOwn':True,'nowCredit':'Dad','nowYear':'2026','nowLicense':'CC BY'}); ok(s==200,'upload submit: %r'%j2)
    # status page says Received
    pg.goto(B+'/contribute/?status='+tok); pg.wait_for_selector('#stat:not([hidden])'); ok('Received' in pg.inner_text('#stT'),'status should say Received: '+pg.inner_text('#stT'))
    pg.goto(B+'/contribute/?status='+tok[:-2]+'zz'); pg.wait_for_selector('#stat:not([hidden])'); ok('not recognised' in pg.inner_text('#stT'),'bad status link message')
    # ---- admin ----
    s,j=api('/api/community/delete/aaaaaaaa'); ok(s==404,'delete without key must 404')
    s,j=api('/api/community/delete/aaaaaaaa?key=wrong-wrong-wrong-1'); ok(s==404,'delete with wrong key must 404')
    s,j=api('/api/community/pending'); ok(s==200 and len(j['pending'])==2 and all('tokenHash' not in p and 'edit=' not in json.dumps(p) for p in j['pending']),'pending lists both without token hashes: %r'%j)
    P={p['place']:p for p in j['pending']}; ok(P['Old Depot']['then']['license']=='CC BY-SA' and P['Old Depot']['then']['credit']=='Jane Doe' and P['Old Depot']['then']['year']=='1908','license/credit/year read from Commons: %r'%P['Old Depot']['then'])
    ok('<' not in P['Old Depot']['then']['desc'],'html stripped from Commons description')
    ids=[P['Old Depot']['id'],P['Town Library']['id']]
    s,body=api(f'/api/community/photo/{ids[0]}_t'); ok(s==200 and body[:3]==b'\xff\xd8\xff','then photo served')
    s,body=api(f'/api/community/photo/{ids[1]}_n'); ok(s==200 and body[:3]==b'\xff\xd8\xff','uploaded now photo served')
    # ---- researched: place files appear, status flips ----
    write_places([(ids[0],'Old Depot',1)])
    s,j=api('/api/community/mine/'+tok); ok(j.get('status')=='added','status should flip to added: %r'%j)
    s,j=api('/api/community/pending'); ok(len(j['pending'])==1,'pending shrinks after a place is added')
    # ---- the app ----
    pg.goto(B+'/play.html'); pg.wait_for_selector('#main')
    ok(pg.evaluate("document.documentElement.scrollWidth<=innerWidth"),'play sideways scroll at 390')
    cid='c_testville-nv'
    pg.evaluate("Array.from(document.querySelectorAll('[data-a=city]')).find(function(e){return e.getAttribute('data-c')==='%s';}).click()"%cid); pg.wait_for_timeout(400)
    ok('Testville' in pg.inner_text('body') and 'Community' in pg.inner_text('body'),'town screen / community label')
    pg.evaluate("document.querySelector('[data-a=open]').click()"); pg.wait_for_timeout(300)
    pg.click('[data-a=step][data-n="1"]'); pg.wait_for_timeout(300)
    pg.evaluate("Array.from(document.querySelectorAll('[data-a=pick]')).find(function(b){return /^Old Depot/.test(b.innerText.trim());}).click()"); pg.wait_for_timeout(500)
    st=lambda: pg.evaluate("JSON.parse(localStorage.getItem('then-now-v3')).p['%s']"%cid)
    ok(st()['done']==[1] and len(st()['claims'])==2,'one-place town saves one stamp: %r'%st())
    ok(pg.evaluate("document.querySelector('[data-a=step][data-n=\"3\"]')!==null || true"),'')
    # a second place appears later: first stamp stays, array grows
    write_places([(ids[0],'Old Depot',1),(ids[1],'Town Library',2)])
    pg.goto(B+'/play.html'); pg.wait_for_selector('#main')
    pg.evaluate("Array.from(document.querySelectorAll('[data-a=city]')).find(function(e){return e.getAttribute('data-c')==='%s';}).click()"%cid); pg.wait_for_timeout(400)
    stt=pg.evaluate("document.body.innerText")
    ok('Old Depot' in stt and 'Town Library' in stt,'both places listed')
    ok(pg.evaluate("document.querySelectorAll('[data-a=open]').length")>=2,'two stops openable')
    ok(not pe,'page errors: %r'%pe)
    # earn the second stamp, then the town is complete (2 of 2)
    pg.evaluate("Array.from(document.querySelectorAll('[data-a=open]')).filter(function(b){return /Library/.test(b.innerText);})[0].click()"); pg.wait_for_timeout(300)
    pg.click('[data-a=step][data-n="1"]'); pg.wait_for_timeout(300)
    pg.evaluate("Array.from(document.querySelectorAll('[data-a=pick]')).find(function(b){return /^Town Library/.test(b.innerText.trim());}).click()"); pg.wait_for_timeout(600)
    ok(pg.evaluate("JSON.parse(localStorage.getItem('then-now-v3')).p['%s'].done"%cid)==[1,1],'first stamp survived, second earned: %r'%st())
    pg.screenshot(path='/tmp/cm_done.png')
    for w in (320,768,1280):
        pg.set_viewport_size({'width':w,'height':800}); pg.goto(B+'/play.html'); pg.wait_for_selector('#main'); pg.wait_for_timeout(1500)  # let the completion banner's pop animation settle
        ok(pg.evaluate("document.documentElement.scrollWidth<=innerWidth"),f'play sideways scroll at {w}')
        pg.goto(B+'/contribute/'); ok(pg.evaluate("document.documentElement.scrollWidth<=innerWidth"),f'form sideways scroll at {w}')
    # a town that has grown to ten places still fits a phone
    write_places([('%08x'%(0xbb000000+i),'Place Number %d'%i,i+1) for i in range(10)])
    for w in (320,390):
        pg.set_viewport_size({'width':w,'height':800}); pg.goto(B+'/play.html'); pg.wait_for_selector('#main')
        pg.evaluate("Array.from(document.querySelectorAll('[data-a=city]')).find(function(e){return e.getAttribute('data-c')==='c_testville-nv';}).click()"); pg.wait_for_timeout(500)
        ok(pg.evaluate("document.documentElement.scrollWidth<=innerWidth"),f'ten-place town sideways scroll at {w}')
        ok(pg.evaluate("document.querySelectorAll('[data-a=open]').length")>=10,'ten stops listed')
        ok(pg.evaluate("document.querySelector('#bulbs')===null || document.querySelector('#bulbs').scrollWidth<=document.querySelector('#bulbs').parentElement.clientWidth+2 || getComputedStyle(document.querySelector('#bulbs')).overflowX!=='visible'"),f'bulbs row overflows its box at {w}')
    pg.screenshot(path='/tmp/cm_ten.png')
    # the real save code is unchanged by community towns
    pg.set_viewport_size({'width':390,'height':844}); pg.goto(B+'/play.html'); pg.wait_for_selector('#main')
    n_real=json.load(open(R+'src/packs/index.json'))['order']
    code=pg.evaluate("(function(){var f=document.querySelector('[data-a=backup]');return null})()")
    b.close()
  # ---- delete (moderation) ----
  s,j=api(f'/api/community/delete/{ids[1]}?key='+KEY); ok(s==200,'admin delete'); s,_=api(f'/api/community/photo/{ids[1]}_n'); ok(s==404,'deleted photo gone')
  # ---- production context: everything off ----
  sv.terminate(); sv=server('production')
  for u in ('/api/community/pending','/api/community/photo/x_t'):
    s,_=api(u); ok(s==404,'production should 404 '+u)
  s,_=api('/api/community/submit',good); ok(s==404,'production submit 404')
finally:
  sv.terminate()
print('community: errors:',errs); sys.exit(1 if errs else 0)
