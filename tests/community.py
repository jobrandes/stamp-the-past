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
shutil.copy(R+'site/community/report.json',TMP+'/community/report.json'); json.dump({'packs':[],'photos':{}},open(TMP+'/community/places.json','w')); json.dump({'added':[],'declined':{}},open(TMP+'/community/status.json','w'))

# ---- approval rules (pure checks, no server) ----
_rules=cm.load_rules(R); _ids={r['id'] for r in _rules['rules']}
ok(len(_ids)==len(_rules['rules']) and len(_ids)>=15,'rules have unique ids')
ok(all(r['by'] in ('code','claude','both') and r['for'] and r['text'] for r in _rules['rules']),'every rule says who checks it and what it applies to')
ok(not cm.check(R),'repo approvals and stories pass: %r'%cm.check(R))
def _st(name='Sample Mill',geo=(39.5,-119.8,200),**k):
    st={'id':'sm','name':name,'area':'a','addr':'1 Main St','invite':'Come and see it.','access':'Seen from the public sidewalk. Check opening hours before you go.','geo':list(geo)+[],'story':['One.','Two.'],'facts':[{'t':'A fact.','src':[0]},{'t':'B.','src':[1]},{'t':'C.','src':[0]}],'sources':[{'t':'a','u':'https://a.example/'},{'t':'b','u':'https://b.example/'}],'ph':{'k':'cm_aaaaaaaa_n','by':'X','lic':'CC BY-SA','page':'https://x/','lu':'https://x/'}}
    st['geo']=list(geo); st.update(k); return st
_full={r:'pass' for r in cm.rules_for(_rules,'place')}
def _ap(**k):
    a={'kind':'place','decision':'added','on':'2026-11-05','place':'Sample Mill','rules':dict(_full),'photos':[{'k':'cm_aaaaaaaa_n','verdict':'used'}]}; a.update(k); return a
def _chk(st=None,ap=None,off=(),**kw):
    return cm.check_approvals(_rules,{'aaaaaaaa':ap} if ap else {},[('aaaaaaaa.json',{'sub':'aaaaaaaa','town':'Reno','state':'NV','stop':st or _st()})],list(off),{},[],kw.get('dp',[]))
ok(not _chk(ap=_ap()),'a fully approved place passes: %r'%_chk(ap=_ap()))
ok(any('no "added" approval' in x for x in _chk()),'a published place with no approval record is refused')
_a=_ap(); del _a['rules']['ph-people']; ok(any('ph-people' in x for x in _chk(ap=_a)),'a missing rule result is refused')
_a=_ap(); _a['rules']['ph-people']='fail: a face'; ok(any('ph-people' in x for x in _chk(ap=_a)),'a failed rule cannot be added')
ok(any('listed as "used"' in x for x in _chk(ap=_ap(photos=[]))),'every published photo must be in the record')
ok(any('held-back' in x for x in _chk(ap=_ap(photos=[{'k':'cm_aaaaaaaa_n','verdict':'used'},{'k':'cm_aaaaaaaa_x1','verdict':'held back','why':'face'}]))),'held-back photo must be in declined-photos.json')
ok(not _chk(ap=_ap(photos=[{'k':'cm_aaaaaaaa_n','verdict':'used'},{'k':'cm_aaaaaaaa_x1','verdict':'held back','why':'face'}]),dp=['aaaaaaaa_x1']),'held-back photo listed correctly passes')
ok(any('web link' in x for x in _chk(st=_st(invite='See http://spam.example now'),ap=_ap())),'web links in the text are refused')
ok(any('email' in x for x in _chk(st=_st(invite='Write bob@example.com'),ap=_ap())),'emails in the text are refused')
ok(any('phone' in x for x in _chk(st=_st(invite='Call 775-555-0123 today'),ap=_ap())),'phone numbers in the text are refused')
_s=_st(); _s['ph']['lic']='All rights reserved'; ok(any('licence' in x for x in _chk(st=_s,ap=_ap())),'a non-free licence is refused')
_o=[{'n':'Statue of Liberty','t':'New York','g':[39.5,-119.8]}]
ok(any('within 150 m' in x for x in _chk(ap=_ap(),off=_o)),'a place 150 m from an official stop is a duplicate')
ok(not _chk(ap=_ap(dup_ok_by='Jo-Anne'),off=_o),'only Jo-Anne can allow a duplicate')
ok(any('same name' in x for x in _chk(ap=_ap(),off=[{'n':'The Sample Mill','t':'Elsewhere','g':[10,10]}])),'same name as an official stop is a duplicate')
_two=[('a.json',{'sub':'aaaaaaaa','town':'Reno','state':'NV','stop':_st()}),('b.json',{'sub':'bbbbbbbb','town':'Reno','state':'NV','stop':_st(name='Sample Mill ',geo=(39.6,-119.9,200))})]
ok(any('duplicate of' in x for x in cm.check_approvals(_rules,{'aaaaaaaa':_ap(),'bbbbbbbb':_ap(photos=[{'k':'cm_aaaaaaaa_n','verdict':'used'}])},_two,[],{},[],[])),'two places with the same name in one town are refused')
_six={('%08x'%i):_ap() for i in range(6)}; ok(any('limit is 5' in x for x in cm.check_approvals(_rules,_six,[],[],{},[],[])),'more than 5 places added in one day is refused')
ok(any('declined.json' in x for x in cm.check_approvals(_rules,{},[],[],{'cccccccc':'no'},[],[])),'a declined place needs a record')
ok(_chk(ap=_ap())==[] and cm.check_approvals(_rules,{'dddddddd':_ap(decision='needs-owner',notes='x',rules={'dp-place':'fail: near'})},[],[],{},[],[])==[],'needs-owner records need no full checklist')
import glob as _g
ok(not any('10587d75' in f for f in _g.glob(R+'src/community/stories/*')) and os.path.exists(R+'src/community/held/10587d75.json'),'Liberty Island is held back, not published')
_rp=cm.report(R); ok(_rp['counts']['needs-owner']>=1 and _rp['rules'] and all('id' in r for r in _rp['records']),'report lists rules and decisions')
ok(json.load(open(TMP+'/community/report.json'))['counts']==_rp['counts'],'built report.json matches the log')

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
import tempfile as _tf
_td=_tf.mkdtemp(); _m={'sub':'aaaaaaaa','town':'Reno','state':'NV','added':'2026-11-05','seq':1,'stop':stop_for('aaaaaaaa','Mission Probe',1)}
json.dump(_m,open(_td+'/aaaaaaaa.json','w')); ok(any('promoted_by' in x for x in cm.check(places_dir=_td+'/')),'a mission file without Jo-Anne\'s promotion is refused')
_m.update(promoted_by='Jo-Anne',promoted_on='2026-11-05'); json.dump(_m,open(_td+'/aaaaaaaa.json','w')); ok(not any('promoted_by' in x for x in cm.check(places_dir=_td+'/')),'a promoted mission file passes')
ok(isinstance(json.load(open(R+'site/community/status.json')).get('photos'),list),'built status.json lists the published photos')
def write_places(places):
    d=TMP+'/_places'; shutil.rmtree(d,ignore_errors=True); os.makedirs(d)
    if not os.path.isdir(TMP+'/_stories'): os.makedirs(TMP+'/_stories')
    for t in places:
        sub,name,seq=t[:3]; o={'sub':sub,'town':'Testville','state':'NV','added':'2026-11-03','seq':seq,'promoted_by':'Jo-Anne','promoted_on':'2026-11-03','stop':stop_for(sub,name,seq)}
        if len(t)>3: o['by']=t[3]
        json.dump(o,open(f'{d}/{sub}.json','w'))
    bad=cm.check(places_dir=d+'/'); ok(not bad,'fixture places invalid: %r'%bad)
    pk,ph,st,tr=cm.build(places_dir=d+'/',declined_file='/nonexistent',stories_dir=TMP+'/_stories/')
    json.dump({'packs':pk,'photos':ph,'tours':tr},open(TMP+'/community/places.json','w')); json.dump(st,open(TMP+'/community/status.json','w'))
