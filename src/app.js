(function(){
  var DATA=__DATA__;
  /* ---------- native progress backup (iPhone/Android app only) ---------- */
  (function(){
    var NB=null;
    try{ if(window.Capacitor&&Capacitor.isNativePlatform&&Capacitor.isNativePlatform()) NB=Capacitor.registerPlugin('StampStore'); }catch(e){}
    if(!NB) return;
    var MIR=/^(then-now|stp-)/;
    var si=Storage.prototype.setItem, ri=Storage.prototype.removeItem;
    Storage.prototype.setItem=function(k,v){ si.call(this,k,v); if(this===window.localStorage&&MIR.test(k)) try{ NB.setItem({key:k,value:String(v)}).catch(function(){}); }catch(e){} };
    Storage.prototype.removeItem=function(k){ ri.call(this,k); if(this===window.localStorage&&MIR.test(k)) try{ NB.removeItem({key:k}).catch(function(){}); }catch(e){} };
    NB.getAll().then(function(r){
      var d=(r&&r.values)||{}, restored=false, ls=window.localStorage;
      Object.keys(d).forEach(function(k){ if(ls.getItem(k)===null){ si.call(ls,k,d[k]); restored=true; } });
      for(var i=0;i<ls.length;i++){ var k=ls.key(i); if(MIR.test(k)&&d[k]===undefined) NB.setItem({key:k,value:ls.getItem(k)}).catch(function(){}); }
      if(restored&&!sessionStorage.getItem('stp-restored')){ sessionStorage.setItem('stp-restored','1'); location.reload(); }
    }).catch(function(){});
  })();
  /* ---------- scene + badge drawing ---------- */
  var BMAPS={}; Object.keys(DATA.packs).forEach(function(k){ BMAPS[k]=DATA.packs[k].badgeMap||{}; });
  function mono(id,pid){
    pid=pid||cityId; var c=CITIES[pid];
    if(id==='master') return c.initials;
    var t='?'; c.stops.forEach(function(st){ if(st.id===id) t=st.short.replace(/[^A-Za-z]/g,'').slice(0,2).toUpperCase(); });
    return t;
  }
  function badge(id,on,pid){
    pid=pid||cityId; var c=CITIES[pid];
    var m=(id==='master')?(c.heroKey&&PHOTOS[c.heroKey]?[c.heroKey,'50% 60%']:null):(BMAPS[pid]||{})[id];
    if(m&&PHOTOS[m[0]]) return '<span class="bimg'+(on?' on':'')+'"><img loading="lazy" src="'+PHOTOS[m[0]]+'" alt="" style="object-position:'+m[1]+'"></span>';
    return '<span class="bimg plain'+(on?' on':'')+'"><b>'+mono(id,pid)+'</b></span>';
  }
  var PHOTOS=__PHOTOS__;
  function preloadTown(k){ try{ var c=CITIES[k]; if(!c||c._pre) return; c._pre=1; var seen={}; c.stops.forEach(function(st){ ['then','now'].forEach(function(e){ var p=st[e].ph&&st[e].ph.k; if(p&&PHOTOS[p]&&!seen[p]){ seen[p]=1; var im=new Image(); im.src=PHOTOS[p]; } }); }); }catch(e){} }
  function hasPh(st,era){return !!(st[era].ph && PHOTOS[st[era].ph.k]);}
  function visual(st,era,label,extra){
    if(hasPh(st,era)) return '<div class="scene ph'+(extra||'')+'"><img src="'+PHOTOS[st[era].ph.k]+'" alt="'+label+'"></div>';
    return '<div class="scene pend'+(extra||'')+'"><span>Photo pending. A free-to-use photo has not been added here yet.</span></div>';
  }
  function compare(st){
    if(!(hasPh(st,'then')&&hasPh(st,'now'))) return '';
    return '<section class="cmp" aria-label="Then and now slider"><div class="box"><img src="'+PHOTOS[st.now.ph.k]+'" alt="'+st.now.label+', today"><img class="top" src="'+PHOTOS[st.then.ph.k]+'" alt="'+st.then.label+', '+st.then.yr+'">'+(slDragged()?'':'<span class="dragtip" aria-hidden="true">&lsaquo; Drag to travel back &rsaquo;</span>')+'</div><div class="row"><span>Now</span><input type="range" min="0" max="100" value="0" aria-label="Fade from now to then" data-cmp="1"><span>Then</span></div><p class="hint">Swipe the photo or drag the slider to travel back to '+st.then.yr+'.'+(st.spot?' Then spot the change below.':'')+'</p><button class="btn small sharefade" data-a="sharefade" data-n="'+st.now.ph.k+'" data-t="'+st.then.ph.k+'" data-y="'+String(st.then.yr).replace(/"/g,'')+'" data-s="'+String(st.name).replace(/"/g,'&quot;')+'" data-c="'+String(city().name).replace(/"/g,'&quot;')+'">Share this fade</button>'+spotHtml(st)+'</section>';
  }

  /* story: the first few sentences up front, the rest under "Read more" (the full text is always in the page for search engines and screen readers) */
  var ABBR=/(\b(Dr|Mr|Mrs|Ms|St|Mt|Jr|Sr|No|vs|Gen|Col|Capt|Lt|Rev|Gov|Sen|Co|Inc|Ft)\.|\b[A-Z]\.)$/;
  function sentences(p){ var m=p.match(/[^.!?]+(?:[.!?]+["\u201D\u2019)]*|$)\s*/g)||[p], out=[], cur=''; m.forEach(function(x){ cur+=x; if(!ABBR.test(cur.trim())){ out.push(cur); cur=''; } }); if(cur) out.push(cur); return out; }
  function storyHtml(st){
    var paras=st.story||[], head=[], rest=[], len=0, n=0, done=false;
    paras.forEach(function(p){
      if(done){ rest.push(p); return; }
      var ss=sentences(p), h='', r='';
      ss.forEach(function(x,i){ if(!done){ h+=x; len+=x.length; n++; if(len>=190||n>=3) { done=true; } } else r+=x; });
      head.push(h.trim()); if(r.trim()) rest.push(r.trim());
      if(done&&r.trim()) { /* remainder of this paragraph leads the hidden part */ }
    });
    var restLen=rest.join(' ').length;
    var more=restLen>=120;
    var all=more?head:head.concat(rest);
    var out='<section class="card story">'+all.map(function(p){ return '<p>'+p+'</p>'; }).join('');
    if(more) out+='<details class="more"><summary>Read more</summary>'+rest.map(function(p){ return '<p>'+p+'</p>'; }).join('')+'</details>';
    return out+'</section>';
  }

  /* about how far apart a town's stops are, from their map points (straight-line, shortest order, so real routes run longer) */
  /* about how long a stop takes once you are at the spot: reading the story plus answering (200 words a minute, plus one minute for the question) */
  function stopMins(st){ var w=((st.story||[]).join(' ')+' '+(st.q&&st.q.q||'')).split(/\s+/).length; return Math.min(6,Math.max(2,Math.ceil(w/200)+1)); }
  function tourInfo(c){
    var P=c.stops.map(function(st){ return st.geo; }); if(P.length<2||P.some(function(g){ return !g||g.length<2; })) return '';
    var best=1e12;
    (function perm(a,r){ if(!r.length){ var d=0; for(var i=1;i<a.length;i++) d+=distM(a[i-1][0],a[i-1][1],a[i][0],a[i][1]); if(d<best) best=d; return; } for(var i=0;i<r.length;i++) perm(a.concat([r[i]]),r.slice(0,i).concat(r.slice(i+1))); })([],P);
    var mi=best/1609.34, n=P.length+' stops. ';
    if(mi<0.1) return n+'All within a short stroll of each other.';
    var mtxt=mi<10?mi.toFixed(1):String(Math.round(mi));
    if(mi>2.5) return n+'Spread out: about '+mtxt+' miles from first to last. Plan to drive between stops.';
    var min=Math.max(5,Math.round(mi*1.3/3*60/5)*5);
    return n+'About '+mtxt+' miles in all, roughly '+min+' minutes of walking. Straight-line, so your route may be longer.';
  }
  function spotHtml(st){
    var sp=st.spot; if(!sp||!sp.options) return '';
    return '<div class="spot" id="spot"><p class="stag"><span aria-hidden="true">?</span> Puzzle: spot the change</p><p class="sq">'+sp.q+'</p><div class="spopts" role="group" aria-label="Spot the change answers">'+sp.options.map(function(o,k){ return '<button type="button" class="btn ghost small spo" data-a="spotpick" data-k="'+k+'">'+o+'</button>'; }).join('')+'</div><p class="sfb" aria-live="polite"></p></div>';
  }
  document.addEventListener('input',function(e){
    var q=e.target; if(q&&q.id==='townSearch'){ var v=q.value.trim().toLowerCase(), any=false;
      document.querySelectorAll('#missions details.reg').forEach(function(d){ var vis=0; d.querySelectorAll('li').forEach(function(li){ var m=!v||(li.textContent+' '+(li.getAttribute('data-q')||'')).toLowerCase().indexOf(v)>-1; li.hidden=!m; if(m) vis++; }); d.hidden=!!v&&!vis; if(v) d.open=vis>0; if(vis) any=true; });
      var nn=document.getElementById('townNone'); if(nn) nn.hidden=!v||any; return; }
    var t=e.target; if(!t||!t.getAttribute||!t.getAttribute('data-cmp')) return;
    var top=t.closest('.cmp').querySelector('.top'); if(top) top.style.opacity=(t.value/100); slUsed(t.closest('.cmp'));
  });
  function slDragged(){ try{ return localStorage.getItem('stp-dragged')==='1'; }catch(e){ return false; } }
  function slUsed(c){ try{ localStorage.setItem('stp-dragged','1'); }catch(e){} var t=c&&c.querySelector('.dragtip'); if(t) t.remove(); }
  (function(){var drag=null;
    function setv(box,x){var r=box.getBoundingClientRect();var v=Math.max(0,Math.min(100,(x-r.left)/r.width*100));var c=box.closest('.cmp');var inp=c.querySelector('input[data-cmp]');var top=c.querySelector('.top');if(inp)inp.value=v;if(top)top.style.opacity=v/100;slUsed(c);}
    document.addEventListener('pointerdown',function(e){var b=e.target.closest&&e.target.closest('.cmp .box');if(!b)return;drag=b;try{b.setPointerCapture(e.pointerId);}catch(_){}setv(b,e.clientX);});
    document.addEventListener('pointermove',function(e){if(drag)setv(drag,e.clientX);});
    function end(){drag=null;}document.addEventListener('pointerup',end);document.addEventListener('pointercancel',end);
  })();
  function credit(st,era){
    var p=st[era].ph;
    if(hasPh(st,era)) return '<span class="credit">Photo: '+p.by+' · <a target="_blank" rel="noopener" href="'+p.lu+'">'+p.lic+'</a> · <a target="_blank" rel="noopener" href="'+p.page+'">Source</a>'+(p.note?' · '+p.note:'')+'</span>';
    return '<span class="credit">Photo pending.</span>';
  }
  function creditsList(){
    var seen={}, li='';
    STOPS.forEach(function(st){['then','now'].forEach(function(era){
      var p=st[era].ph; if(!p||seen[p.k]) return; seen[p.k]=1;
      li+='<li>'+st.name+', '+era+': '+p.by+' · <a target="_blank" rel="noopener" href="'+p.lu+'">'+p.lic+'</a> · <a target="_blank" rel="noopener" href="'+p.page+'">Source</a></li>';
    });});
    li+=city().heroLi||'';    return '<p class="mono">Photo credits</p><ul>'+li+'</ul><p class="why">Photos were resized. Badge pictures reuse these photos.</p>';
  }
  function creditTxt(st,era){
    var p=st[era].ph;
    return hasPh(st,era)?('Photo: '+p.by+' ('+p.lic+')'):'Photo pending';
  }

  /* ---------- content ---------- */
  var RIGHT = DATA.right;
  var RENO_STOPS = DATA.packs.reno.stops, VC_STOPS = DATA.packs.vc.stops;
  var RENO_RANKS = DATA.packs.reno.ranks, VC_RANKS = DATA.packs.vc.ranks;
  var CITIES = DATA.packs;
  var RANKS=RENO_RANKS;
  var KEY='then-now-reno-v1', KEY2='then-now-v2', KEY3='then-now-v3';
  /* shown on the share card; swap for the real domain or App Store link once it exists */
  var SHARE_URL='stampthepast.com';
  var railRegion=null, ORDER=DATA.order, SOON=DATA.soon||[], atHome=true, onPass=false;
  function blank(){ return {done:[0,0,0,0],claims:[0,0,0,0,0,0,0,0]}; }
  var ALL={}; ORDER.forEach(function(k){ ALL[k]=blank(); });
  var cityId='reno';
  var S=ALL.reno, STOPS=RENO_STOPS;
  function city(){ return CITIES[cityId]; }
  var tab='trail';
  var cur=null;          /* {i, step, entry, wrong:[], picks:[], checked:false} */
  var confirmReset=false;
  var toastTimer=null, nudged=false;
  var pushed=false, ignorePop=false;

  function norm(o){
    if(o && Array.isArray(o.done) && o.done.length===4 && Array.isArray(o.claims) && o.claims.length===8){
      return {done:o.done.map(function(x){return x?1:0}),claims:o.claims.map(function(x){return x?1:0})};
    }
    return null;
  }
  function load(){
    try{
      var r3=localStorage.getItem(KEY3);
      if(r3){
        var o3=JSON.parse(r3), n;
        ORDER.forEach(function(k){ if(o3.p && (n=norm(o3.p[k]))) ALL[k]=n; });
        if(o3.city && CITIES[o3.city]) cityId=o3.city;
        atHome=!!o3.home;
      } else {
        var r2=localStorage.getItem(KEY2), r=localStorage.getItem(KEY);
        if(r2){
          var o2=JSON.parse(r2);
          ORDER.forEach(function(k){ if((n=norm(o2[k]))) ALL[k]=n; });
          if(o2.city && CITIES[o2.city]) cityId=o2.city;
          atHome=false;
        } else if(r){ var n1=norm(JSON.parse(r)); if(n1) ALL.reno=n1; atHome=false; }
      }
    }catch(e){}
    S=ALL[cityId]; STOPS=CITIES[cityId].stops; RANKS=CITIES[cityId].ranks;
  }
  var demoSnap=null, demoC=null;
  function endDemo(){ if(demoSnap&&demoC){ demoC.done=demoSnap.done.slice(); demoC.claims=demoSnap.claims.slice(); } var was=!!demoSnap; demoSnap=null; demoC=null; if(was&&typeof awardSoon==='function') awardSoon(); }
  function save(){ if(demoSnap) return; try{ localStorage.setItem(KEY3,JSON.stringify({city:cityId,home:atHome?1:0,p:ALL})); }catch(e){} }
  function sum(a){ return a.reduce(function(x,y){return x+y;},0); }
  function xp(){ var d=(demoSnap&&demoC===S)?demoSnap:S; return sum(d.done)*100 + sum(d.claims)*25; }
  function rank(x){
    var i=0; RANKS.forEach(function(r,k){ if(x>=r[0]) i=k; });
    var next=RANKS[i+1]||null;
    return {i:i,name:RANKS[i][1],from:RANKS[i][0],to:next?next[0]:RANKS[i][0],next:next};
  }
  var INKS=[{n:'Blue',c:'#1B58B8'},{n:'Red',c:'#C0392B'},{n:'Green',c:'#2E8B57'},{n:'Purple',c:'#7B4BB7'},{n:'Gold',c:'#D4A017'}], inkI=0;
  try{ var _k=parseInt(localStorage.getItem('then-now-ink'),10); if(_k>=0&&_k<INKS.length) inkI=_k; }catch(e){}
  function bestRank(){
    var best=0; ORDER.forEach(function(k){ var st=ALL[k]; var x=sum(st.done)*100+sum(st.claims)*25, i=0; [0,100,250,450,600].forEach(function(t,k){ if(x>=t) i=k; }); if(i>best) best=i; });
    return best;
  }
  function code(){ return 'TN3-'+ORDER.map(function(k){ return ALL[k].done.join('')+ALL[k].claims.join(''); }).join('-'); }
  function allDone(){ return sum(S.done)===4; }

  var stampFx=false;
  function isNativeApp(){ try{ return !!(window.Capacitor&&Capacitor.isNativePlatform&&Capacitor.isNativePlatform()); }catch(e){ return false; } }
  function hapticPlugin(){ try{ if(!isNativeApp()) return null; var P=Capacitor.Plugins&&Capacitor.Plugins.StampStore; if(!P&&Capacitor.registerPlugin) P=Capacitor.registerPlugin('StampStore'); return (P&&P.haptic)?P:null; }catch(e){ return null; } }
  function haptic(k,cb){ try{ var P=hapticPlugin(); if(!P){ if(cb) cb('missing'); return; } var p=P.haptic({kind:k||'success'}); if(p&&p.then) p.then(function(){ if(cb) cb('ok'); },function(){ if(cb) cb('error'); }); else if(cb) cb('ok'); }catch(e){ if(cb) cb('error'); } }
  function virtGet(){ try{ var o=JSON.parse(localStorage.getItem('stp-virt')||'{}'); return (o&&typeof o==='object')?o:{}; }catch(e){ return {}; } }
  function virtHas(c,i){ var st=CITIES[c]&&CITIES[c].stops[i]; return !!(st&&virtGet()[c+':'+st.id]&&!(ALL[c]&&ALL[c].done[i])); }
  function virtSave(){ var v=virtGet(); v[cityId+':'+STOPS[cur.i].id]=1; try{ localStorage.setItem('stp-virt',JSON.stringify(v)); }catch(e){} }
  function geoGet(){ try{ var o=JSON.parse(localStorage.getItem('stp-geo')||'{}'); return (o&&typeof o==='object')?o:{}; }catch(e){ return {}; } }
  function geoVerified(k,i){ var st=CITIES[k]&&CITIES[k].stops[i]; return !!(st&&geoGet()[k+':'+st.id]); }
  function distM(a,b,c,d){ var R=6371000,p=Math.PI/180,x=Math.sin((c-a)*p/2),y=Math.sin((d-b)*p/2),h=x*x+Math.cos(a*p)*Math.cos(c*p)*y*y; return 2*R*Math.asin(Math.sqrt(h)); }
  function nice(m){ return m<1000?'about '+(Math.max(10,Math.round(m/10)*10))+' m ('+Math.round(m*3.281/10)*10+' ft)':'about '+(m/1000).toFixed(1)+' km ('+(m/1609.34).toFixed(1)+' mi)'; }
  function geoMsg(t,bad){ var e=document.getElementById('geoMsg'); if(e){ e.textContent=t; e.className='geomsg'+(bad?' bad':''); } }
  var geoDenied=false;
  function geoGranted(){ try{ return localStorage.getItem('stp-geo-ok')==='1'; }catch(e){ return false; } }
  try{ if(navigator.permissions&&navigator.permissions.query){ navigator.permissions.query({name:'geolocation'}).then(function(r){
    function sync(){ /* never trust 'denied' here: iOS web views misreport it. Only a refused request counts. */ if(r.state==='granted'){ try{ localStorage.setItem('stp-geo-ok','1'); }catch(e){} } }
    sync(); r.onchange=sync; }).catch(function(){}); } }catch(e){}
  function geoSave(){ var gg=geoGet(); gg[cityId+':'+STOPS[cur.i].id]=1; try{ localStorage.setItem('stp-geo',JSON.stringify(gg)); }catch(e){} awardSoon(); }
  // quiet=true: automatic check, says nothing unless you are in range
  function geoCheck(quiet){
    var st=STOPS[cur.i]; if(!st||!st.geo||cur.demo) return;
    var late=!!S.done[cur.i]; if(late&&geoVerified(cityId,cur.i)) return;
    var at=cur.i, ct=cityId;
    if(!navigator.geolocation){ if(!quiet) geoMsg('This device cannot share its location. You can continue without the gold stamp.',true); return; }
    if(!quiet) geoMsg('Checking your location. Stays on this phone.',false);
    navigator.geolocation.getCurrentPosition(function(pos){
      if(!cur||cur.i!==at||cityId!==ct) return;
      try{ localStorage.setItem('stp-geo-ok','1'); }catch(e){}
      geoStartWatch();
      var acc=pos.coords.accuracy||0, d=distM(pos.coords.latitude,pos.coords.longitude,st.geo[0],st.geo[1]);
      if(acc>150){ if(!quiet) geoMsg('The location signal is too weak here (off by about '+Math.round(acc)+' m). Try again outside, or continue without the gold stamp.',true); return; }
      if(d<=st.geo[2]){
        if(late){ geoSave(); toast('Location confirmed. Visit verified.'); render(false); }
        else if(cur.step===0){ cur.gv=true; toast('You are here. This visit will be verified.'); setStep(1); }
      } else if(!quiet) geoMsg('You look '+nice(d)+' from '+st.name+'. Walk closer and try again'+(late?'.':', or continue without the gold stamp.'),true);
    },function(err){
      if(err&&err.code===1) geoDenied=true;
      if(!quiet) geoMsg(err&&err.code===1?'Location is off for this app, which is fine. You can continue without the gold stamp.':'Could not get your location. Try again, or continue without the gold stamp.',true);
    },{enableHighAccuracy:true,timeout:15000,maximumAge:30000});
  }
  function lateVerify(st,d){
    if(!(d&&st.geo&&!cur.demo)||geoVerified(cityId,cur.i)||geoDenied) return '';
    return '<section class="card"><p class="mono">Verified visit</p><p>You already have this stamp. Standing at '+st.name+' right now? Verify this visit to upgrade it to a gold stamp and earn +50 XP.</p><button class="btn gold" data-a="geo">Verify this visit</button><p class="hint">Optional. Checked on this phone only, never sent anywhere.</p><p id="geoMsg" class="geomsg" role="status"></p></section>';
  }
  // Live location while the app is open (never in the background, never sent anywhere)
  var geoPos=null, geoWatchId=null, nearHit=null;
  function liveOn(){ try{ return localStorage.getItem('stp-geo-live')!=='0'; }catch(e){ return true; } }
  function geoMark(c,i){ var st=CITIES[c]&&CITIES[c].stops[i]; if(!st) return; var gg=geoGet(); gg[c+':'+st.id]=1; try{ localStorage.setItem('stp-geo',JSON.stringify(gg)); }catch(e){} awardSoon(); }
  function geoStopWatch(){ if(geoWatchId!==null){ try{ navigator.geolocation.clearWatch(geoWatchId); }catch(e){} geoWatchId=null; } }
  function geoStartWatch(){
    if(geoWatchId!==null||!navigator.geolocation||!geoGranted()||geoDenied||!liveOn()||document.hidden) return;
    try{ geoWatchId=navigator.geolocation.watchPosition(onFix,function(e){ if(e&&e.code===1){ geoDenied=true; geoStopWatch(); nearHit=null; nearPaint(); } },{enableHighAccuracy:true,maximumAge:10000,timeout:30000}); }catch(e){}
  }
  function nearCardHtml(){
    var n=nearHit; if(!n||atHome===false) return '';
    var c=CITIES[n.c], st=c.stops[n.i];
    if(n.inr) return '<section class="card nearcard here"><p class="mono">You are here</p><p><strong>'+st.name+'</strong>, '+c.name+'. Start the hunt for the gold stamp.</p><button class="btn gold" data-a="neargo" data-c="'+n.c+'" data-i="'+n.i+'">Start this stop</button></section>';
    // outside the stop's circle the nearest-stops list below takes over
    return '';
  }
  /* the one stop Home calls "Next stop": the in-progress town (current town first), else the home town; first stop not yet stamped */
  function nextRef(){
    var res=null; [cityId].concat(ORDER).forEach(function(k){ if(!res&&CITIES[k]){ var d=sum(ALL[k].done); if(d>0&&d<CITIES[k].stops.length) res=k; } });
    var tk=res||homeTown(), tc=CITIES[tk], ni=0; if(!tc) return null;
    for(var q=0;q<tc.stops.length;q++){ if(!ALL[tk].done[q]){ ni=q; break; } }
    return {k:tk,i:ni};
  }
  var nearAll=false;
  function nearListHtml(){
    if(atHome===false||geoDenied||!navigator.geolocation) return '';
    if(!geoPos){ return geoGranted()?'':'<section class="card nearlist"><p class="mono">Stops near me</p><button class="btn ghost" data-a="nearme">Show the closest stops</button><p class="hint">Optional. Your location stays on this phone and is never sent anywhere.</p></section>'; }
    var arr=[], nx=nextRef(); ORDER.forEach(function(k){ CITIES[k].stops.forEach(function(st,i){ if(!st.geo||ALL[k].done[i]||(nx&&nx.k===k&&nx.i===i)) return; var d=distM(geoPos.lat,geoPos.lon,st.geo[0],st.geo[1]); if(d<=150000) arr.push({c:k,i:i,d:d}); }); });
    arr.sort(function(x,y){ return x.d-y.d; }); var more=arr.length>3&&!nearAll; arr=arr.slice(0,nearAll?8:3);
    if(!arr.length) return '<section class="card nearlist"><p class="mono">Stops near me</p><p>No unstamped stop within 90 miles of you. Pick a town from Towns to plan a trip.</p></section>';
    return '<section class="nearlist" aria-label="Stops near you"><p class="mono">Closest to you</p>'+arr.map(function(x){ var st=CITIES[x.c].stops[x.i]; return '<button class="rcard" data-a="neargo" data-c="'+x.c+'" data-i="'+x.i+'" data-far="1"><span><strong>'+st.name+'</strong><span class="rsub">'+CITIES[x.c].name+' · '+nice(x.d)+'</span></span><span class="go">Open ›</span></button>'; }).join('')+(more?'<button class="btn ghost" data-a="nearall">See more nearby stops</button>':'')+'</section>';
  }
  /* starting-town suggestion for players far from Nevada: guessed from the phone's time zone on the phone itself, nothing is sent anywhere */
  function startTownHtml(){
    try{
      var tz=(Intl.DateTimeFormat().resolvedOptions().timeZone||''), M={'America/New_York':'ny','America/Toronto':'buffalo','America/Detroit':'detroit','America/Chicago':'chicago','America/Indiana/Indianapolis':'indianapolis','America/Indianapolis':'indianapolis','America/Kentucky/Louisville':'louisville','America/Denver':'denver','America/Boise':'saltlake','America/Phoenix':'phoenix','America/Anchorage':'sitka','Pacific/Honolulu':'honolulu'};
      var k=M[tz]; if(!k&&tz&&!/^(America|Pacific)\//.test(tz)) k='ny';
      if(!k||!CITIES[k]||sum(ALL[k].done)>0) return '';
      var c=CITIES[k];
      return '<button class="rcard starttown" data-a="city" data-c="'+k+'"><span><strong>New here? Start in '+c.name+'</strong><span class="rsub">A good first town if you are far from Nevada. '+c.stops.length+' stops, picked from your time zone on this phone.</span></span><span class="go">Go ›</span></button>';
    }catch(e){ return ''; }
  }
  function nearHtml(){ return nearCardHtml()+nearListHtml(); }
  function nearPaint(){ var e=document.getElementById('nearBox'); if(e) e.innerHTML=nearHtml(); }
  // Optional alerts when the app is closed (iPhone app only; the phone does the watching, nothing is sent anywhere)
  var NG=null;
  try{ if(window.Capacitor&&Capacitor.isNativePlatform&&Capacitor.isNativePlatform()&&Capacitor.getPlatform&&Capacitor.getPlatform()==='ios') NG=Capacitor.registerPlugin('StampGeo'); }catch(e){}
  function bgOn(){ try{ return localStorage.getItem('stp-bg')==='1'; }catch(e){ return false; } }
  function bgStops(){ var out=[]; ORDER.forEach(function(k){ CITIES[k].stops.forEach(function(st,i){ if(!st.geo||ALL[k].done[i]) return; out.push({id:k+':'+i,n:st.name+', '+CITIES[k].name,lat:st.geo[0],lon:st.geo[1],r:Math.min(st.geo[2],500)}); }); }); return out; }
  function bgSync(){ if(NG&&bgOn()) try{ NG.enable({stops:bgStops()}).catch(function(){}); }catch(e){} }
  function bgOpenPending(){ if(!NG) return; try{ NG.pending().then(function(r){ var id=r&&r.id; if(!id) return; var q=id.split(':'), k=q[0], i=+q[1]; if(CITIES[k]&&CITIES[k].stops[i]){ railRegion=null; if(k!==cityId||atHome) setCity(k); openStop(i,0); } }).catch(function(){}); }catch(e){} }
  var hereSeen={};
  function hereHide(){ var e=document.querySelector('.herebanner'); if(e&&e.parentNode) e.parentNode.removeChild(e); }
  function hereShow(h){
    var key=h.c+':'+h.i; if(hereSeen[key]) return; hereSeen[key]=1;
    var c=CITIES[h.c], st=c.stops[h.i]; hereHide();
    var e=document.createElement('div'); e.className='herebanner'; e.setAttribute('role','alert');
    e.innerHTML='<p><strong>You are at '+st.name+'.</strong> '+(ALL[h.c].done[h.i]?'Tap to open it.':'Ready to stamp it?')+'</p><div class="hbrow"><button class="btn gold" type="button" data-hb="go">Open</button><button class="btn ghost" type="button" data-hb="no">Not now</button></div>';
    e.addEventListener('click',function(ev){ var b=ev.target.closest('[data-hb]'); if(!b) return; hereHide();
      if(b.getAttribute('data-hb')==='go'){ railRegion=null; if(h.c!==cityId||atHome) setCity(h.c); openStop(h.i,0); if(!ALL[h.c].done[h.i]){ cur.gv=true; setStep(1); } } });
    document.body.appendChild(e);
    try{ if(navigator.vibrate) navigator.vibrate(200); }catch(x){}
  }
  function onFix(pos){
    var la=pos.coords.latitude, lo=pos.coords.longitude, acc=pos.coords.accuracy||0;
    geoPos={lat:la,lon:lo,acc:acc};
    var best=null, hit=null, changed=false;
    ORDER.forEach(function(k){ CITIES[k].stops.forEach(function(st,i){
      if(!st.geo) return; var d=distM(la,lo,st.geo[0],st.geo[1]); var inr=acc<=150&&d<=st.geo[2];
      var done=ALL[k].done[i];
      if(inr&&done&&!geoVerified(k,i)){ geoMark(k,i); changed=true; }
      if(done) return;
      if(inr){ if(!hit||d<hit.d) hit={c:k,i:i,d:d,inr:true}; }
      else if(!best||d<best.d) best={c:k,i:i,d:d,inr:false};
    }); });
    var nx=hit||best, key=nx?nx.c+':'+nx.i+':'+(nx.inr?1:0)+':'+Math.round(nx.d/500):'';
    var pk=nearHit?nearHit.c+':'+nearHit.i+':'+(nearHit.inr?1:0)+':'+Math.round(nearHit.d/500):'';
    nearHit=nx; if(key!==pk) nearPaint();
    if(hit&&!(cur&&!atHome&&cityId===hit.c&&cur.i===hit.i)) hereShow(hit);
    if(changed){ toast('Location confirmed. Visit verified.'); if(cur&&S.done[cur.i]) render(false); }
    // standing at the stop you are looking at: go straight to the question
    if(cur&&!atHome&&cur.step===0&&!cur.demo&&!S.done[cur.i]&&STOPS[cur.i]&&STOPS[cur.i].geo&&hit&&hit.c===cityId&&hit.i===cur.i&&!cur.gv){
      cur.gv=true; toast('You are here. This visit will be verified.'); setStep(1);
    }
  }
  document.addEventListener('visibilitychange',function(){ if(document.hidden) geoStopWatch(); else { geoStartWatch(); bgSync(); bgOpenPending(); } });
  function toast(msg){
    var t=document.getElementById('toast');
    t.textContent=msg; t.classList.add('show');
    clearTimeout(toastTimer);
    toastTimer=setTimeout(function(){ t.classList.remove('show'); },2600);
  }

  /* ---------- header ---------- */
  function applyCity(){
    var c=city(); preloadTown(cityId);
    var h1=document.getElementById('cityName'); h1.textContent=c.name; h1.className=c.name.length>9?'long xl':(c.name.length>7?'long':'');
    var hero=document.getElementById('hero'), img=document.getElementById('heroImg');
    if(c.heroKey && PHOTOS[c.heroKey]){ img.src=PHOTOS[c.heroKey]; img.alt=c.heroAlt; hero.classList.remove('nophoto'); }
    else { img.removeAttribute('src'); img.alt=''; hero.classList.add('nophoto'); }
    document.getElementById('heroCredit').innerHTML=c.heroCredit;
    var regsR=[]; ORDER.forEach(function(k){ var r=CITIES[k].region||'More places'; if(regsR.indexOf(r)<0) regsR.push(r); });
    var curR=railRegion||c.region||'More places';
    document.getElementById('cities').innerHTML='<div class="rail1">'+regsR.map(function(r){ return '<button class="rtab" data-a="rregion" data-r="'+r+'" aria-pressed="'+(r===curR)+'">'+r+'</button>'; }).join('')+'</div><div class="rail2">'+ORDER.filter(function(k){ return (CITIES[k].region||'More places')===curR; }).map(function(k){
      return '<button class="city" data-a="city" data-c="'+k+'" aria-pressed="'+(!atHome&&k===cityId)+'">'+CITIES[k].name+'</button>';
    }).join('')+'</div>';
    var act=document.querySelector('#cities .rail2 .city[aria-pressed="true"]'); if(act){ try{ var bx=act.parentNode; var ar=act.getBoundingClientRect(), br=bx.getBoundingClientRect(); if(ar.left<br.left+8||ar.right>br.right-8) bx.scrollLeft=Math.max(0,bx.scrollLeft+(ar.left-br.left)-16); }catch(_){} }
  }
  function setCity(id){
    if(!CITIES[id]||(id===cityId&&!atHome)) return;
    leave(); atHome=false; onPass=false; cityId=id; S=ALL[id]; STOPS=CITIES[id].stops; RANKS=CITIES[id].ranks;
    tab='trail'; confirmReset=false; save(); applyCity(); render(); window.scrollTo(0,0);
  }
  function openPass(){ leave(); atHome=true; onPass=true; confirmReset=false; save(); applyCity(); render(); window.scrollTo(0,0); }
  function goHome(){ bnavSel='home'; leave(); atHome=true; onPass=false; confirmReset=false; save(); applyCity(); render(); window.scrollTo(0,0); }
  function updateHeader(){
    var x=xp(), r=rank(x);
    document.getElementById('rankName').textContent=r.name;
    document.getElementById('xpText').textContent=x+' town XP'+(r.next?' · next rank at '+r.to:' · top rank');
    var frac=r.next?(x-r.from)/(r.to-r.from):1;
    document.getElementById('xpFill').style.width=Math.round(frac*100)+'%';
    var bar=document.getElementById('xpBar');
    bar.setAttribute('aria-valuenow',String(x));
    bar.setAttribute('aria-valuetext',x+' of 600 XP, rank '+r.name);
    document.getElementById('bulbs').innerHTML=STOPS.map(function(s,i){
      return '<div class="bulb'+(S.done[i]?' on':'')+'"><i></i><span>'+s.short+'</span></div>';
    }).join('');
    ['trail','cards','rewards'].forEach(function(t){
      document.getElementById('tab-'+t).setAttribute('aria-selected',String(t===tab));
    });
  }

  /* ---------- views ---------- */
  var HCL=[
    {t:'The first Reno Arch was built in 1926.',a:0,why:'Several sources agree on October 23, 1926. Well documented.'},
    {t:'The arch switched to LED lights in 2018.',a:1,why:'One source says 2009, another says 2018. Until a city record settles it, it is disputed.'}
  ], hi=0, hdone=false, hmsg='Pick one.', hcls='';
  function homeFof(){
    var c=HCL[hi];
    return '<div class="fof" aria-live="polite"><p class="mono">Fact or fiction</p><div class="fcard-h">'+(hdone?'You get the idea.':c.t)+'</div>'+(hdone?'':'<div class="fb-h">'+FLAB.map(function(l,k){ return '<button type="button" data-a="hpick" data-k="'+k+'">'+l+'</button>'; }).join('')+'</div>')+'<p class="res-h '+hcls+'">'+hmsg+'</p></div>';
  }
  function homeTown(){
    var hk=CITIES[cityId]?cityId:ORDER[0];
    if(!atHome||sum(ALL[hk].done)===0){ ORDER.forEach(function(k){ if(sum(ALL[k].done)>0&&(sum(ALL[hk].done)===0)) hk=k; }); }
    return hk;
  }
  var heroFocus=null;
  function townKeys(k){ var out=[]; CITIES[k].stops.forEach(function(st){ var p=((BMAPS[k]||{})[st.id]||[])[0]; if(!(p&&PHOTOS[p])) p=(st.now.ph&&st.now.ph.k)||''; if(p&&PHOTOS[p]&&out.indexOf(p)<0) out.push(p); }); return out; }
  function stampsHtml(){
    var keys=[], cap='';
    if(heroFocus&&heroFocus.r){
      var towns=ORDER.filter(function(k){ return (CITIES[k].region||'More places')===heroFocus.r; }), lists=towns.map(townKeys), i=0;
      while(keys.length<4&&lists.some(function(l){ return l.length>i; })){ lists.forEach(function(l){ if(keys.length<4&&l[i]&&keys.indexOf(l[i])<0) keys.push(l[i]); }); i++; }
      cap=heroFocus.r;
    } else {
      var hk=(heroFocus&&CITIES[heroFocus.c])?heroFocus.c:homeTown(); keys=townKeys(hk); cap=CITIES[hk].name;
    }
    return keys.slice(0,4).map(function(k){ return '<div class="hstamp"><img src="'+PHOTOS[k]+'" alt=""></div>'; }).join('')+'<p class="hstamps-cap mono">'+cap+'</p>';
  }
  var heroPause=0;
  function setHeroFocus(f,auto){
    if(!auto) heroPause=Date.now()+12000;
    if(JSON.stringify(f)===JSON.stringify(heroFocus)) return;
    heroFocus=f; var el=document.querySelector('.hstamps'); if(!el) return;
    el.classList.add('swap'); setTimeout(function(){ el.innerHTML=stampsHtml(); el.classList.remove('swap'); },170);
  }
  (function(){
    var rm=window.matchMedia&&window.matchMedia('(prefers-reduced-motion: reduce)'), seq=null, si=0;
    function build(){ var regs=[], by={}; ORDER.forEach(function(k){ var r=CITIES[k].region||'More places'; if(!by[r]){ by[r]=[]; regs.push(r); } by[r].push(k); }); var out=[], i=0; while(out.length<ORDER.length){ regs.forEach(function(r){ if(by[r][i]) out.push(by[r][i]); }); i++; } return out; }
    setInterval(function(){
      if(!atHome||onPass||document.hidden||(rm&&rm.matches)||Date.now()<heroPause||!document.querySelector('.hstamps')) return;
      if(!seq){ seq=build(); }
      var cur2=heroFocus&&heroFocus.c, at=seq.indexOf(cur2); si=(at<0?si:at)+1; if(si>=seq.length) si=0;
      setHeroFocus({c:seq[si]},true);
    },5000);
  })();
  document.addEventListener('click',function(e){
    var sm=e.target.closest&&e.target.closest('.home-regions summary.region, details.reg:not(.ppreg) > summary.region'); if(!sm) return;
    var r=sm.firstElementChild&&sm.firstElementChild.textContent; if(r) setHeroFocus({r:r});
  });
  document.addEventListener('mouseover',function(e){
    var t=e.target.closest&&e.target.closest('button.town[data-c], #cities button.city[data-c]'); if(t&&t.getAttribute('data-c')&&atHome) setHeroFocus({c:t.getAttribute('data-c')});
  });
  document.addEventListener('focusin',function(e){
    var t=e.target.closest&&e.target.closest('button.town[data-c]'); if(t&&t.getAttribute('data-c')) setHeroFocus({c:t.getAttribute('data-c')});
  });
  function nextBadge(){
    try{ var best=null; bdAll().list.forEach(function(x){ if(x.on||x.cur<=0||x.goal<=1) return; var f=x.cur/x.goal; if(!best||f>best.f) best={f:f,x:x}; }); return best&&best.x; }catch(e){ return null; }
  }
  function statusHtml(got,total,res,hk){
    var gs=gStats(), lv=lvOf(gs.xp), tk=res||hk, tc=CITIES[tk], ni=0;
    for(var q=0;q<tc.stops.length;q++){ if(!ALL[tk].done[q]){ ni=q; break; } }
    var allDone=tc.stops.every(function(x,i){ return ALL[tk].done[i]; });
    var btn=allDone?'<button class="bigbtn" data-a="gomissions"><span class="bl">Town complete</span><span class="bs">Pick your next town</span></button>':'<button class="bigbtn" data-a="nextstop" data-c="'+tk+'" data-i="'+ni+'"><span class="bl">'+(got>0?'Next stop':'Start your first stop')+'</span><span class="bs">'+tc.stops[ni].name+' · '+tc.name+'</span></button>';
    var nb=got>0?nextBadge():null;
    var st=got>0?'<div class="stl"><div class="snum"><b>'+got+'</b><span>of '+total+' stamps</span></div><p class="sverd">Explorer level '+lv.n+' · '+lv.title+' <span class="snext">· '+nfmt(lv.to-gs.xp)+' XP to level '+(lv.n+1)+'</span></p>'+(nb?'<p class="sgoal">Next badge: '+nb.b.n+' · '+nb.cur+' of '+nb.goal+'</p>':'')+'</div>':'';
    return '<section class="stat" aria-label="Your progress">'+st+btn+'</section>';
  }
  function ringsHtml(){
    var seen={}, list=[];
    function add(k){ if(CITIES[k]&&!seen[k]){ seen[k]=1; list.push(k); } }
    [cityId].concat(ORDER).forEach(function(k){ if(CITIES[k]){ var d=sum(ALL[k].done); if(d>0&&d<CITIES[k].stops.length) add(k); } });
    var started=list.length;
    tripGet().forEach(function(k){ var d=CITIES[k]?sum(ALL[k].done):0; if(CITIES[k]&&d<CITIES[k].stops.length) add(k); });
    ORDER.forEach(function(k){ if(list.length<10&&CITIES[k]&&CITIES[k].level==='Classics'&&!sum(ALL[k].done)) add(k); });
    list=list.slice(0,10);
    if(!list.length) return '';
    return '<section class="rings" aria-label="Towns to continue"><p class="mono">'+(started?'Jump back in':'Try one of these')+'</p><div class="rrow">'+list.map(function(k){
      var c=CITIES[k], n=sum(ALL[k].done), pc=Math.round(n/c.stops.length*100), key=c.heroKey||((BMAPS[k]||{})[c.stops[0].id]||[])[0], img=(key&&PHOTOS[key])?'<img loading="lazy" decoding="async" src="'+PHOTOS[key]+'" alt="">':'';
      return '<button class="rbtn" data-a="city" data-c="'+k+'" aria-label="'+c.name+', '+n+' of '+c.stops.length+' stamps"><span class="rg" style="--p:'+pc+'"><span class="rph">'+img+'</span></span><span class="rn">'+c.name+'</span></button>';
    }).join('')+'</div></section>';
  }
  // Daily Fact or Fiction card (website only; the daily page and the game share this origin's storage)
  function dailyCardHtml(){
    if(!(/^https?:$/.test(location.protocol)&&/stampthepast\.com$/.test(location.hostname))) return '';
    var n=new Date(), ds=n.getFullYear()+'-'+('0'+(n.getMonth()+1)).slice(-2)+'-'+('0'+n.getDate()).slice(-2), played=null, st=null;
    try{ played=JSON.parse(localStorage.getItem('stp-daily')||'null'); st=JSON.parse(localStorage.getItem('stp-daily-streak')||'null'); }catch(e){}
    var done=!!(played&&played.d===ds), streak=st&&st.n>1?' · '+st.n+' days in a row':'';
    return '<section class="dailycard" aria-label="Daily Fact or Fiction"><button class="rcard" data-a="daily"><span><strong>Daily Fact or Fiction</strong><span class="rsub">'+(done?'Played today'+streak+'. A new claim tomorrow.':'One claim a day. Solid, disputed or a tall tale?'+streak)+'</span></span><span class="go">'+(done?'See it':'Play')+' ›</span></button></section>';
  }
  // "Protect your stamps": after the first stamp, then again every 8 stamps (shared by Home and the town trail)
  function bkNudgeHtml(){
    var ts=totalStamps(), seen=bkSeen();
    if(!(ts>=1&&(seen<0||ts>=seen+8))) return '';
    return '<section class="card nudge" aria-label="Back up reminder"><h3>Protect your stamps</h3><p>Your passport is saved on this phone only. Copy your backup code so a new phone or a cleared browser does not erase it.</p><div class="row2"><button class="btn small" data-a="backup">Back up now</button><button class="btn small ghost" data-a="bkdismiss">Not now</button></div></section>';
  }
  function viewHome(){
    var got=0,total=0;
    ORDER.forEach(function(k){ total+=CITIES[k].stops.length; got+=sum(ALL[k].done); });
    var hk=homeTown(), stamps=stampsHtml();
    document.body.classList.toggle('homefirst',got===0);
    var res0=null; [cityId].concat(ORDER).forEach(function(k){ if(!res0&&CITIES[k]){ var d0=sum(ALL[k].done); if(d0>0&&d0<CITIES[k].stops.length) res0=k; } });
    var h='<section class="home-hero'+(got>0?' ret':'')+'"><div><div class="wordmark" role="img" aria-label="Stamp the Past">Stamp the Past</div><h1>Go there.<br>Prove it.<br>Stamp it.</h1><p class="sub">A mission game for real places. Travel to the spot, answer what is in front of you, sort fact from tall tale, and watch the past fade into the present.</p><button class="btn heroGo" data-a="gomissions">'+(got>0?'Choose a mission':'Pick a mission')+'</button></div><div class="hstamps" aria-label="Four passport stamps, each a real photo of a landmark">'+stamps+'</div></section>';
    var how=got>0?'':'<section class="howto" aria-label="How it works"><h2>How it works</h2><ol><li><b>Go there.</b> Pick a mission and walk or drive to a real landmark.</li><li><b>Prove it.</b> Tap "I am here", read the story, answer the question in front of you.</li><li><b>Stamp it.</b> Each stamp earns XP, points that raise your level and unlock badges.</li></ol><p class="hint">Not near a mission? Open any stop and tap "Explore from home" to read it and fade the photos. Stamps are saved for real visits.</p></section>';
    var nearH='<div id="nearBox" class="nearbox">'+nearHtml()+'</div>'+(got===0?startTownHtml():'');
    h=(got>0?statusHtml(got,total,res0,hk)+bkNudgeHtml()+nearH+featuredHtml()+ringsHtml()+dailyCardHtml()+h:nearH+h+how+ringsHtml()+dailyCardHtml());
    var vcount=0; ORDER.forEach(function(k){ CITIES[k].stops.forEach(function(st){ if(st.verified&&st.verified.on) vcount++; }); });
    var res=null; [cityId].concat(ORDER).forEach(function(k){ if(!res&&CITIES[k]){ var d=sum(ALL[k].done); if(d>0&&d<CITIES[k].stops.length) res=k; } });
        var passTop=got>0?'<section class="passport" id="passport"><button class="rcard" data-a="mypass"><span><strong>Your passport</strong><span class="rsub">'+got+' of '+total+' stamps earned'+(totalPts()?' · '+totalPts()+' challenge points':'')+'</span></span><span class="go">Open ›</span></button></section>':'';
    h+=goalHtml();
    function townLi(k){
      var c=CITIES[k], st=ALL[k], n=sum(st.done), x=sum(st.done)*100+sum(st.claims)*25, rk=c.ranks[0][1];
      c.ranks.forEach(function(r){ if(x>=r[0]) rk=r[1]; });
      var key=c.heroKey||((BMAPS[k]||{})[c.stops[0].id]||[])[0], img=(key&&PHOTOS[key])?'<img loading="lazy" decoding="async" src="'+PHOTOS[key]+'" alt="">':'';
      var label=n===c.stops.length?'Complete':(n>0?'Continue':'Start');
      return '<li data-q="'+stOf(k).toLowerCase()+'"><button class="town" data-a="city" data-c="'+k+'"><span class="tph">'+img+'</span><span class="tin"><h3>'+c.name+'</h3>'+(c.level?'<span class="lvl '+(c.level==='Classics'?'ic':'dc')+'">'+(c.level==='Classics'?'Classics · easy':'Hidden Gems · harder')+'</span>':'')+'<span class="sub">'+(TSTATE[k]?TSTATE[k]+' · ':'')+n+' of '+c.stops.length+' stamps · '+rk+'</span></span><span class="go">'+label+' ›</span></button><button class="tstar'+(tripGet().indexOf(k)>-1?' on':'')+'" data-a="trip" data-c="'+k+'" aria-pressed="'+(tripGet().indexOf(k)>-1?'true':'false')+'" aria-label="'+(tripGet().indexOf(k)>-1?'Remove '+c.name+' from my trip':'Add '+c.name+' to my trip')+'">'+(tripGet().indexOf(k)>-1?'★':'☆')+'</button></li>';
    }
    function soonLi(o){ var nm=(typeof o==='string')?o:o.name; return '<li><div class="town soon"><span class="tph"></span><span class="tin"><h3>'+nm+'</h3><span class="sub">Coming soon</span></span></div></li>'; }
    var regs=[]; ORDER.forEach(function(k){ var r=CITIES[k].region||'More places'; if(regs.indexOf(r)<0) regs.push(r); });
    SOON.forEach(function(o){ var r=(typeof o==='string')?'More places':(o.region||'More places'); if(regs.indexOf(r)<0) regs.push(r); });
    h+=browseOpen()+'<section id="missions"><h2 class="hh">Pick a mission</h2>'+chipsHtml()+'<label class="tsearch"><span class="sr">Search towns or states</span><input id="townSearch" type="search" placeholder="Search towns or states" autocomplete="off" autocapitalize="words" spellcheck="false" aria-controls="missions"></label><p class="tnone" id="townNone" hidden>No town matches. Try another spelling.</p>'+regs.map(function(r){
      var items=ORDER.filter(function(k){ return (CITIES[k].region||'More places')===r; }).map(townLi).join('')+SOON.filter(function(o){ return ((typeof o==='string')?'More places':(o.region||'More places'))===r; }).map(soonLi).join('');
      var rk=ORDER.filter(function(k){ return (CITIES[k].region||'More places')===r; }), rg=0, rt=0; rk.forEach(function(k){ rg+=sum(ALL[k].done); rt+=CITIES[k].stops.length; });
      var open=(CITIES[cityId]&&(CITIES[cityId].region||'More places')===r)||(regs[0]===r&&!(CITIES[cityId]&&(ALL[cityId]&&sum(ALL[cityId].done)>0)));
      return '<details class="reg"'+(open?' open':'')+'><summary class="region"><span class="rname"><i class="ring" style="--p:'+(rt?Math.round(rg/rt*100):0)+'" aria-hidden="true"></i>'+r+'</span><span class="rcount">'+(rt?rg+' of '+rt+' stamps':'soon')+'</span></summary><ul class="towns">'+items+'</ul></details>';
    }).join('')+'<p class="passport-line"><strong>'+got+' of '+total+'</strong> stamps collected across '+ORDER.length+' missions.</p></section>';
    h+='</div><div class="bpanel" id="bp-trails" role="tabpanel"'+(btab==='trails'?'':' hidden')+'>'+trailsHtml()+'</div><div class="bpanel" id="bp-trip" role="tabpanel"'+(btab==='trip'?'':' hidden')+'>'+tripHtml()+'</div></section>';
    if(got>0) h+='<details class="pitch"><summary><span class="mono">About</span><strong>How Stamp the Past works</strong></summary>';
    var hs=CITIES[hk].stops, HT=[['Find the spot','A clue sends you to a real landmark. Bring your own two feet.'],['Prove it','Answer a question about what is right in front of you.'],['Fact or fiction','Is the famous story solid, disputed, or a tall tale? Historians argue. Now so can you.'],['Get stamped','Every stop adds a stamp to your passport and a Then/Now photo you can fade through.']];
    h+='<section class="navy"><p class="mono">How it works</p><h2>Four steps. One stamp.</h2><p class="why" style="color:inherit;opacity:.85">Pictured: your current mission, '+CITIES[hk].name+'.</p><div class="hsteps">'+HT.map(function(t,i){ var st=hs[i]; return '<div class="hstep"><span class="bbox sm" aria-hidden="true">'+badge(st.id,true,hk)+'</span><b>'+(i+1)+'</b><h3>'+t[0]+'</h3><p>'+t[1]+'</p><p class="mono" style="opacity:.8">e.g. '+st.name+'</p></div>'; }).join('')+'</div></section>';
    if(PHOTOS.arch_now&&PHOTOS.sign1973) h+='<section class="hsec"><p class="mono">Then and now</p><h2 class="hh2">Swipe back through time.</h2><p>Swipe the photo or drag the slider. Every stop unlocks a real old photo next to a current one. This one is the Reno Arch, 1973 to 2021.</p><div class="cmp" style="margin-top:12px"><div class="box"><img src="'+PHOTOS.arch_now+'" alt="The Reno Arch in 2021"><img class="top" src="'+PHOTOS.sign1973+'" alt="The Reno sign in 1973"></div><div class="row"><span>Now</span><input type="range" min="0" max="100" value="0" aria-label="Fade from now to 1973" data-cmp="1"><span>1973</span></div></div></section>';
    h+='<section class="hsec"><p class="mono">The part nobody else does</p><h2 class="hh2">Is that actually true?</h2><p>Every story comes with claims to sort: well documented, disputed, or not true. Every answer shows its sources, so the game rewards checking, not guessing.</p><div id="homefof" style="margin-top:12px">'+homeFof()+'</div></section>';
    h+='<section class="grown"><p class="mono">For parents (the grown-up section)</p><h2 class="hh2">A game that makes your teen read a plaque. Voluntarily.</h2><ul><li>No accounts and no sign-up</li><li>Location is optional, used only on the phone and never sent anywhere</li><li>No photo uploads</li><li>No ads</li><li>Every story shows its sources</li><li>Every photo shows its credit</li>'+(vcount?'<li>'+vcount+' of '+total+' stops verified on site by the makers</li>':'')+'</ul></section>';
    if(got>0) h+='</details>';
    h+='<p class="home-foot"><strong>Made by a mom and her teenage son.</strong><br>The West, the Midwest, the South, the East and the Southwest so far. More regions on the way.<br><button class="link" data-a="menu">Menu: backup, help, settings</button></p>';
    return h;
  }
  function curTownLine(){
    try{ var n=nextRef(); if(!n) return ''; var c=CITIES[n.k], d=sum(ALL[n.k].done), t=c.stops.length; if(d<=0||d>=t) return '';
      return '<p class="pcur"><b>Right now: '+c.name+'</b> · '+d+' of '+t+' stamps, '+(t-d)+' to go</p>'; }catch(e){ return ''; }
  }
  function viewPass(){
    var got=0,total=0,full=0,seals=0,b=bossBest();
    ORDER.forEach(function(k){ total+=CITIES[k].stops.length; var d=sum(ALL[k].done); got+=d; if(d===CITIES[k].stops.length) full++; if(sealTier(b[k])) seals++; });
    var regs=[]; ORDER.forEach(function(k){ var r=CITIES[k].region||'More places'; if(regs.indexOf(r)<0) regs.push(r); });
    var h='<section class="passhead"><p class="mono">Stamp the Past</p><h1 class="hh2">Your passport</h1><div class="pstats"><div><b>'+got+'</b><span>of '+total+' stamps</span></div><div><b>'+full+'</b><span>of '+ORDER.length+' towns done</span></div><div><b>'+seals+'</b><span>challenge seals</span></div><div><b>'+totalPts()+'</b><span>challenge points</span></div></div>'+curTownLine()+(seals===0?'<p class="pnote">Challenge seals and points come from a town\'s final challenge. Stamp every stop in a town to unlock it.</p><button class="btn small" data-a="'+(got>0?'nextstop':'gomissions')+'">'+(got>0?'Go to my next stop':'Pick a town')+'</button>':'')+(got>0?'<button class="btn small" data-a="share" data-k="" style="margin-top:12px">Share my passport</button>':'')+'</section>';
    var bd=bdAll(); h+=levelHtml(bd.s)+trophyHtml(bd);
    h+='<section class="passport" id="passport">'+regs.map(function(r){ var rk=ORDER.filter(function(k){ return (CITIES[k].region||'More places')===r; }); if(!rk.length) return ''; var g=0,t=0; rk.forEach(function(k){ g+=sum(ALL[k].done); t+=CITIES[k].stops.length; }); return '<details class="reg ppreg"'+(g>0?' open':'')+'><summary class="region"><span>'+r+'</span><span class="rcount">'+g+' of '+t+' stamps</span></summary>'+rk.filter(function(k){ return sum(ALL[k].done)>0; }).map(function(k){
      var c=CITIES[k], d=sum(ALL[k].done);
      return '<div class="pprow'+(d===c.stops.length?' full':'')+'"><div class="ppname"><strong>'+c.name+'</strong><span class="mono">'+d+' of '+c.stops.length+(d===c.stops.length?' · complete':'')+(bossBest()[k]!==undefined?' · challenge '+bossBest()[k]+'/4':'')+'</span></div><div class="ppstamps">'+(sealTier(bossBest()[k])?'<span class="bbox sm sealbox" title="'+SEALS[sealTier(bossBest()[k])][3]+'">'+seal(sealTier(bossBest()[k]),38)+'</span>':'')+c.stops.map(function(st,i){ return '<span class="bbox sm" title="'+st.badge+'">'+badge(st.id,ALL[k].done[i],k)+'</span>'; }).join('')+'</div></div>';
    }).join('')+(function(){ var n=rk.filter(function(k){ return sum(ALL[k].done)===0; }).map(function(k){ return CITIES[k].name; }); return n.length?'<p class="pp-rest"><strong>'+n.length+' not started:</strong> '+n.join(', ')+'</p>':''; })()+'</details>'; }).join('')+'<p class="passport-line"><strong>'+got+' of '+total+'</strong> stamps. Blank circles are waiting for you.'+(totalPts()?' Challenge points: <strong>'+totalPts()+'</strong>.':'')+'</p>'+(grandOk()?'<div class="grand-line">'+seal('grand',56)+' <span><strong>Grand Historian.</strong> Gold seal in every town.</span></div>':'')+'</section>';
    var vl=[]; ORDER.forEach(function(k){ CITIES[k].stops.forEach(function(st,i){ if(virtHas(k,i)) vl.push({k:k,i:i,st:st}); }); });
    if(vl.length) h+='<section class="card vpass" id="vpass"><h3>Explored from home</h3><p class="mono">'+vl.length+' virtual stamp'+(vl.length>1?'s':'')+' · 25 XP each</p><ul class="vlist">'+vl.map(function(x){ return '<li><span class="bbox sm virt">'+badge(x.st.id,true)+'</span><span><strong>'+x.st.name+'</strong><em>'+CITIES[x.k].name+'</em></span></li>'; }).join('')+'</ul><p class="hint">Go there to turn each one into a full stamp worth 100 XP. Virtual stamps are not part of the backup code below.</p></section>';
    h+='<section class="card" id="backup"><h3>Back up your passport</h3><p>Your stamps live on this phone only, which is great for privacy but means a lost phone loses them. Copy this code and keep it somewhere safe (a note, a message to yourself). On a new phone, paste it below. No account needed.</p><div class="code"><input id="codeOut" readonly value="'+code()+'" aria-label="Progress code"><button class="btn small" data-a="copy">Copy</button></div><div class="code"><input id="codeIn" placeholder="Paste a code" aria-label="Paste a progress code" autocomplete="off" autocapitalize="characters" spellcheck="false"><button class="btn small ghost" data-a="restore">Restore</button></div><p id="codeMsg" class="why" aria-live="polite"></p></section>';
    return h;
  }
  function homeAnswer(k){
    var c=HCL[hi];
    if(k===c.a){ hcls='good'; hmsg='Right. '+c.why;
      if(hi<HCL.length-1){ hi++; hmsg+=' Next one is below.'; } else { hdone=true; hmsg+=' That is the game. Pick a town and try it for real.'; }
    } else { hcls='bad'; hmsg='Not quite. Try again.'; }
    var el=document.getElementById('homefof'); if(el) el.innerHTML=homeFof();
  }

  function viewTrail(){
    var h='';
    if(allDone()){
      h+='<section class="done-banner pop" aria-label="Mission complete"><div class="bbox lg">'+badge('master',true)+'</div><div><h2>'+city().explorer+'</h2><p>'+city().afterDone+'</p></div></section>';
      if(((DATA.boss||{})[cityId]||[]).length){ var bb=bossBest()[cityId]; h+='<section class="card"><p class="mono">Final challenge</p><p>Four questions across every stop. No hints, no do-overs inside a run.'+(bb!==undefined?' Your best: <strong>'+bb+' of 4</strong>.':'')+'</p>'+(sealTier(bb)?'<div class="sealwrap">'+seal(sealTier(bb),64)+'<strong>'+SEALS[sealTier(bb)][3]+'</strong></div>':'<p class="why">Score 2 of 4 or better to earn a seal.</p>')+'<button class="btn" data-a="boss">'+(bb!==undefined?'Play again':'Start the final challenge')+'</button></section>'; }
    } else {
      var nm=STOPS.map(function(s){ return s.name; }); var lst=nm.slice(0,-1).join(', ')+' and '+nm[nm.length-1];
      h+='<section class="card"><h3>Your mission</h3><p>'+(sum(S.done)===0?city().mission:'On your list: '+lst+'. Do them in any order.')+'</p>'+(sum(S.done)===0?'<p class="why" style="margin:8px 0 0">On your list: '+lst+'.</p>':'')+(tourInfo(city())?'<p class="tourinfo">'+tourInfo(city())+'</p>':'')+(((DATA.boss||{})[cityId]||[]).length?'<p class="why finalnote">Finish all four to unlock the final challenge: four questions across every stop, and a seal to earn.</p>':'')+'</section>';
    }
    h+=bkNudgeHtml();
    h+='<ul class="stops">'+STOPS.map(function(s,i){
      var d=S.done[i];
      return '<li><button class="stop" data-a="open" data-i="'+i+'"><span class="bbox'+(!d&&virtHas(cityId,i)?' virt':'')+'">'+badge(s.id,d||virtHas(cityId,i))+(!d&&virtHas(cityId,i)?'<i class="vtag">Virtual</i>':'')+'</span><span><h3>'+s.name+'</h3><span class="sub">'+s.teaser+'</span><br><span class="status'+(d?' ok':(virtHas(cityId,i)?' virt':''))+'">'+(d?'Badge earned':(virtHas(cityId,i)?'Virtual stamp':'Not found yet'))+'</span>'+(s.verified&&s.verified.on?' <span class="vchip">Verified</span>':'')+(s.spot?' <span class="vchip puz">Puzzle</span>':'')+(d&&geoVerified(cityId,i)?' <span class="vchip gold">Visit verified</span>':'')+(d&&s.geo&&!geoVerified(cityId,i)&&!geoDenied?' <span class="vchip">Tap to verify when you visit</span>':'')+'</span><span class="chev" aria-hidden="true">›</span></button></li>';
    }).join('')+'</ul>';
    h+='<details class="card"><summary>Privacy and photo credits</summary><ul><li>This page has no accounts, uploads or camera use. Location is optional and only checked on your phone, never sent anywhere. Badges and XP are saved only in this browser.</li><li>Photos come from Wikimedia Commons under free licenses, with credit under each one. Where no free photo exists yet, the app says so instead of showing a stand-in.</li></ul>'+creditsList()+'</details>';
    return h;
  }

  var menuFrom=null;
  function themeGet(){ try{ var t=localStorage.getItem('stp-theme'); return (t==='light'||t==='dark')?t:'system'; }catch(e){ return 'system'; } }
  function themeApply(t){ var r=document.documentElement; if(t==='light'||t==='dark') r.setAttribute('data-theme',t); else r.removeAttribute('data-theme'); }
  themeApply(themeGet());
  function menuHtml(){
    var got=totalStamps(), th=themeGet();
    var ex=function(txt){ return '<li>'+txt+'</li>'; };
    var seg=['system','light','dark'].map(function(t){ return '<button class="seg'+(th===t?' on':'')+'" data-a="theme" data-t="'+t+'" aria-pressed="'+(th===t)+'">'+(t==='system'?'Match phone':t.charAt(0).toUpperCase()+t.slice(1))+'</button>'; }).join('');
    var item=function(a,label,sub,extra){ return '<button class="mitem" data-a="'+a+'"'+(extra||'')+'><span><strong>'+label+'</strong>'+(sub?'<span class="msub">'+sub+'</span>':'')+'</span><span class="go" aria-hidden="true">›</span></button>'; };
    return '<div class="menu-panel" role="document"><div class="menu-head"><h2 id="menuT">Menu</h2><button class="menu-x" data-a="menuclose" aria-label="Close menu">&times;</button></div>'
     +'<p class="mgroup">Your passport</p>'
     +item('backup','Back up your passport','Save a code so a lost phone does not lose your stamps')
     +(got>0?item('share','Share my passport','Make a picture of your stamps',' data-k=""'):'')
     +(/^https?:$/.test(location.protocol)?'<p class="mgroup">Play anywhere</p>'+item('daily','Daily Fact or Fiction','One claim a day, with sources. No travel needed'):'')
     +'<p class="mgroup">Settings</p>'
     +'<div class="mrow"><span id="thl">Appearance</span><div class="segs" role="group" aria-labelledby="thl">'+seg+'</div></div>'
     +(geoGranted()?'<div class="mrow"><span id="lvl">Live location while the app is open</span><div class="segs"><button class="seg on" data-a="livetoggle" aria-labelledby="lvl" aria-pressed="'+liveOn()+'">'+(liveOn()?'On':'Off')+'</button></div></div>':'')
     +(NG?'<div class="mrow"><span id="bgl">Alert me near stops, even when the app is closed</span><div class="segs"><button class="seg on" data-a="bgtoggle" aria-labelledby="bgl" aria-pressed="'+bgOn()+'">'+(bgOn()?'On':'Off')+'</button></div></div><p class="msub">iPhone asks for "Always" location. It only watches the 20 nearest stops, and nothing leaves your phone.</p>':'')
     +'<p class="mgroup">Help</p>'
     +item('report','Report a problem or send feedback','Tell us what is wrong or confusing')
     +'<details class="mdet mhelp"><summary>Guide and about</summary>'
     +item('replaytour','Replay the guide','The quick tour of how a stop works')
     +(isNativeApp()?item('hapticTest','Test the stamp buzz','Feel the little tap you get when a stamp is earned'):'')
     +'<details class="mdet"><summary>How Stamp the Past works</summary><ol><li><strong>Find the spot.</strong> A clue sends you to a real landmark.</li><li><strong>Prove it.</strong> Answer a question about what is right in front of you.</li><li><strong>Fact or fiction.</strong> Sort the famous story into solid, disputed or not true.</li><li><strong>Get stamped.</strong> Every stop adds a stamp and a then and now photo.</li></ol></details>'
     +(/^https?:$/.test(location.protocol)&&/stampthepast\.com$/.test(location.hostname)?'<a class="mlink" href="/">About Stamp the Past (our website)</a>':'')
     +'</details>'
     +'<p class="mgroup">Privacy</p>'
     +'<details class="mdet"><summary>For parents and grown-ups</summary><ul><li>No accounts and no sign-up</li><li>Location is optional and stays on your phone</li><li>No photo uploads</li><li>No ads</li><li>Every story shows its sources</li><li>Every photo shows its credit</li></ul></details>'
     +'<details class="mdet"><summary>Photo credits for '+city().name+'</summary>'+creditsList()+'</details>'
     +'<p class="mgroup">Account</p>'
     +'<div class="macct"><strong>No account needed.</strong><span class="msub">Your stamps live on this phone. Use a backup code to move them to a new one. Optional sign-in may come later, so your stamps can follow you between devices.</span></div>'
     +'<p class="mfoot">Made by a mom and her teenage son.</p></div>';
  }
  function openMenu(){
    closeMenu(); menuFrom=document.activeElement;
    var d=document.createElement('div'); d.id='menu'; d.className='menu'; d.setAttribute('role','dialog'); d.setAttribute('aria-modal','true'); d.setAttribute('aria-labelledby','menuT');
    d.innerHTML='<div class="menu-scrim" data-a="menuclose"></div>'+menuHtml(); document.body.appendChild(d); document.body.classList.add('menuopen');
    var f=d.querySelector('.menu-x'); if(f) f.focus();
  }
  function closeMenu(){ var e=document.getElementById('menu'); if(e){ e.remove(); document.body.classList.remove('menuopen'); if(menuFrom&&menuFrom.focus&&document.body.contains(menuFrom)) try{ menuFrom.focus(); }catch(x){} } }
  function celebKeyGet(){ try{ return JSON.parse(localStorage.getItem('then-now-cel')||'{}')||{}; }catch(e){ return {}; } }
  function celebrate(){
    var kv=celebKeyGet(); if(kv[cityId]) return; kv[cityId]=1; try{ localStorage.setItem('then-now-cel',JSON.stringify(kv)); }catch(e){}
    var c=city(), x=xp(), r=rank(x), old=document.getElementById('celeb'); if(old) old.remove();
    var cf=''; for(var q=0;q<14;q++) cf+='<i style="--x:'+(q*7+3)+'%;--d:'+((q%5)*0.12)+'s;--c:'+(q%3)+'"></i>';
    var d=document.createElement('div'); d.id='celeb'; d.className='celeb'; d.setAttribute('role','dialog'); d.setAttribute('aria-modal','true'); d.setAttribute('aria-labelledby','celebT');
    d.innerHTML='<div class="celeb-card"><div class="confetti" aria-hidden="true">'+cf+'</div><div class="celeb-stamp"><div class="bbox lg">'+badge('master',true)+'</div></div><p class="mono">Mission complete</p><h2 id="celebT">'+c.explorer+'</h2><p>'+c.afterDone+'</p><p class="celeb-stats"><strong>'+r.name+'</strong> · '+x+' XP · 4 of 4 stamps</p><div class="celeb-btns">'+(((DATA.boss||{})[cityId]||[]).length?'<button class="btn" data-a="celebboss">Play the final challenge</button>':'')+'<button class="btn'+(((DATA.boss||{})[cityId]||[]).length?' ghost':'')+'" data-a="share" data-k="'+cityId+'">Share my stamps</button><button class="btn ghost" data-a="passport">See my passport</button><button class="btn ghost" data-a="celebclose">Keep exploring</button></div></div>';
    document.body.appendChild(d);
    var f=d.querySelector('button'); if(f) f.focus();
  }
  function closeCeleb(){ var e=document.getElementById('celeb'); if(e){ e.remove(); setTimeout(flushBadges,250); } }
  document.addEventListener('keydown',function(e){
    if(e.key==='Tab'){ var dlg=document.getElementById('report')||document.getElementById('menu')||document.getElementById('tour')||document.getElementById('celeb'); if(dlg&&dlg.offsetParent!==null||dlg&&getComputedStyle(dlg).display!=='none'){ var f=[].filter.call(dlg.querySelectorAll('button,a[href],input,select,textarea,summary,[tabindex]:not([tabindex="-1"])'),function(x){ return !x.disabled&&x.offsetParent!==null&&(!x.checkVisibility||x.checkVisibility()); }); if(f.length){ var first=f[0], last=f[f.length-1]; if(!dlg.contains(document.activeElement)){ first.focus(); e.preventDefault(); } else if(e.shiftKey&&document.activeElement===first){ last.focus(); e.preventDefault(); } else if(!e.shiftKey&&document.activeElement===last){ first.focus(); e.preventDefault(); } } } }
  });
  document.addEventListener('keydown',function(e){ if(e.key==='Escape'){ closeReport(); closeCeleb(); closeBpop(); closeMenu(); if(document.getElementById('tour')) endTour(); } });
  /* offline: the web version caches itself (sw.js). Say so when the connection changes. */
  try{ if('serviceWorker' in navigator && /^https?:$/.test(location.protocol)) navigator.serviceWorker.register('sw.js').catch(function(){}); }catch(e){}
  window.addEventListener('offline',function(){ toast('You are offline. Everything still works except map links.'); });
  window.addEventListener('online',function(){ toast('Back online.'); });
  var MON=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  function vdate(d){ var m=/^(\d{4})-(\d{2})/.exec(d||''); return m?MON[+m[2]-1]+' '+m[1]:''; }
  function vnote(st){
    var v=st.verified;
    if(v&&v.on) return '<div class="vbadge ok"><b>Verified on site</b><span>by '+v.by+(vdate(v.on)?' · '+vdate(v.on):'')+'</span>'+(v.note?'<em>'+v.note+'</em>':'')+'</div>';
    var fn=st.field.replace(/^Field notes pending:\s*/i,''); return '<div class="vbadge"><b>Researched from sources. On-site check coming</b>'+(/nobody has walked/i.test(fn)?'':'<span>'+fn+'</span>')+'</div>';
  }
  /* ---------- report a problem ---------- */
  function whereAmI(){
    if(cur) return city().name+' / '+STOPS[cur.i].name+' / step '+(cur.step+1);
    if(boss) return city().name+' / final challenge / question '+(boss.i+1);
    return atHome?(onPass?'Passport':'Home'):city().name+' / '+tab;
  }
  function showReport(){
    var old=document.getElementById('report'); if(old) old.remove();
    var d=document.createElement('div'); d.id='report'; d.className='celeb'; d.setAttribute('role','dialog'); d.setAttribute('aria-modal','true'); d.setAttribute('aria-labelledby','repT'); d.dataset.where=whereAmI();
    d.innerHTML='<div class="celeb-card tour-card rep-card"><h2 id="repT">Something wrong?</h2><p>Wrong answer, confusing screen, broken photo, or a plaque that says something else. Tell us in a sentence or two.</p><label class="mono" for="repMsg">What happened</label><textarea id="repMsg" maxlength="600" rows="4"></textarea><label class="mono" for="repWho">Your email (optional, only if you want a reply)</label><input id="repWho" type="email" maxlength="120" autocomplete="off"><p class="why">Please do not include personal details. We send along only where in the app you were: <em>'+d.dataset.where+'</em>.</p><p id="repMsgOut" class="feedback" aria-live="polite"></p><div class="celeb-btns"><button class="btn" data-a="repsend">Send</button><button class="btn ghost" data-a="repclose">Cancel</button></div></div>';
    document.body.appendChild(d); var f=document.getElementById('repMsg'); if(f) f.focus();
  }
  function closeReport(){ var e=document.getElementById('report'); if(e){ e.remove(); var m=document.getElementById('menuBtn'); if(m&&m.offsetParent!==null&&(!document.activeElement||document.activeElement===document.body)) try{ m.focus(); }catch(x){} } }
  function sendReport(){
    var d=document.getElementById('report'); if(!d) return;
    var msg=document.getElementById('repMsg').value.trim(), out=document.getElementById('repMsgOut');
    if(!msg){ out.className='feedback bad'; out.textContent='Write a sentence first.'; return; }
    var body=new URLSearchParams({'form-name':'report','bot-field':'','where':d.dataset.where,'message':msg,'contact':document.getElementById('repWho').value.trim()}).toString();
    out.className='feedback'; out.textContent='Sending...';
    var web=/^https?:$/.test(location.protocol);
    fetch(web?'/':'https://stampthepast.com/',{method:'POST',mode:web?'same-origin':'no-cors',headers:{'Content-Type':'application/x-www-form-urlencoded'},body:body}).then(function(r){
      if(web&&!r.ok) throw new Error('bad'); closeReport(); toast('Thanks. Sent.');
    }).catch(function(){ out.className='feedback bad'; out.textContent='Could not send from here. Try the test site, or check your connection.'; });
  }
  /* ---------- first-run tour ---------- */
  var TOUR=[
    {h:'Go there. Prove it.',p:'A history game played on real streets. Sixty seconds to learn the moves, then you are on your own. Bring shoes.',ill:'hello',nx:'Show me'},
    {h:'Find it. Prove it.',p:'Every town is four real landmarks. A clue sends you there. Stand in front of it, tap "I am here", and answer a question about what is right in front of you.',ill:'find'},
    {h:'Travel back',p:'Every stamp unlocks a real old photo. Drag the slider to fade between then and now.',ill:'cmp'},
    {h:'Fact or fiction',p:'Famous stories are often wrong. Sort each claim: documented, disputed, or not true. Every stamp lands in your passport, and you can replay this guide from Home.',ill:'fof',nx:'Pick a mission',done:1}
  ], tourI=0;
  var TILL={
    hello:'<div class="ti ti-hero"><span>A history game</span><b>Stamp<br>the Past</b></div>',
    town:'<div class="ti"><div class="ti-town on"><i></i><span><b>Reno</b><small>0 of 4 stamps</small></span><em>START ›</em></div><div class="ti-town"><i></i><span><b>Seattle</b><small>0 of 4 stamps</small></span><em>START ›</em></div></div>',
    find:'<div class="ti"><div class="ti-card"><span class="mono">Find it</span><p>Go to the corner of Commercial Row and Lake Street. Look for the old brick depot.</p><div class="ti-btn">I am here</div></div></div>',
    quiz:'<div class="ti"><div class="ti-card"><span class="mono">Check in</span><p><b>What is carved above the main door?</b></p><div class="ti-opt">A year</div><div class="ti-opt ok">A name</div></div></div>',
    cmp:'<div class="ti"><div class="ti-cmp"><span style="left:8px">THEN</span><span style="right:8px">NOW</span></div><div class="ti-sl"></div></div>',
    fof:'<div class="ti"><div class="ti-claim">The first depot burned down in 1905.</div><div class="ti-chips"><span>Well documented</span><span>Disputed</span><span>Not true</span></div></div>',
    pass:'<div class="ti"><div class="ti-stamps"><i class="f"></i><i class="f"></i><i></i><i></i><i></i><i></i></div></div>'
  };
  function maybeTour(){
    var seen=null; try{ seen=localStorage.getItem('then-now-tour'); }catch(e){}
    if(seen) return;
    var anyProgress=false; ORDER.forEach(function(k){ if(sum(ALL[k].done)>0) anyProgress=true; });
    if(anyProgress){ try{ localStorage.setItem('then-now-tour','1'); }catch(e){} return; }
    tourI=0; showTour();
  }
  function showTour(){
    var old=document.getElementById('tour'); if(old) old.remove();
    var t=TOUR[tourI], n=TOUR.length;
    var d=document.createElement('div'); d.id='tour'; d.className='celeb'; d.setAttribute('role','dialog'); d.setAttribute('aria-modal','true'); d.setAttribute('aria-labelledby','tourT');
    d.innerHTML='<div class="celeb-card tour-card"><p class="mono">'+(tourI===0?'Quick tour':'Step '+(tourI+1)+' of '+n)+'</p>'+TILL[t.ill]+'<h2 id="tourT">'+t.h+'</h2><p>'+t.p+'</p><div class="tour-dots" aria-hidden="true">'+TOUR.map(function(_,i){ return '<i'+(i===tourI?' class="on"':'')+'></i>'; }).join('')+'</div><div class="celeb-btns"><button class="btn" data-a="tournext">'+(t.nx||'Next')+'</button>'+(tourI>0?'<button class="btn ghost" data-a="tourback">Back</button>':'')+(t.done?'':'<button class="link tour-skip" data-a="tourskip">Skip the tour</button>')+'</div></div>';
    document.body.appendChild(d); var f=d.querySelector('button'); if(f) f.focus();
  }
  function replayTour(){ tourI=0; showTour(); }
  function endTour(){ var e=document.getElementById('tour'); if(e) e.remove(); try{ localStorage.setItem('then-now-tour','1'); }catch(x){} }
  /* ---------- final challenge (boss round) ---------- */
  var boss=null;
  function bossBest(){ try{ return JSON.parse(localStorage.getItem('then-now-boss')||'{}')||{}; }catch(e){ return {}; } }
  var SEALS={gold:['#f2cf72','#b8872a','#6e4b0c','Gold Seal','Master Historian'],silver:['#eceff3','#9aa3b0','#566070','Silver Seal','Sharp Eye'],bronze:['#e8b58a','#a8693a','#643415','Bronze Seal','Plaque Reader'],grand:['#f2cf72','#1d3557','#f2cf72','Grand Historian','Gold in every town']};
  function sealTier(n){ return n>=4?'gold':(n===3?'silver':(n===2?'bronze':null)); }
  function ptsOf(n){ return n===undefined||n===null?0:50*n+(n>=4?100:0); }
    var TSTATE={"reno":"NV","vc":"NV","sparks":"NV","carson":"NV","tahoeicons":"CA/NV","tahoe":"CA/NV","boston":"MA","dc":"DC","ny":"NY","chicago":"IL","sf":"CA","philly":"PA","la":"CA","seattle":"WA","nola":"LA","detroit":"MI","minneapolis":"MN","atlanta":"GA","memphis":"TN","savannah":"GA","denver":"CO","santafe":"NM","phoenix":"AZ","albuquerque":"NM","tucson":"AZ","pittsburgh":"PA","baltimore":"MD","cleveland":"OH","stlouis":"MO","cincinnati":"OH","indianapolis":"IN","buffalo":"NY","richmond":"VA","charleston":"SC","houston":"TX","nashville":"TN","providence":"RI","saltlake":"UT","sandiego":"CA","portland":"OR","milwaukee":"WI","columbus":"OH","gettysburg":"PA","louisville":"KY","newport":"RI","knoxville":"TN","portlandme":"ME","newhaven":"CT","burlington":"VT","coloradosprings":"CO","lasvegas":"NV","flagstaff":"AZ","elpaso":"TX","sanantonio":"TX","dayton":"OH","honolulu":"HI","skagway":"AK","sitka":"AK","sacramento":"CA"}, TFULL={"NV":"Nevada","CA":"California","MA":"Massachusetts","DC":"District of Columbia Washington","NY":"New York","IL":"Illinois","PA":"Pennsylvania","WA":"Washington","LA":"Louisiana","MI":"Michigan","MN":"Minnesota","GA":"Georgia","TN":"Tennessee","CO":"Colorado","NM":"New Mexico","AZ":"Arizona","MD":"Maryland","OH":"Ohio","MO":"Missouri","IN":"Indiana","VA":"Virginia","SC":"South Carolina","TX":"Texas","RI":"Rhode Island","UT":"Utah","OR":"Oregon","WI":"Wisconsin","KY":"Kentucky","ME":"Maine","CT":"Connecticut","VT":"Vermont","HI":"Hawaii","AK":"Alaska"};
    function placeLabel(k){ var nm=CITIES[k].name, st=TSTATE[k]||''; return (!st||st==='DC'||/,\s*\S+$/.test(nm))?nm:nm+', '+st; }
    function stOf(k){ var a=TSTATE[k]||''; return a.split('/').map(function(x){return TFULL[x]||x;}).join(' ')+' '+a.replace('/',' '); }

  var DISP={DC:'Washington DC'};
  function logGet(){ try{ var a=JSON.parse(localStorage.getItem('stp-log')||'[]'); return Array.isArray(a)?a:[]; }catch(e){ return []; } }
  function dstr(d){ function z(n){ return (n<10?'0':'')+n; } return d.getFullYear()+'-'+z(d.getMonth()+1)+'-'+z(d.getDate()); }
  /* anonymous event counts (GoatCounter, web only; a no-op in the native app and offline). No ids, no places, no location. */
  function ping(n){ try{ if(window.goatcounter&&window.goatcounter.count) window.goatcounter.count({path:'event/'+n,title:n,event:true}); }catch(e){} }
  /* anonymous error counter: counts that something broke and the script line, never any message text or player data. Website only, at most 3 per visit. */
  var errSent=0;
  function errPing(line){ try{ if(errSent>=3) return; errSent++; if(window.goatcounter&&window.goatcounter.count) window.goatcounter.count({path:'event/error',title:'error L'+(line||0),event:true}); }catch(e){} }
  window.addEventListener('error',function(ev){ errPing(ev&&ev.lineno); });
  window.addEventListener('unhandledrejection',function(){ errPing(0); });
  function pingOnce(key,evt){ try{ var o=JSON.parse(localStorage.getItem('stp-pinged')||'{}'); if(o[key]) return; o[key]=1; localStorage.setItem('stp-pinged',JSON.stringify(o)); ping(evt); }catch(e){} }
  function logStamp(){ var a=logGet(); a.push(dstr(new Date())); if(a.length>500) a=a.slice(-500); try{ localStorage.setItem('stp-log',JSON.stringify(a)); }catch(e){} }
  function wkOf(ds){ var m=/^(\d{4})-(\d{2})-(\d{2})/.exec(ds); if(!m) return null; return Math.floor((Date.UTC(+m[1],+m[2]-1,+m[3])/86400000-4)/7); }
  function streakWeeks(){ var set={}; logGet().forEach(function(d){ var w=wkOf(d); if(w!==null) set[w]=1; }); var now=wkOf(dstr(new Date())), w=set[now]?now:now-1, n=0; while(set[w]){ n++; w--; } return n; }
  function monthStamps(){ var m=dstr(new Date()).slice(0,7); return logGet().filter(function(d){ return d.slice(0,7)===m; }).length; }
  function goalHtml(){
    var n=totalStamps(); var tw=weekTrailHtml(); if(n<1) return tw?'<section class="goal"><p class="mono">This week</p>'+tw+'</section>':'';
    var best=null; ORDER.forEach(function(k){ var d=sum(ALL[k].done), t=CITIES[k].stops.length; if(d>0&&d<t){ var left=t-d; if(!best||left<best.left) best={k:k,left:left}; } });
    var sw=streakWeeks(), ms=monthStamps(), bits=[];
    if(sw>0) bits.push('<strong>'+sw+(sw===1?' week':' weeks')+' in a row</strong> with a new stamp');
    if(ms>0) bits.push('<strong>'+ms+'</strong> '+(ms===1?'stamp':'stamps')+' this month');
    var goal=best?'<button class="rcard" data-a="city" data-c="'+best.k+'"><span><strong>Next goal: finish '+CITIES[best.k].name+'</strong><span class="rsub">'+best.left+' more '+(best.left===1?'stamp':'stamps')+' to complete it</span></span><span class="go">Go ›</span></button>':'<p class="rsub">Pick a new town below to start your next goal.</p>';
    return '<section class="goal"><p class="mono">Your progress</p>'+(bits.length?'<p class="gbits">'+bits.join(' · ')+'</p>':'')+goal+tw+'</section>';
  }
  // one calm featured trail per week (rotates, same for everyone, no timers)
  function weekTrailHtml(){
    var el=TRAILS.filter(function(tr){ return trailStops(tr.re).length>=3; }); if(!el.length) return '';
    var tr=el[Math.floor(Date.now()/604800000)%el.length], L=trailStops(tr.re), d=L.filter(function(x){ return x.done; }).length;
    return '<button class="rcard" data-a="trailweek" data-t="'+tr.id+'"><span><strong>Trail of the week: '+tr.name+'</strong><span class="rsub">'+d+' of '+L.length+' stamped. '+tr.note+'</span></span><span class="go">Open ›</span></button>';
  }
  function tripGet(){ try{ var a=JSON.parse(localStorage.getItem('stp-trip')||'[]'); return Array.isArray(a)?a.filter(function(k){ return CITIES[k]; }):[]; }catch(e){ return []; } }
  function tripSet(a){ try{ localStorage.setItem('stp-trip',JSON.stringify(a)); }catch(e){} }
  function savedRaw(){ try{ var a=JSON.parse(localStorage.getItem('stp-saved')||'[]'); return Array.isArray(a)?a.filter(function(x){ return typeof x==='string'; }):[]; }catch(e){ return []; } }
  function savedSet(a){ try{ localStorage.setItem('stp-saved',JSON.stringify(a)); }catch(e){} }
  function savedKey(k,i){ var st=CITIES[k]&&CITIES[k].stops[i]; return st?k+':'+st.id:''; }
  function isSaved(k,i){ var key=savedKey(k,i); return !!key&&savedRaw().indexOf(key)>-1; }
  function savedList(){ var out=[]; savedRaw().forEach(function(key){ var p=key.split(':'), k=p[0], c=CITIES[k]; if(!c) return; for(var i=0;i<c.stops.length;i++){ if(c.stops[i].id===p.slice(1).join(':')){ out.push({k:k,i:i}); break; } } }); return out; }
  var btab='towns', btrail='stations', bnavSel='home';
  (function(){ var ly=0, ut=0; function u(){ ut=Date.now(); } window.addEventListener('touchmove',u,{passive:true}); window.addEventListener('wheel',u,{passive:true}); window.addEventListener('scroll',function(){ var y=window.pageYOffset||0, d=y-ly; if(Math.abs(d)<10) return; ly=y; if(Date.now()-ut>1200) return; document.body.classList.toggle('navhide',d>0&&y>160); },{passive:true}); })();
  function updateBnav(){ var nb=document.getElementById('bnav'); if(!nb) return; var cur2=onPass&&atHome?'pass':(atHome?bnavSel:''); nb.querySelectorAll('button').forEach(function(x){ var on=x.getAttribute('data-t')===cur2; x.classList.toggle('on',on); if(on) x.setAttribute('aria-current','page'); else x.removeAttribute('aria-current'); if(x.getAttribute('data-t')==='pass'){ if(on) passSeenSet(); var nd=!on&&passNew(); x.classList.toggle('dot',nd); if(nd) x.setAttribute('aria-label','Passport, new stamps'); else x.removeAttribute('aria-label'); } }); }
  function passNew(){ try{ return totalStamps()>parseInt(localStorage.getItem('stp-pass-seen')||'0',10)||Object.keys(bdGet()).length>parseInt(localStorage.getItem('stp-bseen')||'0',10); }catch(e){ return false; } }
  function passSeenSet(){ try{ localStorage.setItem('stp-pass-seen',String(totalStamps())); localStorage.setItem('stp-bseen',String(Object.keys(bdGet()).length)); }catch(e){} }
  function tripHtml(){
    var t=tripGet(), sv=savedList();
    var svHtml=sv.length?'<p class="mono savedh">Saved stops</p><ul class="tlist">'+sv.map(function(x){ var st=CITIES[x.k].stops[x.i], dn=ALL[x.k].done[x.i]; return '<li class="trow'+(dn?' done':'')+'"><button class="trowb" data-a="neargo" data-c="'+x.k+'" data-i="'+x.i+'" data-far="1"><span class="tcheck" aria-hidden="true">'+(dn?'&#10003;':'')+'</span><span class="tn"><strong>'+st.name+'</strong><span class="sub">'+CITIES[x.k].name+(dn?' · Stamped':'')+'</span></span><span class="go">Open ›</span></button><button class="tstar on" data-a="savestop" data-c="'+x.k+'" data-i="'+x.i+'" aria-pressed="true" aria-label="Remove '+st.name.replace(/"/g,'&quot;')+' from saved stops">★</button></li>'; }).join('')+'</ul>':'';
    if(!t.length&&!sv.length) return '<div class="bempty"><h3>Plan a trip</h3><p>Tap the star on any town, or Save on any stop, to keep it here. You will see how many stamps are left in each place, like a checklist for the road.</p></div>';
    if(!t.length) return '<div class="trip" id="trip">'+svHtml+'</div>';
    var left=0, rows=t.map(function(k){ var c=CITIES[k], d=sum(ALL[k].done), n=c.stops.length, r=n-d; left+=r; var pc=Math.round(d/n*100);
      return '<li class="trow'+(r?'':' done')+'"><button class="trowb" data-a="city" data-c="'+k+'"><span class="tcheck" aria-hidden="true">'+(r?'':'&#10003;')+'</span><span class="tn"><strong>'+c.name+'</strong><span class="sub">'+(TSTATE[k]?TSTATE[k]+' · ':'')+(r?r+' of '+n+' stamps to go':'All stamped')+'</span><span class="pbar" aria-hidden="true"><i style="width:'+pc+'%"></i></span></span><span class="go">Open ›</span></button><button class="tstar on" data-a="trip" data-c="'+k+'" aria-pressed="true" aria-label="Remove '+c.name+' from my trip">★</button></li>'; }).join('');
    return '<div class="trip" id="trip"><p class="tripsum"><strong>'+t.length+(t.length===1?' town':' towns')+'</strong> · '+left+' stamps to collect</p><ul class="tlist">'+rows+'</ul>'+svHtml+'</div>';
  }
  var STATE_ORDER=null;
  function chipsHtml(){
    var seen={}, list=[]; ORDER.forEach(function(k){ (TSTATE[k]||'').split('/').forEach(function(a){ if(a&&!seen[a]){ seen[a]=1; list.push(a); } }); });
    list.sort(function(a,b){ return (DISP[a]||TFULL[a]||a).localeCompare(DISP[b]||TFULL[b]||b); });
    return '<div class="schips" role="group" aria-label="Browse by state">'+list.map(function(a){ var nm=DISP[a]||TFULL[a]||a, q=a==='DC'?'District of Columbia':nm; return '<button class="chip" data-a="schip" data-s="'+q+'">'+nm+'</button>'; }).join('')+'</div>';
  }
  var TRAILS=[
    {id:'stations',name:'Train stations',note:'Depots and terminals where the country arrived.',re:/station|depot|terminal/i},
    {id:'capitols',name:'Capitols and courthouses',note:'Where laws were made and arguments settled.',re:/capitol|statehouse|state house|courthouse|city hall/i},
    {id:'faith',name:'Churches and missions',note:'Cathedrals, missions and meeting houses.',re:/church(?!ill| street)|cathedral|temple|mission|basilica|meeting ?house/i},
    {id:'bridges',name:'Bridges and towers',note:'Big things people built to reach farther.',re:/bridge|\b(?!terminal\b)\w+ tower|monument|needle|gate\b/i}
  ];
  function trailStops(re){ var out=[]; ORDER.forEach(function(k){ CITIES[k].stops.forEach(function(st,i){ if(re.test(st.name)) out.push({k:k,st:st,done:!!ALL[k].done[i]}); }); }); return out; }
  var TRICON={"stations": "<path d=\"M6 5h12a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2zm0 4h12M8 20l1.5-3m6.5 3-1.5-3M9 13h.01M15 13h.01\"/>", "capitols": "<path d=\"M4 20h16M6 20v-7m4 7v-7m4 7v-7m4 7v-7M3 13h18M5 13a7 7 0 0 1 14 0M12 3v3\"/>", "faith": "<path d=\"M12 2v5m-2-3h4M7 21V12l5-5 5 5v9M10 21v-4h4v4M4 21h16\"/>", "bridges": "<path d=\"M2 18h20M4 18v-5m16 5v-5M4 13c3-6 13-6 16 0M8 14v4m4-5v5m4-4v4\"/>"};
  var TRCOL={stations:'#B7791F',capitols:'#1B58B8',faith:'#2F855A',bridges:'#0F766E'};
  function browseOpen(){
    var n=tripGet().length, T=[['towns','Towns'],['trails','Trails'],['trip','My trip'+(n?' ('+n+')':'')]];
    return '<section class="browse" id="browse"><div class="btabs" role="tablist" aria-label="Browse">'+T.map(function(t){ return '<button class="btab" role="tab" id="bt-'+t[0]+'" data-a="btab" data-t="'+t[0]+'" aria-selected="'+(btab===t[0])+'" aria-controls="bp-'+t[0]+'">'+t[1]+'</button>'; }).join('')+'</div><div class="bpanel" id="bp-towns" role="tabpanel"'+(btab==='towns'?'':' hidden')+'>';
  }
  function setBtab(t){ btab=t; if(t==='towns'||t==='trails') bnavSel=t; ['towns','trails','trip'].forEach(function(x){ var p=document.getElementById('bp-'+x), b=document.getElementById('bt-'+x); if(p) p.hidden=(x!==t); if(b) b.setAttribute('aria-selected',x===t?'true':'false'); }); }
  function trailsHtml(){
    var cards='', lists='';
    TRAILS.forEach(function(tr){ var L=trailStops(tr.re); if(L.length<3) return; var d=L.filter(function(x){ return x.done; }).length, pc=Math.round(d/L.length*100), on=(btrail===tr.id);
      cards+='<button class="tcard'+(on?' on':'')+'" data-a="trail" data-t="'+tr.id+'" style="--tc:'+TRCOL[tr.id]+';--p:'+pc+'" aria-pressed="'+on+'"><span class="tic"><svg viewBox="0 0 24 24" width="30" height="30" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'+TRICON[tr.id]+'</svg></span><strong>'+tr.name+'</strong><span class="tcount">'+d+' of '+L.length+' stamped</span><span class="pbar" aria-hidden="true"><i style="width:'+pc+'%"></i></span></button>';
      lists+='<div class="trl" data-trail="'+tr.id+'"'+(on?'':' hidden')+' style="--tc:'+TRCOL[tr.id]+'"><p class="why">'+tr.note+'</p><ul class="tlist">'+L.map(function(x){ return '<li class="trow'+(x.done?' done':'')+'"><button class="trowb" data-a="city" data-c="'+x.k+'"><span class="tcheck" aria-hidden="true">'+(x.done?'&#10003;':'')+'</span>'+((x.st.now&&x.st.now.ph&&PHOTOS[x.st.now.ph.k])?'<img class="tthumb" loading="lazy" decoding="async" src="'+PHOTOS[x.st.now.ph.k]+'" alt="">':'')+'<span class="tn"><strong>'+x.st.name+'</strong><span class="sub">'+placeLabel(x.k)+'</span></span><span class="go">Open ›</span></button></li>'; }).join('')+'</ul></div>'; });
    return '<h2 class="hh">Pick a trail</h2><p class="why">Collect a theme, not just a town. Pick a trail to see every stop on it.</p><div class="tcards" role="group" aria-label="Trails">'+cards+'</div>'+lists;
  }
  // share card
  /* one notable discovery for a finished town's share card: one stop's sourced "fact" (same one every time for a town), trimmed to fit two lines */
  /* phone UX audit u08: one real photo and sourced fact from the current town, changing daily, for returning players */
  function featuredHtml(){
    try{ var nx=nextRef(), fk=nx?nx.k:cityId, c=CITIES[fk]; if(!c||!c.stops||!c.stops.length) return '';
      var open=[]; c.stops.forEach(function(st,i){ if(!ALL[fk].done[i]&&!(nx&&nx.i===i)) open.push(i); });
      var pool=open.length?open:c.stops.map(function(x,i){ return i; }).filter(function(i){ return !(nx&&nx.k===fk&&nx.i===i); }); if(!pool.length) return '';
      var day=Math.floor((Date.now()-new Date().getTimezoneOffset()*6e4)/864e5), i=pool[day%pool.length], st=c.stops[i];
      var ph=st.now&&st.now.ph, src=ph&&PHOTOS[ph.k]; if(!src) return '';
      var f=(st.fact&&st.fact.length>20&&st.fact.length<=170)?st.fact:(st.teaser||'');
      return '<section class="feat" aria-label="Story of the day"><img loading="lazy" decoding="async" src="'+src+'" alt="'+(st.now.label||st.name).replace(/"/g,'&quot;')+'"><div class="fin"><p class="mono">Story of the day · '+c.name+'</p><h3>'+st.name+'</h3><p>'+f+'</p><p class="fcred">Photo: '+(ph.by||'')+(ph.lic?' · '+ph.lic:'')+'</p><button class="btn small" data-a="neargo" data-c="'+fk+'" data-i="'+i+'" data-far="1">Read this stop</button></div></section>'; }catch(e){ return ''; }
  }
  function townDiscovery(k){
    try{ var c=CITIES[k]; if(!c||sum(ALL[k].done)<c.stops.length) return '';
      var L=c.stops.map(function(st){ return st.fact||''; }).filter(function(x){ return x.length>20&&x.length<=150; }), h=0; for(var i=0;i<k.length;i++) h+=k.charCodeAt(i); var f=L.length?L[h%L.length]:'';
      if(f.length>125){ f=f.slice(0,122).replace(/\s+\S*$/,'')+'...'; } return f; }catch(e){ return ''; }
  }
  function shareDraw(kind,k,cb,noimg){
    var W=1080,H=1350,c=document.createElement('canvas'); c.width=W; c.height=H; var g=c.getContext('2d');
    var keys=[], title, big, line;
    if(kind==='town'){ keys=townKeys(k).slice(0,4); title=CITIES[k].name; big=sum(ALL[k].done)+' of '+CITIES[k].stops.length+' stamps'; line=CITIES[k].explorer; }
    else { var tk=ORDER.filter(function(x){ return sum(ALL[x].done)>0; }).sort(function(a,b){ return sum(ALL[b].done)-sum(ALL[a].done); }); tk.slice(0,4).forEach(function(x){ var kk=townKeys(x)[0]; if(kk) keys.push(kk); }); var full=ORDER.filter(function(x){ return sum(ALL[x].done)===CITIES[x].stops.length; }).length; title='My passport'; big=totalStamps()+' stamps'; line=tk.length+(tk.length===1?' town':' towns')+(full?' · '+full+' complete':''); }
    var disc=(kind==='town'?townDiscovery(k):'');
    g.fillStyle='#13202C'; g.fillRect(0,0,W,H); g.fillStyle='#F2B01E'; g.fillRect(0,0,W,14);
    g.fillStyle='#9AAAB8'; g.font='600 34px system-ui,sans-serif'; g.textAlign='center'; g.fillText('STAMP THE PAST',W/2,110);
    g.fillStyle='#FFFFFF'; g.font='800 96px system-ui,sans-serif'; var t=title; while(g.measureText(t).width>W-120&&g.font.indexOf('px')>0){ var sz=parseInt(g.font.split(' ')[1],10)-6; g.font='800 '+sz+'px system-ui,sans-serif'; } g.fillText(t,W/2,235);
    g.fillStyle='#F2B01E'; g.font='700 64px system-ui,sans-serif'; g.fillText(big,W/2,325); g.fillStyle='#C9D1D9'; g.font='500 38px system-ui,sans-serif'; g.fillText(line,W/2,385);
    var n=keys.length, loaded=0, imgs=[], cell=(disc?(n===1?440:312):(n===1?560:380)), gap=(disc?28:36), startX=(W-(2*cell+gap))/2, rows=Math.max(1,Math.ceil(n/2)), startY=430+Math.max(0,((disc?690:800)-(rows*cell+(rows-1)*gap))/2);
    function finish(){
      imgs.forEach(function(im,i){ if(!im) return; var x=startX+(i%2)*(cell+gap), y=startY+Math.floor(i/2)*(cell+gap); if(i===imgs.length-1&&i%2===0) x=(W-cell)/2; g.save(); g.beginPath(); g.arc(x+cell/2,y+cell/2,cell/2,0,Math.PI*2); g.clip(); var r=Math.max(cell/im.width,cell/im.height), w=im.width*r, h=im.height*r; g.drawImage(im,x+(cell-w)/2,y+(cell-h)/2,w,h); g.restore(); g.lineWidth=10; g.strokeStyle='#F2B01E'; g.beginPath(); g.arc(x+cell/2,y+cell/2,cell/2,0,Math.PI*2); g.stroke(); });
      if(disc){ g.fillStyle='#F2B01E'; g.font='700 28px system-ui,sans-serif'; g.fillText('DID YOU KNOW?',W/2,1140); g.fillStyle='#FFFFFF'; g.font='500 31px system-ui,sans-serif'; var ws=disc.split(' '), ln='', yy=1182; ws.forEach(function(w){ var tt=ln?ln+' '+w:w; if(g.measureText(tt).width>W-140&&ln){ g.fillText(ln,W/2,yy); yy+=40; ln=w; } else ln=tt; }); if(ln) g.fillText(ln,W/2,yy); }
      g.fillStyle='#9AAAB8'; g.font='500 34px system-ui,sans-serif'; g.fillText('Go there. Prove it. Stamp the past.',W/2,1270); g.fillStyle='#FFFFFF'; g.font='700 36px system-ui,sans-serif'; g.fillText(SHARE_URL,W/2,1318);
      try{ c.toBlob(function(b){ cb(b); },'image/png'); }catch(e){ if(!noimg) shareDraw(kind,k,cb,true); else cb(null); }
    }
    if(!n||noimg){ finish(); return; }
    keys.forEach(function(key,i){ var im=new Image(); im.onload=function(){ imgs[i]=im; if(++loaded===n) finish(); }; im.onerror=function(){ if(++loaded===n) finish(); }; im.src=PHOTOS[key]; });
  }
  /* ---------- share the fade: a short clip of the old photo melting into today (still picture if the phone cannot record) ---------- */
  function fadeCover(g,im,x,y,w,h){ var r=Math.max(w/im.width,h/im.height), sw=w/r, sh=h/r; g.drawImage(im,(im.width-sw)/2,(im.height-sh)/2,sw,sh,x,y,w,h); }
  function fadeFit(g,txt,max,start,wt){ var sz=start; g.font=wt+' '+sz+'px system-ui,sans-serif'; while(g.measureText(txt).width>max&&sz>20){ sz-=2; g.font=wt+' '+sz+'px system-ui,sans-serif'; } }
  function fadeFrame(g,W,H,a,b,m,mix){
    g.fillStyle='#13202C'; g.fillRect(0,0,W,H); g.fillStyle='#F2B01E'; g.fillRect(0,0,W,10);
    g.textAlign='center'; g.fillStyle='#9AAAB8'; g.font='600 26px system-ui,sans-serif'; g.fillText('STAMP THE PAST',W/2,62);
    g.fillStyle='#FFFFFF'; fadeFit(g,m.s,W-80,60,'800'); g.fillText(m.s,W/2,132);
    g.fillStyle='#F2B01E'; g.font='700 30px system-ui,sans-serif'; g.fillText(m.c,W/2,178);
    var y0=206, ih=Math.round(W*0.75); g.save(); g.beginPath(); g.rect(0,y0,W,ih); g.clip(); fadeCover(g,a,0,y0,W,ih); g.globalAlpha=mix; fadeCover(g,b,0,y0,W,ih); g.restore();
    var lab=mix<0.5?'TODAY':m.y; g.font='800 30px system-ui,sans-serif'; var lw=g.measureText(lab).width+44; g.fillStyle='rgba(19,32,44,.82)'; g.beginPath(); if(g.roundRect) g.roundRect(W/2-lw/2,y0+ih-70,lw,48,24); else g.rect(W/2-lw/2,y0+ih-70,lw,48); g.fill(); g.fillStyle='#FFFFFF'; g.fillText(lab,W/2,y0+ih-36);
    var ty=y0+ih+52, x1=110, x2=W-110; g.strokeStyle='#3A4A5A'; g.lineWidth=8; g.lineCap='round'; g.beginPath(); g.moveTo(x1,ty); g.lineTo(x2,ty); g.stroke(); g.strokeStyle='#F2B01E'; g.beginPath(); g.moveTo(x1,ty); g.lineTo(x1+(x2-x1)*mix,ty); g.stroke(); g.fillStyle='#FFFFFF'; g.beginPath(); g.arc(x1+(x2-x1)*mix,ty,16,0,Math.PI*2); g.fill();
    g.fillStyle='#9AAAB8'; g.font='600 24px system-ui,sans-serif'; g.textAlign='left'; g.fillText('NOW',24,ty+9); g.textAlign='right'; g.fillText(m.y,W-24,ty+9); g.textAlign='center';
    g.fillStyle='#9AAAB8'; g.font='500 26px system-ui,sans-serif'; g.fillText('Go there. Prove it. Stamp the past.',W/2,H-62); g.fillStyle='#FFFFFF'; g.font='700 30px system-ui,sans-serif'; g.fillText(SHARE_URL,W/2,H-22);
  }
  function fadeMix(t){ if(t<0.8) return 0; if(t>3.2) return 1; var u=(t-0.8)/2.4; return u<0.5?2*u*u:1-Math.pow(-2*u+2,2)/2; }
  function fadeShare(btn){
    var m={s:btn.getAttribute('data-s')||'',c:btn.getAttribute('data-c')||'',y:btn.getAttribute('data-y')||''}, nk=btn.getAttribute('data-n'), tk=btn.getAttribute('data-t');
    if(!PHOTOS[nk]||!PHOTOS[tk]){ toast('Photos are missing for this stop.'); return; }
    toast('Making your clip...');
    var a=new Image(), b=new Image(), left=2, bad=false;
    function go(){ if(bad||--left) return; fadeMake(a,b,m); }
    a.onload=go; b.onload=go; a.onerror=b.onerror=function(){ if(!bad){ bad=true; toast('Could not load the photos.'); } };
    a.src=PHOTOS[nk]; b.src=PHOTOS[tk];
  }
  var fadeFile=null;
  function fadeOut(blob,m,isVideo){
    var ext=isVideo?(/mp4/.test(blob.type)?'mp4':'webm'):'png', name='stamp-the-past-fade.'+ext, f=null; try{ f=new File([blob],name,{type:blob.type||(isVideo?'video/mp4':'image/png')}); }catch(e){}
    var txt=m.s+', then and now. Go there. Prove it. Stamp the past. https://'+SHARE_URL;
    var canSh=!!(f&&navigator.canShare&&navigator.canShare({files:[f]})&&navigator.share); fadeFile=canSh?{f:f,t:txt}:null;
    shareClose(); var u=URL.createObjectURL(blob), d=document.createElement('div'); d.id='sharem'; d._u=u; d.className='celeb'; d.setAttribute('role','dialog'); d.setAttribute('aria-modal','true'); d.setAttribute('aria-label','Your fade clip');
    d.innerHTML='<div class="celeb-card sharecard">'+(isVideo?'<video src="'+u+'" autoplay loop muted playsinline aria-label="Then and now clip"></video>':'<img src="'+u+'" alt="Then and now picture">')+'<p class="why">'+(isVideo?'Tap Share or save it, then choose Save Video, Messages, or any app.':'Press and hold the picture to save or share it.')+'</p><div class="celeb-btns">'+(canSh?'<button class="btn" data-a="sharefile">Share or save it</button>':'<a class="btn" href="'+u+'" download="'+name+'">Save it</a>')+'<button class="btn ghost" data-a="shareclose">Close</button></div></div>';
    document.body.appendChild(d); var cb=d.querySelector('button'); if(cb) cb.focus();
  }
  function fadeMake(a,b,m){
    var W=720,H=960, c=document.createElement('canvas'); c.width=W; c.height=H; var g=c.getContext('2d');
    var mt=''; try{ if(window.MediaRecorder&&MediaRecorder.isTypeSupported&&c.captureStream) mt=['video/mp4;codecs=avc1.42E01E','video/mp4','video/webm;codecs=vp9','video/webm'].filter(function(x){ return MediaRecorder.isTypeSupported(x); })[0]||''; }catch(e){}
    function still(){ fadeFrame(g,W,H,a,b,m,0.5); try{ c.toBlob(function(bl){ if(bl) fadeOut(bl,m,false); else toast('Could not make the picture on this device.'); },'image/png'); }catch(e){ toast('Could not make the picture on this device.'); } }
    if(!mt){ still(); return; }
    var rec, chunks=[], t0=0, done=false, fin=false, wd=0;
    function finish(bl){ if(fin) return; fin=true; clearTimeout(wd); if(bl&&bl.size>=1000) fadeOut(bl,m,true); else still(); }
    try{ rec=new MediaRecorder(c.captureStream(30),{mimeType:mt,videoBitsPerSecond:2500000}); }catch(e){ still(); return; }
    rec.ondataavailable=function(e){ if(e.data&&e.data.size) chunks.push(e.data); };
    rec.onstop=function(){ finish(new Blob(chunks,{type:(rec.mimeType||mt).split(';')[0]})); };
    rec.onerror=function(){ finish(null); };
    wd=setTimeout(function(){ if(!fin){ done=true; try{ rec.stop(); }catch(e){} setTimeout(function(){ finish(null); },800); } },9000);
    function tick(now){ if(done) return; if(!t0) t0=now; var t=(now-t0)/1000; fadeFrame(g,W,H,a,b,m,fadeMix(t)); if(t>=4.8){ done=true; setTimeout(function(){ try{ rec.stop(); }catch(e){ finish(null); } },200); return; } requestAnimationFrame(tick); }
    fadeFrame(g,W,H,a,b,m,0); try{ rec.start(); }catch(e){ finish(null); return; } requestAnimationFrame(tick);
  }
  function shareClose(){ var e=document.getElementById('sharem'); if(e){ if(e._u) try{ URL.revokeObjectURL(e._u); }catch(x){} e.remove(); } }
  function shareStamps(kind,k){
    toast('Making your card...');
    shareDraw(kind,k,function(b){
      if(!b){ toast('Could not make the card on this device.'); return; }
      var name='stamp-the-past-'+(kind==='town'?k:'passport')+'.png', f=null; try{ f=new File([b],name,{type:'image/png'}); }catch(e){}
      var txt=(kind==='town'?'I finished '+CITIES[k].name+' on Stamp the Past.'+(townDiscovery(k)?' Did you know? '+townDiscovery(k):''):'My Stamp the Past passport.')+' Go there. Prove it. Stamp the past. https://'+SHARE_URL;
      if(f&&navigator.canShare&&navigator.canShare({files:[f]})&&navigator.share){ navigator.share({files:[f],text:txt}).catch(function(){}); return; }
      shareClose(); var u=URL.createObjectURL(b), d=document.createElement('div'); d.id='sharem'; d._u=u; d.className='celeb'; d.setAttribute('role','dialog'); d.setAttribute('aria-modal','true'); d.setAttribute('aria-label','Your share card');
      d.innerHTML='<div class="celeb-card sharecard"><img src="'+u+'" alt="Your stamp card"><p class="why">Press and hold the picture to save or share it.</p><div class="celeb-btns"><a class="btn" href="'+u+'" download="'+name+'">Save the picture</a><button class="btn ghost" data-a="shareclose">Close</button></div></div>';
      document.body.appendChild(d);
    });
  }
  function totalStamps(){ var t=0; ORDER.forEach(function(k){ t+=sum(ALL[k].done); }); return t; }
  function bkSeen(){ try{ return parseInt(localStorage.getItem('stp-bk-seen')||'-1',10); }catch(e){ return -1; } }
  function totalPts(){ var b=bossBest(),t=0; ORDER.forEach(function(k){ t+=ptsOf(b[k]); }); return t; }
  function grandOk(){ var b=bossBest(); return ORDER.length>0&&ORDER.every(function(k){ return b[k]>=4; }); }
  /* ---------- explorer level + badges (everything is worked out from saved progress; only the earned list is stored) ---------- */
  var LVTITLES=[[1,'Newcomer'],[3,'Wanderer'],[5,'Trailblazer'],[8,'Pathfinder'],[12,'Explorer'],[16,'Historian'],[21,'Archivist'],[27,'Time Traveler'],[34,'Grand Chronicler']];
  function lvXp(L){ return 25*(L-1)*(L+2); }
  function lvOf(x){ var L=1; while(L<60&&lvXp(L+1)<=x) L++; var t=LVTITLES[0][1]; LVTITLES.forEach(function(e){ if(L>=e[0]) t=e[1]; }); return {n:L,title:t,from:lvXp(L),to:lvXp(L+1),pc:Math.max(0,Math.min(100,Math.round((x-lvXp(L))/(lvXp(L+1)-lvXp(L))*100)))}; }
  function nfmt(n){ return String(n).replace(/\B(?=(\d{3})+(?!\d))/g,','); }
  function gStats(){
    var b=bossBest(), g=geoGet(), vg=virtGet(), s={virt:0,xp:0,stamps:0,claims:0,full:0,ver:0,gems:0,seals:0,golds:0,reg:{},st:{},nv:0,town:{},cnt:{}};
    ORDER.forEach(function(k){
      var a=ALL[k], c=CITIES[k], d=sum(a.done); s.stamps+=d; s.claims+=sum(a.claims); s.xp+=d*100+sum(a.claims)*25; s.town[k]=d;
      if(d===c.stops.length){ s.full++; s.xp+=100; }
      if(d>0){ if(c.region) s.reg[c.region]=1; if(c.level==='Hidden Gems') s.gems+=d; (TSTATE[k]||'').split('/').forEach(function(x){ if(x&&!s.st[x]){ s.st[x]=1; s.xp+=50; } }); if(/NV/.test(TSTATE[k]||'')&&!/CA/.test(TSTATE[k]||'')) s.nv++; }
      c.stops.forEach(function(st,i){ if(a.done[i]&&g[k+':'+st.id]){ s.ver++; s.xp+=50; } if(!a.done[i]&&vg[k+':'+st.id]){ s.virt++; s.xp+=25; } });
      if(sealTier(b[k])) s.seals++; if(b[k]>=4) s.golds++; s.xp+=ptsOf(b[k]);
    });
    var cnt={}, mx=0; logGet().forEach(function(d){ cnt[d]=(cnt[d]||0)+1; if(cnt[d]>mx) mx=cnt[d]; }); s.day=mx; s.wk=streakWeeks();
    s.nst=Object.keys(s.st).length; s.nreg=Object.keys(s.reg).length;
    return s;
  }
  function trailN(re){ return trailStops(re).filter(function(x){ return x.done; }).length; }
  function hasReg(s,re){ return Object.keys(s.reg).some(function(r){ return re.test(r); })?1:0; }
  var BADGES=[
    {id:'first',n:'First Stamp',d:'Get your first stamp. Everything after this is momentum.',t:'c',g:'1',f:function(s){ return [s.stamps,1]; }},
    {id:'s10',n:'Ten Down',d:'Collect 10 stamps.',t:'c',g:'10',f:function(s){ return [s.stamps,10]; }},
    {id:'s25',n:'Pocket Full of Stamps',d:'Collect 25 stamps.',t:'c',g:'25',f:function(s){ return [s.stamps,25]; }},
    {id:'s50',n:'Half a Hundred',d:'Collect 50 stamps.',t:'r',g:'50',f:function(s){ return [s.stamps,50]; }},
    {id:'s100',n:'Centurion',d:'Collect 100 stamps. Your passport is getting thick.',t:'r',g:'100',f:function(s){ return [s.stamps,100]; }},
    {id:'s200',n:'Double Century',d:'Collect 200 stamps.',t:'l',g:'200',f:function(s){ return [s.stamps,200]; }},
    {id:'s400',n:'Walking Archive',d:'Collect 400 stamps. Libraries call you for advice.',t:'l',g:'400',f:function(s){ return [s.stamps,400]; }},
    {id:'t1',n:'Town Done',d:'Stamp all four stops in one town. Trivia night is now winnable.',t:'c',g:'★',f:function(s){ return [s.full,1]; }},
    {id:'t5',n:'Five Towns Deep',d:'Finish 5 towns.',t:'r',g:'5',f:function(s){ return [s.full,5]; }},
    {id:'t15',n:'Mayor of Everywhere',d:'Finish 15 towns.',t:'l',g:'15',f:function(s){ return [s.full,15]; }},
    {id:'st3',n:'Road Tripper',d:'Get stamps in 3 different states.',t:'c',g:'3',f:function(s){ return [s.nst,3]; }},
    {id:'st10',n:'Double Digits',d:'Get stamps in 10 different states.',t:'r',g:'10',f:function(s){ return [s.nst,10]; }},
    {id:'st25',n:'Half the Map',d:'Get stamps in 25 different states.',t:'l',g:'25',f:function(s){ return [s.nst,25]; }},
    {id:'coast',n:'Coast to Coast',d:'Get a stamp in the West and a stamp in the East.',t:'c',g:'⇄',f:function(s){ return [hasReg(s,/West/)+hasReg(s,/East/),2]; }},
    {id:'reg5',n:'Every Region',d:'Get a stamp in all five regions.',t:'r',g:'5',f:function(s){ return [s.nreg,5]; }},
    {id:'far',n:'Aloha and Brrr',d:'Get stamps in both Hawaii and Alaska. Pack accordingly.',t:'r',g:'☀',f:function(s){ return [(s.st.HI?1:0)+(s.st.AK?1:0),2]; }},
    {id:'nv',n:'Battle Born',d:'Get stamps in 4 different Nevada towns.',t:'c',g:'NV',f:function(s){ return [s.nv,4]; }},
    {id:'rush',n:'Gold Rush Gremlin',d:'Get stamps in Virginia City, Carson City and Skagway.',t:'r',g:'Au',f:function(s){ return [(s.town.vc>0?1:0)+(s.town.carson>0?1:0)+(s.town.skagway>0?1:0),3]; }},
    {id:'gem5',n:'Off the Beaten Path',d:'Collect 5 stamps in Hidden Gems towns.',t:'c',g:'◆',f:function(s){ return [s.gems,5]; }},
    {id:'gem20',n:'Where Is That?',d:'Collect 20 stamps in Hidden Gems towns. Hidden from everyone but you.',t:'r',g:'◆',f:function(s){ return [s.gems,20]; }},
    {id:'c10',n:'Fact Checker',d:'Sort 10 claims correctly.',t:'c',g:'✓',f:function(s){ return [s.claims,10]; }},
    {id:'c50',n:'Myth Buster',d:'Sort 50 claims correctly.',t:'r',g:'✓',f:function(s){ return [s.claims,50]; }},
    {id:'c150',n:'Citation Needed',d:'Sort 150 claims correctly. Footnotes fear you.',t:'l',g:'✓',f:function(s){ return [s.claims,150]; }},
    {id:'q1',n:'Quiz Show',d:'Earn your first challenge seal.',t:'c',g:'?',f:function(s){ return [s.seals,1]; }},
    {id:'q4',n:'Perfect Score',d:'Score 4 of 4 on a final challenge.',t:'r',g:'4',f:function(s){ return [s.golds,1]; }},
    {id:'q5',n:'Perfect Five',d:'Score 4 of 4 on five final challenges.',t:'l',g:'5',f:function(s){ return [s.golds,5]; }},
    {id:'v1',n:'Boots on the Ground',d:'Get a stamp verified by being there.',t:'c',g:'⚑',f:function(s){ return [s.ver,1]; }},
    {id:'v10',n:'Certified Wanderer',d:'Verify 10 visits by being there.',t:'r',g:'10',f:function(s){ return [s.ver,10]; }},
    {id:'v40',n:'Professional Loiterer',d:'Verify 40 visits. You have stood near a lot of plaques.',t:'l',g:'40',f:function(s){ return [s.ver,40]; }},
    {id:'w2',n:'Two Weeks Running',d:'Stamp something in 2 weeks in a row.',t:'c',g:'2w',f:function(s){ return [s.wk,2]; }},
    {id:'w4',n:'A Month of Weeks',d:'Stamp something in 4 weeks in a row.',t:'r',g:'4w',f:function(s){ return [s.wk,4]; }},
    {id:'w12',n:'Habit Formed',d:'Stamp something in 12 weeks in a row.',t:'l',g:'12w',f:function(s){ return [s.wk,12]; }},
    {id:'d3',n:'Hat Trick',d:'Get 3 stamps in one day.',t:'c',g:'3',f:function(s){ return [s.day,3]; }},
    {id:'d5',n:'Stamp Rush',d:'Get 5 stamps in one day.',t:'r',g:'5',f:function(s){ return [s.day,5]; }},
    {id:'d8',n:'Overachiever',d:'Get 8 stamps in one day. Snack break earned.',t:'l',g:'8',f:function(s){ return [s.day,8]; }},
    {id:'arm',n:'Armchair Explorer',d:'Explore 10 stops from home. The couch counts, but the real stamp is better.',t:'c',g:'≈',f:function(s){ return [s.virt,10]; }},
    {id:'tr1',n:'All Aboard',d:'Stamp 5 train stations or depots.',t:'r',g:'☰',f:function(){ return [trailN(/station|depot|terminal/i),5]; }},
    {id:'tr2',n:'Capitol Gains',d:'Stamp 5 capitols or courthouses.',t:'r',g:'⌂',f:function(){ return [trailN(/capitol|statehouse|state house|courthouse|city hall/i),5]; }},
    {id:'tr3',n:'Steeple Chaser',d:'Stamp 5 churches, cathedrals or missions.',t:'r',g:'✚',f:function(){ return [trailN(/church(?!ill| street)|cathedral|temple|mission|basilica|meeting ?house/i),5]; }},
    {id:'tr4',n:'Bridge Troll',d:'Stamp 5 bridges, towers or monuments.',t:'r',g:'∩',f:function(){ return [trailN(/bridge|\b(?!terminal\b)\w+ tower|monument|needle|gate\b/i),5]; }}
  ];
  var TIERN={c:'Common',r:'Rare',l:'Legendary'};
  function bdGet(){ try{ var o=JSON.parse(localStorage.getItem('stp-badges')||'{}'); return (o&&typeof o==='object'&&!Array.isArray(o))?o:{}; }catch(e){ return {}; } }
  function bdAll(){
    var s=gStats(), have=bdGet();
    return {s:s,list:BADGES.map(function(b){ var p=b.f(s), ok=p[0]>=p[1]; return {b:b,cur:Math.min(p[0],p[1]),goal:p[1],on:!!have[b.id]||ok,when:have[b.id]||''}; })};
  }
  /* medal art: rarity picks the frame (round coin, faceted hexagon, gold starburst), the badge picks the icon */
  var MEDN=0;
  var MICON={
    stamp:{a:'<path d="M15 3h10a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2h-1l3 5H13l3-5h-1a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2z"/><path d="M6 24h28a2 2 0 0 1 2 2v4H4v-4a2 2 0 0 1 2-2z"/><path d="M6 33h28v3H6z"/>',b:''},
    star:{a:'<path d="M20 2l5.4 12.2L38.5 15l-10 8.7L31.6 37 20 30l-11.6 7 3.1-13.3-10-8.7 13.1-.8z"/>',b:''},
    flag:{a:'<path d="M8 3h3.5v34H8z"/><path d="M11.5 5h22l-6.5 8 6.5 8h-22z"/>',b:''},
    pin:{a:'<path fill-rule="evenodd" d="M20 2C12.8 2 7 7.7 7 14.7 7 24.6 20 38 20 38s13-13.4 13-23.3C33 7.7 27.2 2 20 2zm0 18.5a6 6 0 1 1 0-12 6 6 0 0 1 0 12z"/>',b:''},
    map:{a:'<path d="M2 8l12-4.5 12 4.5 12-4.5v28.5L26 36.5 14 32 2 36.5z"/>',b:'<path d="M14 3.5v28.5M26 8v28.5" stroke="@D" stroke-width="2" fill="none"/>'},
    compass:{a:'<path fill-rule="evenodd" d="M20 1.5a18.5 18.5 0 1 0 0 37 18.5 18.5 0 0 0 0-37zm0 4a14.5 14.5 0 1 1 0 29 14.5 14.5 0 0 1 0-29z"/><path d="M28 12l-5.2 10.8L12 28l5.2-10.8z"/>',b:'<circle cx="20" cy="20" r="2.2" fill="@D"/>'},
    sun:{a:'<circle cx="20" cy="20" r="8.5"/><path d="M20 2.5v6M20 31.5v6M2.5 20h6M31.5 20h6M7.6 7.6l4.2 4.2M28.2 28.2l4.2 4.2M32.4 7.6l-4.2 4.2M11.8 28.2l-4.2 4.2" stroke="#fff" stroke-width="3.2" stroke-linecap="round" fill="none"/>',b:''},
    gem:{a:'<path d="M11 5h18l9 11-18 22L2 16z"/>',b:'<path d="M2 16h36M11 5l4 11 5 22 5-22 4-11" stroke="@D" stroke-width="1.8" fill="none" stroke-linejoin="round"/>'},
    nugget:{a:'<path d="M6 30l-3-9 7-9 9-3 9 2 8 8-2 9-8 5H14z"/>',b:'<path d="M12 14l5 6-3 8M25 11l-2 9 7 3" stroke="@D" stroke-width="1.8" fill="none" stroke-linejoin="round"/>'},
    check:{a:'<path d="M20 1.5l15 5.5v11c0 9.5-6.200 16.500-15 20.500C11.200 34.500 5 27.500 5 18V7z"/>',b:'<path d="M12.500 19.500l5.500 5.500 10-11.500" stroke="@D" stroke-width="4" fill="none" stroke-linecap="round" stroke-linejoin="round"/>'},
    quiz:{a:'<path d="M20 1.5l15 5.5v11c0 9.5-6.200 16.500-15 20.500C11.200 34.500 5 27.500 5 18V7z"/>',b:'<text x="20" y="27" text-anchor="middle" font-family="Georgia,serif" font-weight="800" font-size="22" fill="@D">?</text>'},
    trophy:{a:'<path d="M10 3h20v11c0 7-4.500 11-10 11S10 21 10 14z"/><path d="M10 6H4v4.500c0 4 3 6.500 6.500 6.500M30 6h6v4.500c0 4-3 6.500-6.500 6.500" stroke="#fff" stroke-width="2.600" fill="none"/><path d="M17 25h6v6h-6z"/><path d="M11 31h18v5H11z"/>',b:''},
    flame:{a:'<path d="M21 1.500c1.500 8 11 11.500 11 22.500a11.500 11.500 0 0 1-23 0c0-5 2-8.500 5.500-11 0 4 1.500 6 4 6.500-1.500-6.500-1-12.500 2.500-18z"/>',b:'<path d="M20.500 22c3 3 5 5 5 8.500a5 5 0 0 1-10 0c0-2.500 1.500-4 2.500-5 .5 1.500 1.500 2 2 2-.5-2.500 0-4 .5-5.500z" fill="@D" opacity=".55"/>'},
    bolt:{a:'<path d="M24 1.500L7 22.500h10.500L14.500 38.500 33 16.500H22z"/>',b:''},
    train:{a:'<path d="M10 3h20a4 4 0 0 1 4 4v18a6 6 0 0 1-6 6H12a6 6 0 0 1-6-6V7a4 4 0 0 1 4-4z"/><path d="M11 31l-4.500 6.500M29 31l4.500 6.500" stroke="#fff" stroke-width="3" stroke-linecap="round" fill="none"/>',b:'<rect x="10" y="8" width="20" height="10" rx="2.500" fill="@D"/><circle cx="13.500" cy="24.500" r="2" fill="@D"/><circle cx="26.500" cy="24.500" r="2" fill="@D"/>'},
    dome:{a:'<path d="M20 1.500v5M7.500 22a12.500 12.500 0 0 1 25 0z"/><path d="M9 23.500h22v3H9zM10.500 28h3.500v7h-3.500zM16.250 28h3.500v7h-3.500zM22.250 28h3.500v7h-3.500zM28 28h3.500v7H28zM5 36h30v3H5z"/><path d="M20 1.500v5" stroke="#fff" stroke-width="2.200"/>',b:''},
    church:{a:'<path d="M20 1v8M16.500 4.500h7" stroke="#fff" stroke-width="2.400" fill="none"/><path d="M20 10l8 10v4H12v-4z"/><path d="M5 25h30v13H5z"/>',b:'<path d="M16.500 38v-6a3.500 3.500 0 0 1 7 0v6z" fill="@D"/>'},
    bridge:{a:'<path d="M1 25h38v4H1z"/><path d="M8.500 8h3.500v30H8.500zM28 8h3.500v30H28z"/><path d="M2 25Q8 12 10.200 8Q20 27 29.800 8Q32 12 38 25" stroke="#fff" stroke-width="2.200" fill="none"/>',b:''},
    mountain:{a:'<path d="M1 36L14 12l7 11 5-7 13 20z"/>',b:'<path d="M14 12l-4 7 4-2 3 3zM26 16l-3 5 3-1.500 2.500 2z" fill="@D" opacity=".35"/>'},
    wave:{a:'<path d="M2 14q4-5 8 0t8 0 8 0 8 0M2 22q4-5 8 0t8 0 8 0 8 0M2 30q4-5 8 0t8 0 8 0 8 0" stroke="#fff" stroke-width="3.400" fill="none" stroke-linecap="round"/>',b:''}
  };
  var BDART={first:['stamp'],s10:['stamp','10'],s25:['stamp','25'],s50:['stamp','50'],s100:['stamp','100'],s200:['stamp','200'],s400:['stamp','400'],t1:['star'],t5:['flag','5'],t15:['flag','15'],st3:['map','3'],st10:['map','10'],st25:['map','25'],coast:['compass'],reg5:['compass','5'],far:['sun'],nv:['mountain','NV'],rush:['nugget'],gem5:['gem','5'],gem20:['gem','20'],c10:['check','10'],c50:['check','50'],c150:['check','150'],q1:['quiz'],q4:['trophy'],q5:['trophy','5'],v1:['pin'],v10:['pin','10'],v40:['pin','40'],w2:['flame','2w'],w4:['flame','4w'],w12:['flame','12w'],d3:['bolt','3'],d5:['bolt','5'],d8:['bolt','8'],tr1:['train'],tr2:['dome'],tr3:['church'],tr4:['bridge']};
  function medal(b,on,sz){
    var id='m'+(++MEDN), art=BDART[b.id]||['star'], ic=MICON[art[0]]||MICON.star, lb=art[1]||'', t=b.t;
    var P={c:{r0:'#8fdcf0',r1:'#1c6786',d0:'#59bfe0',d1:'#145a78',rb:'#1c6786',rb2:'#2f8fb3',dk:'#0f3f56'},r:{r0:'#e2c8ff',r1:'#51299a',d0:'#a678e6',d1:'#42207f',rb:'#42207f',rb2:'#7a4cc4',dk:'#2e1560'},l:{r0:'#fff6bf',r1:'#a8730a',d0:'#ffdc63',d1:'#b97a06',rb:'#a82a18',rb2:'#e0503a',dk:'#6b4204'}}[t];
    if(!on) P={r0:'#cfd4db',r1:'#7b8390',d0:'#aab0ba',d1:'#6a7280',rb:'#7b8390',rb2:'#979eaa',dk:'#4d5461'};
    var cx=50, cy=42, frame, disc, defs='<linearGradient id="'+id+'r" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="'+P.r0+'"/><stop offset="1" stop-color="'+P.r1+'"/></linearGradient><radialGradient id="'+id+'d" cx=".38" cy=".3" r=".85"><stop offset="0" stop-color="'+P.d0+'"/><stop offset="1" stop-color="'+P.d1+'"/></radialGradient><linearGradient id="'+id+'b" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="'+P.rb+'"/><stop offset=".5" stop-color="'+P.rb2+'"/><stop offset="1" stop-color="'+P.rb+'"/></linearGradient>';
    var rib='<path d="M31 62L20 97l14-7 8 9 7-34z" fill="url(#'+id+'b)"/><path d="M69 62L80 97l-14-7-8 9-7-34z" fill="url(#'+id+'b)"/>';
    if(t==='r'){ frame='<polygon points="50,2 85,22 85,62 50,82 15,62 15,22" fill="url(#'+id+'r)" stroke="'+P.dk+'" stroke-width="1.6" stroke-linejoin="round"/>'; disc='<polygon points="50,10 78,26 78,58 50,74 22,58 22,26" fill="url(#'+id+'d)" stroke="#fff" stroke-opacity=".55" stroke-width="1.6" stroke-linejoin="round"/><polygon points="50,15 73,28.500 73,55.500 50,69 27,55.500 27,28.500" fill="none" stroke="#fff" stroke-opacity=".28" stroke-width="1"/>'; }
    else if(t==='l'){ var pts=[],k,a,rr; for(k=0;k<32;k++){ a=k*Math.PI/16-Math.PI/2; rr=k%2?36:42; pts.push((50+rr*Math.cos(a)).toFixed(1)+','+(42+rr*Math.sin(a)).toFixed(1)); } frame='<polygon points="'+pts.join(' ')+'" fill="url(#'+id+'r)" stroke="'+P.dk+'" stroke-width="1.4" stroke-linejoin="round"/><circle cx="50" cy="42" r="33" fill="none" stroke="'+P.r1+'" stroke-width="1.2" stroke-dasharray="1.500 3"/>'; disc='<circle cx="50" cy="42" r="29" fill="url(#'+id+'d)" stroke="#fff" stroke-opacity=".7" stroke-width="1.8"/>'; }
    else { frame='<circle cx="50" cy="42" r="39" fill="url(#'+id+'r)" stroke="'+P.dk+'" stroke-width="1.6"/><circle cx="50" cy="42" r="34" fill="none" stroke="#fff" stroke-opacity=".45" stroke-width="1.4" stroke-dasharray="1.800 3.400"/>'; disc='<circle cx="50" cy="42" r="29" fill="url(#'+id+'d)" stroke="#fff" stroke-opacity=".6" stroke-width="1.6"/>'; }
    var sc=lb?0.84:1.0, tx=50-20*sc, ty=(lb?36:42)-20*sc, det=ic.b.replace(/@D/g,P.dk);
    var icon='<g transform="translate('+tx.toFixed(1)+' '+(ty+1.6).toFixed(1)+') scale('+sc+')" fill="'+P.dk+'" opacity=".38">'+ic.a.replace(/stroke="#fff"/g,'stroke="'+P.dk+'"')+'</g><g transform="translate('+tx.toFixed(1)+' '+ty.toFixed(1)+') scale('+sc+')" fill="#fff" opacity="'+(on?1:.62)+'">'+ic.a+det+'</g>';
    var plate=lb?'<rect x="'+(50-Math.max(15,lb.length*5.4+6)).toFixed(1)+'" y="57.500" width="'+(Math.max(30,lb.length*10.8+12)).toFixed(1)+'" height="14.500" rx="7.200" fill="'+P.dk+'" stroke="'+(on?(t==='l'?'#ffe58a':'#fff'):'#c9ced6')+'" stroke-opacity=".85" stroke-width="1.200"/><text x="50" y="68.300" text-anchor="middle" font-family="Georgia,serif" font-weight="800" font-size="11.500" fill="'+(on?(t==='l'?'#ffe58a':'#fff'):'#dfe3e8')+'">'+lb+'</text>':'';
    var shine=on?'<clipPath id="'+id+'c"><circle cx="50" cy="42" r="29"/></clipPath><g clip-path="url(#'+id+'c)"><ellipse cx="40" cy="25" rx="23" ry="9" transform="rotate(-24 40 25)" fill="#fff" opacity=".26"/>'+(t==='l'?'<rect class="msh" x="-34" y="4" width="16" height="76" fill="#fff" opacity=".42"/>':'')+'</g>':'';
    var lock=on?'':'<g transform="translate(60 54)"><circle cx="11" cy="11" r="11" fill="#4d5461" stroke="#e4e7ec" stroke-width="1.400"/><rect x="6.500" y="10.500" width="9" height="7" rx="1.400" fill="#fff"/><path d="M8.300 10.500V8.600a2.700 2.700 0 0 1 5.400 0v1.900" stroke="#fff" stroke-width="1.700" fill="none"/></g>';
    var glow=(on&&t==='l')?'<circle cx="50" cy="42" r="46" fill="#ffd34d" opacity=".22"/>':'';
    return '<svg viewBox="0 0 100 100" width="'+sz+'" height="'+sz+'" aria-hidden="true" focusable="false" class="medal t-'+t+(on?' on':' lock')+'"><defs>'+defs+'</defs>'+glow+rib+frame+disc+icon+shine+plate+lock+'</svg>';
  }
  var badgeQ=[];
  function awardCheck(){
    if(demoSnap) return;
    var first=false; try{ first=localStorage.getItem('stp-badges')===null; }catch(e){}
    var r=bdAll(), have=bdGet(), today=dstr(new Date()), fresh=[];
    r.list.forEach(function(x){ if(x.cur>=x.goal&&!have[x.b.id]){ have[x.b.id]=today; fresh.push(x.b); } });
    if(!fresh.length&&!first) return;
    try{ localStorage.setItem('stp-badges',JSON.stringify(have)); }catch(e){}
    if(first){ if(fresh.length) setTimeout(function(){ toast('New: the Trophy Case is in your Passport. You already have '+fresh.length+(fresh.length===1?' badge.':' badges.')); },900); try{ localStorage.setItem('stp-bseen',String(fresh.length)); }catch(e){} return; }
    fresh.forEach(function(b){ badgeQ.push(b); });
    flushBadges(); updateBnav();
  }
  function awardSoon(){ setTimeout(awardCheck,1900); }
  var bsnT=null;
  function flushBadges(){
    if(!badgeQ.length||document.getElementById('celeb')||document.getElementById('bpop')) return;
    var q=badgeQ.splice(0,badgeQ.length), s=gStats(), lv=lvOf(s.xp), b0=q[0], place='';
    try{ var ps=(q.length===1&&document.body.classList.contains('instop')&&cur&&STOPS[cur.i])||null;
      if(ps){ var f1=(ps.fact||'').split(/(?<=\.)\s/)[0], pf=(f1.length>20&&f1.length<=120)?' '+f1:''; place='<span class="bsn-p">Earned at '+ps.name+', '+CITIES[cityId].name+'.'+pf+'</span>'; } }catch(e){ place=''; }
    var d=document.createElement('div'); d.id='bpop'; d.className='bsnack'; d.setAttribute('role','status'); d.setAttribute('aria-live','polite');
    d.innerHTML='<span class="bsn-m">'+medal(b0,true,56)+'</span><span class="bsn-t"><span class="mono">'+(q.length===1?'Badge unlocked':q.length+' badges unlocked')+'</span><strong>'+(q.length===1?b0.n:q.slice(0,3).map(function(b){ return b.n; }).join(', ')+(q.length>3?' and more':''))+'</strong><span class="bsn-d">'+(q.length===1?b0.d:'Level '+lv.n+' · '+lv.title)+'</span>'+place+'</span><span class="bsn-b"><button class="btn small" data-a="trophy">See</button><button class="bsn-x" data-a="bpopclose" aria-label="Dismiss">\u00d7</button></span>';
    document.body.appendChild(d); clearTimeout(bsnT); bsnT=setTimeout(closeBpop,place?13000:9000);
    try{ haptic('success'); }catch(e){}
  }
  function closeBpop(){ clearTimeout(bsnT); var e=document.getElementById('bpop'); if(e){ e.remove(); setTimeout(flushBadges,300); } }
  function levelHtml(s){
    var lv=lvOf(s.xp);
    return '<section class="xlv" aria-label="Explorer level"><div class="lvl-top"><div class="lvl-n"><span>Level</span><b>'+lv.n+'</b></div><div class="lvl-t"><strong>'+lv.title+'</strong><span>Explorer · '+nfmt(s.xp)+' XP · '+nfmt(lv.to-s.xp)+' to level '+(lv.n+1)+'</span></div></div><div class="lbar" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="'+lv.pc+'" aria-label="Progress to level '+(lv.n+1)+'"><i style="width:'+lv.pc+'%"></i></div>'
      +'<details class="lvl-how"><summary>How XP works</summary><ul><li><b>+100</b> for every stamp</li><li><b>+25</b> for each claim you sort correctly</li><li><b>+50</b> for a stamp verified by being there</li><li><b>+50</b> for your first stamp in a new state</li><li><b>+100</b> for finishing a town</li><li><b>Up to +300</b> from a town’s final challenge</li></ul></details></section>';
  }
  function tileHtml(x){
    var b=x.b, pc=Math.round(x.cur/x.goal*100);
    return '<li class="bt'+(x.on?' on':' lock')+' t-'+b.t+'"><span class="bt-m">'+medal(b,x.on,64)+'</span><span class="bt-i"><strong>'+b.n+'</strong><span class="bt-d">'+b.d+'</span>'
      +(x.on?'<span class="mono bt-s">'+TIERN[b.t]+' · earned'+(vdate(x.when)?' '+vdate(x.when):'')+'</span>':'<span class="bt-p" role="progressbar" aria-valuemin="0" aria-valuemax="'+x.goal+'" aria-valuenow="'+x.cur+'" aria-label="'+b.n+' progress"><i style="width:'+pc+'%"></i></span><span class="mono bt-s">'+TIERN[b.t]+' · '+x.cur+' of '+x.goal+'</span>')+'</span></li>';
  }
  function trophyHtml(r){
    var on=r.list.filter(function(x){ return x.on; }), off=r.list.filter(function(x){ return !x.on; });
    off.sort(function(a,b){ return (b.cur/b.goal)-(a.cur/a.goal); });
    on.sort(function(a,b){ return (b.when||'').localeCompare(a.when||''); });
    var next=off.slice(0,3);
    return '<section class="tcase" id="trophy" aria-label="Trophy Case"><div class="tc-head"><h2 class="hh2">Trophy Case</h2><span class="mono">'+on.length+' of '+r.list.length+' badges</span></div>'
      +(next.length?'<p class="mono tc-sub">Closest to earning</p><ul class="bgrid next">'+next.map(tileHtml).join('')+'</ul>':'<p class="why">You have every badge. Frankly, we are a little scared of you.</p>')
      +(on.length?'<p class="mono tc-sub">Earned</p><ul class="bgrid">'+on.slice(0,6).map(tileHtml).join('')+'</ul>':'')
      +((on.length>6||off.length>3)?'<details class="tc-more"><summary>More badges ('+(Math.max(0,on.length-6)+Math.max(0,off.length-3))+')</summary>'+(on.length>6?'<p class="mono tc-sub">Earned</p><ul class="bgrid">'+on.slice(6).map(tileHtml).join('')+'</ul>':'')+(off.length>3?'<p class="mono tc-sub">Still locked</p><ul class="bgrid">'+off.slice(3).map(tileHtml).join('')+'</ul>':'')+'</details>':'')+'</section>';
  }
  function seal(t,sz){
    var c=SEALS[t]; if(!c) return '';
    var p='',i,a,x,y,pts='';
    for(i=0;i<14;i++){ a=i*Math.PI*2/14; p+='<circle cx="'+(50+39*Math.cos(a)).toFixed(1)+'" cy="'+(50+39*Math.sin(a)).toFixed(1)+'" r="8" fill="'+c[1]+'"/>'; }
    for(i=0;i<10;i++){ a=-Math.PI/2+i*Math.PI/5; var r=i%2?9:21; pts+=(50+r*Math.cos(a)).toFixed(1)+','+(50+r*Math.sin(a)).toFixed(1)+' '; }
    return '<svg class="seal" width="'+(sz||64)+'" height="'+(sz||64)+'" viewBox="0 0 100 100" role="img" aria-label="'+c[3]+'">'+p+'<circle cx="50" cy="50" r="38" fill="'+c[1]+'"/><circle cx="50" cy="50" r="31" fill="'+c[0]+'" stroke="'+c[2]+'" stroke-width="2"/><polygon points="'+pts+'" fill="'+c[2]+'"/></svg>';
  }
  var OKL=['Stamped.','Nailed it.','Clean.','Plaque reader.'], BADL=['Ouch. The plaque disagrees.','Nope. Historians winced.','Close, the way a bird is close to a plane.','Not this time. The answer is in green.'];
  function bossSave(pid,n){ awardSoon(); var b=bossBest(); boss.prev=b[pid]; boss.gain=ptsOf(Math.max(n,b[pid]===undefined?0:b[pid]))-ptsOf(b[pid]); if(b[pid]===undefined||n>b[pid]){ b[pid]=n; try{ localStorage.setItem('then-now-boss',JSON.stringify(b)); }catch(e){} } }
  function viewBoss(){
    var Q=(DATA.boss||{})[boss.pid]||[], n=Q.length;
    var h='<div class="stophead"><button class="link" data-a="bossexit">‹ Trail</button><span class="mono">Final challenge</span></div>';
    if(boss.i>=n){
      var perfect=boss.score===n, best=bossBest()[boss.pid];
      var rt=sealTier(boss.score);
      h+='<section class="card boss-res'+(perfect?' perfect':'')+'"><p class="mono">'+(perfect?'Perfect score':'Challenge complete')+'</p>'+(rt?'<div class="sealwrap pop">'+seal(rt,96)+'<strong>'+SEALS[rt][3]+'</strong><span>'+SEALS[rt][4]+'</span></div>':'<p class="why">No seal yet. Re-read the stories and come back. It is 2 of 4 for Bronze.</p>')+'<h2>'+boss.score+' of '+n+'</h2><p>'+(perfect?'Not one slip. You really read the plaques.':(boss.score>=n-1?'So close. One more try for a perfect run?':'Good effort. The stories are still on the Cards tab if you want to read them again.'))+'</p>'+(best!==undefined?'<p class="mono">Best: '+best+' of '+n+'</p>':'')+'<p class="mono">'+(boss.gain>0?'+'+boss.gain+' challenge points':'No new points. Beat your best to earn more.')+'</p>'+(grandOk()?'<p class="grand-line">'+seal('grand',44)+' <strong>Grand Historian.</strong> Gold in every town.</p>':'')+'<div class="celeb-btns"><button class="btn" data-a="bossagain">Try again</button><button class="btn ghost" data-a="bossexit">Back to the trail</button></div></section>';
      return h;
    }
    var q=Q[boss.i];
    h+='<h2 id="stopTitle" tabindex="-1">Question '+(boss.i+1)+' of '+n+'</h2><fieldset class="opts"><legend>'+q.q+'</legend>'+q.o.map(function(o,k){
      var cls=''; if(boss.pick!==null){ if(k===q.a) cls=' right'+(k===boss.pick?' thunk':''); else if(k===boss.pick) cls=' wrong shk'; }
      return '<button class="opt'+cls+'" data-a="bpick" data-k="'+k+'"'+(boss.pick!==null?' disabled':'')+'><span>'+o+'</span>'+(boss.pick!==null&&k===q.a?'<em>Correct</em>':(boss.pick===k?'<em>Not this one</em>':''))+'</button>';
    }).join('')+'</fieldset>';
    if(boss.pick!==null){ var okb=boss.pick===q.a; h+='<p class="bfb '+(okb?'good':'bad')+'" aria-live="polite">'+(okb?OKL[boss.i%4]+((boss.streak||0)>1?' '+boss.streak+' in a row.':''):BADL[boss.i%4])+'</p>'; }
    if(boss.pick!==null) h+='<p class="why" aria-live="polite">'+q.why+'</p><button class="btn" data-a="bnext">'+(boss.i+1>=n?'See my score':'Next question')+'</button>';
    return h;
  }
  function stepper(){
    var names=['Find it','Check in','Unlock','Sources'];
    var d=S.done[cur.i];
    return '<div class="steps" role="group" aria-label="Stop steps">'+names.map(function(n,k){
      var locked=(k>=2&&!d);
      var ok=(k<cur.step)||(d&&k>=2&&k!==cur.step&&k<=2);
      var cls='step'+(k===cur.step?' cur':'')+(ok&&k!==cur.step?' ok':'');
      return '<button class="'+cls+'" data-a="step" data-n="'+k+'"'+(locked?' disabled':'')+(k===cur.step?' aria-current="step"':'')+'><span>'+n+'</span></button>';
    }).join('')+'</div>';
  }

  var streak=0;
  var FLAB=['Well documented','Disputed or unproven','Not true'];
  var FSUB=['Solid sources back it up','Historians disagree or cannot prove it','It is a myth or a mistake'];
  function nextPanel(){
    var n=STOPS.length, j=-1, k, t;
    for(k=1;k<n;k++){ t=(cur.i+k)%n; if(!S.done[t]){ j=t; break; } }
    var h='<section class="card nextstop"><p class="mono">What next</p>';
    if(j>=0){
      h+='<p>Stop done. Now go to <strong>'+STOPS[j].name+'</strong>, then check in there.</p><button class="btn" data-a="nextstop" data-i="'+j+'">Next stop: '+STOPS[j].name+'</button><button class="btn ghost" data-a="exit">Back to the trail</button>';
    } else {
      h+='<p>That is every stop in '+city().name+'. Nicely done.</p>';
      if(((DATA.boss||{})[cityId]||[]).length) h+='<button class="btn" data-a="bossgo">Take the final challenge</button>';
      h+='<button class="btn ghost" data-a="tab" data-t="rewards">See my passport</button><button class="btn ghost" data-a="exit">Back to the trail</button>';
    }
    return h+'</section>';
  }
  function factGame(st){
    var n=st.claims.length, next=-1, doneN=0;
    st.claims.forEach(function(c,ci){ if(S.claims[cur.i*2+ci]) doneN++; else if(next<0) next=ci; });
    var h='<section class="card fof"><p class="mono">Fact or Fiction</p>';
    h+='<div class="fdots" aria-label="'+doneN+' of '+n+' claims done">';
    for(var q=0;q<n;q++) h+='<i class="'+(q<doneN?'on':'')+'"></i>';
    h+='</div>';
    if(streak>1) h+='<p class="streak">Streak: '+streak+' in a row</p>';
    if(next<0){
      h+='<p><strong>All claims sorted.</strong> Here is what the sources say.</p>';
      st.claims.forEach(function(c){ h+='<div class="fdone"><p><strong>'+c.t+'</strong></p><p class="feedback good">'+FLAB[c.a]+'. <span class="why">'+c.why+'</span></p></div>'; });
      return nextPanel()+h+'</section>';
    }
    var c=st.claims[next];
    h+='<p class="why">Open book: the answers are in the story and sources you just read. Is this claim solid, disputed, or not true? Tap a label'+(('ontouchstart' in window)?', or swipe the card right for solid and left for not true':'')+'.</p>';
    h+='<div class="fcard'+(cur.fbad?' shake':'')+'" data-claim="'+next+'" tabindex="0"><p class="ftxt">'+c.t+'</p></div>';
    if(cur.fbad) h+='<p class="feedback bad" aria-live="polite">Not quite. Check the story and the sources, then try again.</p>';
    h+='<div class="fbtns" role="group" aria-label="Choose a label">'+FLAB.map(function(r,k){
      return '<button class="fbtn" data-a="fpick" data-c="'+next+'" data-k="'+k+'"><b>'+r+'</b><span>'+FSUB[k]+'</span></button>';
    }).join('')+'</div></section>';
    return h;
  }
  function factAnswer(ci,k){
    var st=STOPS[cur.i], c=st.claims[ci], gi=cur.i*2+ci;
    if(S.claims[gi]) return;
    if(k===c.a){
      S.claims[gi]=1; streak++; cur.fbad=false; save(); render();
      toast('Right. +25 XP'+(streak>1?' ('+streak+' in a row)':''));
    } else {
      streak=0; cur.fbad=true; render(); toast('Not quite. Try again.');
    }
  }
  (function(){ var x0=null,y0=null;
    document.addEventListener('touchstart',function(e){ var t=e.target.closest&&e.target.closest('.fcard'); if(!t){x0=null;return;} x0=e.touches[0].clientX; y0=e.touches[0].clientY; },{passive:true});
    document.addEventListener('touchend',function(e){ if(x0===null) return; var t=e.target.closest&&e.target.closest('.fcard'); var dx=e.changedTouches[0].clientX-x0, dy=e.changedTouches[0].clientY-y0; x0=null;
      if(!t||Math.abs(dx)<70||Math.abs(dx)<Math.abs(dy)*1.5) return; factAnswer(+t.getAttribute('data-claim'), dx>0?0:2); },{passive:true});
  })();
  function viewStop(){
    var st=STOPS[cur.i], d=S.done[cur.i];
    var h='<div class="stophead"><button class="link" data-a="exit">‹ '+(tab==='cards'?'Time Cards':'Trail')+'</button><span class="sh-r">'+(!d&&!cur.demo?'<button class="link" data-a="savestop" data-c="'+cityId+'" data-i="'+cur.i+'" aria-pressed="'+(isSaved(cityId,cur.i)?'true':'false')+'">'+(isSaved(cityId,cur.i)?'&#9733; Saved':'&#9734; Save')+'</button>':'')+'<button class="link" data-a="home">Home</button><span class="mono">'+st.tag+'</span></span></div>';
    h+='<h1 id="stopTitle" tabindex="-1">'+st.name+'</h1>';
    if(cur.demo) h+='<p class="demo-banner" role="status"><strong>Exploring from home.</strong> Read the story, answer the question and fade the photos. Get it right and you earn a virtual stamp, worth 25 XP. The full stamp (100 XP) is for real visits. Go there to earn it.</p>';
    h+=stepper();

    if(cur.step===0){
      h+='<div class="banner">'+visual(st,'now',st.name+' today')+'<span class="tagline">'+(hasPh(st,'now')?'Photo':'Illustration')+'</span></div><p class="credit">'+credit(st,'now')+'</p>';
      h+='<section class="card"><p class="mono">Find it</p><p>'+st.clue+'</p>'+(!d&&!cur.demo?'<p class="hint stopmeta">Go there for the real stamp. About '+stopMins(st)+' minutes once you arrive. Or explore from home.</p>':'')+vnote(st)
        +'<button class="btn stickgo" data-a="step" data-n="1">I am here. Show me the question</button>'+(!d&&!cur.demo?'<p class="hint">Tapping this is on your honor. Verifying with your location is optional and earns a gold stamp.</p>':'')+(st.geo&&!d&&!cur.demo&&!geoDenied?'<button class="btn ghost" data-a="geo">'+(geoGranted()?'Re-check my location':'Verify with my location (optional)')+'</button><p class="hint">Your location is checked on this phone and never sent anywhere.</p><p id="geoMsg" class="geomsg" role="status"></p>':'')+'<a class="btn ghost" target="_blank" rel="noopener" href="'+(st.geo&&st.geo.length>1?'https://www.google.com/maps/dir/?api=1&amp;destination='+st.geo[0]+','+st.geo[1]:'https://www.google.com/maps/search/?api=1&amp;query='+encodeURIComponent(st.map))+'">Get directions in Maps</a>'+(d?'':'<button class="btn ghost" data-a="demo">'+(virtHas(cityId,cur.i)?'Virtual stamp saved. Explore again':'Not there? Explore from home')+'</button>')+'</section>';
    }
    if(cur.step===1){
      h+='<section class="card"><p class="mono">Check in</p>';
      h+='<fieldset class="opts"><legend>'+st.q.prompt+'</legend>'+st.q.options.map(function(o,k){
        var cls='opt'; var mark='';
        if(d && k===st.q.answer){cls+=' right'; mark='<em>Correct</em>';}
        else if(cur.wrong.indexOf(k)>-1){cls+=' wrong'; mark='<em>Not this one</em>';}
        return '<button type="button" class="'+cls+'" data-a="pick" data-k="'+k+'"'+(d?' disabled':'')+'><span>'+o+'</span>'+mark+'</button>';
      }).join('')+'</fieldset>';
      if(d){
        h+='<div class="earned pop"><div class="bbox lg'+(cur.demo?' virt':'')+'">'+badge(st.id,true)+(cur.demo?'<i class="vtag">Virtual</i>':'')+'</div><div><strong>'+(cur.demo?'Virtual stamp earned':(geoVerified(cityId,cur.i)?'Badge earned: visit verified':'Badge earned'))+'</strong><span>'+(cur.demo?'+25 XP. Go there for the full stamp (100 XP).':st.badge)+'</span></div></div><button class="btn" data-a="step" data-n="2">Unlock the story</button>';
      } else {
        h+='<p class="feedback'+(cur.wrong.length?' bad':'')+'" aria-live="polite">'+(cur.wrong.length?'Not yet. '+st.q.hint:'Get it right to earn the '+st.badge+' badge and 100 XP.')+'</p>';
      }
      h+='</section>';
    }
    if(cur.step===2 && d){
      h+=lateVerify(st,d);
      h+='<div class="stopcols"><div class="sc-l">';
      h+=compare(st);
      if(hasPh(st,'then')&&hasPh(st,'now')){
        h+='<div class="caps"><div class="then"><div class="cap"><strong>Then, '+st.then.yr+'</strong><br>'+st.then.line+'</div>'+credit(st,'then')+'<a target="_blank" rel="noopener" href="'+st.then.link.u+'">'+st.then.link.t+'</a></div>'
          +'<div class="now"><div class="cap"><strong>'+(/^\d/.test(st.now.yr)?'Today, '+st.now.yr:'Today')+'</strong><br>'+st.now.line+'</div>'+credit(st,'now')+'</div></div>';
      } else {
        h+='<div class="pair"><div class="then">'+visual(st,'then',st.then.label+', '+st.then.yr)+'<div class="cap"><strong>Then, '+st.then.yr+': '+st.then.label+'</strong><br>'+st.then.line+'</div>'+credit(st,'then')+'<a target="_blank" rel="noopener" href="'+st.then.link.u+'">'+st.then.link.t+'</a></div>'
        +'<div class="now">'+visual(st,'now',st.now.label)+'<span class="mono">'+(st.now.head||'Now')+'</span><b class="yr">'+st.now.yr+'</b><div class="cap"><strong>'+st.now.label+'</strong><br>'+st.now.line+'</div>'+credit(st,'now')+'</div></div>';
      }
      h+='</div><div class="sc-r">';
      h+=storyHtml(st);
      if(st.disputed) h+='<aside class="argue" aria-label="Historians argue about this"><div class="argue-h"><span class="argue-ic" aria-hidden="true">?</span><span><b>Historians argue about this</b><em>Not everything here is settled.</em></span></div><p>'+st.disputed+'</p><p class="argue-go">Think you can tell solid from shaky? The Source check is next.</p></aside>';
      h+='<div class="fact"><span class="mono">Did you know</span><span>'+st.fact+'</span></div>';
      h+='<details class="card"><summary>Sources</summary><ul class="srcs">'+st.sources.map(function(s){return '<li><a target="_blank" rel="noopener" href="'+s.u+'">'+s.t+'</a></li>';}).join('')+'</ul></details>';
      h+='<button class="btn" data-a="step" data-n="3">Next: sort fact from fiction (up to 50 XP)</button>';
      h+='</div></div>';
    }
    if(cur.step===3 && d){ h+=factGame(st); }
    h+='<p class="repline"><button class="link" data-a="report">Something wrong here? Tell us</button></p>';
    return h;
  }

  function viewCards(){
    var h='<p>Each stop you unlock adds a Time Card to your collection. Tap one to reopen its story.</p><div class="grid">';
    var lockedN=[];
    STOPS.forEach(function(s,i){
      if(S.done[i]){
        h+='<button class="tcard" data-a="open" data-i="'+i+'" data-s="2"><span class="mono">'+s.name+'</span>'
          +'<span class="mini">'+visual(s,'then','Then: '+s.card.la,' then-s').replace(/<div/g,'<span').replace(/<\/div>/g,'</span>')+visual(s,'now','Now: '+s.card.lb).replace(/<div/g,'<span').replace(/<\/div>/g,'</span>')+'</span><span class="credit-txt">Then: '+creditTxt(s,'then')+'. Now: '+creditTxt(s,'now')+'.</span>'
          +'<span class="years">'+s.card.a+' <i>→</i> '+s.card.b+'</span><span><strong>Then:</strong> '+s.card.la+'</span><span><strong>Now:</strong> '+s.card.lb+'</span></button>';
      } else lockedN.push(s.name);
    });
    if(lockedN.length) h+='<div class="tcard locked"><span class="mono">'+lockedN.length+' locked</span><span class="years">? <i>→</i> ?</span><span>Find '+lockedN.join(', ').replace(/, ([^,]*)$/,' and $1')+' to collect '+(lockedN.length>1?'these cards':'this card')+'.</span></div>';
    return h+'</div>';
  }

  function viewRewards(){
    var x=xp(), r=rank(x);
    var h='<section class="card"><h3>Passport: '+city().name+'</h3><p class="why" style="margin:0 0 10px">Each stop you finish stamps a page.</p><div class="cases" style="--ink:'+INKS[Math.min(inkI,bestRank())].c+'">'+STOPS.map(function(s,i){
      return '<div class="case'+(S.done[i]?' got':'')+'"><div class="bbox lg">'+badge(s.id,S.done[i])+'</div><span class="nm">'+s.badge+'</span><span class="mono">'+(S.done[i]?'Stamped':'Blank page')+'</span></div>';
    }).join('')+'</div></section>';
    h+='<section class="card"><h3>'+city().explorer+'</h3><div class="master"><div class="bbox lg">'+badge('master',allDone())+'</div><p>'+(allDone()?'Earned. You found every stop in '+city().name+'.':'Earn all four badges to unlock it.')+'</p></div></section>';
    var br=bestRank();
    h+='<section class="card"><h3>Stamp ink</h3><p class="why" style="margin:0 0 8px">XP unlocks new inks for your stamps. Higher ranks in any town unlock more.</p><div class="inks" role="group" aria-label="Stamp ink">'+INKS.map(function(k,i){
      var open=i<=br;
      return '<button class="ink" data-a="ink" data-i="'+i+'" aria-pressed="'+(i===Math.min(inkI,br))+'"'+(open?'':' disabled')+' style="color:'+k.c+'"><i></i><span style="color:var(--ink)">'+(open?k.n:RANKS[i][0]+' XP')+'</span></button>';
    }).join('')+'</div></section>';
    h+='<section class="card"><h3>Rank</h3><ul class="ladder">'+RANKS.map(function(rk,i){
      return '<li class="'+(i<=r.i?'got':'')+'"><span>'+rk[1]+'</span><span class="mono">'+(i<=r.i?'Earned':rk[0]+' XP')+'</span></li>';
    }).join('')+'</ul></section>';
    h+='<section class="card"><h3>Back up your passport</h3><p>There are no accounts. To move your badges to another phone, copy this code there and paste it below.</p><div class="code"><input id="codeOut" readonly value="'+code()+'" aria-label="Progress code"><button class="btn small" data-a="copy">Copy</button></div>'
      +'<div class="code"><input id="codeIn" placeholder="Paste a code" aria-label="Paste a progress code" autocomplete="off" autocapitalize="characters" spellcheck="false"><button class="btn small ghost" data-a="restore">Restore</button></div><p id="codeMsg" class="why" aria-live="polite"></p></section>';
    h+='<section class="card"><h3>Start over</h3>'+(confirmReset?'<p>Erase every badge and all XP for '+city().name+' on this phone?</p><div class="row"><button class="btn" data-a="resetyes">Yes, erase</button><button class="btn ghost" data-a="resetno">Cancel</button></div>':'<button class="btn ghost" data-a="resetask">Reset progress</button>')+'</section>';
    return h;
  }

  function render(focusTitle){
    updateHeader();
    document.body.classList.toggle('ishome',atHome); document.body.classList.toggle('ispass',atHome&&onPass); document.body.classList.remove('navhide'); updateBnav();
    document.body.classList.toggle('instop',!!cur&&!boss);
    document.body.classList.toggle('inboss',!!boss);
    var m=document.getElementById('main');
    m.setAttribute('aria-labelledby','tab-'+tab);
    if(boss&&(atHome||boss.pid!==cityId)) boss=null;
    if(boss) m.innerHTML=viewBoss();
    else if(atHome&&!cur) m.innerHTML=onPass?viewPass():viewHome();
    else if(cur) m.innerHTML=viewStop();
    else if(tab==='trail') m.innerHTML=viewTrail();
    else if(tab==='cards') m.innerHTML=viewCards();
    else m.innerHTML=viewRewards();
    var bar=document.getElementById('bar');
    var showBar=false;
    if(cur) showBar=cur.step>cur.entry;
    bar.hidden=!showBar;
    document.body.classList.toggle('hasbar',showBar);
    if(cur){
      var atRoot=cur.step<=cur.entry;
      document.getElementById('barBack').textContent='‹ Previous step';
      document.getElementById('barBack').setAttribute('aria-label',atRoot?('Back to '+(tab==='cards'?'Time Cards':'Trail')):'Back to previous step');
      document.getElementById('barExit').textContent=(tab==='cards'?'All cards':'All stops');
    }
    if(cur&&cur.step===2&&!nudged&&!window.matchMedia('(prefers-reduced-motion: reduce)').matches){
      var rg=document.querySelector('#main input[data-cmp]');
      if(rg){ nudged=true; var t0=null, tp=document.querySelector('#main .cmp .top');
        var go=function(ts){ if(!t0) t0=ts; var k=(ts-t0)/1100; if(k>=1){ rg.value=0; if(tp) tp.style.opacity=0; return; } var v=Math.sin(k*Math.PI)*45; rg.value=v; if(tp) tp.style.opacity=v/100; requestAnimationFrame(go); };
        setTimeout(function(){ requestAnimationFrame(go); },500); }
    }
    if(focusTitle){
      var t=document.getElementById('stopTitle');
      if(t) t.focus({preventScroll:true});
    }
  }

  /* ---------- navigation ---------- */
  function leave(){
    endDemo(); cur=null;
    if(pushed){
      pushed=false; ignorePop=true;
      try{ history.back(); }catch(e){ ignorePop=false; }
    }
  }
  function exitStop(){ leave(); render(); window.scrollTo(0,0); }
  function openStop(i,step){
    endDemo();
    var entry=(step!==undefined?step:(S.done[i]?2:0));
    cur={i:i,step:entry,entry:entry,wrong:[],picks:[],checked:false};
    if(!pushed){ try{ history.pushState({stop:1},'','#stop'); pushed=true; }catch(e){} }
    render(true); window.scrollTo(0,0); autoGeo();
  }
  function autoGeo(){ if(cur&&cur.step===0&&!cur.autoTried&&!cur.demo&&!S.done[cur.i]&&STOPS[cur.i]&&STOPS[cur.i].geo&&geoGranted()&&!geoDenied){ cur.autoTried=true; geoCheck(true); } }
  function setStep(n){
    if(n>=2 && !S.done[cur.i]) return;
    cur.step=n; cur.checked=false; render(true); window.scrollTo(0,0);
  }
  function goBack(){
    if(!cur) return;
    if(cur.step>cur.entry) setStep(cur.step-1); else exitStop();
  }
  window.addEventListener('popstate',function(){
    if(ignorePop){ ignorePop=false; return; }
    if(cur){ pushed=false; cur=null; render(); window.scrollTo(0,0); }
  });

  document.addEventListener('click',function(e){
    var b=e.target.closest('[data-a]'); if(!b) return;
    var a=b.getAttribute('data-a');
    if(a==='menu'){ openMenu(); return; }
    if(a==='menuclose'){ closeMenu(); return; }
    if(a==='daily'){ location.href='/daily/'; return; }
    if(a==='theme'){ var tv=b.getAttribute('data-t'); try{ if(tv==='system') localStorage.removeItem('stp-theme'); else localStorage.setItem('stp-theme',tv); }catch(x){} themeApply(tv); b.parentNode.querySelectorAll('.seg').forEach(function(x){ var on=x===b; x.classList.toggle('on',on); x.setAttribute('aria-pressed',on?'true':'false'); }); return; }
    if(document.getElementById('menu')&&['backup','share','replaytour','report'].indexOf(a)>-1) closeMenu();
    if(a==='home'){ goHome(); return; }
    if(a==='nextstop'){ var nc=b.getAttribute('data-c'); if(nc&&CITIES[nc]&&nc!==cityId){ railRegion=null; setCity(nc); } openStop(+b.getAttribute('data-i'),0); return; }
    if(a==='bossgo'){ leave(); boss={pid:cityId,i:0,score:0,pick:null}; render(); window.scrollTo(0,0); return; }
    if(a==='boss'||a==='bossagain'){ boss={pid:cityId,i:0,score:0,pick:null}; render(); window.scrollTo(0,0); return; }
    if(a==='bossexit'){ boss=null; render(); window.scrollTo(0,0); return; }
    if(a==='bpick'){ if(boss&&boss.pick===null){ var qq=DATA.boss[boss.pid][boss.i], kk=+b.getAttribute('data-k'); boss.pick=kk; if(kk===qq.a){ boss.score++; boss.streak=(boss.streak||0)+1; } else boss.streak=0; render(); } return; }
    if(a==='bnext'){ if(boss){ boss.i++; boss.pick=null; if(boss.i>=DATA.boss[boss.pid].length) bossSave(boss.pid,boss.score); render(); window.scrollTo(0,0); } return; }
    if(a==='hapticTest'){ haptic('success',function(r){ toast(r==='ok'?'Buzz sent. If you felt nothing, check Settings, Sounds and Haptics, System Haptics.':r==='missing'?'The buzz part of the app did not load. Please tell us.':'The buzz did not run. Please tell us.'); }); return; }
    if(a==='report'){ showReport(); return; }
    if(a==='repclose'){ closeReport(); return; }
    if(a==='repsend'){ sendReport(); return; }
    if(a==='tournext'){ if(tourI>=TOUR.length-1){ endTour(); if(!atHome||onPass) goHome(); var mm0=document.getElementById('missions'); if(mm0&&mm0.scrollIntoView) mm0.scrollIntoView({behavior:'smooth',block:'start'}); } else { tourI++; showTour(); } return; }
    if(a==='tourback'){ if(tourI>0){ tourI--; showTour(); } return; }
    if(a==='replaytour'){ replayTour(); return; }
    if(a==='tourskip'){ endTour(); return; }
    if(a==='celebclose'){ closeCeleb(); return; }
    if(a==='celebboss'){ closeCeleb(); boss={pid:cityId,i:0,score:0,pick:null}; render(); window.scrollTo(0,0); return; }
    if(a==='bnav'){ var bt=b.getAttribute('data-t');
      if(bt==='pass'){ openPass(); return; }
      if(bt==='home'){ bnavSel='home'; goHome(); return; }
      bnavSel=bt; if(!atHome||onPass) goHome(); setBtab(bt); updateBnav(); var bw=document.getElementById('browse'); if(bw&&bw.scrollIntoView) bw.scrollIntoView({behavior:'smooth',block:'start'}); return; }
    if(a==='btab'){ setBtab(b.getAttribute('data-t')); return; }
    if(a==='trail'){ btrail=b.getAttribute('data-t'); document.querySelectorAll('.tcard').forEach(function(c){ var on=c.getAttribute('data-t')===btrail; c.classList.toggle('on',on); c.setAttribute('aria-pressed',on?'true':'false'); }); document.querySelectorAll('.trl').forEach(function(x){ x.hidden=(x.getAttribute('data-trail')!==btrail); }); return; }
    if(a==='share'){ var sk=b.getAttribute('data-k'); if(sk&&CITIES[sk]) shareStamps('town',sk); else shareStamps('passport'); return; }
    if(a==='shareclose'){ shareClose(); return; }
    if(a==='sharefile'){ if(fadeFile&&navigator.share) navigator.share({files:[fadeFile.f],text:fadeFile.t}).catch(function(){}); return; }
    if(a==='sharefade'){ fadeShare(b); return; }
    if(a==='spotpick'){ var sp=STOPS[cur.i]&&STOPS[cur.i].spot, box=document.getElementById('spot'); if(!sp||!box) return; var k=+b.getAttribute('data-k'), fb=box.querySelector('.sfb'); if(k===sp.answer){ box.querySelectorAll('.spo').forEach(function(x){ x.disabled=true; x.classList.remove('wrong'); }); b.classList.add('right'); fb.textContent='Right. '+sp.why; } else { b.classList.add('wrong'); b.disabled=true; fb.textContent='Not that one. Slide the photo again and try another.'; } return; }
    if(a==='savestop'){ var sk=b.getAttribute('data-c'), si=+b.getAttribute('data-i'), key=savedKey(sk,si), sa=savedRaw(), sx=sa.indexOf(key); if(!key) return; if(sx>-1) sa.splice(sx,1); else sa.push(key); savedSet(sa); var sy=window.scrollY; render(false); window.scrollTo(0,sy); toast(sx>-1?'Removed from saved stops.':'Saved. Find it under Towns, My trip.'); return; }
    if(a==='trip'){ var tk=b.getAttribute('data-c'), ta=tripGet(), ti=ta.indexOf(tk); if(ti>-1) ta.splice(ti,1); else ta.push(tk); tripSet(ta); var sv=window.scrollY; render(); window.scrollTo(0,sv); toast(ti>-1?'Removed from your trip.':'Added to your trip.'); return; }
    if(a==='schip'){ var inp=document.getElementById('townSearch'); if(inp){ var sv2=b.getAttribute('data-s'); inp.value=(inp.value.trim().toLowerCase()===sv2.toLowerCase())?'':sv2; inp.dispatchEvent(new Event('input',{bubbles:true})); } return; }
    if(a==='gomissions'){ setBtab('towns'); var mm=document.getElementById('missions'); if(mm&&mm.scrollIntoView) mm.scrollIntoView({behavior:'smooth',block:'start'}); return; }
    if(a==='backup'){ closeCeleb(); try{ localStorage.setItem('stp-bk-seen',String(totalStamps())); }catch(e){} openPass(); setTimeout(function(){ var el=document.getElementById('backup'); if(el) el.scrollIntoView({behavior:window.matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth',block:'start'}); },60); return; }
    if(a==='bkdismiss'){ try{ localStorage.setItem('stp-bk-seen',String(totalStamps())); }catch(e){} render(); return; }
    if(a==='passport'||a==='mypass'){ closeCeleb(); openPass(); return; }
    if(a==='bpopclose'){ closeBpop(); return; }
    if(a==='trophy'){ closeBpop(); closeCeleb(); openPass(); setTimeout(function(){ var el=document.getElementById('trophy'); if(el) el.scrollIntoView({behavior:window.matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth',block:'start'}); },60); return; }
    if(a==='rregion'){ railRegion=b.getAttribute('data-r'); if(atHome) setHeroFocus({r:railRegion}); applyCity(); return; }
    if(a==='trailweek'){ btrail=b.getAttribute('data-t'); setBtab('trails'); render(); updateBnav(); var bw2=document.getElementById('browse'); if(bw2&&bw2.scrollIntoView) bw2.scrollIntoView({behavior:'smooth',block:'start'}); return; }
    if(a==='city'){ railRegion=null; setCity(b.getAttribute('data-c')); return; }
    if(a==='tab'){ boss=null; leave(); tab=b.getAttribute('data-t'); confirmReset=false; render(); window.scrollTo(0,0); return; }
    if(a==='open'){ var s=b.getAttribute('data-s'); openStop(+b.getAttribute('data-i'), s?+s:undefined); return; }
    if(a==='exit'){ exitStop(); return; }
    if(a==='goback'){ goBack(); return; }
    if(a==='demo'){ if(!S.done[cur.i]){ demoSnap={done:S.done.slice(),claims:S.claims.slice()}; demoC=S; cur.demo=1; cur.step=1; render(true); window.scrollTo(0,0);} return; }
    if(a==='geo'){ geoCheck(false); return; }
    if(a==='nearall'){ nearAll=true; nearPaint(); return; }
    if(a==='nearme'){
      if(!navigator.geolocation){ toast('This device cannot share its location.'); return; }
      navigator.geolocation.getCurrentPosition(function(pos){ try{ localStorage.setItem('stp-geo-ok','1'); }catch(e){} geoStartWatch(); onFix(pos); nearPaint(); },function(err){ if(err&&err.code===1){ geoDenied=true; toast('Location is off for this app, which is fine. Pick a town from Towns.'); } else toast('Could not get your location. Try again outside.'); nearPaint(); },{enableHighAccuracy:false,timeout:15000,maximumAge:60000});
      return;
    }
    if(a==='neargo'){ var nc2=b.getAttribute('data-c'), ni=+b.getAttribute('data-i'); var inr=!b.getAttribute('data-far'); if(nc2&&CITIES[nc2]){ railRegion=null; if(nc2!==cityId||atHome) setCity(nc2); openStop(ni,0); if(inr&&!S.done[ni]){ cur.gv=true; setStep(1); } } return; }
    if(a==='bgtoggle'){ var on=!bgOn(); try{ localStorage.setItem('stp-bg',on?'1':'0'); }catch(x){} if(on) bgSync(); else if(NG) try{ NG.disable(); }catch(x){} b.setAttribute('aria-pressed',on); b.textContent=on?'On':'Off'; return; }
    if(a==='livetoggle'){ try{ localStorage.setItem('stp-geo-live',liveOn()?'0':'1'); }catch(x){} if(liveOn()) geoStartWatch(); else { geoStopWatch(); nearHit=null; } b.setAttribute('aria-pressed',liveOn()); b.textContent=liveOn()?'On':'Off'; return; }
    if(a==='step'){ setStep(+b.getAttribute('data-n')); return; }
    if(a==='pick'){
      var k=+b.getAttribute('data-k'), st=STOPS[cur.i];
      if(k===st.q.answer){
        if(cur.demo){ if(!S.done[cur.i]){ S.done[cur.i]=1; var vnew=!virtGet()[cityId+':'+st.id]; virtSave(); if(vnew){ ping('virtual-stamp'); toast('Correct. Virtual stamp saved, +25 XP. Go there for the real one.'); } else toast('Correct. You already have this virtual stamp.'); } }
        else if(!S.done[cur.i]){ S.done[cur.i]=1; if(cur.gv){ geoSave(); } logStamp(); save(); awardSoon(); ping('stamp'); pingOnce('first','first-stamp'); if(allDone()) pingOnce('t:'+city().name,'town-finished'); stampFx=true; haptic('success'); try{ if(navigator.vibrate) navigator.vibrate([18,40,28]); }catch(e){} if(allDone()) setTimeout(celebrate,1400); }
        cur.wrong=[]; render(); if(stampFx){ stampFx=false; var eb=document.querySelector('.earned .bbox'); if(eb){ eb.classList.add('thud'); try{ var er=eb.closest('.earned'); if(er&&er.scrollIntoView) er.scrollIntoView({behavior:'smooth',block:'center'}); }catch(e){} } }
      } else {
        if(cur.wrong.indexOf(k)<0) cur.wrong.push(k);
        render(); try{ var fb=document.querySelector('.feedback.bad'); if(fb&&fb.scrollIntoView) fb.scrollIntoView({behavior:'smooth',block:'nearest'}); }catch(e){}
      }
      return;
    }
    if(a==='ink'){ var ii=+b.getAttribute('data-i'); if(ii<=bestRank()){ inkI=ii; try{ localStorage.setItem('then-now-ink',String(ii)); }catch(e){} render(); } return; }
    if(a==='hpick'){ homeAnswer(+b.getAttribute('data-k')); return; }
    if(a==='fpick'){ factAnswer(+b.getAttribute('data-c'),+b.getAttribute('data-k')); return; }
    if(a==='cpick'){
      cur.picks[+b.getAttribute('data-c')]=+b.getAttribute('data-k'); cur.checked=false; render(); return;
    }
    if(a==='check'){
      var st2=STOPS[cur.i], gained=0, ok=0;
      st2.claims.forEach(function(c,ci){
        var gi=cur.i*2+ci;
        if(S.claims[gi]){ ok++; return; }
        if(cur.picks[ci]===c.a){ S.claims[gi]=1; gained+=25; ok++; }
      });
      cur.checked=true; save(); render();
      if(gained){ toast('+'+gained+' XP'); awardSoon(); }
      else if(ok<st2.claims.length) toast('Not yet. Try again.');
      return;
    }
    if(a==='copy'){
      var inp=document.getElementById('codeOut');
      var done=function(){ toast('Code copied'); };
      var fb=function(){ inp.focus(); inp.select(); toast('Code selected. Copy it manually.'); };
      try{ navigator.clipboard.writeText(code()).then(done,fb); }catch(err){ fb(); }
      return;
    }
    if(a==='restore'){
      var v=(document.getElementById('codeIn').value||'').trim().toUpperCase();
      var m1=/^TN1-([01]{4})([01]{8})$/.exec(v), m2=/^TN2-([01]{4})([01]{8})-([01]{4})([01]{8})$/.exec(v), m3=/^TN3-([01]{12}(?:-[01]{12})*)$/.exec(v), msg=document.getElementById('codeMsg');
      if(!m1 && !m2 && !m3){ msg.textContent='That code does not look right. It starts with TN3- (older TN1- and TN2- codes work too).'; return; }
      var arr=function(x){return x.split('').map(Number);};
      if(m1){ ALL.reno={done:arr(m1[1]),claims:arr(m1[2])}; }
      else if(m2){ ALL.reno={done:arr(m2[1]),claims:arr(m2[2])}; ALL.vc={done:arr(m2[3]),claims:arr(m2[4])}; }
      else {
        var segs=m3[1].split('-');
        if(segs.length>ORDER.length){ msg.textContent='That code has more towns than this version of the app. Update the app and try again.'; return; }
        segs.forEach(function(g,i){ ALL[ORDER[i]]={done:arr(g.slice(0,4)),claims:arr(g.slice(4))}; });
      }
      S=ALL[cityId]; save(); render(); toast('Progress restored'); awardSoon(); return;
    }
    if(a==='resetask'){ confirmReset=true; render(); return; }
    if(a==='resetno'){ confirmReset=false; render(); return; }
    if(a==='resetyes'){ ALL[cityId]=blank(); S=ALL[cityId]; save(); confirmReset=false; render(); toast('Progress erased'); return; }
  });

  load(); applyCity(); render(); maybeTour(); geoStartWatch(); bgSync(); bgOpenPending(); try{ if(totalStamps()>0) pingOnce('d:'+dstr(new Date()),'active-day'); }catch(e){} try{ if(localStorage.getItem('stp-badges')===null&&!totalStamps()) localStorage.setItem('stp-badges','{}'); }catch(e){} awardSoon();
  if(NG){ try{ NG.addListener('stopTap',function(){ bgOpenPending(); }); }catch(e){} }
})();
