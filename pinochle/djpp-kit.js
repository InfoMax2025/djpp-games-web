/* DJ's Puzzle Palace — shared game kit v1.1
   Adds to any DJPP card game: local stats, a rating prompt, the "Fair Deal" panel,
   the "More games" panel and the shared Top 10 board (djpp-board.js, loaded by this file). Configured by window.DJPP_CONFIG (set before this loads):
     { game:'cribbage', title:'Cribbage', pkg:'com.djspuzzlepalace.cribbage',
       team:false,                       // true for partnership games (Euchre, Pinochle, Spades)
       target:'121 points',              // how a game is won (for the Fair Deal text)
       extras:[{key:'bestHand',label:'Biggest hand counted',mode:'max'}] }
   The game calls DJPP.record({won:true, you:121, opp:96, extra:{...}}) once when a game ends,
   and DJPP.stat(key, value) for game-specific extras at any time.
*/
(function(){
'use strict';
var C = window.DJPP_CONFIG || {};
var GAME = C.game || 'game';
var TITLE = C.title || 'this game';
var PKG = C.pkg || '';
var LS = 'djpp.'+GAME+'.';
var CATALOG = [
  {pkg:'com.djspuzzlepalace.cribbage', name:'Cribbage Seniors', line:'Big cards. Every point counted for you, out loud.'},
  {pkg:'com.djspuzzlepalace.euchre', name:'Euchre for Seniors', line:'Relaxed trick-taking with a fair partner.'},
  {pkg:'com.djspuzzlepalace.ginrummy', name:'Gin Rummy Seniors', line:'Melds outlined, deadwood totalled for you.'},
  {pkg:'com.djspuzzlepalace.pinochle', name:'Pinochle Seniors', line:'Every meld counted and explained.'},
  {pkg:'com.djspuzzlepalace.spades', name:'Spades Seniors', line:'Nil bids, jokers or classic — your table, your rules.'},
  {pkg:'com.djspuzzlepalace.towercontrol3d', name:'Control Tower 3D', line:'Run the tower. Land them all. A calm ATC sim.'}
];

/* ---------- storage ---------- */
function load(k, d){ try{ var v=localStorage.getItem(LS+k); return v?JSON.parse(v):d; }catch(e){ return d; } }
function save(k, v){ try{ localStorage.setItem(LS+k, JSON.stringify(v)); }catch(e){} }
function freshStats(){ return {games:0,wins:0,losses:0,streak:0,bestStreak:0,bestMargin:0,extras:{},last:0,first:Date.now()}; }
var S = load('stats', freshStats());
if(!S.extras) S.extras={};
var R = load('rate', {done:false,lastAsk:0,asks:0});

/* ---------- environment ---------- */
var ref = document.referrer||'';
var ENV = load('env', {twa:false});
if(ref.indexOf('android-app://')===0){ ENV.twa=true; save('env', ENV); }
var STANDALONE = (window.matchMedia && matchMedia('(display-mode: standalone)').matches) || navigator.standalone===true;
var IS_APP = ENV.twa || STANDALONE || /\bwv\b|; wv\)/.test(navigator.userAgent);
function playUrl(pkg){ return 'https://play.google.com/store/apps/details?id='+pkg; }
function openPlay(pkg){ var u=playUrl(pkg); try{ var w=window.open(u,'_blank'); if(!w) location.href=u; }catch(e){ location.href=u; } }

/* ---------- styles ---------- */
var css = ''+
'#djppMenu{display:flex;gap:10px;flex-wrap:wrap;justify-content:center;margin-top:16px;}'+
'.djpp-btn{cursor:pointer;border:2px solid rgba(255,255,255,.32);border-radius:14px;background:rgba(255,255,255,.10);'+
'  color:var(--cream,#faf6ea);font:800 17px/1 "Segoe UI",Roboto,Helvetica,Arial,sans-serif;padding:13px 18px;letter-spacing:.3px;}'+
'.djpp-btn:active{transform:scale(.97);}'+
'.djpp-btn.gold{background:linear-gradient(180deg,#ffe08a,#e5ad2e);color:#241800;border-color:transparent;font-size:20px;padding:16px 26px;}'+
'.djpp-btn.green{background:linear-gradient(180deg,#8ceaa8,#37b565);color:#06210f;border-color:transparent;font-size:20px;padding:16px 26px;}'+
'#djppResult{margin:2px 0 14px;font:700 17px/1.5 "Segoe UI",Roboto,Helvetica,Arial,sans-serif;color:var(--cream,#faf6ea);'+
'  background:rgba(255,255,255,.07);border:1px solid rgba(255,255,255,.14);border-radius:14px;padding:10px 18px;max-width:560px;}'+
'#djppResult .hi{color:var(--gold,#f6c945);}'+
'#djppResult .bd{margin-top:6px;font-size:15px;opacity:.9;}'+
'#djppResult .bd.link{cursor:pointer;text-decoration:underline;text-decoration-color:rgba(246,201,69,.6);}'+
'#djppPanel{position:fixed;inset:0;z-index:2000;display:flex;flex-direction:column;align-items:center;justify-content:flex-start;'+
'  padding:24px 16px 32px;overflow-y:auto;text-align:center;color:var(--cream,#faf6ea);'+
'  font-family:"Segoe UI",Roboto,Helvetica,Arial,sans-serif;background:radial-gradient(ellipse at 50% 30%,rgba(8,52,27,.985),rgba(3,20,10,.995));}'+
'#djppPanel .kick{font-size:13px;letter-spacing:3px;color:var(--gold,#f6c945);font-weight:800;margin-bottom:8px;}'+
'#djppPanel h2{font-size:clamp(28px,7vw,40px);margin:0 0 14px;font-weight:900;color:#fff;}'+
'#djppPanel .box{background:rgba(255,255,255,.07);border:1px solid rgba(255,255,255,.14);border-radius:16px;'+
'  padding:16px 22px;margin:0 0 16px;text-align:left;max-width:600px;width:100%;font-size:clamp(17px,3vw,20px);line-height:1.5;}'+
'#djppPanel .box b{color:var(--gold,#f6c945);}'+
'#djppPanel .row{display:flex;justify-content:space-between;gap:12px;padding:9px 0;border-bottom:1px solid rgba(255,255,255,.1);font-size:20px;}'+
'#djppPanel .row:last-child{border-bottom:none;}'+
'#djppPanel .row .v{font-weight:900;color:var(--gold,#f6c945);white-space:nowrap;}'+
'#djppPanel .big{font-size:clamp(40px,12vw,64px);font-weight:900;color:var(--gold,#f6c945);line-height:1;margin:6px 0 2px;}'+
'#djppPanel .cap{font-size:15px;opacity:.75;margin-bottom:14px;}'+
'#djppPanel .stars{font-size:38px;letter-spacing:4px;color:#ffd35c;margin:6px 0 10px;text-shadow:0 2px 6px rgba(0,0,0,.5);}'+
'#djppPanel .acts{display:flex;flex-direction:column;gap:12px;width:100%;max-width:420px;margin-top:6px;}'+
'#djppPanel .acts .djpp-btn{width:100%;font-size:20px;padding:16px 20px;}'+
'#djppPanel .game{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:12px 0;border-bottom:1px solid rgba(255,255,255,.1);}'+
'#djppPanel .game:last-child{border-bottom:none;}'+
'#djppPanel .game .n{font-weight:900;font-size:19px;}'+
'#djppPanel .game .l{font-size:15px;opacity:.8;font-weight:600;}'+
'#djppPanel .game .djpp-btn{flex:none;padding:11px 14px;font-size:15px;}'+
'#djppPanel .foot{margin-top:14px;font-size:12px;color:rgba(255,255,255,.4);}'+
'@media (max-height:560px){#djppPanel{padding-top:12px;} #djppPanel h2{margin-bottom:8px;}}';
var st=document.createElement('style'); st.textContent=css; document.head.appendChild(st);

/* ---------- panel plumbing ---------- */
var panel=null, onClose=null;
function openPanel(kick, title, bodyEl, actions, closeLabel){
  closePanel();
  panel=document.createElement('div'); panel.id='djppPanel';
  var k=document.createElement('div'); k.className='kick'; k.textContent=kick||"DJ'S PUZZLE PALACE";
  var h=document.createElement('h2'); h.textContent=title;
  panel.appendChild(k); panel.appendChild(h);
  if(bodyEl) panel.appendChild(bodyEl);
  var acts=document.createElement('div'); acts.className='acts';
  (actions||[]).forEach(function(a){ var b=document.createElement('button'); b.className='djpp-btn '+(a.cls||''); b.textContent=a.label;
    b.onclick=function(){ if(a.fn) a.fn(); if(!a.keep) closePanel(); }; acts.appendChild(b); });
  if(closeLabel!==null){ var c=document.createElement('button'); c.className='djpp-btn'; c.textContent=closeLabel||'Back to game'; c.onclick=closePanel; acts.appendChild(c); }
  panel.appendChild(acts);
  var f=document.createElement('div'); f.className='foot'; f.textContent="A DJ's Puzzle Palace game"; panel.appendChild(f);
  document.body.appendChild(panel);
  panel.scrollTop=0;
}
function closePanel(){ if(panel&&panel.parentNode) panel.parentNode.removeChild(panel); panel=null; if(onClose){ var f=onClose; onClose=null; f(); } }
function box(html){ var d=document.createElement('div'); d.className='box'; d.innerHTML=html; return d; }
function esc(s){ return String(s).replace(/[&<>"]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c];}); }

/* ---------- stats ---------- */
function pct(a,b){ return b? Math.round(a/b*100)+'%' : '—'; }
function showStats(){
  var b=document.createElement('div'); b.className='box';
  var rows=[
    ['Games played', S.games],
    ['Wins', S.wins],
    ['Losses', S.losses],
    ['Win rate', pct(S.wins,S.games)],
    ['Current streak', S.streak+(S.streak>=3?' 🔥':'')],
    ['Best streak', S.bestStreak],
    ['Biggest win margin', S.bestMargin? '+'+S.bestMargin : '—']
  ];
  (C.extras||[]).forEach(function(x){ var v=S.extras[x.key]; rows.push([x.label, (v===undefined||v===null)?'—':v]); });
  rows.forEach(function(r){ var d=document.createElement('div'); d.className='row'; d.innerHTML='<span>'+esc(r[0])+'</span><span class="v">'+esc(r[1])+'</span>'; b.appendChild(d); });
  var wrap=document.createElement('div'); wrap.style.width='100%'; wrap.style.maxWidth='600px';
  var big=document.createElement('div'); big.className='big'; big.textContent=S.wins+'–'+S.losses;
  var cap=document.createElement('div'); cap.className='cap'; cap.textContent= S.games? ('wins–losses · since '+new Date(S.first||Date.now()).toLocaleDateString()) : 'No games finished yet — your record starts with the first one.';
  wrap.appendChild(big); wrap.appendChild(cap); wrap.appendChild(b);
  openPanel("DJ'S PUZZLE PALACE · "+TITLE.toUpperCase(), 'My Stats', wrap, [
    {label:'Reset my stats', fn:function(){ if(confirm('Erase your '+TITLE+' record on this device?')){ S=freshStats(); save('stats',S); showStats(); } }, keep:true}
  ]);
}

/* ---------- fair deal ---------- */
function showFair(){
  var t = ''+
    '<div><b>The shuffle is random.</b> Every deal comes from your device’s own random number generator — the same one banks and browsers rely on. No two games are alike, and nothing is chosen for you.</div>'+
    '<div><b>The computer sees only its own cards.</b> It plays by the same rules you do, with the same information. It never peeks at your hand or the deck.</div>'+
    '<div><b>No rubber bands.</b> The computer does not get better hands when you are winning, or worse ones when you are losing. There is no hidden “difficulty” dial.</div>'+
    '<div><b>Nothing to sell you.</b> No coins, no timers, no energy, no pay-to-win. '+(IS_APP?'':'Ads, if any, only ever appear between games. ')+'</div>'+
    '<div><b>Every point is shown.</b> Scores are counted in the open so you can check them yourself.</div>';
  var d=box(t); d.querySelectorAll('div').forEach(function(x){ x.style.margin='10px 0'; });
  openPanel("DJ'S PUZZLE PALACE · "+TITLE.toUpperCase(), 'Fair Deal, Always', d, []);
}

/* ---------- more games ---------- */
function showMore(){
  var b=document.createElement('div'); b.className='box';
  CATALOG.forEach(function(g){
    if(g.pkg===PKG) return;
    var row=document.createElement('div'); row.className='game';
    var txt=document.createElement('div'); txt.innerHTML='<div class="n">'+esc(g.name)+'</div><div class="l">'+esc(g.line)+'</div>';
    var btn=document.createElement('button'); btn.className='djpp-btn'; btn.textContent='Get it'; btn.onclick=function(){ openPlay(g.pkg); };
    row.appendChild(txt); row.appendChild(btn); b.appendChild(row);
  });
  var acts=[];
  if(PKG) acts.push({label:'⭐ Rate '+TITLE+' on Google Play', cls:'gold', fn:function(){ rated('button'); openPlay(PKG); }});
  openPanel("DJ'S PUZZLE PALACE", 'More Big-Card Games', b, acts);
}

/* ---------- rating prompt ---------- */
function rated(how){ R.done=true; R.lastAsk=Date.now(); R.how=how; save('rate',R); }
function maybeAskRating(won){
  if(R.done) return false;
  if(!IS_APP) return false;                     // only inside the installed app
  if(!won) return false;                        // ask on a win
  if(S.wins<3 || S.games<4) return false;       // they've had a good taste
  if(Date.now()-R.lastAsk < 21*864e5) return false;
  if(R.asks>=3){ R.done=true; save('rate',R); return false; }
  R.asks++; R.lastAsk=Date.now(); save('rate',R);
  setTimeout(function(){
    var b=document.createElement('div');
    b.innerHTML='<div class="stars">★★★★★</div>'+
      '<div class="box" style="text-align:center">You’ve won <b>'+S.wins+' games</b> of '+esc(TITLE)+'. Would you take a moment to rate it? '+
      'A quick rating helps other players find a fair, honest game.</div>';
    openPanel("DJ'S PUZZLE PALACE", 'Enjoying '+TITLE+'?', b, [
      {label:'Yes, rate it ⭐', cls:'gold', fn:function(){ rated('prompt'); openPlay(PKG); }},
      {label:'Maybe later', fn:function(){}},
      {label:'No thanks, don’t ask again', fn:function(){ rated('declined'); }}
    ], null);
  }, 1400);
  return true;
}

/* ---------- shared Top 10 board (djpp-board.js) ---------- */
var boardP=null;
function loadBoard(){
  if(window.DJPPBoard) return Promise.resolve();
  if(boardP) return boardP;
  boardP=new Promise(function(res, rej){
    var s=document.createElement('script'); s.src='djpp-board.js'; s.async=true;
    s.onload=function(){ res(); }; s.onerror=function(){ boardP=null; rej(new Error('djpp-board.js failed to load')); };
    document.head.appendChild(s);
  });
  return boardP;
}
function showBoard(){
  loadBoard().then(function(){ if(window.DJPPBoard) DJPPBoard.open(); }, function(){
    openPanel("DJ'S PUZZLE PALACE · "+TITLE.toUpperCase(), 'Top 10', box('<div>The shared board could not load just now. Please check your connection and try again.</div>'), []);
  });
}
function boardJoined(){ return !!(window.DJPPBoard && DJPPBoard.joined()); }

/* ---------- public API ---------- */
var DJPP = {
  version:'1.1',
  stats:function(){ return S; },
  stat:function(key, value, mode){
    mode=mode||'max'; var cur=S.extras[key];
    if(mode==='max'){ if(cur===undefined||value>cur) S.extras[key]=value; }
    else if(mode==='min'){ if(cur===undefined||value<cur) S.extras[key]=value; }
    else if(mode==='count'){ S.extras[key]=(cur||0)+1; }
    else if(mode==='sum'){ S.extras[key]=(cur||0)+value; }
    else S.extras[key]=value;
    save('stats',S);
  },
  record:function(r){
    r=r||{}; var won=!!r.won;
    S.games++; if(won){ S.wins++; S.streak++; if(S.streak>S.bestStreak) S.bestStreak=S.streak; } else { S.losses++; S.streak=0; }
    var newBest = won && S.streak===S.bestStreak && S.streak>=2;
    var margin = (typeof r.you==='number' && typeof r.opp==='number') ? (r.you-r.opp) : 0;
    var newMargin = won && margin>S.bestMargin;
    if(newMargin) S.bestMargin=margin;
    if(r.extra){ Object.keys(r.extra).forEach(function(k){ var v=r.extra[k]; if(v===true) DJPP.stat(k,1,'count'); else if(typeof v==='number') DJPP.stat(k,v,'max'); }); }
    S.last=Date.now(); save('stats',S);
    // result line under the final score
    var host=document.getElementById('resultbox')||document.getElementById('finalline');
    var old=document.getElementById('djppResult'); if(old) old.remove();
    if(host){
      var d=document.createElement('div'); d.id='djppResult';
      var line='Your record: <span class="hi">'+S.wins+' win'+(S.wins===1?'':'s')+'</span> · '+S.losses+' loss'+(S.losses===1?'':'es');
      if(S.streak>=2) line+=' · <span class="hi">'+S.streak+' in a row'+(newBest?' — new best!':'')+'</span>';
      else if(S.bestStreak>=2) line+=' · best streak '+S.bestStreak;
      if(newMargin && margin>0 && S.games>1) line+='<br><span class="hi">Biggest win yet: +'+margin+'</span>';
      d.innerHTML=line;
      host.parentNode.insertBefore(d, host.nextSibling);
      if(boardJoined()){
        var tag=document.createElement('div'); tag.className='bd'; tag.textContent='Top 10 board: sending your result…'; d.appendChild(tag);
        DJPPBoard.record({won:won}).then(function(info){
          if(!tag.parentNode) return;
          if(info && info.total) tag.innerHTML='Top 10 board: you’re <span class="hi">#'+info.rank+' of '+info.total+'</span> this week';
          else if(DJPPBoard.joined() && DJPPBoard._state().pending.length) tag.textContent='Top 10 board: saved here — it goes up when you’re back online';
          else tag.textContent=DJPPBoard.joined()?'Top 10 board: result saved':'Top 10 board: you’re no longer on it';
        });
      } else if(S.games>=3 && S.games%4===3){
        var nudge=document.createElement('div'); nudge.className='bd link'; nudge.textContent='Compete with other players — join the Top 10 board';
        nudge.onclick=function(){ showBoard(); }; d.appendChild(nudge);
      }
    } else if(boardJoined()){
      DJPPBoard.record({won:won});
    }
    maybeAskRating(won);
    return {won:won, streak:S.streak, newBest:newBest, newMargin:newMargin};
  },
  showStats:showStats, showFair:showFair, showMore:showMore, showBoard:showBoard, openPlay:openPlay,
  reset:function(){ S=freshStats(); save('stats',S); R={done:false,lastAsk:0,asks:0}; save('rate',R); }
};
window.DJPP=DJPP;

/* ---------- menu buttons on the title overlay ---------- */
function mount(){
  var start=document.getElementById('startbtn');
  if(!start || document.getElementById('djppMenu')) return;
  var m=document.createElement('div'); m.id='djppMenu';
  [['My Stats',showStats],['Top 10',showBoard],['Fair Deal',showFair],['More Games',showMore]].forEach(function(x){
    var b=document.createElement('button'); b.className='djpp-btn'; b.textContent=x[0]; b.onclick=function(e){ e.preventDefault(); x[1](); }; m.appendChild(b);
  });
  start.parentNode.insertBefore(m, start.nextSibling);
  // the record line belongs to the game that just ended; clear it when the next one starts
  start.addEventListener('click', function(){ var d=document.getElementById('djppResult'); if(d) d.remove(); });
}
if(document.readyState==='loading') document.addEventListener('DOMContentLoaded', mount); else mount();
loadBoard().catch(function(){});
})();
