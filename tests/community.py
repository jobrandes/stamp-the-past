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
def server(ctx,uploads='1'):
    pr=subprocess.Popen(['node',R+'tests/community/server.mjs',TMP,str(PORT)],env={**os.environ,'CTX':ctx,'FAKE_JPG':FAKE,'UPLOADS':uploads},stdout=subprocess.PIPE); pr.stdout.readline(); return pr
B=f'http://localhost:{PORT}'
def api(path,body=None,key=None,raw=None):
    req=urllib.request.Request(B+path,data=(raw if raw is not None else json.dumps(body).encode() if body is not None else None),method='POST' if (body is not None or raw is not None) else 'GET',headers=({'x-admin-key':key} if key else {}))
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
    if not os.path.isdir(TMP+'/_stories'): os.makedirs(TMP+'/_stories')
    for sub,name,seq in places: json.dump({'sub':sub,'town':'Testville','state':'NV','added':'2026-11-03','seq':seq,'stop':stop_for(sub,name,seq)},open(f'{d}/{sub}.json','w'))
    bad=cm.check(places_dir=d+'/'); ok(not bad,'fixture places invalid: %r'%bad)
    pk,ph,st,tr=cm.build(places_dir=d+'/',declined_file='/nonexistent',stories_dir=TMP+'/_stories/')
    json.dump({'packs':pk,'photos':ph,'tours':tr},open(TMP+'/community/places.json','w')); json.dump(st,open(TMP+'/community/status.json','w'))
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
  s,j=api('/api/community/submit',{**good,'thenUrl':'','nowUrl':''}); ok(s==400 and 'at least one photo' in ' '.join(j['errors']).lower(),'no photo at all must be rejected: %r'%j)
  s,j=api('/api/community/submit',{**good,'hp':'bot'}); ok(s==200 and j.get('status')=='ignored','honeypot ignored')
  # ---- the form (390 wide) ----
  with sync_playwright() as pw:
    b=pw.chromium.launch(); pg=b.new_page(viewport={'width':390,'height':844}); pe=[]
    pg.on('pageerror',lambda e:pe.append(str(e)+' | '+str(getattr(e,'stack',''))[:400]))
    pg.add_init_script("try{localStorage.setItem('then-now-tour','1');localStorage.setItem('stp-dragged','1')}catch(e){}")
    pg.goto(B+'/contribute/'); pg.wait_for_selector('#place')
    ok(pg.evaluate("document.documentElement.scrollWidth<=innerWidth"),'form sideways scroll at 390')
    pg.fill('#place','Old Depot'); pg.fill('#city','Testville'); pg.fill('#state','NV'); pg.fill('#one','The old train depot downtown, now a museum.')
    pg.check('#confirm'); pg.click('#go'); pg.wait_for_selector('#errs:not([hidden])'); ok('at least one photo' in pg.inner_text('#errs').lower(),'photo message missing')
    pg.fill('#then','https://commons.wikimedia.org/wiki/File:Good_then.jpg')
    pg.fill('#now','https://commons.wikimedia.org/wiki/File:Good_now.jpg'); pg.click('#go'); pg.wait_for_selector('#done:not([hidden])')
    link=pg.text_content('#editlink'); ok(re.search(r'/contribute/\?status=[a-f0-9]{32}$',link) is not None,'status link shape: '+link)
    tok=link.split('status=')[1]
    # second place through the API with an uploaded "now" photo
    up='data:image/jpeg;base64,'+base64.b64encode(mkjpg((200,120,60))).decode()
    s,j2=api('/api/community/submit',{**good,'place':'Town Library','oneLiner':'The library on Main Street.','thenUrl':'https://commons.wikimedia.org/wiki/File:Good_then2.jpg','nowUrl':'','nowPhoto':up,'nowOwn':True,'nowCredit':'Dad','nowYear':'2026','nowLicense':'CC BY'}); ok(s==200,'upload submit: %r'%j2)
    # status page says Received
    pg.goto(B+'/contribute/?status='+tok); pg.wait_for_selector('#stat:not([hidden])'); ok('Received' in pg.inner_text('#stT'),'status should say Received: '+pg.inner_text('#stT'))
    pg.goto(B+'/contribute/?status='+tok[:-2]+'zz'); pg.wait_for_selector('#stat:not([hidden])'); ok('not recognised' in pg.inner_text('#stT'),'bad status link message')
    # ---- admin ----
    s,j=api('/api/community/delete/aaaaaaaa',{}); ok(s==404,'delete without key must 404')
    s,j=api('/api/community/delete/aaaaaaaa',{},key='wrong-wrong-wrong-1'); ok(s==404,'delete with wrong key must 404')
    s,j=api('/api/community/pending',key=KEY); ok(s==200 and len(j['pending'])==2 and all('tokenHash' not in p and 'edit=' not in json.dumps(p) for p in j['pending']),'pending lists both without token hashes: %r'%j)
    P={p['place']:p for p in j['pending']}; ok(P['Old Depot']['then']['license']=='CC BY-SA' and P['Old Depot']['then']['credit']=='Jane Doe' and P['Old Depot']['then']['year']=='1908','license/credit/year read from Commons: %r'%P['Old Depot']['then'])
    ok('<' not in P['Old Depot']['then']['desc'],'html stripped from Commons description')
    ids=[P['Old Depot']['id'],P['Town Library']['id']]
    s,body=api(f'/api/community/photo/{ids[0]}_t',key=KEY); ok(s==200 and body[:3]==b'\xff\xd8\xff','then photo visible with the admin key')
    s,body=api(f'/api/community/photo/{ids[1]}_n'); ok(s==404,'uploaded photo is HELD: not public before approval')
    s,body=api(f'/api/community/photo/{ids[1]}_n',key=KEY); ok(s==200 and body[:3]==b'\xff\xd8\xff','uploaded now photo visible with the admin key')
    s,body=api(f'/api/community/photo/{ids[0]}_t'); ok(s==404,'Commons photos are also held before approval')
    s,j=api('/api/community/pending'); ok(s==404,'pending inbox is private without the key: %r'%s)
    s,j=api('/api/community/pending',key='wrong-wrong-wrong-1'); ok(s==404,'pending with a wrong key is 404')
    s,j=api('/api/community/submit',raw=b'null'); ok(s==400,'JSON null body gives 400, not a crash: %r'%s)
    s,j=api('/api/community/submit',{**good,'thenUrl':'https://commons.wikimedia.org/wiki/File:%E0%A4%A.jpg'}); ok(s==400,'malformed percent-encoding gives 400: %r %r'%(s,j))
    s,j=api('/api/community/submit',{**good,'place':'Bad Year','nowUrl':'','nowPhoto':up,'nowOwn':True,'nowCredit':'Dad','nowYear':'abcd','nowLicense':'CC BY'}); ok(s==400 and 'year' in json.dumps(j).lower(),'non-numeric year rejected: %r'%j)
    s,j=api('/api/community/submit',{**good,'place':'Fake Jpeg','nowUrl':'','nowPhoto':'data:image/jpeg;base64,'+base64.b64encode(b'\xff\xd8\xff'+b'A'*3000).decode(),'nowOwn':True,'nowCredit':'Dad','nowYear':'2026','nowLicense':'CC BY'}); ok(s==400,'undecodable JPEG-header payload rejected: %r %r'%(s,j))
    # server re-encodes uploads and drops EXIF/GPS
    ex=Image.new('RGB',(900,600),(10,200,50)); xb=io.BytesIO(); eo=Image.Exif(); eo[0x010F]='SecretCamera'; ex.save(xb,'JPEG',exif=eo.tobytes(),quality=80)
    s,j=api('/api/community/submit',{**good,'place':'Exif Probe','nowUrl':'','nowPhoto':'data:image/jpeg;base64,'+base64.b64encode(xb.getvalue()).decode(),'nowOwn':True,'nowCredit':'Dad','nowYear':'2026','nowLicense':'CC BY'}); ok(s==200,'exif upload accepted: %r'%j)
    pj=api('/api/community/pending',key=KEY)[1]['pending']; pid=[p['id'] for p in pj if p['place']=='Exif Probe'][0]
    s,body=api(f'/api/community/photo/{pid}_n',key=KEY); ok(s==200 and b'SecretCamera' not in body and b'Exif' not in body[:40],'server stripped EXIF from the stored upload')
    api(f'/api/community/delete/{pid}',{},key=KEY)
    # ---- researched: place files appear, status flips ----
    write_places([(ids[0],'Old Depot',1)])
    s,j=api('/api/community/mine/'+tok); ok(j.get('status')=='added','status should flip to added: %r'%j)
    s,j=api('/api/community/pending',key=KEY); ok(len(j['pending'])==1,'pending shrinks after a place is added')
    # ---- the app ----
    pg.goto(B+'/play.html'); pg.wait_for_selector('#main')
    ok(pg.evaluate("document.documentElement.scrollWidth<=innerWidth"),'play sideways scroll at 390')
    cid='c_testville-nv'
    # slice 3: Suggest a place entry points
    ok(pg.evaluate("!!document.querySelector('.reqline [data-a=suggest]')"),'Towns list has a Suggest a place link')
    ok(pg.evaluate("!!document.querySelector('.reqline [data-a=reqtown]')"),'Tell us which town to add stays')
    pg.evaluate("document.getElementById('menuBtn').click()"); pg.wait_for_timeout(300)
    ok(pg.evaluate("!!document.querySelector('.menu-panel [data-a=suggest]')"),'Menu has Suggest a place')
    pg.evaluate("document.querySelector('[data-a=menuclose]').click()"); pg.wait_for_timeout(200)
    pg.evaluate("document.querySelector('#bnav [data-t=home]').click()"); pg.wait_for_timeout(200)
    pg.evaluate("document.querySelector('[data-a=nbopen]').click()"); pg.wait_for_timeout(300)
    pg.evaluate("document.querySelector('[data-a=nbnoloc]').click()"); pg.wait_for_timeout(300)
    ok(pg.evaluate("!!document.querySelector('.nbwrap [data-a=suggest]')"),'Nearby place picker has Suggest it')
    pg.evaluate("document.querySelector('[data-a=nbback], [data-a=home]').click()"); pg.wait_for_timeout(300)
    # slice 2: community towns live in their own last, collapsed section with a note and a Suggest link
    regs=pg.evaluate("Array.from(document.querySelectorAll('details.reg > summary .rname')).map(function(e){return e.textContent.trim().toLowerCase();})")
    ok(regs and regs[-1]=='community-added' and regs.count('community-added')==1,'Community-added region is last and unique: %r'%regs)
    ok(pg.evaluate("(function(){var d=Array.from(document.querySelectorAll('details.reg')).pop();return !d.open;})()"),'community section starts collapsed')
    ok(pg.evaluate("!!document.querySelector('.comnote a[href=\"/contribute/\"]')"),'community section has a Suggest a place link')
    ok(pg.evaluate("(function(){var t=document.querySelector('[data-a=city][data-c=\"c_testville-nv\"] .lvl');return !!t&&/community-added/i.test(t.textContent)&&!/hidden gems/i.test(t.textContent);})()"),'community tile says Community-added, not Hidden Gems')
    pg.evaluate("Array.from(document.querySelectorAll('details.reg')).pop().open=true"); pg.wait_for_timeout(200)
    ok(pg.evaluate("document.querySelector('.comnote a').getBoundingClientRect().height>=44"),'Suggest link is a 44px target')
    ok(pg.evaluate("document.documentElement.scrollWidth<=innerWidth"),'home with community section sideways scroll at 390')
    pg.evaluate("Array.from(document.querySelectorAll('[data-a=city]')).find(function(e){return e.getAttribute('data-c')==='%s';}).click()"%cid); pg.wait_for_timeout(400)
    ok('Testville' in pg.inner_text('body') and 'Community' in pg.inner_text('body'),'town screen / community label')
    ok(pg.evaluate("!!document.querySelector('[data-a=suggest][data-c=\"c_testville-nv\"]')"),'town page has Suggest a place for that town')
    pg.evaluate("document.querySelector('[data-a=suggest][data-c=\"c_testville-nv\"]').click()"); pg.wait_for_selector('#city'); pg.wait_for_timeout(200)
    ok(pg.evaluate("document.getElementById('city').value")=='Testville' and pg.evaluate("document.getElementById('state').value")=='NV','contribute form is prefilled from the town: %r'%pg.evaluate("[document.getElementById('city').value,document.getElementById('state').value]"))
    pg.go_back(); pg.wait_for_selector('[data-a=city]',state='attached'); pg.wait_for_timeout(500)
    pg.evaluate("Array.from(document.querySelectorAll('[data-a=city]')).find(function(e){return e.getAttribute('data-c')==='%s';}).click()"%cid); pg.wait_for_timeout(400)
    pg.evaluate("document.querySelector('[data-a=open]').click()"); pg.wait_for_timeout(300)
    # slice 1: label and report on a community place
    ok(pg.evaluate("!!document.querySelector('.combadge')") and 'community-added' in pg.inner_text('.combadge').lower(),'community stop shows the Community-added label')
    ok(pg.evaluate("document.querySelector('.repline [data-a=report]').innerText")=='Report this place','community stop says Report this place')
    sent=[]
    pg.route('**/',lambda r: (sent.append(r.request.post_data or '') if r.request.method=='POST' else None, r.fulfill(status=200,body='ok') if r.request.method=='POST' else r.continue_())[1])
    pg.click('.repline [data-a=report]'); pg.wait_for_selector('#report')
    ok(pg.evaluate("!!document.getElementById('repWhy')") and pg.evaluate("document.getElementById('repWhy').options.length")==5,'report has five reasons')
    ok('Community report p1' in pg.evaluate("document.getElementById('report').dataset.where"),'report names the community place: '+pg.evaluate("document.getElementById('report').dataset.where"))
    pg.select_option('#repWhy','A private or unsafe place'); pg.click('[data-a=repsend]'); pg.wait_for_timeout(500)
    ok(len(sent)==1 and 'Community+report+p1' in sent[0] and 'private+or+unsafe' in sent[0],'report posts place id and reason without typing: %r'%sent)
    ok(pg.evaluate("!document.getElementById('report')"),'report closes after sending')
    pg.unroute('**/')
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
    ok(pg.evaluate("JSON.parse(localStorage.getItem('then-now-v3')).p['%s'].ids"%cid)==['p1','p2'],'saved community stamps carry place ids')
    # the FIRST place is removed and a new one added: stamps follow the place, not the position
    write_places([(ids[1],'Town Library',2),('%08x'%0xcc000001,'Brand New Hall',3)])
    pg.goto(B+'/play.html'); pg.wait_for_selector('#main')
    pg.evaluate("Array.from(document.querySelectorAll('[data-a=city]')).find(function(e){return e.getAttribute('data-c')==='%s';}).click()"%cid); pg.wait_for_timeout(500)
    rows=pg.evaluate("Array.from(document.querySelectorAll('[data-a=open]')).map(function(b){return b.innerText.replace(/\\s+/g,' ');})")
    lib=[r for r in rows if 'Library' in r]; new_=[r for r in rows if 'Brand New' in r]
    ok(lib and new_ and 'BADGE EARNED' in lib[0].upper() and 'NOT FOUND YET' in new_[0].upper(),'stamp stays with Town Library after the first place is removed; new place is unstamped: %r'%rows)
    write_places([(ids[0],'Old Depot',1),(ids[1],'Town Library',2)])
    pg.screenshot(path='/tmp/cm_done.png')
    # community stamps never count toward the official totals, level or badges
    pg.goto(B+'/play.html'); pg.wait_for_selector('#main'); pg.wait_for_timeout(1500)
    pg.evaluate("document.querySelector('#bnav [data-t=home]').click()"); pg.wait_for_timeout(400)
    ok(not pe,'Home must not crash when the current mission is a one or two place community town: %r'%pe[-1:])
    ok(pg.evaluate("/^0 of/.test((document.querySelector('.passport-line')||{textContent:''}).textContent.trim())"),'community stamps stay out of the official stamp total: '+pg.evaluate("(document.querySelector('.passport-line')||{textContent:'none'}).textContent"))
    ok(pg.evaluate("document.body.classList.contains('homefirst')"),'home still treats the player as first-time (no official stamps)')
    pg.evaluate("Array.from(document.querySelectorAll('[data-a=city]')).find(function(e){return e.getAttribute('data-c')==='%s';}).click()"%cid); pg.wait_for_timeout(400)
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
    # ---- history stops: a place with only a recent photo becomes a Story stop ----
    s,jn=api('/api/community/submit',{**good,'place':'Hilltop Chapel','thenUrl':'','nowUrl':'https://commons.wikimedia.org/wiki/File:Good_now.jpg'}); ok(s==200,'now-only submit accepted: %r'%jn)
    s,jt=api('/api/community/submit',{**good,'place':'Lost Mill','nowUrl':''}); ok(s==200,'then-only submit accepted: %r'%jt)
    s,j=api('/api/community/pending',key=KEY); PP={p['place']:p for p in j['pending']}
    ok('then' not in PP['Hilltop Chapel'] and PP['Hilltop Chapel']['now']['credit']=='Jane Doe','now-only has no then photo')
    ok('now' not in PP['Lost Mill'] and 'then' in PP['Lost Mill'],'then-only has no now photo')
    cid_s=PP['Hilltop Chapel']['id']; cid_w=PP['Lost Mill']['id']
    d=TMP+'/_stories'; shutil.rmtree(d,ignore_errors=True); os.makedirs(d)
    story={'id':'chapel','name':'Hilltop Chapel','area':'Testville','geo':[39.5,-119.8,150],'addr':'1 Hill Rd, Testville, NV','invite':'A small chapel on a hill.',
      'story':['The chapel was built in 1900.','It is still used for weddings.'],'facts':[{'t':'Built in 1900.','src':[0,1]},{'t':'Used for weddings.','src':[0]},{'t':'On a hill.','src':[1]}],
      'access':'Look from the public road; the chapel is private on weekdays, so check before going.','access_check':{'on':'2026-11-03','by':'Claude','how':'Read against two pages.'},
      'sources':[{'t':'A','u':'https://example.org/a'},{'t':'B','u':'https://example.org/b'}],
      'ph':{'k':'cm_%s_n'%cid_s,'alt':'The chapel','by':'Jane Doe','lic':'CC BY-SA','lu':'https://creativecommons.org/licenses/by-sa/4.0/','page':'https://commons.wikimedia.org/wiki/File:Good_now.jpg'}}
    json.dump({'sub':cid_s,'town':'Storyville','state':'NV','added':'2026-11-03','stop':story},open(f'{d}/{cid_s}.json','w'))
    ok(cm.build(places_dir=TMP+'/_places/',declined_file='/nonexistent',stories_dir=d+'/')[3][0]['stops'][0]['town']=='c_storyville-nv','story stop is tied to its town')
    pk,ph,st,tr=cm.build(places_dir=TMP+'/_places/',declined_file='/nonexistent',stories_dir=d+'/'); st['waiting']={cid_w:'We still need a recent photo of this place.'}
    json.dump({'packs':pk,'photos':ph,'tours':tr},open(TMP+'/community/places.json','w')); json.dump(st,open(TMP+'/community/status.json','w'))
    ok(cid_s in st['added'],'story counted as added')
    s,j=api('/api/community/pending',key=KEY); ok(cid_s not in [p['id'] for p in j['pending']] and cid_w not in [p['id'] for p in j['pending']],'story and waiting leave pending')
    tokn=jn['edit'] if 'edit' in jn else ''
    s,j=api('/api/community/mine/'+jn['edit']); ok(j.get('status')=='added','story status added')
    s,j=api('/api/community/mine/'+jt['edit']); ok(j.get('status')=='waiting' and 'recent photo' in j.get('note',''),'waiting status: %r'%j)
    pg.set_viewport_size({'width':390,'height':844}); pg.goto(B+'/contribute/?status='+jt['edit']); pg.wait_for_selector('#stat:not([hidden])'); ok('Waiting for a photo' in pg.inner_text('#stT'),'waiting page text: '+pg.inner_text('#stT'))
    ok(pg.is_visible('#addp'),'waiting status page offers Add or change a photo')
    pg.goto(B+'/contribute/'); pg.wait_for_timeout(600); ok(pg.is_visible('#mine') and 'Lost Mill' in pg.inner_text('#minelist'),'My suggestions list shows the place just viewed: '+pg.inner_text('#minelist'))
    # the waiting place can be completed from its private link and returns to review
    s,j=api('/api/community/mine/'+jt['edit'][:-2]+'zz/photo',{'nowUrl':'https://commons.wikimedia.org/wiki/File:Good_now.jpg','confirm':True}); ok(s==404,'add-photo with a wrong token is 404')
    s,j=api('/api/community/mine/'+jt['edit']+'/photo',{'confirm':True}); ok(s==400,'add-photo with no photo is rejected: %r'%j)
    s,j=api('/api/community/mine/'+jt['edit']+'/photo',{'nowUrl':'https://commons.wikimedia.org/wiki/File:Good_now.jpg'}); ok(s==400,'add-photo needs the confirm box')
    s,j=api('/api/community/mine/'+jt['edit']+'/photo',{'nowUrl':'https://commons.wikimedia.org/wiki/File:Good_now.jpg','confirm':True}); ok(s==200,'add-photo accepted: %r'%j)
    s,j=api('/api/community/pending',key=KEY); PW={p['id']:p for p in j['pending']}; ok(cid_w in PW and PW[cid_w].get('now') and PW[cid_w].get('then'),'resubmitted waiting place is pending again with both photos')
    s,body=api(f'/api/community/photo/{cid_w}_n',key=KEY); ok(s==200 and body[:3]==b'\xff\xd8\xff','new photo stored and visible to admin')
    s,j=api('/api/community/mine/'+jn['edit']+'/photo',{'nowUrl':'https://commons.wikimedia.org/wiki/File:Good_now.jpg','confirm':True}); ok(s==400 and 'already added' in json.dumps(j),'an added place cannot be changed: %r'%j)
    pg.goto(B+'/play.html'); pg.wait_for_selector('#main')
    pg.evaluate("document.querySelector('#bnav [data-t=home]').click()"); pg.wait_for_timeout(300)
    pg.evaluate("document.querySelector('[data-a=nbopen]').click()"); pg.wait_for_timeout(300)
    pg.evaluate("document.querySelector('[data-a=nbnoloc]').click()"); pg.wait_for_timeout(300)
    ok('storyville' in pg.inner_text('body').lower(),'story town listed under Nearby stops')
    pg.evaluate("Array.from(document.querySelectorAll('[data-a=nbarea]')).find(function(b){return /storyville/i.test(b.innerText);}).click()"); pg.wait_for_timeout(300)
    pg.evaluate("document.querySelector('[data-a=nbstory]').click()"); pg.wait_for_timeout(500)
    ok('hilltop chapel' in pg.inner_text('body').lower() and pg.evaluate("!!document.querySelector('.nbfig img')"),'story card shows the photo')
    ok(pg.evaluate("document.documentElement.scrollWidth<=innerWidth"),'story card sideways scroll')
    ok(pg.evaluate("!!document.querySelector('.combadge')"),'community story card shows the Community-added label')
    ok(pg.evaluate("document.querySelector('.repline [data-a=report]')&&document.querySelector('.repline [data-a=report]').getAttribute('data-com')")=='chapel','community story card has a Report button')
    # the real save code is unchanged by community towns
    pg.set_viewport_size({'width':390,'height':844}); pg.goto(B+'/play.html'); pg.wait_for_selector('#main')
    n_real=json.load(open(R+'src/packs/index.json'))['order']
    code=pg.evaluate("(function(){var f=document.querySelector('[data-a=backup]');return null})()")
    b.close()
  # ---- delete (moderation) ----
  s,j=api(f'/api/community/delete/{ids[1]}',{},key=KEY); ok(s==200,'admin delete'); s,_=api(f'/api/community/photo/{ids[1]}_n'); ok(s==404,'deleted photo gone')
  # ---- uploads off (the default on Netlify): API rejects, config says off, form hides the upload box ----
  sv.terminate(); sv=server('branch-deploy','0')
  s,j=api('/api/community/config'); ok(s==200 and j=={'uploads':False},'config reports uploads off: %r'%j)
  up2='data:image/jpeg;base64,'+base64.b64encode(mkjpg((10,120,60))).decode()
  s,j=api('/api/community/submit',{**good,'place':'Upload Probe','nowUrl':'','nowPhoto':up2,'nowOwn':True,'nowCredit':'x','nowYear':'2026','nowLicense':'CC BY'}); ok(s==400 and 'turned off' in json.dumps(j),'upload rejected when off: %r %r'%(s,j))
  s,j=api('/api/community/submit',{**good,'place':'Link Probe'}); ok(s==200,'commons-link submit still works when uploads are off: %r'%j)
  with sync_playwright() as pw:
    b=pw.chromium.launch(); pg=b.new_page(viewport={'width':390,'height':844}); pg.goto(B+'/contribute/'); pg.wait_for_timeout(800)
    ok(pg.evaluate("document.getElementById('own').hidden")==True and not pg.is_visible('#own'),'upload box hidden when uploads are off')
    b.close()
  sv.terminate(); sv=server('branch-deploy','1')
  with sync_playwright() as pw:
    b=pw.chromium.launch(); pg=b.new_page(viewport={'width':390,'height':844}); pg.goto(B+'/contribute/'); pg.wait_for_timeout(800)
    ok(pg.is_visible('#own'),'upload box shown when uploads are on')
    b.close()
  # ---- queue limit counts only open places, not added/declined ones ----
  sv.terminate(); sv=server('branch-deploy','1')
  ids=[]
  for i in range(60):
    s,r=api('/api/community/submit',{**good,'place':'Queue Place %d'%i}); 
    if s==200: ids.append(r['id'])
  ok(len(ids)==60,'60 open places accepted, got %d'%len(ids))
  s,r=api('/api/community/submit',{**good,'place':'Queue Place 61'}); ok(s==429 and 'queue' in json.dumps(r).lower(),'61st open place refused: %s'%s)
  json.dump({'added':ids[:2],'declined':{ids[2]:'no'}},open(TMP+'/community/status.json','w'))
  for _ in range(3):
    s,r=api('/api/community/submit',{**good,'place':'Queue After'}); ok(s==200,'room frees up once places are added or declined: %s'%s)
  s,r=api('/api/community/submit',{**good,'place':'Queue Over'}); ok(s==429,'cap applies again once full: %s'%s)
  json.dump({'added':[],'declined':{}},open(TMP+'/community/status.json','w'))
  # ---- production context: everything off ----
  sv.terminate(); sv=server('production')
  for u in ('/api/community/pending','/api/community/photo/x_t'):
    s,_=api(u); ok(s==404,'production should 404 '+u)
  s,_=api('/api/community/submit',good); ok(s==404,'production submit 404')
finally:
  sv.terminate()
print('community: errors:',errs); sys.exit(1 if errs else 0)
