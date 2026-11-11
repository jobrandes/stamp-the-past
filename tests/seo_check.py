"""Check generated web pages: titles unique, internal links and photos resolve, no horizontal overflow on phone and desktop (sample)."""
import os,re,sys,glob,threading,http.server,socketserver,functools
R=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))+'/site'
pages=[p for p in glob.glob(R+'/*/index.html') if '/photos/' not in p]+glob.glob(R+'/*/*/index.html')
bad=[];titles={}
for p in pages:
    s=open(p).read()
    import html as _h; t=_h.unescape(re.search(r'<title>(.*?)</title>',s).group(1))
    if t in titles: bad.append('dup title '+t)
    titles[t]=p
    if len(t)>80: bad.append('long title '+t)
    if not re.search(r'<meta name="description" content="[^"]{40,}',s): bad.append('desc '+p)
    for m in re.findall(r'(?:src|href)="(/[^"#?]*)"',s):
        if m.startswith('//') or m=='/play': continue
        f=R+m
        if m.endswith('/'): f+='index.html'
        if not os.path.exists(f): bad.append('broken %s in %s'%(m,p))
# every town and stop page carries a Play button that opens a real stop of that town from the couch
import json as _j
SRC=os.path.dirname(R)+'/src/packs/'
for tid in _j.load(open(SRC+'index.json'))['order']:
    pk=_j.load(open(SRC+'%s.json'%tid)); ids=[x['id'] for x in pk['stops']]
    t=open(R+'/'+tid+'/index.html').read()
    if t.count('href="/play#play=%s:%s"'%(tid,ids[0]))<2: bad.append('town page %s lacks the Play buttons'%tid)
    for sid in ids:
        if open(R+'/%s/%s/index.html'%(tid,sid)).read().count('href="/play#play=%s:%s"'%(tid,sid))<2: bad.append('stop page %s/%s lacks the Play buttons'%(tid,sid))
print(len(pages),'pages;',len(bad),'problems'); [print(' ',b) for b in bad[:20]]
if bad: sys.exit(1)
from playwright.sync_api import sync_playwright
class Q(socketserver.TCPServer): allow_reuse_address=True
h=functools.partial(http.server.SimpleHTTPRequestHandler,directory=R)
h.log_message=lambda *a:None
srv=Q(('127.0.0.1',0),h); port=srv.server_address[1]; threading.Thread(target=srv.serve_forever,daemon=True).start()
import random; random.seed(3); sample=['/reno/arch/','/charleston/','/places/']+[ '/'+'/'.join(p[len(R)+1:].split('/')[:-1])+'/' for p in random.sample(pages,12)]
with sync_playwright() as pw:
    b=pw.chromium.launch(); errs=[]
    for w,hh in ((390,844),(1280,900)):
        pg=b.new_page(viewport={'width':w,'height':hh}); pg.on('pageerror',lambda e:errs.append(str(e)))
        for u in sample:
            pg.goto('http://127.0.0.1:%d%s'%(port,u),wait_until='load')
            if pg.evaluate('document.documentElement.scrollWidth>innerWidth+1'): errs.append('overflow %s @%d'%(u,w))
            if u=='/reno/arch/' and w==390: pg.screenshot(path=os.environ.get('SHOT','/tmp/seo_phone.png'),full_page=False)
            if u=='/reno/arch/' and w==1280: pg.screenshot(path=os.environ.get('SHOT2','/tmp/seo_desk.png'))
    b.close()
print('layout errors:',errs); sys.exit(1 if errs else 0)
