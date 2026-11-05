#!/usr/bin/env python3
"""Community places (test branch): build town packs from src/community/places/*.json and check them.
   python3 tools/community.py check   -> validate every place file"""
import json,os,re,sys,glob,math
R=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))+'/'
RANK_NAMES=['Newcomer','Visitor','Local Guide','Regular']
def slug(s): return re.sub(r'[^a-z0-9]+','-',s.lower()).strip('-')
def load_places(R=R,d=None):
    d=d or R+'src/community/places/'
    out=[]
    for f in sorted(glob.glob(d+'*.json')):
        out.append((os.path.basename(f),json.load(open(f))))
    return out
def load_stories(R=R,d=None):
    d=d or R+'src/community/stories/'
    return [(os.path.basename(f),json.load(open(f))) for f in sorted(glob.glob(d+'*.json'))]
def build(R=R,places_dir=None,declined_file=None,stories_dir=None):
    """Return (packs, photos, status). Every town with at least one place becomes one pack, any number of stops."""
    towns={}
    for fn,p in load_places(R,places_dir):
        key=(p['town'],p.get('state',''))
        towns.setdefault(key,[]).append(p)
    packs=[];photos={}
    for (town,state),pl in sorted(towns.items(),key=lambda kv:kv[0][0].lower()):
        pl.sort(key=lambda p:(p.get('seq',0),p.get('sub','')))  # seq only ever grows, so saved stamps never shift
        n=len(pl); mx=125*n
        thr=[0]+[round(mx*r/600) for r in (100,250,450,600)]
        stops=[]
        for i,p in enumerate(pl):
            st=json.loads(json.dumps(p['stop'])); st['tag']=f'Stop {i+1} of {n}'; st['community']=True
            if p.get('by'): st['by']=p['by']
            stops.append(st)
            for era in ('then','now'):
                ph=(st.get(era) or {}).get('ph')
                if ph: photos[ph['k']]='/api/community/photo/'+ph['k'][3:]
        first=stops[0]; hk=first['now']['ph']['k']
        nm=town
        initials=(re.findall(r'[A-Za-z]',town)[:2] or ['C','M']); initials=''.join(initials).upper().ljust(2,'X')
        pid='c_'+slug(town+'-'+state if state else town)
        hp=first['now']['ph']
        packs.append({
          'id':pid,'name':nm,'explorer':nm+' Explorer','initials':initials,'community':True,
          'ranks':[[thr[i],RANK_NAMES[i]] for i in range(4)]+[[thr[4],nm+' Historian']],
          'heroKey':hk,'heroAlt':first['now'].get('label') or first['name'],'heroLi':'',
          'heroCredit':'Photo: '+hp.get('by','')+' · '+hp.get('lic',''),
          'mission':f'Community-added places in {nm}. Visit each one, check in to earn its badge and unlock its story. Each place was suggested by a contributor and researched from sources, and none has been walked yet. Everything stays on this phone.',
          'afterDone':f'All {n} badges earned. {nm} is stamped.','safetyNote':'<li>Stay on public paths and sidewalks.</li>',
          'badgeMap':{st['id']:[st['now']['ph']['k'],'50% 50%'] for st in stops},
          'level':'Community','region':'Community-added','state':state,'added':max(p.get('added','') for p in pl),'stops':stops})
    # Story stops: places with a recent photo only. They become a "tour" per town, shown under Nearby stops / Explore history.
    tours={}
    for fn,p in load_stories(R,stories_dir):
        tid='c_'+slug(p['town']+'-'+p['state'] if p.get('state') else p['town'])
        sp=json.loads(json.dumps(p['stop'])); sp['town']=tid; sp['community']=True
        if p.get('by'): sp['by']=p['by']
        t=tours.setdefault(tid,{'id':tid,'name':p['town'],'towns':[tid] if tid in {x['id'] for x in packs} else [],'community':True,'state':p.get('state',''),'stops':[]})
        t['stops'].append(sp)
        ph=sp.get('ph')
        if ph: photos[ph['k']]='/api/community/photo/'+ph['k'][3:]
        for m in sp.get('more') or []:
            if m.get('k'): photos[m['k']]='/api/community/photo/'+m['k'][3:]
    mf=R+'src/community/merged.json'  # add-photo submissions the agent has merged into an existing place's `more`
    merged=json.load(open(mf)) if os.path.exists(mf) else []
    added=sorted({p['sub'] for _,p in load_places(R,places_dir)}|{p['sub'] for _,p in load_stories(R,stories_dir)}|set(merged))
    df=declined_file or R+'src/community/declined.json'
    declined=json.load(open(df)) if os.path.exists(df) else {}
    wf=R+'src/community/waiting.json'
    waiting=json.load(open(wf)) if os.path.exists(wf) else {}
    dpf=R+'src/community/declined-photos.json'
    dphotos=json.load(open(dpf)) if os.path.exists(dpf) else []
    return packs,photos,{'added':added,'declined':declined,'waiting':waiting,'declinedPhotos':dphotos},list(tours.values())
