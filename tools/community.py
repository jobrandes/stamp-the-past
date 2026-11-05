#!/usr/bin/env python3
"""Community places (test branch): build town packs from src/community/places/*.json and check them.
   python3 tools/community.py check   -> validate every place file"""
import json,os,re,sys,glob
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
        t=tours.setdefault(tid,{'id':tid,'name':p['town'],'towns':[tid] if tid in {x['id'] for x in packs} else [],'community':True,'stops':[]})
        t['stops'].append(sp)
        ph=sp.get('ph')
        if ph: photos[ph['k']]='/api/community/photo/'+ph['k'][3:]
    added=sorted({p['sub'] for _,p in load_places(R,places_dir)}|{p['sub'] for _,p in load_stories(R,stories_dir)})
    df=declined_file or R+'src/community/declined.json'
    declined=json.load(open(df)) if os.path.exists(df) else {}
    wf=R+'src/community/waiting.json'
    waiting=json.load(open(wf)) if os.path.exists(wf) else {}
    return packs,photos,{'added':added,'declined':declined,'waiting':waiting},list(tours.values())
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
        ph=st.get('ph') or {}
        need(ph.get('k')==f'cm_{p.get("sub")}_n' and ph.get('by') and ph.get('lic') and ph.get('page','').startswith('https://') and ph.get('lu'),f'{w}: now photo key cm_<sub>_n with by, lic, lu, page required')
        need(st.get('sens') is None or isinstance(st['sens'],str),f'{w}: sens must be text')
    return bad
if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='check':
        b=check(); print('community places:',len(load_places()),'places,',len(load_stories()),'stories;',len(b),'problems'); [print(' ',x) for x in b]; sys.exit(1 if b else 0)
