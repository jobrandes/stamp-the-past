#!/usr/bin/env python3
"""Content checks for every town pack. Fails loudly instead of shipping a broken stop."""
import json,os,re,sys
R=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))+'/'
order=json.load(open(R+'src/packs/index.json'))['order']
photos=set(json.load(open(R+'src/photos/manifest.json')))
bad=[]
def need(c,msg):
    if not c: bad.append(msg)
for cid in order:
    p=json.load(open(R+f'src/packs/{cid}.json'))
    for f in ('id','name','explorer','initials','mission','afterDone','safetyNote'): need(p.get(f),f'{cid}: missing {f}')
    need(len(p['ranks'])==5 and p['ranks'][0][0]==0,f'{cid}: ranks must be 5 tiers starting at 0 XP')
    need([r[0] for r in p['ranks']]==[0,100,250,450,600],f'{cid}: rank thresholds must match the XP model (0,100,250,450,600)')
    need(len(p['stops'])==4,f'{cid}: the save code and XP model assume 4 stops')
    need(p.get('heroKey') is None or p['heroKey'] in photos,f'{cid}: heroKey not in photos')
    need(len({st['q']['answer'] for st in p['stops']})>=3,f'{cid}: correct answers should not sit in the same slot every time (use at least 3 different positions)')
    for st in p['stops']:
        w=f'{cid}/{st["id"]}'
        for f in ('id','name','short','badge','tag','teaser','map','clue','safety','field','fact'): need(st.get(f),f'{w}: missing {f}')
        if st.get('verified'):
            for f in ('on','by','note'): need(st['verified'].get(f),f'{w}: verified is missing {f}')
            need(__import__('re').match(r'^\d{4}-\d{2}-\d{2}$',st['verified'].get('on','')),f'{w}: verified.on must be YYYY-MM-DD')
        q=st['q']; need(2<=len(q['options'])<=4 and 0<=q['answer']<len(q['options']),f'{w}: bad question options/answer')
        need(len(set(q['options']))==len(q['options']),f'{w}: duplicate options')
        need(q.get('hint') and q['hint'] not in q['options'][q['answer']],f'{w}: hint missing or gives the answer away')
        need(len(st['claims'])==2,f'{w}: the XP model assumes 2 claims per stop')
        for c in st['claims']: need(c['a'] in (0,1,2) and c['t'] and c['why'],f'{w}: bad claim')
        need(len(st['story'])>=2,f'{w}: story too short')
        g=st.get('geo')
        if g is not None: need(isinstance(g,list) and len(g)==3 and -90<=g[0]<=90 and -180<=g[1]<=180 and 50<=g[2]<=1000,f'{w}: geo must be [lat, lon, radius_m 50..1000]')
        need(len(st['sources'])>=2 and all(s['u'].startswith('https://') for s in st['sources']),f'{w}: needs 2+ https sources')
        for era in ('then','now'):
            e=st[era]; need(e.get('yr') and e.get('label') and e.get('line'),f'{w}/{era}: missing text')
            ph=e.get('ph')
            if ph:
                need(ph['k'] in photos,f'{w}/{era}: photo file missing')
                for f in ('by','lic','lu','page'): need(ph.get(f),f'{w}/{era}: photo credit missing {f}')
                need(ph['page'].startswith('https://'),f'{w}/{era}: credit page must be https')
        if st['id'] in p['badgeMap']:  # no entry = plain letter badge until a free photo exists
            k,pos=p['badgeMap'][st['id']]; need(k in photos,f'{w}: badge photo missing')
            need(re.match(r'^\d+% \d+%$',pos),f'{w}: bad badge position')
# final challenge questions
import json as _j,os as _o
_b=_j.load(open(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)),'..','src','boss.json')))
_order=_j.load(open(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)),'..','src','packs','index.json')))['order']
for _k in _order:
    _q=_b.get(_k)
    if not _q or len(_q)!=4: bad.append(f'BOSS: {_k} needs exactly 4 questions'); continue
    if len({x['a'] for x in _q})<2: bad.append(f'BOSS: {_k} answers all in one slot')
    for x in _q:
        if len(x['o'])!=4 or len(set(x['o']))!=4 or not 0<=x['a']<4 or not x.get('why'): bad.append(f'BOSS: {_k} bad question')

# Story stops (src/tours/*.json): separate from town packs, never part of the 4-stop XP model
_td=os.path.join(R,'src','tours'); _nt=0
if os.path.isdir(_td):
    for _f in sorted(os.listdir(_td)):
        if not _f.endswith('.json'): continue
        _t=json.load(open(os.path.join(_td,_f))); _w0='tour '+_f
        need(_t.get('id') and _t.get('name'),_w0+': missing id/name')
        need(isinstance(_t.get('towns'),list) and all(x in order for x in _t['towns']),_w0+': towns must be existing town ids')
        _ids=set()
        for st in _t['stops']:
            _nt+=1; w=_w0+'/'+str(st.get('id'))
            need(st.get('id') and st['id'] not in _ids,w+': missing or duplicate id'); _ids.add(st.get('id'))
            for f in ('name','area','addr','invite','access'): need(st.get(f),w+': missing '+f)
            g=st.get('geo'); need(isinstance(g,list) and len(g)==3 and -90<=g[0]<=90 and -180<=g[1]<=180 and 50<=g[2]<=1000,w+': geo must be [lat, lon, radius_m 50..1000]')
            need(isinstance(st.get('story'),list) and len(st['story'])>=2 and all(isinstance(x,str) and x for x in st['story']),w+': story needs 2+ paragraphs')
            need(len(st.get('access',''))>=40,w+': access note must be specific, not a one-word placeholder')
            ac=st.get('access_check') or {}
            need(ac.get('on') and ac.get('by') and ac.get('how') and re.match(r'^\d{4}-\d{2}-\d{2}$',ac.get('on','')),w+': access_check {on,by,how} is required before a stop can be published')
            srcs=st.get('sources') or []
            need(len(srcs)>=2 and all(x.get('t') and str(x.get('u','')).startswith('https://') for x in srcs),w+': needs 2+ https sources with titles')
            fa=st.get('facts') or []
            need(len(fa)>=3,w+': list the claims (facts) with the sources that support each')
            used=set()
            for x in fa:
                need(x.get('t') and x.get('src') and all(isinstance(i,int) and 0<=i<len(srcs) for i in x['src']),w+': every fact needs src indexes that exist')
                used|=set(x.get('src') or [])
            need(used==set(range(len(srcs))),w+': every source must support at least one listed fact')
            ph=st.get('ph')
            if ph:
                need(ph.get('k') in photos,w+': photo file missing')
                for f in ('by','lic','lu','page'): need(ph.get(f),w+': photo credit missing '+f)
print(f'TOURS: {_nt} story stops checked')
bad=[b for b in bad if b]
print('PACKS: '+('OK' if not bad else 'FAILED')+f' ({len(order)} towns)')
for b in bad: print(' -',b)
sys.exit(1 if bad else 0)
