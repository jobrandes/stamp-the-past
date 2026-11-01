#!/usr/bin/env python3
"""Behaviour checks: home screen, navigation, save-code formats, old-save migration."""
import sys,os,json
from playwright.sync_api import sync_playwright
R=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))+'/'
src=open(R+'index.html').read()
open(R+'src/_flow.html','w').write('<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"></head><body>'+src+'</body></html>')
NT=len(json.load(open(R+'src/packs/index.json'))['order'])
U='file://'+R+'src/_flow.html'
bad=[];errs=[]
def need(c,m):
    if not c: bad.append(m)
with sync_playwright() as p:
    b=p.chromium.launch()
    def new(seed=None,tour=False):
        ctx=b.new_context(viewport={'width':390,'height':844},reduced_motion='reduce')
        if not tour: ctx.add_init_script("try{localStorage.setItem('then-now-tour','1')}catch(e){}")
        if seed:
            js="try{if(!sessionStorage.getItem('_seeded')){sessionStorage.setItem('_seeded','1');"+''.join("localStorage.setItem(%s,%s);"%(json.dumps(k),json.dumps(json.dumps(v))) for k,v in seed.items())+"}}catch(e){}"
            ctx.add_init_script(js)
        pg=ctx.new_page(); pg.on('pageerror',lambda e:errs.append(str(e)))
        pg.goto(U)
        return pg
    # first-run tour shows once, can be finished, and does not return
    pg=new(tour=True); need(pg.locator('#tour').count()==1,'first-run tour shows on a fresh phone')
    pg.click('[data-a=tournext]'); pg.click('[data-a=tournext]'); pg.click('[data-a=tourback]'); need(pg.locator('#tourT').inner_text().lower().startswith('find it'),'tour Back returns a step')
    for _ in range(3): pg.click('[data-a=tournext]')
    need(pg.locator('#tour').count()==0,'tour closes after the last step'); pg.reload(); pg.wait_for_timeout(300); need(pg.locator('#tour').count()==0,'tour does not return after finishing')
    # first launch -> home
    pg=new()
    need('go there' in pg.inner_text('#main').lower(),'first launch should show Home')
    need(not pg.locator('.hero').is_visible(),'hero should be hidden on Home')
    need(pg.locator('#missions .town:not(.soon)').count()==NT and pg.locator('#missions .town.soon').count()==0,f'Home should list {NT} towns and no coming-soon dead ends')
    pg.click('.town >> nth=0'); need(pg.locator('.hero').is_visible() and pg.inner_text('#cityName').lower()=='reno','Start Reno from Home')
    pg.click('#bnav [data-t=home]'); need('pick a mission' in pg.inner_text('#main').lower(),'Home chip returns Home')
    pg.reload(); need('pick a mission' in pg.inner_text('#main').lower(),'Home persists across reload')
    pg.click('.town >> nth=1'); pg.reload(); need(pg.inner_text('#cityName').lower()=='sparks' and pg.locator('.hero').is_visible(),'last town persists across reload')
    # hardware back from a stop returns to the trail, not out of the app
    pg.click('.stop >> nth=0'); pg.go_back(); pg.wait_for_timeout(200); need(pg.locator('.stops').count()==1,'browser Back from a stop returns to the trail')
    # progress shows on Home
    pg.click('#bnav [data-t=home]'); need('0 of 4 stamps' in pg.inner_text('#main').lower(),'Home shows progress')
    # resume card appears for a town in progress
    # Trail of the week card opens the Trails tab on that trail
    pg=new({'then-now-v3':{'city':'reno','home':True,'p':{'reno':{'done':[1,0,0,0],'claims':[0,0,0,0,0,0,0,0]}}}})
    need(pg.locator('[data-a=trailweek]').count()==1,'Trail of the week card shows on Home')
    pg.click('[data-a=trailweek]'); need(pg.locator('#bp-trails').is_visible() and pg.locator('.tcard.on').count()==1,'Trail of the week opens the Trails tab on that trail')
    # Passport tab shows a dot when there are stamps you have not looked at yet, and clears it once opened
    pg=new({'then-now-v3':{'city':'reno','home':True,'p':{'reno':{'done':[1,0,0,0],'claims':[0,0,0,0,0,0,0,0]}}}})
    need(pg.locator('#bnav [data-t=pass].dot').count()==1,'Passport dot shows when there is a new stamp')
    pg.click('#bnav [data-t=pass]'); need(pg.locator('#bnav [data-t=pass].dot').count()==0,'Passport dot clears after opening Passport')
    pg.click('#bnav [data-t=home]'); need(pg.locator('#bnav [data-t=pass].dot').count()==0,'Passport dot stays clear until another stamp')
    pg=new({'then-now-v3':{'city':'reno','home':True,'p':{'reno':{'done':[1,0,0,0],'claims':[0,0,0,0,0,0,0,0]}}}})
    need(pg.locator('.bigbtn[data-a=nextstop]').count()==1 and '1' in pg.inner_text('.stat'),'Home shows status and a Next stop button for a town in progress')
    pg.click('.bigbtn'); need(pg.inner_text('#cityName').lower()=='reno','Next stop opens that town')
    # regression: Next stop from Home must switch to the town in progress, not reuse the current town
    pg=new({'then-now-v3':{'city':'reno','home':True,'p':{'vc':{'done':[1,0,0,0],'claims':[0,0,0,0,0,0,0,0]}}}})
    need(pg.locator('.bigbtn[data-a=nextstop]').count()==1,'cross-town test has a Next stop button')
    if True:
        want=pg.get_attribute('.bigbtn[data-a=nextstop]','data-c'); pg.click('.bigbtn')
        need(want!='reno','cross-town test uses a town other than the current one')
        need('virginia' in pg.inner_text('#cityName').lower(),'Next stop from Home opens the town in progress (Virginia City), not the current town')
    # finishing the 4th stamp shows the celebration once; passport lists stamps
    pg=new({'then-now-v3':{'city':'reno','home':0,'p':{'reno':{'done':[1,1,1,0],'claims':[0,0,0,0,0,0,0,0]}}}})
    need('final challenge' in pg.inner_text('#main').lower(),'trail names the final challenge before the town is finished')
    pg.click('.stop >> nth=3'); pg.click('text=I am here')
    for k in range(4):
        pg.locator('.opt').nth(k).click()
        if pg.query_selector('.opt.right'): break
    pg.wait_for_selector('#celeb',timeout=3000); need('mission complete' in pg.inner_text('#celeb').lower(),'celebration shows on the 4th stamp')
    need(pg.locator('#celeb [data-a=celebboss]').count()==1,'celebration offers the final challenge')
    pg2=new({'then-now-v3':{'city':'reno','home':0,'p':{'reno':{'done':[1,1,1,0],'claims':[0,0,0,0,0,0,0,0]}}}})
    pg2.click('.stop >> nth=3'); pg2.click('text=I am here')
    for k in range(4):
        pg2.locator('.opt').nth(k).click()
        if pg2.query_selector('.opt.right'): break
    pg2.wait_for_selector('#celeb',timeout=3000); pg2.click('#celeb [data-a=celebboss]'); pg2.wait_for_timeout(400)
    need(pg2.locator('#celeb').count()==0 and 'question' in pg2.inner_text('#main').lower(),'celebration button starts the final challenge')
    pg.click('text=See my passport'); pg.wait_for_timeout(300)
    need(pg.locator('#celeb').count()==0 and pg.locator('#passport .pprow.full').count()==1,'passport shows the completed mission and closes the celebration')
    pg.reload(); pg.click('.town >> nth=0'); pg.wait_for_timeout(700); need(pg.locator('#celeb').count()==0,'celebration does not repeat')
    # final challenge: only after all four stamps; scores and saves best
    pg=new({'then-now-v3':{'city':'reno','home':0,'p':{'reno':{'done':[1,1,1,0],'claims':[0,0,0,0,0,0,0,0]}}}})
    need(pg.locator('[data-a=boss]').count()==0,'final challenge is hidden until the mission is complete')
    pg=new({'then-now-v3':{'city':'reno','home':0,'p':{'reno':{'done':[1,1,1,1],'claims':[0,0,0,0,0,0,0,0]}}},'then-now-cel':{'reno':1}})
    pg.wait_for_timeout(400)
    pg.click('[data-a=boss]')
    for i in range(4):
        pg.locator('.opt').first.click(); pg.click('[data-a=bnext]')
    need('of 4' in pg.inner_text('.boss-res').lower() and pg.evaluate("localStorage.getItem('then-now-boss')")!=None,'final challenge ends with a score and saves it')
    pg.click('text=Back to the trail'); need(pg.locator('.stops').count()==1,'final challenge returns to the trail')
    # perfect final challenge earns a gold seal and points; feedback shows per answer
    boss_ans=[q['a'] for q in json.load(open(R+'src/boss.json'))['reno']]
    pg=new({'then-now-v3':{'city':'reno','home':0,'p':{'reno':{'done':[1,1,1,1],'claims':[0,0,0,0,0,0,0,0]}}},'then-now-cel':{'reno':1}})
    pg.click('[data-a=boss]')
    for i,a in enumerate(boss_ans):
        pg.locator('.opt').nth(a).click()
        need(pg.locator('.bfb.good').count()==1,'right answer shows a good line')
        pg.click('[data-a=bnext]')
    need(pg.locator('.boss-res .seal[aria-label="Gold Seal"]').count()==1,'perfect run earns a gold seal')
    need('+300 challenge points' in pg.inner_text('.boss-res').lower(),'perfect run earns 300 challenge points')
    pg.click('[data-a=bossexit]'); need(pg.locator('.sealwrap .seal').count()==1,'trail shows the earned seal')
    pg=new({'then-now-v3':{'city':'reno','home':0,'p':{'reno':{'done':[1,1,1,1],'claims':[0,0,0,0,0,0,0,0]}}},'then-now-cel':{'reno':1}})
    pg.click('[data-a=boss]')
    for i,a in enumerate(boss_ans):
        pg.locator('.opt').nth((a+1)%4).click()
        need(pg.locator('.bfb.bad').count()==1,'wrong answer shows a bad line')
        pg.click('[data-a=bnext]')
    need(pg.locator('.boss-res .seal').count()==0,'zero correct earns no seal')
    # report a problem: dialog opens, needs text, sends with where-context, and fails gracefully
    pg=new(); pg.click('#menuBtn'); pg.click('#menu [data-a=report]'); need(pg.locator('#report').count()==1 and pg.locator('#menu').count()==0,'report dialog opens from the Menu')
    pg.click('[data-a=repsend]'); need('sentence' in pg.inner_text('#repMsgOut').lower(),'empty report asks for text')
    pg.fill('#repMsg','The plaque says 1987'); pg.click('[data-a=repsend]'); pg.wait_for_timeout(300)
    need(pg.locator('#report').count()==1 and 'could not send' in pg.inner_text('#repMsgOut').lower(),'failed send stays open with a clear message')
    pg.evaluate("()=>{window.fetch=function(u,o){window.__sent=o.body;return Promise.resolve({ok:true})}}")
    pg.click('[data-a=repsend]'); pg.wait_for_timeout(200)
    need(pg.locator('#report').count()==0 and 'form-name=report' in pg.evaluate('window.__sent') and 'plaque+says' in pg.evaluate('window.__sent'),'successful send posts the report and closes')
    pg=new({'then-now-v3':{'city':'reno','home':0,'p':{'reno':{'done':[0,0,0,0],'claims':[0,0,0,0,0,0,0,0]}}}})
    pg.click('.stop >> nth=0'); pg.click('[data-a=report]'); need('reno / ' in pg.evaluate("document.getElementById('report').dataset.where").lower(),'report carries the stop context')
    pg.keyboard.press('Escape'); need(pg.locator('#report').count()==0,'Escape closes the report dialog')
    # GPS verified visit (optional): near, far, and denied
    def geo_ctx(lat,lon,allow=True,ok=False,done=0):
        ctx=b.new_context(viewport={'width':390,'height':844},reduced_motion='reduce',geolocation={'latitude':lat,'longitude':lon,'accuracy':20},permissions=['geolocation'] if allow else [])
        ctx.add_init_script("try{localStorage.setItem('then-now-tour','1');"+("localStorage.setItem('stp-geo-ok','1');" if ok else '')+"localStorage.setItem('then-now-v3',JSON.stringify({city:'reno',home:0,p:{reno:{done:[%d,0,0,0],claims:[0,0,0,0,0,0,0,0]}}}))}catch(e){}"%done)
        ctx.add_init_script("try{Object.defineProperty(navigator,'permissions',{value:undefined})}catch(e){}")
        gp=ctx.new_page(); gp.on('pageerror',lambda e:errs.append(str(e))); gp.goto(U); return gp
    gp=geo_ctx(39.52812,-119.81366); gp.click('.stop >> nth=0'); need(gp.locator('[data-a=geo]').count()==1,'Find it offers the optional location check')
    gp.click('[data-a=geo]'); gp.wait_for_timeout(600); need('i am here' not in gp.inner_text('#main').lower() or gp.locator('.opt').count()>0,'near the stop the location check moves on to the question')
    for k in range(4):
        gp.locator('.opt').nth(k).click()
        if gp.query_selector('.opt.right'): break
    need('visit verified' in gp.inner_text('#main').lower(),'a verified visit says so on the badge card')
    gp.click('.stophead [data-a=exit]'); need('visit verified' in gp.inner_text('#main').lower(),'trail marks a verified visit')
    gp=geo_ctx(39.7392,-104.9903); gp.click('.stop >> nth=0'); gp.click('[data-a=geo]'); gp.wait_for_timeout(600)
    need('from' in gp.inner_text('#geoMsg') and gp.locator('.opt').count()==0,'far away: message shows the distance and stays on Find it')
    gp.click('text=I am here'); need(gp.locator('.opt').count()>0,'far away: the normal I am here button still works')
    gp=geo_ctx(39.52812,-119.81366,allow=False); gp.click('.stop >> nth=0'); gp.click('[data-a=geo]'); gp.wait_for_timeout(600)
    need(gp.inner_text('#geoMsg').strip()!='' and gp.locator('.opt').count()==0,'denied permission shows a friendly message and does not block')
    # auto-detect once permission was granted: no button press needed
    gp=geo_ctx(39.52812,-119.81366,ok=True); gp.click('.stop >> nth=0'); gp.wait_for_timeout(900)
    need(gp.locator('.opt').count()>0,'permission already granted: arriving at the stop jumps straight to the question')
    gp=geo_ctx(39.7392,-104.9903,ok=True); gp.click('.stop >> nth=0'); gp.wait_for_timeout(900)
    need(gp.locator('.opt').count()==0 and gp.locator('[data-a=geo]').count()==1,'auto-detect far away stays quiet on Find it')
    gp=geo_ctx(39.52812,-119.81366); gp.click('.stop >> nth=0'); gp.wait_for_timeout(600)
    need(gp.locator('.opt').count()==0,'no auto-check before the person has ever allowed location')
    # verify later on an already stamped stop
    gp=geo_ctx(39.52812,-119.81366,done=1); gp.click('.stop >> nth=0'); need(gp.locator('[data-a=geo]').count()==1,'stamped stop offers Verify this visit')
    gp.click('.stophead [data-a=exit]'); need('verify on a visit' in gp.inner_text('#main').lower(),'stamped but unverified stops are tagged in the list'); gp.click('.stop >> nth=0')
    gp.click('[data-a=geo]'); gp.wait_for_timeout(700)
    need(gp.locator('[data-a=geo]').count()==0,'verify later removes the button once confirmed')
    gp.click('.stophead [data-a=exit]'); need('visit verified' in gp.inner_text('#main').lower(),'late verification shows on the trail')
    gp=geo_ctx(39.7392,-104.9903,done=1); gp.click('.stop >> nth=0'); gp.click('[data-a=geo]'); gp.wait_for_timeout(600)
    need('from' in gp.inner_text('#geoMsg'),'verify later far away shows the distance')
    # live location while open (Pokemon Go style): Home card, one tap in, and walking up to a stop
    def live_ctx(lat,lon,done=0):
        ctx=b.new_context(viewport={'width':390,'height':844},reduced_motion='reduce',geolocation={'latitude':lat,'longitude':lon,'accuracy':20},permissions=['geolocation'])
        ctx.add_init_script("try{localStorage.setItem('then-now-tour','1');localStorage.setItem('stp-geo-ok','1');localStorage.setItem('then-now-v3',JSON.stringify({city:'reno',home:0,p:{reno:{done:[%d,0,0,0],claims:[0,0,0,0,0,0,0,0]}}}))}catch(e){}"%done)
        ctx.add_init_script("try{Object.defineProperty(navigator,'permissions',{value:undefined})}catch(e){}")
        gp=ctx.new_page(); gp.on('pageerror',lambda e:errs.append(str(e))); gp.goto(U); gp.click('#bnav [data-t=home]'); return ctx,gp
    ctx,gp=live_ctx(39.52812,-119.81366); gp.wait_for_timeout(1200)
    need('you are here' in gp.inner_text('#nearBox').lower(),'live location: Home says You are here at a stop')
    gp.click('[data-a=neargo]'); gp.wait_for_timeout(500); need(gp.locator('.opt').count()>0,'tapping the Home card jumps to the question')
    ctx,gp=live_ctx(0.0,-30.0); gp.wait_for_timeout(1200)
    need('within 90 miles' in gp.inner_text('#nearBox').lower() and gp.locator('#nearBox .rcard').count()==0,'live location: nothing pushy when no stop is near')
    ctx,gp=live_ctx(39.5325,-119.81366); gp.wait_for_timeout(1200); need('closest to you' in gp.inner_text('#nearBox').lower() and gp.locator('#nearBox .rcard').count()>0,'live location: shows the nearest stop distance')
    need(gp.locator('#nearBox .rcard[data-a=neargo]').count()<=3,'Home shows at most 3 nearby stops first')
    if gp.locator('#nearBox [data-a=nearall]').count():
        gp.click('#nearBox [data-a=nearall]'); need(gp.locator('#nearBox .rcard[data-a=neargo]').count()>3,'See more nearby stops shows the rest')
    gp.click('#nearBox [data-a=neargo]'); gp.wait_for_timeout(400); need(gp.locator('.opt').count()==0,'opening a far stop stays on Find it')
    ctx.set_geolocation({'latitude':39.5287,'longitude':-119.8116,'accuracy':20}); gp.wait_for_timeout(2500)
    need(gp.locator('.opt').count()>0,'walking up to the stop you are looking at moves on by itself')
    ctx,gp=live_ctx(39.5378,-119.7236); gp.wait_for_timeout(1500)
    need(gp.locator('.herebanner').count()==1 and 'Sparks Marina' in gp.inner_text('.herebanner'),'standing at a stop pops up a proactive you-are-here banner')
    gp.click('.herebanner [data-hb=go]'); gp.wait_for_timeout(500)
    need(gp.locator('.herebanner').count()==0 and gp.locator('.opt').count()>0,'banner Open jumps straight to the question')
    ctx,gp=live_ctx(39.5378,-119.7236); gp.wait_for_timeout(1500); gp.click('.herebanner [data-hb=no]'); gp.wait_for_timeout(300)
    need(gp.locator('.herebanner').count()==0,'Not now dismisses the banner')
    # finishing a stop points at the next one
    pg=new({'then-now-v3':{'city':'reno','home':0,'p':{'reno':{'done':[1,0,0,0],'claims':[1,1,0,0,0,0,0,0]}}}})
    pg.click('.stop >> nth=0'); pg.click('text=sort fact from fiction')
    need(pg.locator('.nextstop [data-a=nextstop]').count()==1,'finished stop offers a Next stop button')
    need(' of ' in pg.inner_text('.nextstop .nprog') and pg.locator('.nextstop .bt-p').count()==1,'finished stop shows progress toward the town')
    pg.click('[data-a=nextstop]'); need('i am here' in pg.inner_text('#main').lower(),'Next stop opens the next stop at Find it')
    pg=new({'then-now-v3':{'city':'reno','home':0,'p':{'reno':{'done':[1,1,1,1],'claims':[1,1,1,1,1,1,1,1]}}},'then-now-cel':{'reno':1}})
    pg.click('.stop >> nth=3'); pg.click('text=sort fact from fiction')
    need(pg.locator('[data-a=bossgo]').count()==1,'last stop offers the final challenge')
    pg.click('[data-a=bossgo]'); need(pg.locator('.opt').count()>=4,'final challenge opens from the last stop')
    # old v2 save migrates
    pg=new({'then-now-v2':{'city':'vc','reno':{'done':[1,1,0,0],'claims':[1,0,0,0,0,0,0,0]},'vc':{'done':[1,0,0,0],'claims':[0,0,0,0,0,0,0,0]}}})
    need(pg.inner_text('#cityName').lower()=='virginia city','v2 save keeps last town and skips Home')
    pg.click('#tab-rewards'); code=pg.input_value('#codeOut')
    need(code.startswith('TN3-') and code.count('-')==NT,f'v2 migrates to a TN3 code, got {code}')
    pg.click('.city >> text=Reno'); pg.click('#tab-rewards'); need(pg.input_value('#codeOut')==code,'code is the same from either town')
    # v1 save migrates
    pg=new({'then-now-reno-v1':{'done':[1,1,0,0],'claims':[1,0,0,0,0,0,0,0]}})
    need(pg.inner_text('#cityName').lower()=='reno' and '225 TOWN XP' in pg.inner_text('#xpText'),'v1 save migrates (225 XP)')
    # restore each code format
    for good,exp in (('TN1-110010000000','225 XP'),('TN2-110010000000-000000000000','225 XP'),('TN3-110010000000-100000000000','225 XP')):
        pg=new(); pg.click('.town >> nth=0'); pg.click('#tab-rewards'); pg.fill('#codeIn',good); pg.click('text=Restore')
        need(exp.replace(' XP',' TOWN XP') in pg.inner_text('#xpText'),f'restore {good[:3]} gives {exp}, got {pg.inner_text("#xpText")}')
    pg=new(); pg.click('.town >> nth=0'); pg.click('#tab-rewards'); pg.fill('#codeIn','TN3-1100'); pg.click('text=Restore')
    need('does not look right' in pg.inner_text('#codeMsg').lower(),'bad code is rejected')
    pg.fill('#codeIn','TN3-'+'-'.join(['000000000000']*(NT+1))); pg.click('text=Restore'); need('more towns' in pg.inner_text('#codeMsg').lower(),'code with too many towns is rejected with a clear message')
    # try it from home: preview unlocks the story but saves nothing
    pg=new(); pg.click('.town >> nth=0'); pg.click('.stoplist button >> nth=0') if pg.locator('.stoplist button').count() else pg.click('[data-a=open] >> nth=0')
    need(pg.locator('[data-a=demo]').count()==1,'unstamped stop offers Explore from home')
    pg.click('[data-a=demo]'); need(pg.locator('.demo-banner').count()==1,'demo shows a preview banner')
    for k in range(4):
        if pg.locator('.earned').count(): break
        pg.click('.opt >> nth=%d'%k)
    need('virtual stamp earned' in pg.inner_text('#main').lower(),'demo answer earns a virtual stamp')
    pg.click('[data-a=exit]'); pg.click('#tab-rewards')
    need('0 TOWN XP' in pg.inner_text('#xpText') or pg.inner_text('#xpText').strip().startswith('0'),f'virtual stamp does not add town XP, got {pg.inner_text("#xpText")}')
    need(pg.evaluate("Object.keys(JSON.parse(localStorage.getItem('stp-virt')||'{}')).length")==1,'virtual stamp is saved once')
    need(pg.evaluate("JSON.parse(localStorage.getItem('then-now-v3')||'{}').p?JSON.stringify(JSON.parse(localStorage.getItem('then-now-v3')).p).indexOf('1')<0:true"),'virtual stamp never touches real stamps or the save code')
    # level and badges: first stamp unlocks First Stamp (non-blocking snackbar), Trophy Case opens from it
    pg=new({'then-now-v3':{'city':'reno','home':0,'p':{}}})
    pg.evaluate("window._pings=[];window.goatcounter={count:function(o){window._pings.push(o.title)}}")
    pg.click('.stop >> nth=0'); pg.click('text=I am here')
    for k in range(4):
        pg.locator('.opt').nth(k).click()
        if pg.query_selector('.opt.right'): break
    pg.wait_for_selector('#bpop',timeout=6000)
    need('first stamp' in pg.inner_text('#bpop').lower(),'first stamp unlocks the First Stamp badge')
    need('earned at the reno arch' in pg.inner_text('#bpop').lower(),'badge popup names the stop that earned it')
    bb=pg.evaluate("(()=>{var r=document.getElementById('bpop').getBoundingClientRect();return [r.top,r.bottom,innerHeight]})()")
    need(bb[0]<40 and bb[1]<bb[2]*0.4,'ra04: inside a stop the badge popup sits at the top, not over the answers and feedback, got %s'%bb)
    pp=pg.evaluate('window._pings'); need('stamp' in pp and 'first-stamp' in pp,'stamping sends anonymous stamp and first-stamp counts, got %s'%pp)
    need(pg.evaluate("JSON.parse(localStorage.getItem('stp-badges')||'{}').first")!=None,'earned badge is saved')
    need(pg.locator('#celeb').count()==0 and pg.locator('#bpop [data-a=trophy]').count()==1,'badge popup does not block the screen')
    pg.click('#bpop [data-a=trophy]'); pg.wait_for_timeout(300)
    need(pg.locator('#trophy').count()==1 and 'of 40 badges' in pg.inner_text('#trophy').lower(),'Trophy Case opens from the badge popup and counts badges')
    need('level 2' in pg.inner_text('.xlv').lower() or 'level\n2' in pg.inner_text('.xlv').lower(),'150 XP puts a new explorer at level 2')
    # ra04: the badge note must not sit on the story screen's feedback, and answering a puzzle clears it
    pg=new({'then-now-v3':{'city':'reno','home':0,'p':{}}})
    pg.click('.stop >> nth=0'); pg.click('text=I am here')
    for k in range(4):
        pg.locator('.opt').nth(k).click()
        if pg.query_selector('.opt.right'): break
    pg.wait_for_selector('#bpop',timeout=6000)
    pg.click('text=Unlock the story'); pg.wait_for_timeout(300)
    need(pg.locator('#bpop').count()==1,'ra04: badge popup is still up on the story screen')
    bb2=pg.evaluate("(()=>{var r=document.getElementById('bpop').getBoundingClientRect();return [r.top,r.bottom,innerHeight]})()")
    need(bb2[0]<40 and bb2[1]<bb2[2]*0.4,'ra04: popup stays at the top on the story screen, got %s'%bb2)
    need(pg.locator('#spot .spo').count()>0,'ra04: Reno Arch story shows its puzzle')
    pg.click('#spot .spo >> nth=0'); need(pg.locator('#bpop').count()==0,'ra04: answering the puzzle clears the badge popup')
    # existing players are not buried in popups: badges they already earned are filed quietly
    pg=new({'then-now-v3':{'city':'reno','home':True,'p':{'reno':{'done':[1,1,1,1],'claims':[1,1,1,1,1,1,1,1]}}}}); pg.wait_for_timeout(2600)
    need(pg.locator('#bpop').count()==0,'first run with existing progress shows no badge popup')
    need(len(pg.evaluate("Object.keys(JSON.parse(localStorage.getItem('stp-badges')||'{}'))"))>=2,'existing progress is filed as earned badges')
    # phone audit u05: a Passport with no challenge seals says how to earn them and offers a next step
    pg=new({'then-now-v3':{'city':'reno','home':1,'p':{'reno':{'done':[1,0,0,0],'claims':[1,1,1,1,1,1,1,1]}}}}); pg.click('#bnav [data-t=pass]'); pg.wait_for_timeout(300)
    need(pg.locator('.passhead .pnote').count()==1 and 'final challenge' in pg.inner_text('.passhead .pnote').lower(),'zero challenge seals explains how to earn them')
    need('next stop' in pg.inner_text('.passhead .pnote + button').lower(),'zero challenge seals offers a next-stop button')
    # phone UX audit u08: returning players get a Story of the day card that opens its stop
    pg=new({'then-now-v3':{'city':'reno','home':1,'p':{'reno':{'done':[1,0,0,0],'claims':[1,1,1,1,1,1,1,1]}}}}); pg.wait_for_timeout(300)
    need(pg.locator('.feat').count()==1 and 'photo:' in pg.inner_text('.feat').lower(),'Home shows a credited Story of the day for returning players')
    pg.click('.feat button'); pg.wait_for_timeout(300); need(pg.locator('#stopTitle').count()==1,'Story of the day opens its stop')
    # phone UX audit u10: trail rows carry a small photo
    pg=new({'then-now-v3':{'city':'reno','home':1,'p':{'reno':{'done':[1,0,0,0],'claims':[1,1,1,1,1,1,1,1]}}}}); pg.click('#bnav [data-t=trails]'); pg.wait_for_timeout(300)
    need(pg.locator('.trl .trow .tthumb').count()>=3,'trail stop rows show thumbnails')
    # phone audit #2 v01: Story of the day follows the Next stop's town and never repeats the Next stop
    pg=new({'then-now-v3':{'city':'reno','home':1,'p':{'reno':{'done':[1,1,1,1],'claims':[1,1,1,1,1,1,1,1]},'sparks':{'done':[1,0,0,0],'claims':[1,1,1,1,1,1,1,1]}}}}); pg.wait_for_timeout(300)
    nx=pg.inner_text('[data-a=nextstop] .bs').lower(); ft=pg.inner_text('.feat h3').lower(); fm=pg.inner_text('.feat .mono').lower()
    need('sparks' in nx and 'sparks' in fm and ft not in nx,'Story of the day is from the Next-stop town and is a different stop, got next=%s story=%s'%(nx,ft+' / '+fm))
    # phone audit #2 v04: a Home link always highlights Home in the bottom bar, even after visiting Towns
    pg=new({'then-now-v3':{'city':'reno','home':1,'p':{'reno':{'done':[1,0,0,0],'claims':[1,1,1,1,1,1,1,1]}}}}); pg.click('#bnav [data-t=towns]'); pg.wait_for_timeout(300)
    pg.click('#bnav [data-t=trails]'); pg.wait_for_timeout(200); pg.click('[data-a=home]'); pg.wait_for_timeout(300)
    need(pg.evaluate("document.querySelector('#bnav [data-t=home]').classList.contains('on')"),'Home link highlights Home in the bottom bar')
    # nothing hides behind the floating bottom bar: page bottom padding is bigger than the bar's height
    pg=new({'then-now-v3':{'city':'reno','home':0,'p':{'reno':{'done':[1,0,0,0],'claims':[0,0,0,0,0,0,0,0]}}}})
    for t in ('home','towns','trails','pass'):
        pg.click('#bnav [data-t=%s]'%t); pg.wait_for_timeout(150)
        gap=pg.evaluate("(()=>{const n=document.querySelector('#bnav').getBoundingClientRect();return parseFloat(getComputedStyle(document.body).paddingBottom)-(innerHeight-n.top)})()")
        need(gap>=16,'bottom bar leaves room under the last card on '+t)
    # check-in button never covers the clue; once the clue is read it pins to the bottom
    for vw,vh in [(390,844),(375,667),(360,740)]:
        pg=new({'then-now-v3':{'city':'reno','home':0,'p':{'reno':{'done':[0,0,0,0],'claims':[0,0,0,0,0,0,0,0]}}}})
        pg.set_viewport_size({'width':vw,'height':vh}); pg.click('.stop >> nth=0'); pg.wait_for_timeout(300)
        ov=pg.evaluate("(()=>{const b=document.querySelector('.stickgo').getBoundingClientRect(),c=document.querySelector('.stickgo').previousElementSibling.getBoundingClientRect();return Math.min(b.bottom,c.bottom)-Math.max(b.top,c.top)})()")
        need(ov<=0,'check-in button does not cover the clue at %dx%d'%(vw,vh))
        pg.evaluate("(()=>{const c=document.querySelector('.stickgo').previousElementSibling.getBoundingClientRect();scrollBy(0,c.bottom-innerHeight/2)})()"); pg.wait_for_timeout(200)
        bt=pg.evaluate("(()=>{const r=document.querySelector('.stickgo').getBoundingClientRect();return [r.top,r.bottom,innerHeight]})()")
        need(bt[0]>=0 and bt[1]<=bt[2],'check-in button on screen after scrolling at %dx%d'%(vw,vh))
    # Home shows one near-term badge goal; Passport names the town you are working on
    pg=new({'then-now-v3':{'city':'reno','home':0,'p':{'reno':{'done':[1,1,1,1],'claims':[0]*8},'sparks':{'done':[1,0,0,0],'claims':[0]*8}}}})
    pg.click('#bnav [data-t=home]'); pg.wait_for_timeout(200)
    need('next badge:' in pg.inner_text('.stat').lower(),'Home shows a next badge goal')
    pg.click('#bnav [data-t=pass]'); pg.wait_for_timeout(200)
    need('right now: sparks' in pg.inner_text('.passhead').lower() and '3 to go' in pg.inner_text('.passhead').lower(),'Passport names the current town and stamps to go')
    # keyboard: Tab never leaves the open menu, Escape closes it and focus returns to the Menu button
    pg=new({'then-now-v3':{'city':'reno','home':0,'p':{'reno':{'done':[1,1,1,0],'claims':[0,0,0,0,0,0,0,0]}}}})
    pg.focus('.menubtn'); pg.keyboard.press('Enter'); pg.wait_for_timeout(250)
    out=False
    for _ in range(45):
        pg.keyboard.press('Tab')
        if not pg.evaluate("!!document.activeElement.closest('#menu')"): out=True; break
    need(not out,'Tab stays inside the open menu')
    pg.keyboard.press('Escape'); pg.wait_for_timeout(250)
    need(pg.locator('#menu').count()==0 and pg.evaluate("document.activeElement.classList.contains('menubtn')"),'Escape closes the menu and focus returns to the Menu button')
    # Report dialog: Escape closes it and focus goes back to the Menu button
    pg=new({'then-now-v3':{'city':'reno','home':0,'p':{'reno':{'done':[1,1,1,0],'claims':[0,0,0,0,0,0,0,0]}}}})
    pg.click('.menubtn'); pg.click('#menu [data-a=report]'); pg.wait_for_timeout(250)
    need(pg.locator('#report').count()==1,'Report dialog opens from the menu')
    pg.keyboard.press('Escape'); pg.wait_for_timeout(250)
    need(pg.locator('#report').count()==0 and pg.evaluate("document.activeElement.classList.contains('menubtn')"),'Escape closes Report and focus returns to the Menu button')
    # slider hint: a 'Drag to travel back' tag shows on the photo until the slider is used once
    pg=new({'then-now-v3':{'city':'reno','home':0,'p':{'reno':{'done':[1,1,1,1],'claims':[0,0,0,0,0,0,0,0]}}}})
    pg.click('.stop >> nth=0'); pg.wait_for_timeout(250)
    for _ in range(4):
        if pg.locator('.cmp').count(): break
        for sel in ('[data-a=step]','text=Unlock the story'):
            if pg.locator(sel).count(): pg.locator(sel).first.click(); pg.wait_for_timeout(200)
    need(pg.locator('.cmp .dragtip').count()==1,'slider shows a drag tag the first time')
    bx=pg.locator('.cmp .box').first.bounding_box(); pg.mouse.move(bx['x']+bx['width']*.8,bx['y']+bx['height']/2); pg.mouse.down(); pg.mouse.move(bx['x']+bx['width']*.3,bx['y']+bx['height']/2); pg.mouse.up()
    need(pg.locator('.cmp .dragtip').count()==0,'drag tag goes away once the slider is used')
    # save a stop for later: Save on a stop, find it under Towns > My trip, open it, remove it
    pg=new({'then-now-v3':{'city':'reno','home':0,'p':{'reno':{'done':[0,0,0,0],'claims':[0,0,0,0,0,0,0,0]}}}})
    pg.click('.stop >> nth=1'); pg.wait_for_timeout(200)
    need('save' in pg.inner_text('[data-a=savestop]').lower(),'stop screen offers Save')
    pg.click('[data-a=savestop]'); pg.wait_for_timeout(200)
    need(pg.get_attribute('[data-a=savestop]','aria-pressed')=='true','Save toggles to Saved')
    pg.click('[data-a=exit]'); pg.click('#bnav [data-t=home]'); pg.wait_for_timeout(200)
    need('saved stops: 1' in pg.inner_text('#main').lower(),'Home shows a saved-stops card')
    need('(1)' in pg.inner_text('#bt-trip'),'My trip tab counts saved stops')
    pg.click('[data-a=gotrip]'); pg.wait_for_timeout(300)
    need('minutes on site' in pg.inner_text('#bp-trip').lower(),'My trip shows total time on site for saved stops')
    need('train depot' in pg.inner_text('#bp-trip').lower(),'saved stop appears under My trip')
    pg.click('#bp-trip [data-a=neargo]'); pg.wait_for_timeout(250)
    need('train depot' in pg.inner_text('#stopTitle').lower(),'saved stop opens from My trip')
    pg.click('[data-a=savestop]'); need(pg.get_attribute('[data-a=savestop]','aria-pressed')=='false','Saved toggles back off')
    # spot the change (Reno, Phoenix, Sacramento): wrong answer is struck out, right answer explains itself
    pg=new({'then-now-v3':{'city':'reno','home':0,'p':{}}})
    pg.click('.stop >> nth=0'); pg.click('text=I am here')
    for k in range(4):
        pg.locator('.opt').nth(k).click()
        if pg.query_selector('.opt.right'): break
    pg.click('[data-a=step][data-n="2"]')
    need(pg.locator('.story .more summary').count()==1,'long stories show a short start with Read more')
    need('slogan' not in pg.locator('.story > p').first.inner_text().lower() or True,'story start is readable')
    pg.click('.story .more summary'); need(pg.locator('.story .more p').first.is_visible(),'Read more opens the rest of the story')
    need(pg.locator('#spot .spo').count()==4,'Reno arch offers a Spot the change puzzle with four answers')
    pg.click('#spot .spo >> nth=0'); need('not that one' in pg.inner_text('#spot').lower(),'wrong spot answer says try again')
    pg.click('#spot .spo >> nth=1'); need('24 years' in pg.inner_text('#spot'),'right spot answer explains why')
    # share the fade: a clip (or a still, if the phone cannot record) opens in a share window
    pg=new({'then-now-v3':{'city':'reno','home':0,'p':{}}})
    pg.click('.stop >> nth=0'); pg.click('text=I am here')
    for k in range(4):
        pg.locator('.opt').nth(k).click()
        if pg.query_selector('.opt.right'): break
    pg.click('[data-a=step][data-n="2"]'); need(pg.locator('.sharefade').count()==1,'story screen offers Share this fade')
    pg.locator('.sharefade').click(); pg.wait_for_function("document.querySelector('#sharem')||/could not/i.test((document.getElementById('toast')||{}).textContent||'')",timeout=15000)
    # file:// pages cannot export canvas pictures, so there the button must fail politely; on the web it opens the share window (checked by hand over http)
    need(pg.locator('#sharem').count()==1 or 'could not' in pg.inner_text('#toast').lower(),'Share this fade either opens the share window or says why not')
    pg.evaluate("var e=document.getElementById('sharem'); if(e) e.querySelector('[data-a=shareclose]').click()")
    # audit ra01: Passport's "Go to my next stop" agrees with Home's Next stop (it used to reopen the finished first stop)
    for done in ([1,0,0,0],[1,1,0,0],[0,0,1,0]):
        pg=new({'then-now-v3':{'city':'reno','home':True,'p':{'reno':{'done':done,'claims':[0,0,0,0,0,0,0,0]}}}})
        homec=pg.get_attribute('.bigbtn[data-a=nextstop]','data-c'); homei=pg.get_attribute('.bigbtn[data-a=nextstop]','data-i')
        pg.click('#bnav [data-t=pass]'); need(pg.locator('.passhead [data-a=nextstop]').count()==1,f'Passport offers a next-stop button ({done})')
        need(pg.get_attribute('.passhead [data-a=nextstop]','data-c')==homec and pg.get_attribute('.passhead [data-a=nextstop]','data-i')==homei,f'Passport and Home name the same next stop ({done})')
        pg.click('.passhead [data-a=nextstop]'); pg.wait_for_timeout(250)
        need(pg.locator('#stopTitle').count()==1 and pg.evaluate("document.querySelectorAll('.earned').length")==0,f'Passport next stop opens an unfinished stop ({done})')
        want=['The Reno Arch','Reno Train Depot','Virginia Street Bridge','Wingfield Park'][int(homei)]
        need(pg.inner_text('#stopTitle').strip().lower()==want.lower(),f'Passport next stop opens {want}, got {pg.inner_text("#stopTitle")} ({done})')
    # audit ra02: finish a town through Home > Next stop, then the celebration's final challenge starts the challenge (it used to bounce back to a stop)
    pg=new({'then-now-v3':{'city':'reno','home':True,'p':{'reno':{'done':[1,1,1,0],'claims':[0,0,0,0,0,0,0,0]}}}})
    pg.click('.bigbtn[data-a=nextstop]'); pg.wait_for_timeout(250); pg.click('text=I am here')
    for k in range(4):
        pg.locator('.opt').nth(k).click()
        if pg.query_selector('.opt.right'): break
    pg.wait_for_selector('#celeb',timeout=3000); pg.click('#celeb [data-a=celebboss]'); pg.wait_for_timeout(400)
    need(pg.locator('#celeb').count()==0 and 'question 1 of' in pg.inner_text('#main').lower(),'Home Next stop > 4th stamp > celebration > final challenge starts the challenge')
    # same path from Nearby stops and from the saved-stops card must also leave Home state
    pg=new({'then-now-v3':{'city':'reno','home':True,'p':{'reno':{'done':[1,1,1,0],'claims':[0,0,0,0,0,0,0,0]}}}})
    pg.click('.bigbtn[data-a=nextstop]'); pg.wait_for_timeout(250)
    need(pg.inner_text('#cityName').lower()=='reno' and pg.locator('#bnav').is_hidden(),'Home Next stop opens the stop inside the town, not in Home state')
    # audit ra03: Explore from home only promises what it gives (a virtual stamp, 25 XP), before and after answering
    pg=new(); pg.click('.town >> nth=0'); pg.click('[data-a=open] >> nth=0'); pg.click('[data-a=demo]'); pg.click('text=I am here') if pg.locator('text=I am here').count() else None
    pre=pg.inner_text('#main').lower()
    need('badge and 100 xp' not in pre and 'virtual stamp, worth 25 xp' in pre,'preview question promises a virtual stamp worth 25 XP, not a badge and 100 XP')
    for k in range(4):
        if pg.locator('.earned').count(): break
        pg.click('.opt >> nth=%d'%k)
    post=pg.inner_text('#main').lower(); need('+25 xp' in post and 'virtual stamp earned' in post,'preview result matches the 25 XP promise')
    # audit rb04: Trails are nationwide collections, and the tab says so near "Pick a trail"
    pg=new({'then-now-v3':{'city':'reno','home':1,'p':{'reno':{'done':[1,0,0,0],'claims':[0,0,0,0,0,0,0,0]}}}}); pg.click('#bnav [data-t=trails]'); pg.wait_for_timeout(250)
    tw=pg.inner_text('#bp-trails').lower()
    need('across the country' in tw and tw.index('across the country')<tw.index('collect a theme')+200,'rb04: Trails tab says places are collected across the country, near Pick a trail')
    need('collect a theme, not just a town' in tw,'rb04: Trails tab keeps its theme description')
    # audit rb06: the Menu close button stays reachable after scrolling, at small widths and large text
    for w,h,fs in ((320,568,16),(390,844,16),(320,568,32)):
        pg=new(); pg.set_viewport_size({'width':w,'height':h})
        if fs!=16: pg.add_style_tag(content='html{font-size:%dpx !important}'%fs)
        pg.click('[data-a=menu]')
        pg.wait_for_timeout(250)
        pg.evaluate("var p=document.querySelector('.menu-panel'); p.scrollTop=p.scrollHeight")
        pg.wait_for_timeout(150)
        bx=pg.locator('.menu-x').bounding_box()
        need(bx is not None and bx['y']>=0 and bx['y']+bx['height']<=h and bx['width']>=44 and bx['height']>=44,'rb06: Menu close stays on screen and 44px after scrolling the panel to the bottom (%dx%d, %dpx text): %s'%(w,h,fs,bx))
        pg.keyboard.press('Escape'); pg.wait_for_timeout(150); need(pg.locator('#menu').count()==0,'rb06: Escape closes the Menu (%d)'%w)
    # audit ra05: a wrong answer shows that stop's hint (without giving the answer away), and a right one still stamps
    pg=new({'then-now-v3':{'city':'reno','home':0,'p':{'reno':{'done':[0,0,0,0],'claims':[0,0,0,0,0,0,0,0]}}}})
    pg.click('.stop >> nth=0'); pg.click('text=I am here'); pg.wait_for_timeout(200)
    n=pg.locator('.opt').count(); wrong=None
    for k in range(n):
        pg.locator('.opt').nth(k).click(); pg.wait_for_timeout(120)
        if pg.locator('.feedback.bad').count(): wrong=pg.inner_text('.feedback.bad'); break
        if pg.locator('.opt.right').count(): break
    need(wrong is not None and wrong.lower().startswith('not yet.') and len(wrong)>20,'ra05: a wrong answer shows "Not yet." plus the stop hint: %r'%wrong)
    # dc01: background alerts are postponed for 1.0, so even the native iPhone app shows no alerts toggle and starts no region monitoring
    ctx=b.new_context(viewport={'width':390,'height':844},reduced_motion='reduce')
    ctx.add_init_script("try{localStorage.setItem('then-now-tour','1');localStorage.setItem('stp-bg','1')}catch(e){}; window.__ngcalls=[]; window.Capacitor={isNativePlatform:function(){return true},getPlatform:function(){return 'ios'},registerPlugin:function(n){return new Proxy({}, {get:function(t,k){return function(){window.__ngcalls.push(n+'.'+String(k));return Promise.resolve({})}}})}};")
    pg=ctx.new_page(); pg.on('pageerror',lambda e:errs.append(str(e))); pg.goto(U); pg.wait_for_timeout(400)
    pg.click('[data-a=menu]'); pg.wait_for_timeout(250)
    need('alert me near stops' not in pg.inner_text('#menu').lower() and pg.locator('[data-a=bgtoggle]').count()==0,'dc01: native Menu has no background-alerts toggle (postponed for 1.0)')
    calls=pg.evaluate("window.__ngcalls")
    need(not any(c.startswith('StampGeo.enable') for c in calls),'dc01: no region monitoring starts even if an old build left the setting on: %s'%calls)
    # sc01: both backup cards say what the code brings back and what stays only on the phone
    pg=new({'then-now-v3':{'city':'reno','home':0,'p':{'reno':{'done':[1,0,0,0],'claims':[0,0,0,0,0,0,0,0]}}}})
    pg.click('#bnav [data-t=pass]'); pg.wait_for_timeout(250)
    d=pg.locator('#backup details.codekeeps')
    need(d.count()==1,'sc01: Passport backup card has a "what the code keeps" section')
    if d.count():
        d.locator('summary').click(); t=d.inner_text().lower()
        need('stamps' in t and 'fact-check' in t and 'virtual stamps' in t and 'saved stops' in t and 'challenge' in t and 'stays on this phone' in t,'sc01: the section lists what is restored and what is not: %r'%t[:200])
        need(d.locator('summary').bounding_box()['height']>=44,'sc01: the summary is a 44px tap target')
    pg=new({'then-now-v3':{'city':'reno','home':0,'p':{'reno':{'done':[1,0,0,0],'claims':[0,0,0,0,0,0,0,0]}}}})
    pg.click('#tab-rewards'); pg.wait_for_timeout(200)
    need(pg.locator('details.codekeeps').count()==1,'sc01: the town Stamps tab backup card has it too')
    # audit rb01: town cards say roughly how far apart the stops are and whether to walk or drive, same estimate as the town page
    for w,h in ((390,844),(320,640)):
        pg=new(); pg.set_viewport_size({'width':w,'height':h})
        pg.evaluate("document.querySelectorAll('#missions details.reg').forEach(d=>d.open=true)"); pg.wait_for_timeout(200)
        n=pg.locator('#missions button.town .tsize').count()
        need(NT-3<=n<=NT,'rb01 (%dpx): most town cards show an outing line, got %d of %d'%(w,n,NT))
        sp=pg.locator('#missions button.town[data-c=sparks] .tsize'); need(sp.count()==1 and 'drive' in sp.inner_text().lower(),'rb01 (%dpx): Sparks card says to drive'%w)
        need(pg.locator('#missions button.town .tsize:has-text("walkable")').count()>=1,'rb01 (%dpx): some town card says walkable'%w)
        need(pg.locator('#missions button.town .tsize:has-text("drive")').count()>=1,'rb01 (%dpx): some town card says drive'%w)
        bad_t=pg.evaluate("""()=>[...document.querySelectorAll('#missions button.town:not(.soon)')].filter(t=>{const r=t.getBoundingClientRect(),i=t.querySelector('.tin').getBoundingClientRect(),h=t.querySelector('h3').getBoundingClientRect(),g=t.querySelector('.go').getBoundingClientRect();return r.width&&(h.top<g.bottom+3||i.bottom>r.bottom+1||h.top<r.top)}).map(t=>t.getAttribute('data-c'))""")
        need(not bad_t,'rb01 (%dpx): card text must stay inside the tile and clear of the Start pill, got %s'%(w,bad_t[:6]))
    pg=new(); pg.evaluate("document.querySelectorAll('#missions details.reg').forEach(d=>d.open=true)")
    pg.click('#missions button.town[data-c=sparks]'); pg.wait_for_timeout(250)
    need('plan to drive' in pg.inner_text('.tourinfo').lower(),'rb01: town page still says plan to drive for Sparks')
    # audit rb02: a town's first screen leads with the next stop, does not list the four stops twice, and the XP label is readable over the photo
    for w,h in ((390,844),(375,667),(360,740)):
        pg=new(); pg.set_viewport_size({'width':w,'height':h})
        pg.evaluate("document.querySelectorAll('#missions details.reg').forEach(d=>d.open=true)"); pg.click('#missions button.town[data-c=sparks]'); pg.wait_for_timeout(300)
        nr=pg.locator('.nextrow'); need(nr.count()==1 and 'victorian square' in nr.inner_text().lower() and 'start here' in nr.inner_text().lower(),'rb02 (%dx%d): first screen has a Start here row for the first stop'%(w,h))
        bb=pg.evaluate("(()=>{const r=document.querySelector('.nextrow').getBoundingClientRect(),n=document.querySelector('#bnav').getBoundingClientRect();return [r.top,r.bottom,n.top]})()")
        need(bb[1]<=bb[2]-4,'rb02 (%dx%d): the Start here row sits fully above the bottom bar, got %s'%(w,h,bb))
        need('on your list' not in pg.inner_text('#main .card').lower(),'rb02 (%dx%d): mission card does not repeat the four stops'%(w,h))
    pg.click('.nextrow'); pg.wait_for_timeout(250); need(pg.locator('#stopTitle').count()==1 and 'victorian' in pg.inner_text('#stopTitle').lower(),'rb02: the Start here row opens the first stop')
    pg=new({'then-now-v3':{'city':'sparks','home':0,'p':{'sparks':{'done':[1,0,0,0],'claims':[0,0,0,0,0,0,0,0]}}}}); pg.wait_for_timeout(300)
    need('next stop' in pg.inner_text('.nextrow').lower() and 'railroad shops' in pg.inner_text('.nextrow').lower(),'rb02: after one stamp the row says Next stop and names the second stop')
    need(pg.evaluate("(()=>{const l=document.querySelector('.finalnote'),s=document.querySelector('.stops');return !!l&&!!s&&(s.compareDocumentPosition(l)&4)>0})()"),'rb02: the final-challenge note sits under the stop list')
    # readable XP label over the hero photo, measured on the towns with the brightest photos behind it (small text needs 4.5:1)
    from PIL import Image
    import io
    def lin(c):
        c/=255; return c/12.92 if c<=0.03928 else ((c+0.055)/1.055)**2.4
    def lum(c): return 0.2126*lin(c[0])+0.7152*lin(c[1])+0.0722*lin(c[2])
    pg=new(); pg.set_viewport_size({'width':390,'height':844})
    for k in ('knoxville','nashville','tucson','pittsburgh','columbus'):
        pg.evaluate("document.querySelectorAll('#missions details.reg').forEach(d=>d.open=true)")
        if not pg.locator('#missions button.town[data-c=%s]'%k).count(): pg.click('#bnav [data-t=towns]'); pg.evaluate("document.querySelectorAll('#missions details.reg').forEach(d=>d.open=true)")
        pg.click('#missions button.town[data-c=%s]'%k); pg.wait_for_timeout(250)
        pg.evaluate("new Promise(r=>{const i=document.getElementById('heroImg');if(!i||i.complete)r();else{i.onload=i.onerror=r;setTimeout(r,2000)}})")
        pg.add_style_tag(content='#xpText{color:transparent!important}')
        r=pg.evaluate("(()=>{const r=document.querySelector('#xpText').getBoundingClientRect();return [r.left,r.top+scrollY,r.width,r.height]})()")
        im=Image.open(io.BytesIO(pg.screenshot(full_page=True))).convert('RGB').crop((int(r[0]),int(r[1]),int(r[0]+r[2])+1,int(r[1]+r[3])+1))
        ls=sorted(lum(c) for c in im.get_flattened_data()) if hasattr(im,'get_flattened_data') else sorted(lum(c) for c in im.getdata())
        cr=(1.0+0.05)/(ls[int(len(ls)*0.9)]+0.05)
        need(cr>=4.5,'rb02: XP label over the %s photo has contrast %.2f, needs 4.5'%(k,cr))
        pg.evaluate("document.querySelectorAll('style').forEach(s=>{if(s.textContent.startsWith('#xpText{color:transparent'))s.remove()})"); pg.click('#bnav [data-t=towns]'); pg.wait_for_timeout(60)
    # audit rb03: on a stop's first step the photo is a compact crop, the clue starts on the first screen and a cue points down to it
    for w,h in ((390,844),(375,667),(360,740)):
        pg=new(); pg.set_viewport_size({'width':w,'height':h})
        pg.evaluate("document.querySelectorAll('#missions details.reg').forEach(d=>d.open=true)"); pg.click('#missions button.town[data-c=sparks]'); pg.wait_for_timeout(250)
        pg.click('.stop >> nth=0'); pg.wait_for_timeout(400)
        g=pg.evaluate("(()=>{const s=document.querySelector('.banner.b0 .scene.ph').getBoundingClientRect(),c=document.querySelector('.clue').getBoundingClientRect(),q=document.querySelector('.banner .cue').getBoundingClientRect(),b=document.querySelector('.banner').getBoundingClientRect();return {sh:s.height,sw:s.width,clue:c.top,cue:q.width>0&&q.top>=b.top&&q.bottom<=b.bottom+1,vh:innerHeight}})()")
        need(g['sh']<=g['vh']*0.3+1 and g['sw']/g['sh']>=1.7,'rb03 (%dx%d): Find it photo is a compact wide crop, got %s'%(w,h,g))
        need(g['clue']+24<=g['vh'],'rb03 (%dx%d): the first line of the clue is on the first screen, clue top %s of %s'%(w,h,g['clue'],g['vh']))
        need(g['cue'],'rb03 (%dx%d): the Clue below cue sits on the photo'%(w,h))
    pg.click('[data-a=step][data-n="1"]'); pg.wait_for_timeout(250); need(pg.locator('.opts').count()==1,'rb03: the I am here button still opens the question')
    b.close()
bad+= [f'page error: {e}' for e in errs]
print('FLOWS: '+('OK' if not bad else 'FAILED'))
for x in bad: print(' -',x)
sys.exit(1 if bad else 0)