def check(R=R,places_dir=None):
    bad=[]
    def need(c,m):
        if not c: bad.append(m)
    seen=set()
    for fn,p in load_places(R,places_dir):
        w=fn
        for f in ('sub','town','added','stop'): need(p.get(f),f'{w}: missing {f}')
        need(isinstance(p.get('seq'),int) and p['seq']>=1,f'{w}: seq (1, 2, 3 ... per town, never reused) is required')
        sq=(p.get('town'),p.get('state',''),p.get('seq')); need(sq not in seen,f'{w}: duplicate seq in town'); seen.add(sq)
        if not p.get('stop'): continue
        need(re.fullmatch(r'[a-f0-9]{8}',p.get('sub','')),f'{w}: sub must be the 8-hex submission id')
        need(fn==p.get('sub','')+'.json',f'{w}: file name must be <sub>.json')
        need(p.get('by') is None or (isinstance(p['by'],str) and 0<len(p['by'])<=30 and not re.search(r'[<>&"]',p['by'])),f'{w}: by (nickname credit) must be 1-30 plain characters')
        st=p['stop']
        for f in ('id','name','short','badge','teaser','map','clue','safety','field','fact'): need(st.get(f),f'{w}: missing {f}')
        need((p['town'],st.get('id')) not in seen,f'{w}: duplicate stop id in town'); seen.add((p['town'],st.get('id')))
        need(str(st.get('field','')).startswith('Community-added'),f'{w}: field must start with "Community-added"')
        q=st.get('q') or {}
        need(2<=len(q.get('options',[]))<=4 and 0<=q.get('answer',-1)<len(q.get('options',[])),f'{w}: bad question')
        if q.get('options'): need(len(set(q['options']))==len(q['options']),f'{w}: duplicate options'); need(q.get('hint') and q['hint'] not in q['options'][q['answer']] and q['options'][q['answer']].lower() not in q['hint'].lower(),f'{w}: hint gives the answer away')
        need(len(st.get('claims',[]))==2 and all(c.get('a') in (0,1,2) and c.get('t') and c.get('why') for c in st.get('claims',[])),f'{w}: exactly 2 valid claims')
        need(len(st.get('story',[]))>=2,f'{w}: story needs 2+ paragraphs')
        src=st.get('sources',[]); need(len(src)>=2 and all(str(s.get('u','')).startswith('https://') and s.get('t') for s in src),f'{w}: 2+ https sources')
        g=st.get('geo'); need(g is None or (len(g)==3 and -90<=g[0]<=90 and -180<=g[1]<=180 and 50<=g[2]<=1500),f'{w}: bad geo')
        for era in ('then','now'):
            e=st.get(era) or {}; ph=e.get('ph') or {}
            need(ph.get('k')==f'cm_{p.get("sub")}_{era[0]}',f'{w}: {era} photo key must be cm_<sub>_{era[0]}')
            need(ph.get('by') and ph.get('lic') in ('Public domain','CC0','CC BY','CC BY-SA') and ph.get('page','').startswith('https://'),f'{w}: {era} photo credit, license and https page are required')
            need(e.get('yr') and e.get('label') and e.get('line'),f'{w}: {era} needs yr, label, line')
        need(((st.get('then') or {}).get('link') or {}).get('u','').startswith('https://'),f'{w}: then.link required')
        c=st.get('card') or {}; need(all(c.get(k) for k in ('a','b','la','lb')),f'{w}: card incomplete')
        if st.get('spot'):
            s=st['spot']; need(len(set(s.get('options',[])))==4 and 0<=s.get('answer',-1)<4 and s.get('why'),f'{w}: bad spot puzzle')
    for fn,p in load_stories(R):
        w='stories/'+fn
        for f in ('sub','town','added','stop'): need(p.get(f),f'{w}: missing {f}')
        if not p.get('stop'): continue
        need(re.fullmatch(r'[a-f0-9]{8}',p.get('sub','')) and fn==p['sub']+'.json',f'{w}: file name must be <sub>.json')
        need(p.get('by') is None or (isinstance(p['by'],str) and 0<len(p['by'])<=30 and not re.search(r'[<>&"]',p['by'])),f'{w}: by (nickname credit) must be 1-30 plain characters')
        st=p['stop']
        for f in ('id','name','area','addr','invite','access'): need(st.get(f),f'{w}: missing {f}')
        g=st.get('geo'); need(isinstance(g,list) and len(g)==3 and -90<=g[0]<=90 and -180<=g[1]<=180 and 50<=g[2]<=1000,f'{w}: geo [lat, lon, radius 50..1000] required')
        need(isinstance(st.get('story'),list) and len(st['story'])>=2,f'{w}: story needs 2+ paragraphs')
        need(len(st.get('access',''))>=40,f'{w}: access note must be specific')
        srcs=st.get('sources') or []
        need(len(srcs)>=2 and all(x.get('t') and str(x.get('u','')).startswith('https://') for x in srcs),f'{w}: 2+ https sources')
        fa=st.get('facts') or []; used=set()
        need(len(fa)>=3,f'{w}: list 3+ facts with source indexes')
        for x in fa:
            need(x.get('t') and x.get('src') and all(isinstance(i,int) and 0<=i<len(srcs) for i in x['src']),f'{w}: every fact needs valid src indexes'); used|=set(x.get('src') or [])
        need(used==set(range(len(srcs))),f'{w}: every source must support a fact')
        mo=st.get('more') or []
        need(isinstance(mo,list) and len(mo)<=4,f'{w}: at most 4 extra photos in "more" (5 photos in all)')
        for m in mo if isinstance(mo,list) else []:
            need(re.fullmatch(r'cm_[a-f0-9]{8}_[a-z0-9]+',str(m.get('k',''))) and m.get('by') and m.get('lic') and str(m.get('page','')).startswith('https://'),f'{w}: each extra photo needs k (cm_<id>_<n>), by, lic and an https page')
        ph=st.get('ph') or {}
        need(ph.get('k')==f'cm_{p.get("sub")}_n' and ph.get('by') and ph.get('lic') and ph.get('page','').startswith('https://') and ph.get('lu'),f'{w}: now photo key cm_<sub>_n with by, lic, lu, page required')
        need(st.get('sens') is None or isinstance(st['sens'],str),f'{w}: sens must be text')
    bad+=check_approvals(load_rules(R),load_approvals(R),load_stories(R),official_stops(R),jload(R+'src/community/declined.json',{}),jload(R+'src/community/merged.json',[]),jload(R+'src/community/declined-photos.json',[]))
    return bad

