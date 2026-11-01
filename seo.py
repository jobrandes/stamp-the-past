"""Build crawlable web pages (one per town, one per stop, plus /places/) into site/.
Called by build.py. Everything comes from src/packs, so there is nothing to write by hand.
The game itself stays at /play (noindex)."""
import json,os,re,html
BASE='https://stampthepast.com'
E=lambda s:html.escape(str(s),quote=True)

def trunc(s,n):
    s=re.sub(r'\s+',' ',s).strip()
    if len(s)<=n: return s
    return s[:n-1].rsplit(' ',1)[0].rstrip(' ,;:.')+'…'

CSS='''
:root{--bg:#F3EFE6;--surface:#fff;--surface-2:#E8E2D4;--ink:#13202C;--muted:#55616B;--line:#CFC8B8;--accent:#1B58B8;--accent-ink:#fff;--gold:#E9A91A;--good:#1E7A4C;--bad:#B3322B;--warn:#9A5A08;--navy:#0F1F33;--navy-ink:#F3EFE6}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#0E1722;--surface:#16232F;--surface-2:#1D2D3B;--ink:#EEF1F4;--muted:#A5B1BC;--line:#2C3E4D;--accent:#7FB0F5;--accent-ink:#0E1722;--gold:#F2B83A;--good:#5FC38C;--bad:#F08077;--warn:#E4A24A;--navy:#08111B;--navy-ink:#EEF1F4;color-scheme:dark}}
:root[data-theme="dark"]{--bg:#0E1722;--surface:#16232F;--surface-2:#1D2D3B;--ink:#EEF1F4;--muted:#A5B1BC;--line:#2C3E4D;--accent:#7FB0F5;--accent-ink:#0E1722;--gold:#F2B83A;--good:#5FC38C;--bad:#F08077;--warn:#E4A24A;--navy:#08111B;--navy-ink:#EEF1F4;color-scheme:dark}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:400 17px/1.6 'Public Sans',system-ui,-apple-system,'Segoe UI',sans-serif;padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px));-webkit-text-size-adjust:100%}
.wrap{max-width:860px;margin:0 auto;padding-block:8px 48px}
h1,h2,h3{font-family:'Big Shoulders Display','Arial Narrow',Impact,sans-serif;text-transform:uppercase;line-height:1;margin:0;text-wrap:balance}
h1{font-size:clamp(38px,9vw,64px);letter-spacing:.005em}
h2{font-size:clamp(26px,5.5vw,34px);letter-spacing:.01em;margin-top:34px}
h3{font-size:22px;letter-spacing:.02em}
p{margin:12px 0 0}a{color:var(--accent)}
.mono{font:500 12px 'IBM Plex Mono',ui-monospace,Menlo,monospace;letter-spacing:.14em;text-transform:uppercase;color:var(--muted)}
.top{display:flex;align-items:center;justify-content:space-between;gap:12px;padding-block:16px;flex-wrap:wrap}
.mark{font:800 22px 'Big Shoulders Display','Arial Narrow',Impact,sans-serif;letter-spacing:.06em;text-transform:uppercase;color:var(--ink);text-decoration:none}
.crumbs{font:500 12px 'IBM Plex Mono',ui-monospace,Menlo,monospace;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);margin-top:4px}
.crumbs a{color:var(--muted)}
.btn{display:inline-flex;align-items:center;justify-content:center;min-height:48px;padding:0 24px;border-radius:12px;background:var(--accent);color:var(--accent-ink);font:700 18px 'Big Shoulders Display','Arial Narrow',Impact,sans-serif;letter-spacing:.05em;text-transform:uppercase;text-decoration:none}
.btn:hover{filter:brightness(1.08)}
.top .btn{min-height:40px;padding:0 18px;font-size:16px}
.cmp{max-width:620px;border:1px solid var(--line);border-radius:14px;background:var(--surface);padding:12px;margin-top:18px}
.box{position:relative;aspect-ratio:4/3;border-radius:8px;overflow:hidden;background:var(--surface-2)}
.box img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}
.box .t{opacity:0}
.row{display:flex;align-items:center;gap:10px;margin-top:10px}
.row span{font:600 12px 'IBM Plex Mono',ui-monospace,Menlo,monospace;letter-spacing:.1em;text-transform:uppercase;color:var(--muted)}
.row input{flex:1;min-width:0;height:36px;accent-color:var(--accent)}
.caps{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:12px}
.cap{font-size:14px;line-height:1.45;color:var(--muted);min-width:0}
.cap b{display:block;color:var(--ink);font-size:15px}
.cap small{display:block;margin-top:4px;font:500 11px/1.4 'IBM Plex Mono',ui-monospace,Menlo,monospace;overflow-wrap:anywhere}
.story p{font-size:18px}
.sens{margin:0 0 16px;padding:12px 16px;border-left:4px solid #b45309;border-radius:8px;background:rgba(120,120,120,.12);font-size:16px}.sens b{display:block;font-size:12px;letter-spacing:.06em;text-transform:uppercase}
.dyk{border-left:4px solid var(--gold);background:var(--surface-2);border-radius:0 10px 10px 0;padding:12px 16px;margin-top:20px}
.box2{border:1px solid var(--line);border-radius:12px;background:var(--surface);padding:14px 16px;margin-top:14px}
ul.fc{list-style:none;padding:0;margin:12px 0 0;display:grid;gap:10px}
ul.fc li{border:1px solid var(--line);border-radius:12px;background:var(--surface);padding:12px 14px}
.tag{display:inline-block;font:600 11px 'IBM Plex Mono',ui-monospace,Menlo,monospace;letter-spacing:.1em;text-transform:uppercase;border-radius:99px;padding:2px 10px;margin-right:8px;color:#fff}
.t0{background:var(--good)}.t1{background:var(--warn)}.t2{background:var(--bad)}
ul.src{padding-left:20px;margin:10px 0 0}ul.src li{margin-top:6px;overflow-wrap:anywhere}
.cta{margin-top:34px;background:var(--navy);color:var(--navy-ink);border-radius:16px;padding:24px 20px}
.cta h2{margin-top:0}.cta p{opacity:.92}.cta .btn{margin-top:16px}
.stops{list-style:none;padding:0;margin:14px 0 0;display:grid;grid-template-columns:1fr 1fr;gap:12px}
.stops a{display:block;border:1px solid var(--line);border-radius:12px;background:var(--surface);overflow:hidden;text-decoration:none;color:var(--ink);height:100%}
.stops img{display:block;width:100%;aspect-ratio:4/3;object-fit:cover;background:var(--surface-2)}
.stops span{display:block;padding:10px 12px}.stops b{display:block;font-size:16px}.stops small{color:var(--muted);font-size:13px}
ul.towns{list-style:none;padding:0;margin:12px 0 0;display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px 16px}
.note{font-size:14px;color:var(--muted);margin-top:22px}
form.tc label{display:block;font-weight:600;margin-top:20px}
form.tc .hint{display:block;font-weight:400;color:var(--muted);font-size:14px}
form.tc input[type=text],form.tc select,form.tc textarea{width:100%;margin-top:6px;padding:10px 12px;border:1px solid var(--line);border-radius:10px;background:var(--surface);color:var(--ink);font:inherit}
form.tc textarea{min-height:84px}
form.tc fieldset{border:0;padding:0;margin:22px 0 0}
form.tc legend{font-weight:600;padding:0}
form.tc .opt{display:flex;gap:10px;align-items:center;min-height:44px}
form.tc .opt input{width:20px;height:20px;accent-color:var(--accent)}
form.tc button{margin-top:26px;border:0;cursor:pointer}
.tasks{counter-reset:t;list-style:none;padding:0;margin:14px 0 0;display:grid;gap:10px}
.tasks li{counter-increment:t;border:1px solid var(--line);border-radius:12px;background:var(--surface);padding:12px 14px 12px 52px;position:relative}
.tasks li::before{content:counter(t);position:absolute;left:14px;top:10px;font:800 28px 'Big Shoulders Display','Arial Narrow',Impact,sans-serif;color:var(--accent)}
footer{border-top:1px solid var(--line);margin-top:40px;padding-top:18px;font:400 12px/1.7 'IBM Plex Mono',ui-monospace,Menlo,monospace;color:var(--muted)}
@media (max-width:640px){.caps,.stops{grid-template-columns:1fr}ul.towns{grid-template-columns:1fr 1fr}}
@media (max-width:380px){ul.towns{grid-template-columns:1fr}}
'''
FONTS='<link rel="stylesheet" href="/fonts/fonts.css">'
COUNTER='<script>try{if(/^(www\\.)?stampthepast\\.com$|\\.netlify\\.app$/.test(location.hostname)){var g=document.createElement("script");g.async=true;g.src="//gc.zgo.at/count.js";g.setAttribute("data-goatcounter","https://stampthepast.goatcounter.com/count");document.head.appendChild(g);}}catch(e){}</script>'

