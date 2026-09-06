/* Euchre for Seniors - Big Cards — service worker (network-first for the page, versioned cache for assets) */
var CACHE='euchre-v2-2';
var ASSETS=["./", "./index.html", "./manifest.webmanifest", "./djpp-kit.js", "./djpp-board.js", "./icon-192.png", "./icon-512.png", "./icon-maskable-512.png", "./favicon.png", "./icon-apple-180.png"];
self.addEventListener('install',function(e){self.skipWaiting();
  e.waitUntil(caches.open(CACHE).then(function(c){
    /* add individually: one bad asset must not wedge the whole install */
    return Promise.all(ASSETS.map(function(u){return c.add(u).catch(function(){});}));}));});
self.addEventListener('activate',function(e){
  e.waitUntil(caches.keys().then(function(ks){return Promise.all(ks.map(function(k){if(k!==CACHE)return caches.delete(k);}));})
    .then(function(){return self.clients.claim();}));});
self.addEventListener('fetch',function(e){
  var req=e.request; if(req.method!=='GET')return;
  var url; try{url=new URL(req.url);}catch(err){return;}
  if(url.origin!==self.location.origin)return;
  /* never intercept the worker itself - a cached sw.js can never be replaced */
  if(url.pathname==='/sw.js')return;
  if((req.mode==='navigate')||(req.destination==='document')){
    /* network-first for the page so a new deploy lands on the next load */
    e.respondWith(fetch(req).then(function(resp){
      var cp=resp.clone();caches.open(CACHE).then(function(c){c.put('./index.html',cp);});return resp;})
      .catch(function(){return caches.open(CACHE).then(function(c){return c.match('./index.html');});}));
    return;}
  /* cache-first for assets, scoped to the CURRENT cache so a stale one can never serve */
  e.respondWith(caches.open(CACHE).then(function(c){
    return c.match(req).then(function(r){
      return r||fetch(req).then(function(resp){
        if(resp&&resp.status===200&&resp.type==='basic'){var cp=resp.clone();c.put(req,cp);}
        return resp;})
      .catch(function(){return c.match('./index.html');});});}));});