# ---------- approval rules (src/community/rules.json) and the approval log (approvals.json) ----------
ALLOWED_LIC=('Public domain','CC0','CC BY','CC BY-SA','CC BY-SA 4.0')
MAX_PER_DAY=5; DUP_M=150
def jload(f,default):
    return json.load(open(f)) if os.path.exists(f) else default
def load_rules(R=R): return jload(R+'src/community/rules.json',{'rules':[]})
def load_approvals(R=R): return jload(R+'src/community/approvals.json',{})
STOP_WORDS={'the','of','a','an','and','at','in','historic','old'}
def ntoks(s): return frozenset(w for w in re.findall(r'[a-z0-9]+',(s or '').lower()) if w not in STOP_WORDS)
def metres(a,b):
    la1,lo1,la2,lo2=map(math.radians,(a[0],a[1],b[0],b[1])); d=math.sin((la2-la1)/2)**2+math.cos(la1)*math.cos(la2)*math.sin((lo2-lo1)/2)**2
    return 2*6371000*math.asin(math.sqrt(d))
def official_stops(R=R):
    """Every official stop (packs and tours) with name and geo, used for the duplicate rule."""
    out=[]
    for f in glob.glob(R+'src/packs/*.json'):
        d=json.load(open(f))
        if not isinstance(d,dict) or 'stops' not in d: continue
        for sp in d['stops']: out.append({'n':sp.get('name',''),'t':d.get('name',''),'g':sp.get('geo')})
    for f in glob.glob(R+'src/tours/*.json'):
        d=json.load(open(f))
        for t in (d if isinstance(d,list) else [d]):
            if isinstance(t,dict):
                for sp in t.get('stops',[]): out.append({'n':sp.get('name',''),'t':t.get('name',''),'g':sp.get('geo')})
    return out