def page(path,title,desc,body,og=None,ld=None,canon=None,noindex=False):
    url=BASE+'/'+path
    h=['<!doctype html><html lang="en"><head><meta charset="utf-8">',
       '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">',
       COUNTER,('<meta name="robots" content="noindex">' if noindex else ''),'<title>%s</title>'%E(title),'<meta name="description" content="%s">'%E(desc),
       '<link rel="canonical" href="%s">'%url,'<meta name="theme-color" content="#0f1f33">',
       '<link rel="icon" href="/icon-192.png">','<link rel="apple-touch-icon" href="/apple-touch-icon.png">',
       '<meta property="og:type" content="article">','<meta property="og:site_name" content="Stamp the Past">',
       '<meta property="og:title" content="%s">'%E(title),'<meta property="og:description" content="%s">'%E(desc),
       '<meta property="og:url" content="%s">'%url]
    if og:
        h.append('<meta property="og:image" content="%s/photos/%s.jpg">'%(BASE,og)); h.append('<meta name="twitter:card" content="summary_large_image">')
    h.append(FONTS); h.append('<style>'+CSS+'</style>')
    if ld: h.append('<script type="application/ld+json">'+json.dumps(ld,ensure_ascii=False)+'</script>')
    h.append('</head><body><div class="wrap">')
    h.append('<div class="top"><a class="mark" href="/">Stamp the Past</a><a class="btn" href="/play">Play free</a></div>')
    h.append(body)
    h.append('<footer><p><a href="/daily/">Daily Fact or Fiction</a> · <a href="/places/">All places</a> · <a href="/privacy.html">Privacy</a> · <a href="/support.html">Support</a> · stampthepast@gmail.com</p><p>Made by a mom and her teenage son. Photos are public domain or freely licensed and credited above. Story text is written from the cited sources.</p></footer>')
    h.append('</div></body></html>')
    out=os.path.join(OUT,path)
    os.makedirs(os.path.dirname(out),exist_ok=True)
    open(out,'w').write(''.join(h))