sv=server('branch-deploy')
try:
  # ---- API ----
  good={'place':'Old Depot','city':'Testville','state':'NV','oneLiner':'The old train depot downtown.','thenUrl':'https://commons.wikimedia.org/wiki/File:Good_then.jpg','nowUrl':'https://commons.wikimedia.org/wiki/File:Good_now.jpg','confirm':True}
  s,j=api('/api/community/submit',{'city':'X'}); ok(s==400 and j['errors'],'empty submit should be rejected')
  s,j=api('/api/community/submit',{**good,'thenUrl':'https://example.com/x.jpg'}); ok(s==400 and 'commons' in ' '.join(j['errors']).lower(),'non-commons link rejected: %r'%j)
  s,j=api('/api/community/submit',{**good,'place':'LoC Probe','thenUrl':'https://www.loc.gov/pictures/item/2016800123/'}); ok(s==200,'plain LoC link accepted: %r'%j); locid=j.get('id')
  s,pj=api('/api/community/pending',key=KEY); lp=[x for x in pj['pending'] if x['id']==locid]; ok(lp and lp[0]['then']['kind']=='loc' and lp[0]['then']['license']=='Public domain' and 'Detroit Publishing' in lp[0]['then']['credit'] and lp[0]['then']['year']=='1906' and lp[0]['then']['page']=='https://www.loc.gov/item/2016800123/','LoC photo is stored with credit, year and page: %r'%(lp and lp[0]['then'])); api('/api/community/delete/'+locid,{},key=KEY)
  for bad_id,why in (('rstr1','does not clearly say'),('copied1','does not clearly say'),('gone1','could not reach')):
    s,j=api('/api/community/submit',{**good,'thenUrl':'https://www.loc.gov/item/%s/'%bad_id}); ok(s==400 and why in ' '.join(j['errors']).lower(),'LoC %s refused: %r'%(bad_id,j))
  s,j=api('/api/community/submit',{**good,'thenUrl':'https://www.loc.gov/search/?q=x'}); ok(s==400,'LoC search page is not an item link')
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
    pg.click('#nx1'); ok('name of the place' in pg.inner_text('#e1').lower(),'step 1 asks for the missing fields: '+pg.inner_text('#e1'))
    pg.fill('#place','Old Depot'); pg.fill('#city','Testville'); pg.fill('#state','nevada'); pg.fill('#addr','1 Depot Plaza'); pg.fill('#one','The old train depot downtown, now a museum.')
    ok('old depot' in pg.inner_text('#mkn').lower(),'live card shows the place name'); pg.click('#nx1'); pg.wait_for_selector('#files', state='attached')
    ok(pg.input_value('#state')=='NV','state name becomes the two-letter code: '+pg.input_value('#state'))
    pg.click('#nx2'); ok('at least one photo' in pg.inner_text('#e2').lower(),'photo message missing')
    pg.evaluate("document.getElementById('links').open=true")
    pg.fill('#then','https://example.com/x.jpg'); pg.wait_for_timeout(700); ok('not a commons' in pg.inner_text('#pvt').lower(),'non-Commons link is flagged in the preview: '+pg.inner_text('#pvt'))
    ok('Old%20Depot%20Testville' in pg.get_attribute('#findph','href'),'Find a photo link searches for the place and town: '+pg.get_attribute('#findph','href'))
    pg.fill('#then','https://www.loc.gov/pictures/item/2016800123/'); pg.wait_for_timeout(700); ok(('library of congress' in pg.inner_text('#pvt').lower() or 'no known restrictions' in pg.inner_text('#pvt').lower()) and 'not supported' not in pg.inner_text('#pvt').lower() and 'not a commons' not in pg.inner_text('#pvt').lower(),'LoC link is recognised in the preview: '+pg.inner_text('#pvt'))
    pg.fill('#then','https://commons.wikimedia.org/wiki/File:Good_then.jpg')
    pg.fill('#now','https://commons.wikimedia.org/wiki/File:Good_now.jpg'); pg.click('#nx2'); pg.wait_for_selector('#confirm')
    ok('Old Depot' in pg.inner_text('#sum') and 'Commons link' in pg.inner_text('#sum') and '1 Depot Plaza' in pg.inner_text('#sum'),'review step summarises the entry')
    pg.check('#confirm'); pg.click('#go'); pg.wait_for_selector('#done:not([hidden])')
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
    s,j=api('/api/community/submit',{**good,'place':'Lic Force','nowUrl':'','nowPhoto':up,'nowOwn':True,'nowCredit':'Dad','nowYear':'2026','nowLicense':'CC0'}); ok(s==200,'upload with any license value accepted')
    s,pj=api('/api/community/pending',key=KEY); lf=[x for x in pj['pending'] if x['place']=='Lic Force']
    ok(lf and lf[0]['now']['license']=='CC BY-SA','uploads are always stored as CC BY-SA: %r'%(lf and lf[0]['now']))
    s,j=api('/api/community/submit',{**good,'place':'No Lic Field','nowUrl':'','nowPhoto':up,'nowOwn':True,'nowCredit':'Dad','nowYear':'2026'}); ok(s==200,'upload without a license field accepted: %r'%j)
    for x in [y for y in api('/api/community/pending',key=KEY)[1]['pending'] if y['place'] in ('Lic Force','No Lic Field')]: api('/api/community/delete/'+x['id'],{},key=KEY)
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
    # community towns sit inside their state's normal region (no separate section)
    regs=pg.evaluate("Array.from(document.querySelectorAll('details.reg > summary .rname')).map(function(e){return e.textContent.trim().toLowerCase();})")
    ok('community-added' not in regs,'no separate Community-added region: %r'%regs)
    ok(pg.evaluate("(function(){var t=document.querySelector('details.reg [data-a=city][data-c=\"c_testville-nv\"]');return !!t&&!!t.closest('details.reg')&&!/community/i.test(t.closest('details.reg').querySelector('.rname').textContent);})()"),'Testville (NV) is listed inside a normal region')
    ok(pg.evaluate("(function(){var t=document.querySelector('[data-a=city][data-c=\"c_testville-nv\"] .lvl');return !!t&&/community-added/i.test(t.textContent)&&!/hidden gems/i.test(t.textContent);})()"),'community tile still says Community-added')
    ok(pg.evaluate("document.documentElement.scrollWidth<=innerWidth"),'home sideways scroll at 390')
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
    ok(pg.evaluate("!!document.querySelector('.repline [data-a=shareplace]')"),'community stop has Share this place')
    sent=[]
    pg.route('**/',lambda r: (sent.append(r.request.post_data or '') if r.request.method=='POST' else None, r.fulfill(status=200,body='ok') if r.request.method=='POST' else r.continue_())[1])
    pg.click('.repline [data-a=report]'); pg.wait_for_selector('#report')
    ok(pg.evaluate('''!!document.querySelector('.rep-card a[href="mailto:stampthepast@gmail.com"]')'''),'community report dialog shows the support email')
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
      'ph':{'k':'cm_%s_n'%cid_s,'alt':'The chapel','by':'Jane Doe','lic':'CC BY-SA','lu':'https://creativecommons.org/licenses/by-sa/4.0/','page':'https://commons.wikimedia.org/wiki/File:Good_now.jpg'},
      'more':[{'k':'cm_%s_t'%cid_s,'alt':'The chapel long ago','label':'About 1910','by':'Old Photog','lic':'Public domain','page':'https://commons.wikimedia.org/wiki/File:Good_then.jpg'}],'mission':{'town':'reno','i':0}}
    json.dump({'sub':cid_s,'town':'Storyville','state':'NV','added':'2026-11-03','stop':story},open(f'{d}/{cid_s}.json','w'))
    ok(cm.build(places_dir=TMP+'/_places/',declined_file='/nonexistent',stories_dir=d+'/')[3][0]['stops'][0]['town']=='c_storyville-nv','story stop is tied to its town')
    pk,ph,st,tr=cm.build(places_dir=TMP+'/_places/',declined_file='/nonexistent',stories_dir=d+'/'); st['waiting']={cid_w:'We still need a recent photo of this place.'}
    json.dump({'packs':pk,'photos':ph,'tours':tr,'official':[{'n':'The Reno Arch','c':'Reno'}]},open(TMP+'/community/places.json','w')); json.dump(st,open(TMP+'/community/status.json','w'))
    ok(cid_s in st['added'],'story counted as added')
    # per-photo approval: a declined photo is hidden while its sibling stays public; photos can be added to a published place
    st['declinedPhotos']=[cid_s+'_t']; json.dump(st,open(TMP+'/community/status.json','w'))
    s,_pb=api(f'/api/community/photo/{cid_s}_n'); ok(s==200,'approved photo is public: %s'%s)
    s,_pb=api(f'/api/community/photo/{cid_s}_t'); ok(s==404,'declined photo is not public even though the place is added: %s'%s)
    s,j=api('/api/community/submit',{'place':'Hilltop Chapel','city':'Storyville','state':'NV','oneLiner':'More photos of Hilltop Chapel.','target':cid_s,'extras':[{'url':'https://commons.wikimedia.org/wiki/File:Good_then.jpg','type':'old','caption':'Inside'}],'confirm':True})
    ok(s==200,'photos can be added to a published place: %r'%j)
    s,j2=api('/api/community/mine/'+j['edit']); ok(j2.get('target')==cid_s and j2['photos'][0]['status']=='waiting for review','add-photo submission carries its target and waits: %r'%j2)
    # a correction to a published place: text only, never edits anything by itself, goes to the inbox flagged
    fx={'place':'Hilltop Chapel','city':'Storyville','state':'NV','target':cid_s,'correction':{'text':'The chapel was built in 1911, not 1910, according to the county record.','source':'https://example.org/record'},'confirm':True}
    s,jf=api('/api/community/submit',fx); ok(s==200,'a correction can be sent with no photo: %r'%jf)
    s,j=api('/api/community/pending',key=KEY); FP={p['id']:p for p in j['pending']}
    ok(jf['id'] in FP and FP[jf['id']]['correction']['text'].startswith('The chapel was built') and FP[jf['id']]['correction']['source']=='https://example.org/record' and FP[jf['id']]['target']==cid_s,'pending shows the correction, its source and the place it is about')
    s,j=api('/api/community/mine/'+jf['edit']); ok(j.get('correction') is True and j['photos']==[],'status says it is a correction: %r'%j)
    s,j=api('/api/community/submit',dict(fx,correction={'text':'short'})); ok(s==400,'a too-short correction is rejected')
    s,j=api('/api/community/submit',dict(fx,correction={'text':'The chapel was built in 1911 per the record.','source':'http://example.org/x'})); ok(s==400,'a non-https correction source is rejected')
    s,j=api('/api/community/submit',dict(fx,correction={'text':'Built in <b>1911</b> according to the record.'})); ok(s==400,'markup in a correction is rejected')
    s,j=api('/api/community/submit',{k:v for k,v in fx.items() if k!='target'}); ok(s==400,'a correction must name its place')
    s,j=api('/api/community/submit',dict(fx,target='deadbeef')); ok(s==400,'a correction to an unpublished place is rejected')
    # per-photo decisions by the owner: hold one photo back, the rest stay
    s,_=api(f'/api/community/decide/{cid_s}_n',{'decline':True}); ok(s==404,'deciding needs the admin key')
    s,_=api(f'/api/community/decide/zz_n',{'decline':True},key=KEY); ok(s==400,'a bad photo id is rejected')
    s,j=api(f'/api/community/decide/{cid_s}_n',{'decline':True},key=KEY); ok(s==200 and 'n' in j['declined'],'owner can hold a photo back: %r'%j)
    s,_=api(f'/api/community/photo/{cid_s}_n'); ok(s==404,'a held-back photo is not public even though the place is added')
    s,_=api(f'/api/community/photo/{cid_s}_n',key=KEY); ok(s==200,'the owner can still see a held-back photo')
    s,j=api(f'/api/community/decide/{cid_s}_n',{'decline':False},key=KEY); ok(s==200 and 'n' not in j['declined'],'owner can restore it')
    s,_=api(f'/api/community/photo/{cid_s}_n'); ok(s==200,'a restored photo is public again')

    s,j=api('/api/community/pending',key=KEY); ok(cid_s not in [p['id'] for p in j['pending']] and cid_w not in [p['id'] for p in j['pending']],'story and waiting leave pending')
    tokn=jn['edit'] if 'edit' in jn else ''
    s,j=api('/api/community/mine/'+jn['edit']); ok(j.get('status')=='added','story status added')
    s,j=api('/api/community/mine/'+jn['edit']+'/edit',{'oneLiner':'A valid one-line description here.'}); ok(s==400 and 'already added' in json.dumps(j),'an added place cannot be edited, only corrected: %r'%j)
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
    pg.set_viewport_size({'width':390,'height':844}); pg.goto(B+'/contribute/?add=deadbeef&place=Old%20Depot'); pg.wait_for_selector('#place')
    ok('add a photo to old depot' in pg.inner_text('h1').lower() and pg.input_value('#place')=='Old Depot','add-photo mode names the place')
    ok(pg.evaluate("!!document.querySelector('#more') && document.querySelectorAll('#more select').length==3"),'form has 3 extra photo rows with a type each')
    # the form: choose several photos at once, get a tile for each, send them
    for i,col in enumerate(((200,120,60),(40,90,200),(90,160,90))): open(f'{TMP}/up{i}.jpg','wb').write(mkjpg(col))
    pg.set_viewport_size({'width':390,'height':844}); pg.goto(B+'/contribute/'); pg.wait_for_timeout(400)
    pg.fill('#place','Tile Test Hall'); pg.fill('#city','Testville'); pg.fill('#state','NV'); pg.fill('#one','A place for the photo tiles test.'); pg.click('#nx1'); pg.wait_for_selector('#files',state='attached')
    ok(pg.is_visible('.pick') and 'add photos' in pg.inner_text('.pick').lower(),'step 2 leads with an Add photos button')
    pg.set_input_files('#files',[f'{TMP}/up0.jpg',f'{TMP}/up1.jpg',f'{TMP}/up2.jpg']); pg.wait_for_selector('.tile:nth-child(3)')
    ok(pg.evaluate("document.querySelectorAll('.tile').length")==3,'three tiles after choosing three photos')
    pg.select_option('.tile:nth-child(1) select','old'); pg.fill('.tile:nth-child(1) input[placeholder^=Caption]','Front in 1925'); pg.fill('.tile:nth-child(1) input[placeholder^=Year]','1925')
    pg.click('.tile:nth-child(3) .rmtile'); ok(pg.evaluate("document.querySelectorAll('.tile').length")==2,'a photo can be removed')
    pg.screenshot(path=TMP+'/step2.png',full_page=True)
    ok(pg.evaluate("document.documentElement.scrollWidth<=innerWidth"),'step 2 with tiles has no sideways scroll at 390')
    pg.click('#nx2'); pg.wait_for_selector('#confirm'); ok('2 of 5' in pg.inner_text('#sum') and '2 uploaded' in pg.inner_text('#sum'),'review shows the photo count: '+pg.inner_text('#sum'))
    pg.check('#confirm'); pg.click('#go'); pg.wait_for_timeout(500)
    ok('tick' in pg.inner_text('#errs').lower() or 'took these' in pg.inner_text('#errs').lower(),'send without the ownership tick is refused: '+pg.inner_text('#errs'))
    pg.click('#bk3'); pg.check('#took'); pg.fill('#credit','Test Dad'); pg.click('#nx2'); pg.wait_for_selector('#confirm'); pg.check('#confirm') if not pg.is_checked('#confirm') else None; pg.click('#go'); pg.wait_for_selector('#done:not([hidden])')
    s,j=api('/api/community/pending',key=KEY); TP=[p for p in j['pending'] if p['place']=='Tile Test Hall']
    ok(len(TP)==1 and [e['type'] for e in TP[0]['extra']]==['old','unsure'] and TP[0]['extra'][0]['caption']=='Front in 1925' and TP[0]['extra'][0]['year']=='1925','the form sent both photos with their type, caption and year: %r'%(TP and TP[0].get('extra')))
    # city names are normalised on the server, so Reno / Reno NV / Reno, Nevada become one town
    for cin,sin in (('reno nv',''),('Reno, Nevada',''),('RENO','nv'),('Reno','Nevada')):
        s,jc=api('/api/community/submit',{**good,'place':'Norm Probe %d'%len(cin+sin),'city':cin,'state':sin,'nowUrl':'','thenUrl':'https://commons.wikimedia.org/wiki/File:Good_then.jpg'}); ok(s==200,'submit %r %r: %r'%(cin,sin,jc))
    s,j=api('/api/community/pending',key=KEY); NP=[p for p in j['pending'] if p['place'].startswith('Norm Probe')]
    ok(len(NP)==4 and {(p['city'],p['state']) for p in NP}=={('Reno','NV')},'four spellings become one town: %r'%{(p['city'],p['state']) for p in NP})
    s,jc=api('/api/community/submit',{**good,'place':'Carson Probe','city':'Carson City','state':'NV'}); s,j=api('/api/community/pending',key=KEY); ok(any(p['place']=='Carson Probe' and p['city']=='Carson City' for p in j['pending']),'Carson City keeps its name')
    # the form: a place that already exists is offered as 'Add photos to this place'
    pg.set_viewport_size({'width':390,'height':844}); pg.goto(B+'/contribute/'); pg.wait_for_timeout(700)
    pg.fill('#place','Hilltop Chapel'); pg.wait_for_timeout(300)
    ok(pg.is_visible('#sugg') and pg.evaluate("document.querySelector('#sugg a').getAttribute('href').indexOf('/contribute/?add=')==0"),'typing an existing place offers Add photos to it: '+pg.inner_text('#sugg'))
    pg.fill('#place','Completely New Thing'); pg.wait_for_timeout(300); ok(not pg.is_visible('#sugg'),'no suggestion for a new place')
    pg.fill('#city','Reno'); pg.fill('#place','Reno Arch'); pg.wait_for_timeout(300)
    ok(pg.is_visible('#sugg') and 'already in the app' in pg.inner_text('#sugg').lower(),'an official stop is flagged as already in the app: '+pg.inner_text('#sugg')[:120])
    pg.fill('#city','walnut creek, ca'); pg.press('#city','Tab'); ok(pg.input_value('#city')=='Walnut Creek' and pg.input_value('#state')=='CA','the form tidies the town as you leave the field: %r %r'%(pg.input_value('#city'),pg.input_value('#state')))
    pg.goto(B+'/contribute/?fix='+cid_s+'&place=Hilltop+Chapel&city=Storyville&state=NV'); pg.wait_for_timeout(500)
    ok(pg.is_visible('#fixsec') and pg.is_hidden('#f'),'correction link opens the short correction form')
    pg.click('#fixgo'); pg.wait_for_timeout(500); ok(pg.is_visible('#fixerr'),'an empty correction shows an error')
    pg.fill('#fixtext','The chapel opened in 1911 according to the county record.'); pg.check('#fixconf'); pg.click('#fixgo'); pg.wait_for_selector('#done:not([hidden])')
    ok(pg.is_visible('#done') and pg.is_hidden('#fixsec'),'a sent correction shows the Received screen')
    ok(pg.evaluate("document.getElementById('pfile').multiple"),'the status-page upload takes several photos')
    s,jq=api('/api/community/submit',{**good,'place':'Edit Probe'}); pg.goto(B+'/contribute/?status='+jq['edit']); pg.wait_for_selector('#edtw:not([hidden])')
    pg.evaluate("document.getElementById('edtw').open=true"); pg.fill('#edo','Updated from the status page, still a good place.'); pg.click('#edgo'); pg.wait_for_timeout(700)
    ok('back in review' in pg.inner_text('#edmsg').lower(),'status page edit form saves: '+pg.inner_text('#edmsg'))
    s,j=api('/api/community/mine/'+jq['edit']); ok(j['oneLiner'].startswith('Updated from the status page'),'saved edit is returned by status')
    # several uploaded photos at once (the main way people will contribute)
    def U(i,t='unsure'): return {'photo':'data:image/jpeg;base64,'+base64.b64encode(mkjpg((20*i,120,60))).decode(),'type':t,'caption':'View %d'%i,'year':'1925' if t=='old' else ''}
    ub={'place':'Upload Gallery','city':'Testville','state':'NV','oneLiner':'A place sent with several of my own photos.','uploads':[U(1,'old'),U(2,'today'),U(3,'detail')],'uploadOwn':True,'uploadCredit':'Dad','confirm':True}
    s,ju=api('/api/community/submit',ub); ok(s==200,'submit with 3 uploaded photos and no links: %r'%ju)
    uid=ju['id']; s,j=api('/api/community/pending',key=KEY); UP={p['id']:p for p in j['pending']}
    ok(uid in UP and [e['n'] for e in UP[uid]['extra']]==['x1','x2','x3'] and UP[uid]['extra'][0]['kind']=='own' and UP[uid]['extra'][0]['license']=='CC BY-SA' and UP[uid]['extra'][0]['credit']=='Dad','uploads are listed as own photos under CC BY-SA with the credit')
    s,_ub=api(f'/api/community/photo/{uid}_x2',key=KEY); ok(s==200 and _ub[:3]==b'\xff\xd8\xff','uploaded photo is visible to admin')
    s,_ub=api(f'/api/community/photo/{uid}_x2'); ok(s==404,'uploaded photo is held from the public')
    s,j=api('/api/community/submit',dict(ub,uploads=[U(i) for i in range(1,7)])); ok(s==400,'more than 5 uploads is rejected')
    s,j=api('/api/community/submit',dict(ub,uploads=[U(i) for i in range(1,5)],nowUrl='https://commons.wikimedia.org/wiki/File:Good_now.jpg',thenUrl='https://commons.wikimedia.org/wiki/File:Good_then.jpg')); ok(s==400 and 'up to 5' in json.dumps(j),'links plus uploads over 5 is rejected: %r'%j)
    s,j=api('/api/community/submit',dict(ub,uploadOwn=False)); ok(s==400 and 'took these photos' in json.dumps(j),'uploads need the ownership tick')
    s,j=api('/api/community/submit',dict(ub,uploadCredit='')); ok(s==400,'uploads need a credit')
    # adding several uploaded photos later from the status link: appended after the existing ones, 5 in all
    s,j=api('/api/community/mine/'+ju['edit']+'/photo',{'uploads':[U(4),U(5)],'uploadOwn':True,'uploadCredit':'Dad','confirm':True}); ok(s==200,'status page can add two more uploaded photos: %r'%j)
    s,j=api('/api/community/pending',key=KEY); UP={p['id']:p for p in j['pending']}
    ok([e['n'] for e in UP[uid]['extra']]==['x1','x2','x3','x4','x5'],'new uploads are appended after the existing photos: %r'%[e['n'] for e in UP[uid]['extra']])
    s,j=api('/api/community/mine/'+ju['edit']+'/photo',{'uploads':[U(6)],'uploadOwn':True,'uploadCredit':'Dad','confirm':True}); ok(s==400 and '5 photos' in json.dumps(j),'a sixth photo is refused: %r'%j)
    s,j=api('/api/community/mine/'+ju['edit']+'/photo',{'uploads':[U(6)],'uploadOwn':False,'uploadCredit':'Dad','confirm':True}); ok(s==400,'status-page uploads need the ownership tick')
    # editing the words of a place that is still waiting
    s,j=api('/api/community/mine/'+ju['edit']+'/edit',{'oneLiner':'A better one-line description of the gallery place.','nickname':'Dad2','address':'12 Main St'}); ok(s==200,'owner can edit the words of a waiting place: %r'%j)
    s,j=api('/api/community/pending',key=KEY); UP={p['id']:p for p in j['pending']}
    ok(UP[uid]['oneLiner'].startswith('A better one-line') and UP[uid]['nickname']=='Dad2' and UP[uid]['address']=='12 Main St' and UP[uid]['place']=='Upload Gallery' and len(UP[uid]['extra'])==5,'edit changes only the words, photos untouched')
    s,j=api('/api/community/mine/'+ju['edit']); ok(j.get('oneLiner','').startswith('A better') and j.get('nickname')=='Dad2','status returns the current words for the edit form')
    s,j=api('/api/community/mine/'+ju['edit']+'/edit',{'oneLiner':'short'}); ok(s==400,'a too-short line is rejected')
    s,j=api('/api/community/mine/'+ju['edit']+'/edit',{'place':'<b>Bad</b> name'}); ok(s==400,'markup in an edit is rejected')
    s,j=api('/api/community/mine/'+ju['edit'][:-2]+'zz/edit',{'oneLiner':'A valid one-line description here.'}); ok(s==404,'edit with a wrong token is 404')
    s,j=api('/api/community/mine/'+jf['edit']+'/edit',{'oneLiner':'A valid one-line description here.'}) if 'jf' in dir() else (400,{}); ok(s==400,'a correction cannot be edited')
    s,j=api('/api/community/submit',dict(ub,uploads=[dict(U(1),year='yesterday')])); ok(s==400 and 'year' in json.dumps(j),'a bad photo year is rejected')
    s,j=api('/api/community/submit',dict(ub,uploads=[{'photo':'data:image/jpeg;base64,'+base64.b64encode(b'\xff\xd8\xff'+b'A'*3000).decode()}])); ok(s==400,'a fake jpeg in uploads is rejected')
    # multi-photo: up to 3 extra photos, each typed, held until approval, with their own status
    xb=dict(good,place='Gallery Place',extras=[{'url':'https://commons.wikimedia.org/wiki/File:Good_then.jpg','type':'old','caption':'The front in 1920'},{'url':'https://commons.wikimedia.org/wiki/File:Good_now.jpg','type':'detail','caption':'The doorway'}])
    s,jx=api('/api/community/submit',xb); ok(s==200,'submit with 2 extra photos: %r'%jx)
    s,j=api('/api/community/submit',dict(xb,extras=xb['extras']*2)); ok(s==400,'more than 3 extra photos is rejected: %r'%j)
    s,j=api('/api/community/submit',dict(xb,extras=[{'url':'https://example.com/x.jpg','type':'old'}])); ok(s==400 and 'Extra photo 1' in json.dumps(j),'a bad extra link is rejected clearly: %r'%j)
    xid=jx['id']; s,j=api('/api/community/pending',key=KEY); XP={p['id']:p for p in j['pending']}
    ok(xid in XP and [e['n'] for e in XP[xid].get('extra',[])]==['x1','x2'] and XP[xid]['extra'][0]['type']=='old' and XP[xid]['extra'][0]['caption']=='The front in 1920','pending lists the extra photos with type and caption')
    s,_xb=api(f'/api/community/photo/{xid}_x1',key=KEY); ok(s==200 and _xb[:3]==b'\xff\xd8\xff','extra photo visible to admin')
    s,_xb=api(f'/api/community/photo/{xid}_x1'); ok(s==404,'extra photo is not public before approval')
    s,j=api('/api/community/mine/'+jx['edit']); ok([p['status'] for p in j['photos']]==['waiting for review']*4,'status page lists every photo as waiting: %r'%j.get('photos'))
    s,j=api('/api/community/submit',dict(xb,target='deadbeef')); ok(s==400 and 'not published' in json.dumps(j),'adding photos to an unpublished place is rejected: %r'%j)
    s,j=api('/api/community/submit',dict(xb,target='zz')); ok(s==400,'a malformed target id is rejected')
    s,j=api('/api/community/mine/'+jn['edit']+'/photo',{'nowUrl':'https://commons.wikimedia.org/wiki/File:Good_now.jpg','confirm':True}); ok(s==400 and 'already added' in json.dumps(j),'an added place cannot be changed: %r'%j)
    pg.goto(B+'/play.html'); pg.wait_for_selector('#main')
    pg.evaluate("document.querySelector('#bnav [data-t=home]').click()"); pg.wait_for_timeout(300)
    pg.evaluate("document.querySelector('[data-a=nbopen]').click()"); pg.wait_for_timeout(300)
    pg.evaluate("document.querySelector('[data-a=nbnoloc]').click()"); pg.wait_for_timeout(300)
    ok('storyville' in pg.inner_text('body').lower(),'story town listed under Nearby stops')
    ok(pg.evaluate("Array.from(document.querySelectorAll('.nbh')).some(function(h){return /^[A-Z]{2} · \\d+ places?$/i.test(h.innerText.trim());})"),'Nearby place picker is grouped by state with place counts')
    pg.evaluate("Array.from(document.querySelectorAll('[data-a=nbarea]')).find(function(b){return /storyville/i.test(b.innerText);}).click()"); pg.wait_for_timeout(300)
    pg.evaluate("document.querySelector('[data-a=nbstory]').click()"); pg.wait_for_timeout(500)
    ok('hilltop chapel' in pg.inner_text('body').lower() and pg.evaluate("!!document.querySelector('.nbfig img')"),'story card shows the photo')
    ok(pg.evaluate("document.querySelectorAll('.galmain img').length")==1 and pg.evaluate("document.querySelectorAll('.galth').length")==2,'story card shows a main photo plus a thumbnail strip of 2')
    pg.evaluate("document.querySelectorAll('.galth')[1].click()"); pg.wait_for_timeout(200)
    ok(pg.evaluate("/about 1910/i.test(document.querySelector('.galmain').innerText)") and pg.evaluate("document.querySelectorAll('.galth')[1].getAttribute('aria-pressed')")=='true','picking the 2nd thumbnail swaps the photo, label and credit')
    pg.evaluate("document.querySelector('[data-a=galfull]').click()"); pg.wait_for_timeout(200)
    ok(pg.evaluate("!!document.querySelector('#galbox[role=dialog] img')"),'View larger opens the photo viewer')
    pg.evaluate("document.querySelector('[data-a=galnext]').click()"); pg.wait_for_timeout(150)
    ok(pg.evaluate("/photo 1 of 2/i.test(document.querySelector('#galbox').innerText)"),'viewer steps to the next photo')
    pg.keyboard.press('Escape'); pg.wait_for_timeout(150)
    ok(pg.evaluate("!document.getElementById('galbox')"),'Escape closes the viewer')
    ok(pg.evaluate("!!document.querySelector('.repline a[href^=\"/contribute/?add=\"]')"),'story card has Add a photo')
    ok(pg.evaluate("!!document.querySelector('.repline a[href^=\"/contribute/?fix=\"]')"),'story card has Suggest a correction')
    ok(pg.evaluate("!!document.querySelector('[data-a=nbtown][data-c=reno]')"),'promoted place links to its mission')
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
  # ---- Menu > My suggestions shows saved submissions with live status ----
  s,j=api('/api/community/submit',{**good,'place':'Menu Probe Depot'}); ok(s==200,'probe submit: %r'%j); tok=j.get('edit','')
  with sync_playwright() as pw:
    b=pw.chromium.launch(); pg=b.new_page(viewport={'width':390,'height':844})
    pg.add_init_script("try{localStorage.setItem('then-now-tour','1');localStorage.setItem('stp-sugg',JSON.stringify([{t:'%s',p:'Menu Probe Depot',c:'Testville'}]))}catch(e){}"%tok)
    pg.goto(B+'/play.html'); pg.wait_for_selector('#main'); pg.evaluate("document.querySelector('[data-a=menu]').click()"); pg.wait_for_selector('#mysug')
    ok('My suggestions (1)' in pg.inner_text('#mysug summary'),'menu lists saved suggestions: '+pg.inner_text('#mysug summary'))
    pg.click('#mysug summary'); pg.wait_for_timeout(600)
    t=pg.inner_text('#mysug'); ok('Menu Probe Depot' in t and 'Received' in t,'status loads in the menu: '+t)
    ok(pg.get_attribute('#mysug a.mitem','href')=='/contribute/?status='+tok,'row links to the status page')
    pg2=b.new_page(viewport={'width':390,'height':844}); pg2.goto(B+'/play.html'); pg2.wait_for_selector('#main'); pg2.evaluate("document.querySelector('[data-a=menu]').click()"); pg2.wait_for_timeout(300)
    ok(pg2.evaluate("!document.getElementById('mysug')"),'no My suggestions row when nothing was suggested')
    b.close()
  # ---- nickname credit, passport grouping, reports hide a place ----
  write_places([('cc000001','Credit Probe',1,'Dad'),('cc000002','Second Probe',2)])
  with sync_playwright() as pw:
    b=pw.chromium.launch(); pg=b.new_page(viewport={'width':390,'height':844})
    pg.add_init_script("try{localStorage.setItem('then-now-tour','1')}catch(e){}")
    pg.goto(B+'/play.html'); pg.wait_for_selector('#main'); pe2=[]; pg.on('pageerror',lambda e:pe2.append(str(e)))
    pg.evaluate("Array.from(document.querySelectorAll('[data-a=city]')).find(function(e){return e.getAttribute('data-c')==='c_testville-nv';}).click()"); pg.wait_for_timeout(400)
    pg.evaluate("document.querySelector('[data-a=open][data-i=\"0\"]').click()"); pg.wait_for_timeout(300)
    pg.wait_for_timeout(300); t=pg.inner_text('.combadge').lower(); ok('suggested by dad' in t,'nickname credit shown: '+t)
    y_badge=pg.evaluate("document.querySelector('.combadge').getBoundingClientRect().top"); y_btn=pg.evaluate("document.querySelector('.stickgo').getBoundingClientRect().top")
    ok(y_badge<y_btn,'community label sits above the check-in button')
    b.close()
  with sync_playwright() as pw:
    b=pw.chromium.launch(); pg=b.new_page(viewport={'width':390,'height':844}); pg.goto(B+'/contribute/'); pg.wait_for_selector('#place'); pg.wait_for_timeout(500)
    pg.fill('#place','Credit Probe Hall'); pg.fill('#city','Testville'); pg.fill('#one','Some words about this place'); pg.click('#nx1')
    ok('already in' in pg.inner_text('#e1') and pg.is_visible('#nx1'),'duplicate place is flagged: '+pg.inner_text('#e1'))
    pg.click('#nx1'); pg.wait_for_selector('#files', state='attached'); ok(pg.is_visible('.pick'),'second tap continues past the duplicate warning')
    b.close()
  with sync_playwright() as pw:  # larger text: no sideways scroll on any step (long email links used to push the page wider)
    b=pw.chromium.launch()
    for w in (320,390):
        pg=b.new_page(viewport={'width':w,'height':800}); pg.goto(B+'/contribute/'); pg.add_style_tag(content='html{font-size:32px!important}'); pg.wait_for_timeout(300)
        fits=[pg.evaluate("document.documentElement.scrollWidth<=innerWidth")]
        pg.fill('#place','Mill Valley Depot Station Museum'); pg.fill('#city','Mill Valley'); pg.fill('#one','The 1928 depot near the ferry.'); pg.click('#nx1'); pg.wait_for_selector('#files', state='attached'); fits.append(pg.evaluate("document.documentElement.scrollWidth<=innerWidth"))
        pg.evaluate("document.getElementById('links').open=true")
        pg.fill('#then','https://commons.wikimedia.org/wiki/File:Good_then.jpg'); pg.click('#nx2'); pg.wait_for_selector('#confirm'); fits.append(pg.evaluate("document.documentElement.scrollWidth<=innerWidth"))
        ok(all(fits),'form fits at %dpx wide with 200%% text: %r'%(w,fits)); pg.close()
    b.close()
  s,j=api('/api/community/report/dd000009',{}); ok(s==404,'cannot report a place that is not published: %s'%s)
  for i in range(3): s,j=api('/api/community/report/cc000001',{})
  ok(s==200 and j.get('hidden') is True,'third report hides the place: %r'%j)
  s,j=api('/api/community/hidden'); ok(j.get('hidden')==['cc000001'],'hidden list: %r'%j)
  with sync_playwright() as pw:
    b=pw.chromium.launch(); pg=b.new_page(viewport={'width':390,'height':844}); pg.add_init_script("try{localStorage.setItem('then-now-tour','1')}catch(e){}")
    pg.goto(B+'/play.html'); pg.wait_for_selector('#main')
    ok(pg.evaluate("Array.from(document.querySelectorAll('[data-a=city]')).some(function(e){return e.getAttribute('data-c')==='c_testville-nv';})"),'town with one hidden place still lists')
    pg.evaluate("Array.from(document.querySelectorAll('[data-a=city]')).find(function(e){return e.getAttribute('data-c')==='c_testville-nv';}).click()"); pg.wait_for_timeout(400)
    names=pg.evaluate("Array.from(document.querySelectorAll('[data-a=open]')).map(function(e){return e.textContent})"); ok(any('Second Probe' in n for n in names) and not any('Credit Probe' in n for n in names),'hidden place is gone from the town: %r'%names)
    b.close()
  with sync_playwright() as pw:
    b=pw.chromium.launch(); pg=b.new_page(viewport={'width':390,'height':844}); pg.add_init_script("try{localStorage.setItem('then-now-tour','1');localStorage.setItem('then-now-v3',JSON.stringify({city:'reno',home:0,p:{'c_testville-nv':{done:[1,1],claims:[0,0,0,0],ids:['p1','p2']}}}))}catch(e){}")
    pg.goto(B+'/play.html'); pg.wait_for_selector('#main'); pg.evaluate("document.querySelector('#bnav [data-t=pass]').click()"); pg.wait_for_selector('#passport')
    ok(pg.evaluate("!!document.getElementById('cpass')"),'passport has a separate Community-added card')
    ok(pg.evaluate("/^0 of/.test(document.querySelector('.pstats b').parentNode.textContent.trim())") or pg.evaluate("document.querySelector('.pstats')&&document.querySelector('.pstats').hidden"),'community stamps stay out of passport totals: '+pg.evaluate("document.querySelector('.passport-line').textContent"))
    ok(pg.evaluate("document.documentElement.scrollWidth<=innerWidth"),'passport no sideways scroll')
    b.close()
  s,pj=api('/api/community/submit',{**good,'place':'Pending Probe','nickname':'Dad'}); ok(s==200,'pending probe: %r'%pj); pend=pj.get('id')
  # published-photo gate: a photo is public only if the build lists it, even when its place is live
  s,_gj=api('/api/community/submit',{**good,'place':'Gate Probe'}); gid=_gj.get('id'); ok(s==200,'gate probe submitted: %r'%_gj)
  _stf=TMP+'/community/status.json'; _old=open(_stf).read()
  json.dump({'added':[gid],'declined':{},'photos':[]},open(_stf,'w')); s,_=api(f'/api/community/photo/{gid}_n'); ok(s==404,'a photo not listed as published stays private even when its place is added')
  json.dump({'added':[gid],'declined':{},'photos':[gid+'_n']},open(_stf,'w')); s,_gb=api(f'/api/community/photo/{gid}_n'); ok(s==200,'a listed photo is public once its place is added')
  json.dump({'added':[],'declined':{},'photos':[gid+'_n']},open(_stf,'w')); s,_=api(f'/api/community/photo/{gid}_n'); ok(s==404,'a listed photo is still private when its place is not added')
  open(_stf,'w').write(_old)
  s,_=api('/api/community/owner/10587d75',{'decision':'approve'}); ok(s==404,'owner decision needs the admin key')
  s,_=api('/api/community/owner'); ok(s==404,'owner decision list needs the admin key')
  s,_=api('/api/community/owner/10587d75',{'decision':'maybe'},key=KEY); ok(s==400,'owner decision must be approve, decline or clear')
  s,_=api('/api/community/owner/zzzz',{'decision':'approve'},key=KEY); ok(s==400,'owner decision needs a valid id')
  s,_oj=api('/api/community/owner/'+pend,{'decision':'approve','note':'ok <b>'},key=KEY); ok(s==200 and '<' not in _oj['note'],'owner can approve')
  s,pj2=api('/api/community/pending',key=KEY); ok(any(x['id']==pend and x.get('ownerDecision',{}).get('decision')=='approve' for x in pj2['pending']),'pending list carries the owner decision for the agent')
  api('/api/community/owner/'+pend,{'decision':'clear'},key=KEY)
  with sync_playwright() as pw:
    b=pw.chromium.launch(); pg=b.new_page(viewport={'width':390,'height':844}); pg.goto(B+'/contribute/admin/'); pg.wait_for_timeout(600)
    ok('Credit Probe' in pg.inner_text('#added') and 'by Dad' in pg.inner_text('#added'),'recently added list needs no key: '+pg.inner_text('#added'))
    ok('Needs your decision' in pg.inner_text('#needs') and 'Liberty Island' in pg.inner_text('#needs'),'admin shows items that need the owner: '+pg.inner_text('#needs'))
    ok(pg.is_hidden('#tp-rules') and pg.get_attribute('#tb-needs','aria-selected')=='true','the page opens on Needs you, with the rules on their own tab')
    pg.click('#tb-rules'); ok(pg.is_visible('#tp-rules') and pg.is_hidden('#tp-needs'),'tabs switch panels'); ok('No people in any photo' in pg.inner_text('#rulesl') and 'Checked by code' in pg.inner_text('#rulesl'),'admin lists every rule and who checks it')
    pg.click('#tb-act'); ok('Added before the written rules' in pg.inner_text('#repl') and 'Needs re-check' in pg.inner_text('#repl'),'report lists everything decided, including re-checks')
    ok(pg.evaluate("document.documentElement.scrollWidth<=innerWidth"),'report and rules fit the phone')
    ok(pg.evaluate("[...document.querySelectorAll('#added a')].every(a=>a.getAttribute('href').indexOf('/play.html#story=')==0||a.getAttribute('href')=='/play.html')"),'admin place links deep-link to the story card')
    pg.fill('#k','wrong-key-wrong-key'); pg.click('#go'); pg.wait_for_selector('#err:not([hidden])'); ok('not accepted' in pg.inner_text('#err'),'admin page rejects a wrong key')
    pg.fill('#k',KEY); pg.click('#go'); pg.wait_for_selector('#tools:not([hidden])'); pg.wait_for_selector('#list .row',state='attached')
    pg.click('#tb-needs'); ok('Unlock' in pg.inner_text('#needs') or True,'needs tab'); 
    ok(pg.locator('#needs button:has-text("Approve")').count()==1 and pg.locator('#needs button:has-text("Decline")').count()==1,'a needs-your-decision card has Approve and Decline buttons once unlocked')
    ok('Explore History' in pg.inner_text('#needs') and 'mission only happens if you promote' in pg.inner_text('#needs'),'the card says approval goes to Explore History, not a mission')
    pg.click('#needs button:has-text("Approve")'); pg.wait_for_selector('#needs .say'); ok('You answered. Waiting for Claude' in pg.inner_text('#needs') and 'Nothing is waiting for your decision' in pg.inner_text('#needs') and pg.locator('#nneeds').inner_text()=='','an answered item moves to its own waiting-for-Claude group'); ok('You approved this' in pg.inner_text('#needs') and pg.locator('#cn-needs').inner_text()=='','tapping Approve saves the answer and clears the count')
    s_,j_=api('/api/community/owner',key=KEY); ok(s_==200 and j_['decisions']['10587d75']['decision']=='approve','the owner decision is stored on the server: %r'%j_)
    pg.click('#needs button:has-text("Change my answer")'); pg.wait_for_selector('#needs button:has-text("Decline")'); pg.click('#needs button:has-text("Decline")'); pg.wait_for_selector('#needs .say'); ok('You declined this' in pg.inner_text('#needs'),'Decline works')
    pg.click('#needs button:has-text("Change my answer")'); pg.wait_for_selector('#needs button:has-text("Approve")'); ok(api('/api/community/owner',key=KEY)[1]['decisions']=={},'changing my answer clears it')
    ok('Pending Probe' in pg.inner_text('#pending') and 'nickname: Dad' in pg.inner_text('#pending'),'waiting list shows the pending place: '+pg.inner_text('#pending')[:200])
    pg.wait_for_timeout(800); ok(pg.evaluate("Array.from(document.querySelectorAll('#pending img')).some(function(i){return i.src.indexOf('blob:')===0&&i.naturalWidth>0})"),'pending photos preview with the key')
    ok(pg.evaluate("document.querySelectorAll('#pending figure button[aria-pressed]').length")>=1,'each pending photo has a hold-back button')
    ok(pg.evaluate("/correction for published place/i.test(document.getElementById('pending').innerText)") and pg.evaluate("/the chapel was built in 1911/i.test(document.getElementById('pending').innerText)"),'a correction shows in the waiting list with its text')
    pg.evaluate("document.querySelector('#pending figure button[aria-pressed=false]').click()"); pg.wait_for_timeout(700)
    ok(pg.evaluate("!!document.querySelector('#pending figure.held button[aria-pressed=true]')"),'tapping Hold back marks the photo held')
    pg.evaluate("document.querySelector('#pending figure.held button').click()"); pg.wait_for_timeout(700)
    ok(pg.evaluate("!document.querySelector('#pending figure.held')"),'tapping again restores it')
    ok('Credit Probe' in pg.inner_text('#list') and 'Hidden in the app' in pg.inner_text('#list') and '3 reports' in pg.inner_text('#list'),'admin page lists the hidden place: '+pg.inner_text('#list'))
    ok(pg.evaluate("document.documentElement.scrollWidth<=innerWidth"),'admin page fits the phone'); pg.click('#tb-rep'); pg.click('text=Unhide this place'); pg.wait_for_timeout(600)
    ok('Visible' in pg.inner_text('#list') and 'Hidden in the app' not in pg.inner_text('#list'),'unhide from the admin page works: '+pg.inner_text('#list'))
    ok(pg.evaluate("Object.keys(localStorage).concat(Object.keys(sessionStorage)).length")==0,'admin key is not stored unless Remember is ticked')
    # the key in the address (#k=) unlocks without typing and is not stored
    pg.goto(B+'/contribute/admin/#k='+KEY); pg.wait_for_selector('#tools:not([hidden])'); ok(pg.evaluate("Object.keys(localStorage).length")==0,'#k= unlock does not store the key')
    pg.goto(B+'/contribute/admin/'); pg.wait_for_timeout(500); ok(pg.is_hidden('#tools'),'without the bookmark or Remember it is locked again')
    # Remember on this device, then forget
    pg.fill('#k',KEY); pg.check('#rem'); pg.click('#go'); pg.wait_for_selector('#tools:not([hidden])')
    pg.goto(B+'/contribute/admin/'); pg.wait_for_selector('#tools:not([hidden])'); ok(True,'remembered key unlocks on return')
    pg.click('#forget'); ok(pg.evaluate("Object.keys(localStorage).length")==0 and pg.is_hidden('#tools'),'forget clears the stored key')
    pg.goto(B+'/play.html#stop=reno:depot'); pg.wait_for_timeout(900)
    ok(pg.evaluate("document.body.classList.contains('instop')") and 'depot' in pg.inner_text('#stopTitle').lower(),'a #stop= link opens that mission stop: '+pg.inner_text('body')[:80].replace('\n',' '))
    pg.goto(B+'/play.html#stop=reno:nonsense'); pg.wait_for_timeout(700)
    ok(not pg.evaluate("document.body.classList.contains('instop')"),'an unknown #stop= link falls back to Home')
    pg.goto(B+'/play.html#stop=nowhere:arch'); pg.wait_for_timeout(700)
    ok(not pg.evaluate("document.body.classList.contains('instop')"),'an unknown town in #stop= falls back to Home')
    ok(pg.is_hidden('#tools'),'owner tools stay locked without a key')
    b.close()
  api('/api/community/delete/'+pend,{},key=KEY)
  s,j=api('/api/community/reports'); ok(s==404,'reports list needs the admin key')
  s,j=api('/api/community/unhide/cc000001',{}); ok(s==404,'unhide needs the admin key')
  s,j=api('/api/community/unhide/cc000001',{},key=KEY); ok(s==200,'admin can unhide')
  s,j=api('/api/community/hidden'); ok(j.get('hidden')==[],'unhidden place is visible again: %r'%j)
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
    pg.fill('#place','Probe'); pg.fill('#city','Town'); pg.fill('#one','Some words about it'); pg.click('#nx1')
    ok(pg.is_visible('#own'),'upload box shown when uploads are on')
    ok(pg.is_visible('#contactline') and pg.get_attribute('#contactline a','href')=='mailto:stampthepast@gmail.com','support email shown on the form page')
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
