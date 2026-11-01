/* Offline support for the web version. Build id replaced by build.py. */
var V='tn-6acb89cb94';
var CORE=['play.html','manifest.webmanifest','icon-192.png','icon-512.png','apple-touch-icon.png'];
self.addEventListener('install',function(e){ e.waitUntil(caches.open(V).then(function(c){ return c.addAll(CORE); }).then(function(){ return self.skipWaiting(); })); });
self.addEventListener('activate',function(e){ e.waitUntil(caches.keys().then(function(ks){ return Promise.all(ks.filter(function(k){ return k.indexOf('tn-')===0&&k!==V; }).map(function(k){ return caches.delete(k); })); }).then(function(){ return self.clients.claim(); })); });
self.addEventListener('fetch',function(e){
  var r=e.request; if(r.method!=='GET') return;
  var u=new URL(r.url);
  if(u.origin===location.origin){
    if(r.mode==='navigate'&&(u.pathname==='/play'||u.pathname==='/play.html')){
      e.respondWith(fetch(r).then(function(res){ var cp=res.clone(); caches.open(V).then(function(c){ c.put('play.html',cp); }); return res; }).catch(function(){ return caches.match('play.html');  }));
      return;
    }
    if(r.mode==='navigate') return;
    e.respondWith(caches.match(r).then(function(m){ return m||fetch(r).then(function(res){ var cp=res.clone(); caches.open(V).then(function(c){ c.put(r,cp); }); return res; }); }));
    return;
  }
  if(u.host==='fonts.googleapis.com'||u.host==='fonts.gstatic.com'){
    e.respondWith(caches.open(V+'-fonts').then(function(c){ return c.match(r).then(function(m){ var f=fetch(r).then(function(res){ c.put(r,res.clone()); return res; }).catch(function(){ return m; }); return m||f; }); }));
  }
});