def credit(ph):
    if not ph: return ''
    bits=['Photo: '+E(ph.get('by','Unknown author'))]
    lic=ph.get('lic','')
    if lic: bits.append('<a href="%s" target="_blank" rel="noopener">%s</a>'%(E(ph['lu']),E(lic)) if ph.get('lu') else E(lic))
    if ph.get('page'): bits.append('<a href="%s" target="_blank" rel="noopener">Source</a>'%E(ph['page']))
    if ph.get('note'): bits.append(E(ph['note']))
    return ' · '.join(bits)

def build(R,packs,order,tstate,tfull,common_ids=None):
    global OUT
    OUT=R+'site/'
    urls=[]
    n_stops=0
    for tid in order:
        p=packs[tid]; st=tstate.get(tid,''); stname=(tfull.get(st,'') if st and '/' not in st else '')
        tname=p['name']; place=tname+(', '+st if st and st!='DC' and '/' not in st and not re.search(r',\s*\S+$',tname) else '')
        stops=p['stops']
        # ---- town page ----
        cards=[]
        for s in stops:
            k=(s['now'].get('ph') or s['then'].get('ph') or {}).get('k')
            cards.append('<li><a href="/%s/%s/">%s<span><b>%s</b><small>%s</small></span></a></li>'%(tid,s['id'],
                '<img loading="lazy" width="640" height="480" alt="%s" src="/photos/%s.jpg">'%(E(s['name']+' today'),k) if k else '',E(s['name']),E(s['teaser'])))
        hero=next(((s['now'].get('ph') or s['then'].get('ph') or {}).get('k') for s in stops if (s['now'].get('ph') or s['then'].get('ph'))),None)
        body=('<div class="crumbs"><a href="/places/">Places</a> › %s</div><h1>%s: then and now</h1>'%(E(p.get('region','')),E(place))
              +'<p>%d real landmarks in %s, each with an old photo you can fade into today\'s view. %s</p>'%(len(stops),E(tname),E(trunc(p.get('mission',''),220)))
              +'<ul class="stops">'+''.join(cards)+'</ul>'
              +'<div class="cta"><h2>Walk it. Stamp it.</h2><p>Visit all %d stops in %s, answer what is in front of you, and earn the town\'s passport stamps. Free, no sign-up.</p><a class="btn" href="/play">Play %s</a></div>'%(len(stops),E(tname),E(tname))
              +'<p class="note">Written from sources; not yet walked on site unless a stop says otherwise.</p>')
        ld={"@context":"https://schema.org","@type":"CollectionPage","name":place+': then and now',"url":BASE+'/%s/'%tid}
        page(tid+'/index.html',f'{place}: historic landmarks then and now | Stamp the Past',
             f'{len(stops)} historic landmarks in {tname} with old photos vs today: '+', '.join(s['name'] for s in stops)+'.',body,hero,ld)
        urls.append('/%s/'%tid)
        # ---- stop pages ----
        for i,s in enumerate(stops):
            n_stops+=1
            th,nw=s['then'],s['now']; tph,nph=th.get('ph'),nw.get('ph')
            sl=''
            if tph and nph:
                sl=('<div class="cmp"><div class="box"><img alt="%s, %s" src="/photos/%s.jpg" width="640" height="480"><img class="t" id="t" alt="%s, %s" src="/photos/%s.jpg" width="640" height="480"></div>'
                    '<div class="row"><span>Now</span><input id="r" type="range" min="0" max="100" value="0" aria-label="Fade between now and then"><span>Then</span></div></div>'
                    %(E(s['name']),E(nw['yr']),nph['k'],E(s['name']),E(th['yr']),tph['k']))
                sl+='<script>(function(){var r=document.getElementById("r"),t=document.getElementById("t");r.addEventListener("input",function(){t.style.opacity=r.value/100})})()</script>'
            elif nph or tph:
                ph=nph or tph; sl='<div class="cmp"><div class="box"><img alt="%s" src="/photos/%s.jpg" width="640" height="480"></div></div>'%(E(s['name']),ph['k'])
            caps='<div class="caps"><div class="cap"><b>Then, %s</b>%s<small>%s</small></div><div class="cap"><b>Today, %s</b>%s<small>%s</small></div></div>'%(
                E(th['yr']),E(th['line']),credit(tph),E(nw['yr']),E(nw['line']),credit(nph))
            story=''.join('<p>%s</p>'%E(x) for x in s['story'])
            if s.get('sens'): story='<aside class="sens" role="note"><b>Sensitive history</b> '+E(s['sens'])+'</aside>'+story
            fcs=''
            if s.get('claims'):
                lab={0:'Solid',1:'Disputed',2:'Not true'}
                fcs='<h2>Fact or tall tale?</h2><ul class="fc">'+''.join('<li><span class="tag t%d">%s</span>%s<br><span style="color:var(--muted);font-size:15px">%s</span></li>'%(c['a'],lab[c['a']],E(c['t']),E(c['why'])) for c in s['claims'])+'</ul>'
            disp=('<div class="box2"><b>Historians argue about this.</b> %s</div>'%E(s['disputed'])) if s.get('disputed') else ''
            src='<h2>Sources</h2><ul class="src">'+''.join('<li><a href="%s" target="_blank" rel="noopener">%s</a></li>'%(E(x['u']),E(x['t'])) for x in s['sources'])+'</ul>'
            more=''
            if th.get('link'): more='<p class="note">More: <a href="%s" target="_blank" rel="noopener">%s</a></p>'%(E(th['link']['u']),E(th['link']['t']))
            others=''.join('<li><a href="/%s/%s/">%s</a></li>'%(tid,o['id'],E(o['name'])) for o in stops if o['id']!=s['id'])
            nxt=stops[(i+1)%len(stops)]
            body=('<div class="crumbs"><a href="/places/">Places</a> › <a href="/%s/">%s</a></div><h1>%s: then and now</h1>'%(tid,E(place),E(s['name']))
                  +'<p class="mono" style="margin-top:10px">%s vs %s · %s</p>'%(E(th['yr']),E(nw['yr']),E(place))
                  +sl+caps+'<h2>The story</h2><div class="story">'+story+'</div>'
                  +'<div class="dyk"><b>Did you know?</b> %s</div>'%E(s['fact'])+disp+fcs+src+more
                  +'<div class="cta"><h2>Stamp it in person</h2><p>Go there, answer the question that only someone standing at %s can answer, and add the stamp to your passport. Free, no sign-up.</p><a class="btn" href="/play">Play %s</a></div>'%(E(s['name']),E(tname))
                  +'<h2>More in %s</h2><ul class="src">%s</ul><p class="note">Next: <a href="/%s/%s/">%s</a>. Written from the cited sources, not yet walked on site unless noted.</p>'%(E(tname),others,tid,nxt['id'],E(nxt['name'])))
            ld=[{"@context":"https://schema.org","@type":"Article","headline":f"{s['name']}: then and now","description":trunc(s['story'][0],200),
                 "image":[BASE+'/photos/%s.jpg'%k for k in [(nph or {}).get('k'),(tph or {}).get('k')] if k],
                 "author":{"@type":"Organization","name":"Stamp the Past"},"mainEntityOfPage":BASE+'/%s/%s/'%(tid,s['id'])},
                {"@context":"https://schema.org","@type":"BreadcrumbList","itemListElement":[
                 {"@type":"ListItem","position":1,"name":"Places","item":BASE+'/places/'},
                 {"@type":"ListItem","position":2,"name":place,"item":BASE+'/%s/'%tid},
                 {"@type":"ListItem","position":3,"name":s['name'],"item":BASE+'/%s/%s/'%(tid,s['id'])}]}]
            if s.get('geo'):
                ld.append({"@context":"https://schema.org","@type":"Place","name":s['name'],"geo":{"@type":"GeoCoordinates","latitude":s['geo'][0],"longitude":s['geo'][1]}})
            page(f'{tid}/{s["id"]}/index.html',next((c for c in (f"{s['name']}, {place}: then and now",f"{s['name']}, {tname}: then and now",f"{s['name']}: then and now") if len(c)<=58),f"{s['name']}, {tname}")+' | Stamp the Past',
                 trunc(f"{s['name']} in {place}, {th['yr']} versus today. "+s['story'][0],158),body,(nph or tph or {}).get('k'),ld)
            urls.append('/%s/%s/'%(tid,s['id']))
    # ---- index of all places ----
    regs={}
    for tid in order: regs.setdefault(packs[tid].get('region','Other'),[]).append(tid)
    b='<h1>All places</h1><p>%d towns, %d landmarks, each with an old photo and a modern one. Pick a town.</p>'%(len(order),n_stops)
    for r,ids in regs.items():
        b+='<h2>%s</h2><ul class="towns">'%E(r)+''.join('<li><a href="/%s/">%s</a></li>'%(t,E(packs[t]['name'])) for t in ids)+'</ul>'
    page('places/index.html','All places: historic landmarks then and now | Stamp the Past',f'{len(order)} US towns and {n_stops} historic landmarks with then-and-now photos, sourced stories and fact checks.',b)
    urls.append('/places/')
    return urls