def stop_texts(st):
    t=[st.get('name',''),st.get('area',''),st.get('invite',''),st.get('access',''),st.get('sens') or '']+list(st.get('story') or [])+[x.get('t','') for x in st.get('facts') or []]
    return [x for x in t if isinstance(x,str)]
def text_problems(st):
    bad=[]
    for x in stop_texts(st):
        if re.search(r'[<>]',x): bad.append('contains < or >')
        if re.search(r'[\w.+-]+@[\w-]+\.[\w.]+',x): bad.append('contains an email address')
        if re.search(r'(?<!\d)\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}(?!\d)',x): bad.append('contains a phone number')
        if re.search(r'https?://|www\.',x,re.I): bad.append('contains a web link')
    return sorted(set(bad))
def rules_for(rules,kind): return [r['id'] for r in rules['rules'] if kind in r.get('for',[])]
def check_approvals(rules,approvals,stories,official,declined,merged,dphotos):
    """Pure check of the approval log against the rules. stories = [(filename, story file dict)]."""
    bad=[]
    def need(c,m):
        if not c: bad.append(m)
    ids={r['id'] for r in rules['rules']}
    by_day={}
    for sub,a in approvals.items():
        w='approvals/'+sub
        need(re.fullmatch(r'[a-f0-9]{8}',sub),f'{w}: id must be 8 hex')
        need(a.get('kind') in ('place','photo','correction'),f'{w}: kind must be place, photo or correction')
        need(a.get('decision') in ('added','declined','needs-owner','waiting','removed'),f'{w}: bad decision')
        need(re.fullmatch(r'\d{4}-\d\d-\d\d',str(a.get('on',''))) and a.get('place'),f'{w}: on (date) and place are required')
        for k,v in (a.get('rules') or {}).items():
            need(k in ids,f'{w}: unknown rule {k}'); need(isinstance(v,str) and (v=='pass' or v.startswith('na: ') or v.startswith('fail: ')),f'{w}: rule {k} must be "pass", "na: why" or "fail: why"')
        if a.get('decision')=='added':
            by_day[a['on']]=by_day.get(a['on'],0)+1
            if a.get('legacy'):
                need(a.get('notes'),f'{w}: a legacy record needs a note')
            else:
                for rid in rules_for(rules,a.get('kind')):
                    v=(a.get('rules') or {}).get(rid); need(v is not None and not str(v).startswith('fail'),f'{w}: rule {rid} must be recorded as pass (or "na: why")')
                for ph in a.get('photos') or []:
                    need(ph.get('verdict') in ('used','held back') and ph.get('k'),f'{w}: each photo needs k and verdict')
                    if ph.get('verdict')=='held back': need(ph['k'][3:] in dphotos and ph.get('why'),f'{w}: held-back photo {ph.get("k")} must be in declined-photos.json with a reason')
        elif a.get('decision') in ('declined','needs-owner'):
            need(a.get('notes') or a.get('rules'),f'{w}: say why')
    for d,n in by_day.items():
        need(n<=MAX_PER_DAY,f'{d}: {n} places added in one day, the limit is {MAX_PER_DAY}')
    for sub in declined: need(sub in approvals and approvals[sub].get('decision') in ('declined','removed'),f'declined.json {sub}: needs a declined/removed record in approvals.json')
    for sub in merged: need(sub in approvals and approvals[sub].get('kind') in ('photo','correction') and approvals[sub].get('decision')=='added',f'merged.json {sub}: needs a photo/correction record in approvals.json')
    seen=[]
    for fn,p in stories:
        w='stories/'+fn; sub=p.get('sub'); st=p.get('stop') or {}
        a=approvals.get(sub)
        need(a is not None and a.get('kind')=='place' and a.get('decision')=='added',f'{w}: no "added" approval record in approvals.json (every published place needs one)')
        if a and not a.get('legacy'):
            keys=[(st.get('ph') or {}).get('k')]+[m.get('k') for m in st.get('more') or []]
            used={x.get('k') for x in a.get('photos') or [] if x.get('verdict')=='used'}
            need(all(k in used for k in keys if k),f'{w}: every published photo must be listed as "used" in its approval record')
        for pk in [(st.get('ph') or {})]+list(st.get('more') or []):
            need(pk.get('lic') in ALLOWED_LIC,f'{w}: photo licence {pk.get("lic")} is not an allowed one')
        for t in text_problems(st): need(False,f'{w}: text {t}')
        town=(p.get('town','').lower(),p.get('state','').lower()); nt=ntoks(st.get('name',''))
        for o in seen:
            if o[0]==town: need(not(o[1]==nt or (nt and o[1] and len(nt&o[1])/len(nt|o[1])>=0.7)),f'{w}: duplicate of {o[2]} in the same town')
            g,og=st.get('geo'),o[3]
            if g and og: need(metres(g,og)>DUP_M,f'{w}: within {DUP_M} m of {o[2]}')
        seen.append((town,nt,st.get('name'),st.get('geo')))
        for o in official:
            if nt and ntoks(o['n'])==nt: need(bool(a and a.get('dup_ok_by')=='Jo-Anne'),f'{w}: same name as official stop {o["n"]} ({o["t"]}) - only Jo-Anne can allow it')
            g=st.get('geo')
            if g and o['g'] and metres(g,o['g'])<=DUP_M: need(bool(a and a.get('dup_ok_by')=='Jo-Anne'),f'{w}: within {DUP_M} m of the official stop {o["n"]} ({o["t"]}) - only Jo-Anne can allow it')
    return bad
def report(R=R):
    """Public report for the admin page: the rules and everything new (no personal data)."""
    rules=load_rules(R); ap=load_approvals(R); tid={}
    for fn,p in load_stories(R):
        tid[p['sub']]='/play.html#story='+'c_'+slug(p['town']+'-'+p['state'] if p.get('state') else p['town'])+':'+p['stop']['id']
    recs=[]
    for sub,a in ap.items():
        r={'id':sub}; r.update(a)
        if a.get('decision')=='added' and sub in tid: r['url']=tid[sub]
        recs.append(r)
    recs.sort(key=lambda r:(r.get('on',''),r['id']),reverse=True)
    c={'added':0,'declined':0,'needs-owner':0,'waiting':0,'removed':0,'recheck':0}
    for r in recs:
        c[r['decision']]=c.get(r['decision'],0)+1
        if r.get('legacy'): c['recheck']+=1
    return {'effective':rules.get('effective',''),'intro':rules.get('intro',''),'rules':rules['rules'],'records':recs,'counts':c}
if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='check':
        b=check(); print('community places:',len(load_places()),'places,',len(load_stories()),'stories;',len(b),'problems'); [print(' ',x) for x in b]; sys.exit(1 if b else 0)