def test_pages(R):
    global OUT
    OUT=R+'site/'
    def radio(name,opts):
        return ''.join('<label class="opt"><input type="radio" name="%s" value="%s" required> %s</label>'%(name,E(o),E(o)) for o in opts)
    def task(n,text):
        return '<fieldset><legend>%s</legend>%s</fieldset>'%(E(text),radio('task%d'%n,['Yes, easily','Yes, but it took effort','No, I gave up or got stuck',"I didn't try this"]))
    body=('<h1>Help test Stamp the Past</h1>'
      '<p>Stamp the Past is a free history game. You go to real landmarks, answer a question about what is in front of you, sort fact from tall tale, and fade between an old photo and today\'s view. Nothing to download and no sign-up. This takes about 10 minutes.</p>'
      '<p><b>Honest criticism is what I need.</b> If something is confusing or boring, say so. You can stop at any step and tell me why.</p>'
      '<h2>Try this first</h2><p>Open <a href="/play" target="_blank" rel="noopener">stampthepast.com/play</a> in a new tab. I will not tell you where to tap, because working that out is the test.</p>'
      '<ol class="tasks"><li>Look at the first screen for about 30 seconds. What do you think this is?</li>'
      '<li>Pick any town that looks interesting and try to earn your first stamp. If you are not at the landmark, tap the button that lets you check in anyway; I am testing the screens, not your location.</li>'
      '<li>Find your passport and see what it shows.</li>'
      '<li>Open any then-and-now photo and try the slider.</li></ol>'
      '<form class="tc" name="testcard" method="POST" action="/test-thanks.html" data-netlify="true" netlify-honeypot="bot-field">'
      '<input type="hidden" name="form-name" value="testcard"><p hidden><label>Leave empty <input name="bot-field"></label></p>'
      '<h2>About your device</h2>'
      '<label for="device">What did you use?</label><select id="device" name="device" required><option value="">Choose one</option><option>iPhone</option><option>Android phone</option><option>iPad or tablet</option><option>Windows computer</option><option>Mac</option><option>Other</option></select>'
      '<label for="browser">Which browser? <span class="hint">Safari, Chrome, Edge, Firefox... or "not sure"</span></label><input type="text" id="browser" name="browser" maxlength="60">'
      '<h2>What happened</h2>'
      '<label for="expect">Before you tried it, what did you expect this to be?</label><textarea id="expect" name="expected" maxlength="600"></textarea>'
      +task(1,'Task 1: Could you tell what the app is after the first screen?')+task(2,'Task 2: Could you earn your first stamp?')+task(3,'Task 3: Could you find your passport?')+task(4,'Task 4: Could you use the then-and-now slider?')+
      '<label for="conf">What, if anything, was confusing? <span class="hint">Where did you hesitate or tap the wrong thing?</span></label><textarea id="conf" name="confusing" maxlength="800"></textarea>'
      '<label for="tech">Did anything break or look wrong? <span class="hint">A photo that did not load, a button that did nothing, text cut off.</span></label><textarea id="tech" name="technical" maxlength="800"></textarea>'
      '<h2>What you thought</h2>'
      '<label for="fav">What was the best part, if any?</label><textarea id="fav" name="favorite" maxlength="600"></textarea>'
      '<label for="least">What was the weakest part?</label><textarea id="least" name="least" maxlength="600"></textarea>'
      '<fieldset><legend>Would you use it again?</legend>'+radio('again',['Yes','Maybe','No'])+'</fieldset>'
      '<fieldset><legend>Would you pass it to someone else?</legend>'+radio('recommend',['Yes','Maybe','No'])+'</fieldset>'
      '<label for="more">What would make it more worth your time?</label><textarea id="more" name="more_value" maxlength="600"></textarea>'
      '<fieldset><legend>Which would you prefer?</legend>'+radio('format',['A website','A web app saved to my home screen','A native iPhone app',"Not sure"])+'</fieldset>'
      '<label for="why">Why? <span class="hint">Optional</span></label><textarea id="why" name="why" maxlength="400"></textarea>'
      '<p class="note">No name or email is collected. Answers go to the two people who made the app.</p>'
      '<button class="btn" type="submit">Send my answers</button></form>')
    page('test.html','Help test Stamp the Past','A 10-minute written test of a free history game. Honest criticism welcome. No sign-up.',body,noindex=True)
    page('test-thanks.html','Thank you | Stamp the Past','Thanks for testing.','<h1>Thank you</h1><p>Your answers are in. Every comment gets read, and the repeated ones decide what gets fixed first.</p><p><a class="btn" href="/play">Keep playing</a></p>',noindex=True)


DAILY_JS=r"""
(function(){
var C=__CLAIMS__, N=C.length;
function rng(a){return function(){a|=0;a=a+0x6D2B79F5|0;var t=Math.imul(a^a>>>15,1|a);t=t+Math.imul(t^t>>>7,61|t)^t;return((t^t>>>14)>>>0)/4294967296}}
var idx=[];for(var i=0;i<N;i++)idx.push(i);var r=rng(20261030);for(var j=N-1;j>0;j--){var k=Math.floor(r()*(j+1));var x=idx[j];idx[j]=idx[k];idx[k]=x}
var now=new Date(), ds=now.getFullYear()+'-'+('0'+(now.getMonth()+1)).slice(-2)+'-'+('0'+now.getDate()).slice(-2);
var day=Math.floor((Date.UTC(now.getFullYear(),now.getMonth(),now.getDate())-Date.UTC(2026,10,1))/864e5);
var num=day+1; if(num<1) num=1;
var c=C[idx[((day%N)+N)%N]];
var LAB=['Solid','Disputed','Not true'], EXPL=['Solid: sources agree.','Disputed: sources disagree, or it is not settled.','Not true: it is a myth or an error.'];
var $=function(id){return document.getElementById(id)};
$('num').textContent='#'+num;
$('claim').textContent=c.t;
$('ctx').textContent='About '+c.s+' in '+c.p;
function get(k){try{return JSON.parse(localStorage.getItem(k)||'null')}catch(e){return null}}
function put(k,v){try{localStorage.setItem(k,JSON.stringify(v))}catch(e){}}
function ping(){try{if(window.goatcounter&&window.goatcounter.count)window.goatcounter.count({path:'event/daily-played',title:'daily-played',event:true})}catch(e){}}
function reveal(pick,fresh){
  var ok=pick===c.a;
  $('btns').hidden=true; $('res').hidden=false;
  $('verdict').textContent=ok?'You got it.':'Not quite.';
  $('verdict').className=ok?'dv good':'dv bad';
  $('answer').innerHTML='<span class="tag t'+c.a+'">'+LAB[c.a]+'</span> '+EXPL[c.a];
  $('why').textContent=c.w;
  var h='';for(var i=0;i<c.src.length;i++){h+='<li><a href="'+c.src[i].u+'" target="_blank" rel="noopener">'+c.src[i].t.replace(/</g,'&lt;')+'</a></li>'}
  $('src').innerHTML=h;
  $('more').href=c.u; $('more').textContent='See '+c.s+' then and now';
  var st=get('stp-daily-streak')||{n:0,last:''};
  if(fresh){
    var y=new Date(now.getTime()-864e5), ys=y.getFullYear()+'-'+('0'+(y.getMonth()+1)).slice(-2)+'-'+('0'+y.getDate()).slice(-2);
    if(st.last!==ds){ st.n=(st.last===ys)?st.n+1:1; st.last=ds; put('stp-daily-streak',st); }
    put('stp-daily',{d:ds,p:pick}); ping();
  }
  $('streak').textContent=st.n>1?(st.n+' days in a row'):'Come back tomorrow for a new one.';
  var txt='Stamp the Past, Fact or Fiction '+'#'+num+': '+(ok?'got it ✅':'fooled ❌')+(st.n>1?' · '+st.n+' day streak':'')+'\nstampthepast.com/daily/';
  $('share').onclick=function(){
    if(navigator.share){navigator.share({text:txt}).catch(function(){})}
    else if(navigator.clipboard){navigator.clipboard.writeText(txt).then(function(){$('shmsg').textContent='Copied. Paste it anywhere.'},function(){$('shmsg').textContent=txt})}
    else{$('shmsg').textContent=txt}
  };
}
var saved=get('stp-daily');
if(saved&&saved.d===ds){reveal(saved.p,false)}
var bs=document.querySelectorAll('#btns button');
for(var b=0;b<bs.length;b++){bs[b].addEventListener('click',function(e){reveal(+e.currentTarget.getAttribute('data-p'),true)})}
})();
"""

def daily_page(R,packs,order,tstate):
    global OUT
    OUT=R+'site/'
    claims=[]
    for tid in order:
        p=packs[tid]; st=tstate.get(tid,''); tn=p['name']
        place=tn+(', '+st if st and st!='DC' and '/' not in st and not re.search(r',\s*\S+$',tn) else '')
        for s in p['stops']:
            for c in s.get('claims',[]):
                claims.append({'t':c['t'],'a':c['a'],'w':c['why'],'s':s['name'],'p':place,'u':'/%s/%s/'%(tid,s['id']),
                               'src':[{'t':x['t'],'u':x['u']} for x in s['sources'][:2]]})
    data=json.dumps(claims,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')
    body=('<div class="crumbs"><a href="/places/">Places</a> › Daily</div>'
      '<h1>Fact or Fiction <span id="num"></span></h1>'
      '<p>One claim a day about a real place. Is it solid, disputed, or a tall tale? Everyone gets the same one. No sign-up, nothing to download.</p>'
      '<div class="dcard"><p class="mono" id="ctx"></p><p class="dclaim" id="claim"></p>'
      '<div id="btns" class="dbtns"><button data-p="0">Solid</button><button data-p="1">Disputed</button><button data-p="2">Not true</button></div>'
      '<div id="res" hidden><p id="verdict" class="dv"></p><p id="answer"></p><p id="why"></p><h2>Sources</h2><ul class="src" id="src"></ul>'
      '<p><a id="more" href="/">More</a></p>'
      '<p><button class="btn" id="share" type="button">Share my result</button></p><p class="note" id="shmsg" role="status"></p><p class="note" id="streak"></p></div></div>'
      '<p class="note"><b>Solid</b> means the sources agree. <b>Disputed</b> means they disagree or it is not settled. <b>Not true</b> means it is a myth or an error. Every answer shows its sources, so check us.</p>'
      '<div class="cta"><h2>Want the real thing?</h2><p>Go to the place, answer a question about what is in front of you, and fade between the old photo and today\'s. Free, no sign-up.</p><a class="btn" href="/play">Play Stamp the Past</a></div>'
      '<script>'+DAILY_JS.replace('__CLAIMS__',data)+'</script>')
    css_extra='<style>.dcard{border:1px solid var(--line);border-radius:14px;background:var(--surface);padding:18px;margin-top:18px}.dclaim{font:700 clamp(24px,5.5vw,32px)/1.2 \'Big Shoulders Display\',\'Arial Narrow\',Impact,sans-serif;margin:8px 0 16px}.dbtns{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}.dbtns[hidden]{display:none}.dbtns button{min-height:56px;border:2px solid var(--line);border-radius:12px;background:var(--surface);color:var(--ink);font:700 18px \'Big Shoulders Display\',\'Arial Narrow\',Impact,sans-serif;letter-spacing:.04em;text-transform:uppercase;cursor:pointer}.dbtns button:hover,.dbtns button:focus-visible{border-color:var(--accent)}.dv{font:800 30px \'Big Shoulders Display\',\'Arial Narrow\',Impact,sans-serif;text-transform:uppercase;margin:0}.dv.good{color:var(--good)}.dv.bad{color:var(--bad)}@media (max-width:420px){.dbtns{grid-template-columns:1fr}}</style>'
    page('daily/index.html','Fact or Fiction: a daily history claim | Stamp the Past',
         'One claim a day about a real place. Is it solid, disputed or a tall tale? Play free, see the sources, share your result.',body.replace('<h1>',css_extra+'<h1>',1),None)
    return '/daily/'
