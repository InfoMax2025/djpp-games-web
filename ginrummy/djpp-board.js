/* DJ's Puzzle Palace — shared Top 10 board v1.0
   One public leaderboard per game that every player can see and compete on, kept on Google Firebase (Cloud Firestore).
   Players join with a nickname; only the nickname and game results (wins, streaks, best score) ever leave the device,
   tied to an anonymous player id. Firebase itself is downloaded lazily, the first time the board is opened or a
   result has to be sent — a player who never joins never loads it.

   Configured by window.DJPP_CONFIG (the same object djpp-kit.js reads):
     game    'cribbage' | 'euchre' | 'ginrummy' | 'pinochle' | 'ct3d'      board id, [a-z0-9]{2,20}
     title   'Cribbage'
     board   { metric:'wins'|'score',     what the board ranks — card games count wins, Control Tower 3D its best shift score
               unit:'wins'|'pts',
               theme:{bg,card,border,text,accent,accent2,font,scale} }
   API (window.DJPPBoard):
     open()                 show the Top 10 panel
     record({won, score})   call once when a game ends; ignored until the player joins. Resolves to {rank,total} or null.
     joined()  name()       whether this device has joined, and as whom
     flush()                push results that could not be sent earlier (offline)
*/
(function(){
'use strict';
var C = window.DJPP_CONFIG || {};
var B = C.board || {};
var GAME = String(C.game || '').toLowerCase().replace(/[^a-z0-9]/g, '').slice(0, 20);
var TITLE = C.title || 'this game';
var METRIC = B.metric === 'score' ? 'score' : 'wins';
var WKMETRIC = METRIC === 'score' ? 'wkScore' : 'wkWins';
var UNIT = B.unit || (METRIC === 'score' ? 'pts' : 'wins');
var TH = B.theme || {};
var SCALE = TH.scale || 1;

/* Firebase project "DJPP Games". These values are the public web-client configuration: they identify the project to
   Google's servers and are meant to ship in client code. What players may read or write is decided by the Firestore
   security rules on the server, never by this file. */
var FB_CFG = { apiKey: 'AIzaSyA4F16mIWUIej0pJqaqw96rkEQxunsVUSY', authDomain: 'djpp-games.firebaseapp.com',
               projectId: 'djpp-games', appId: '1:261623083114:web:3b15451efe9d2f4a3d5a13' };
var FB_URL = 'https://www.gstatic.com/firebasejs/12.18.0/';
var MIN_WIN_GAP = 21000;   // the rules refuse a second win within 20 s of the previous write

/* ---------- local state ---------- */
var LS = 'djpp.board.' + GAME;
function load(){ try { return JSON.parse(localStorage.getItem(LS) || 'null') || {}; } catch(e){ return {}; } }
function save(){ try { localStorage.setItem(LS, JSON.stringify(ST)); } catch(e){} }
var ST = load();                 // {joined, uid, name, me:{wins,streak,best,games,score,wk,wkWins,wkBest,wkStreak,wkScore}, pending:[{won,score,at,tries}]}
if(!ST.pending) ST.pending = [];

/* ---------- helpers ---------- */
function weekId(d){   // ISO week, computed in UTC so every player rolls to the new week at the same moment
  var x = new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate()));
  var day = x.getUTCDay() || 7; x.setUTCDate(x.getUTCDate() + 4 - day);
  var y = x.getUTCFullYear(); var w = Math.ceil(((x - Date.UTC(y, 0, 1)) / 864e5 + 1) / 7);
  return y + '-W' + (w < 10 ? '0' : '') + w;
}
function roll(d, wk){   // a copy of the player document with the weekly counters reset when the week has changed
  var o = {}; Object.keys(d).forEach(function(k){ if(k !== 't') o[k] = d[k]; });
  if(o.wk !== wk){ o.wk = wk; o.wkWins = 0; o.wkBest = 0; o.wkStreak = 0; o.wkScore = 0; }
  return o;
}
function cleanName(s){ return String(s || '').replace(/\s+/g, ' ').trim(); }
var BAD = /(fuck|shit|cunt|nigg|fagg|bitch|dick|cock|pussy|asshole|whore|slut|retard|nazi|hitler|rape|penis|vagina|kike|spic|chink)/i;
function nameError(n){
  if(n.length < 2) return 'Pick a name of at least 2 letters or numbers.';
  if(n.length > 16) return 'Keep it to 16 characters.';
  if(!/^[A-Za-z0-9][A-Za-z0-9 _.'\-]*$/.test(n)) return 'Letters, numbers, spaces, dots, dashes, apostrophes and underscores only.';
  if(BAD.test(n)) return 'Please pick a friendlier name.';
  return '';
}
function fmtNum(n){ n = Number(n) || 0; return n.toLocaleString ? n.toLocaleString('en-US') : String(n); }
function fmtVal(v){ return METRIC === 'wins' ? (fmtNum(v) + (v === 1 ? ' win' : ' wins')) : (fmtNum(v) + ' ' + UNIT); }
function wait(ms){ return new Promise(function(r){ setTimeout(r, ms); }); }
function el(tag, cls, text){ var e = document.createElement(tag); if(cls) e.className = cls; if(text !== undefined) e.textContent = text; return e; }

/* ---------- Firebase (lazy) ---------- */
var libP = null;
function dynImport(u){ return (new Function('u', 'return import(u)'))(u); }   // parsed lazily so old browsers still run the rest
function lib(){
  if(libP) return libP;
  libP = Promise.all([dynImport(FB_URL + 'firebase-app.js'), dynImport(FB_URL + 'firebase-auth.js'), dynImport(FB_URL + 'firebase-firestore-lite.js')])
    .then(function(m){
      var app = m[0].getApps().length ? m[0].getApp() : m[0].initializeApp(FB_CFG);
      var auth; try { auth = m[1].initializeAuth(app, { persistence: [m[1].indexedDBLocalPersistence, m[1].browserLocalPersistence] }); }
      catch(e){ auth = m[1].getAuth(app); }
      return { A: m[1], F: m[2], auth: auth, db: m[2].getFirestore(app) };
    });
  libP.catch(function(){ libP = null; });   // a failed download (offline) may be retried later
  return libP;
}
function user(L){   // the anonymous Firebase user for this device, created on first use
  return L.auth.authStateReady().then(function(){
    if(L.auth.currentUser) return L.auth.currentUser;
    return L.A.signInAnonymously(L.auth).then(function(c){ return c.user; });
  });
}
function players(L){ return L.F.collection(L.db, 'boards', GAME, 'players'); }
function pdoc(L, uid){ return L.F.doc(L.db, 'boards', GAME, 'players', uid); }
function ndoc(L, lower){ return L.F.doc(L.db, 'boards', GAME, 'names', lower); }
function errCode(e){ return (e && (e.code || e.message)) ? String(e.code || e.message) : String(e); }

/* ---------- board reads ---------- */
function top(L, tab){
  var F = L.F, wk = weekId(new Date()), q;
  if(tab === 'week') q = F.query(players(L), F.where('wk', '==', wk), F.orderBy(WKMETRIC, 'desc'), F.limit(10));
  else q = F.query(players(L), F.orderBy(METRIC, 'desc'), F.limit(10));
  return F.getDocs(q).then(function(s){
    var rows = [];
    s.forEach(function(d){ var x = d.data() || {}; rows.push({ uid: d.id, name: String(x.name || ''), v: Number(tab === 'week' ? x[WKMETRIC] : x[METRIC]) || 0 }); });
    return rows.filter(function(r){ return r.v > 0; });
  });
}
function rankInfo(L, tab){   // {rank,total,mine} for this device, or null when not joined
  if(!ST.joined || !ST.me) return Promise.resolve(null);
  var F = L.F, wk = weekId(new Date()), q1, q2, mine;
  if(tab === 'week'){
    mine = Number(roll(ST.me, wk)[WKMETRIC]) || 0;
    q1 = F.query(players(L), F.where('wk', '==', wk), F.where(WKMETRIC, '>', mine), F.orderBy(WKMETRIC, 'desc'));
    q2 = F.query(players(L), F.where('wk', '==', wk));
  } else {
    mine = Number(ST.me[METRIC]) || 0;
    q1 = F.query(players(L), F.where(METRIC, '>', mine));
    q2 = players(L);
  }
  return Promise.all([F.getCount(q1), F.getCount(q2)]).then(function(r){
    return { rank: r[0].data().count + 1, total: r[1].data().count, mine: mine, tab: tab };
  });
}

/* ---------- join / rename / leave ---------- */
function join(rawName){
  var name = cleanName(rawName), err = nameError(name);
  if(err) return Promise.reject({ code: 'bad-name', message: err });
  var lower = name.toLowerCase();
  return lib().then(function(L){ return user(L).then(function(u){
    var F = L.F, uid = u.uid, pRef = pdoc(L, uid), nRef = ndoc(L, lower);
    return F.runTransaction(L.db, function(tx){
      return tx.get(nRef).then(function(ns){
        if(ns.exists() && ns.data().uid !== uid) throw { code: 'taken', message: 'Someone already has that name — try another.' };
        return tx.get(pRef).then(function(ps){
          var wk = weekId(new Date()), d, oldLower = '';
          if(ps.exists()){ d = roll(ps.data(), wk); oldLower = String(d.name || '').toLowerCase(); d.name = name; }
          else d = { name: name, wins: 0, streak: 0, best: 0, games: 0, score: 0, wk: wk, wkWins: 0, wkBest: 0, wkStreak: 0, wkScore: 0 };
          // a rename frees the old nickname — read it first: every read must come before the first write
          var oldP = (oldLower && oldLower !== lower) ? tx.get(ndoc(L, oldLower)) : Promise.resolve(null);
          return oldP.then(function(os){
            if(os && os.exists() && os.data().uid === uid) tx.delete(ndoc(L, oldLower));
            if(!ns.exists()) tx.set(nRef, { uid: uid });
            var w = {}; Object.keys(d).forEach(function(k){ w[k] = d[k]; }); w.t = F.serverTimestamp();
            tx.set(pRef, w);
            return d;
          });
        });
      });
    }).then(function(d){ ST.joined = true; ST.uid = uid; ST.name = name; ST.me = d; save(); return d; });
  }); });
}
function leave(){
  return lib().then(function(L){ return user(L).then(function(u){
    var F = L.F, lower = String(ST.name || '').toLowerCase();
    return F.deleteDoc(pdoc(L, u.uid)).then(function(){
      return lower ? F.deleteDoc(ndoc(L, lower)).catch(function(){}) : null;
    });
  }); }).then(function(){ ST = { pending: [] }; save(); });
}

/* ---------- results ---------- */
function writeResult(L, u, it){
  var F = L.F, pRef = pdoc(L, u.uid);
  return F.runTransaction(L.db, function(tx){
    return tx.get(pRef).then(function(ps){
      if(!ps.exists()) throw { code: 'not-found' };
      var d = roll(ps.data(), weekId(new Date()));
      d.games = (d.games | 0) + 1;
      if(it.won){
        d.wins = (d.wins | 0) + 1; d.streak = (d.streak | 0) + 1; if(d.streak > d.best) d.best = d.streak;
        d.wkWins = (d.wkWins | 0) + 1; d.wkStreak = (d.wkStreak | 0) + 1; if(d.wkStreak > d.wkBest) d.wkBest = d.wkStreak;
      } else { d.streak = 0; d.wkStreak = 0; }
      if(it.score !== null && it.score !== undefined){ if(it.score > d.score) d.score = it.score; if(it.score > d.wkScore) d.wkScore = it.score; }
      var w = {}; Object.keys(d).forEach(function(k){ w[k] = d[k]; }); w.t = F.serverTimestamp();
      tx.set(pRef, w);
      return d;
    });
  }).then(function(d){ ST.me = d; save(); return d; });
}
var flushing = null;
function flush(){
  if(flushing) return flushing;
  if(!ST.joined || !ST.pending.length) return Promise.resolve(null);
  flushing = lib().then(function(L){ return user(L).then(function(u){
    if(ST.uid && ST.uid !== u.uid){ ST.joined = false; ST.pending = []; save(); return null; }   // a new anonymous id: the old entry is no longer ours
    return step(L, u);
  }); }).catch(function(){ return null; }).then(function(v){ flushing = null; return v; });
  return flushing;
}
function step(L, u){
  if(!ST.pending.length) return rankInfo(L, 'week').catch(function(){ return null; });
  var it = ST.pending[0];
  return writeResult(L, u, it).then(function(){
    ST.pending.shift(); save();
    if(!ST.pending.length) return rankInfo(L, 'week').catch(function(){ return null; });
    return wait(MIN_WIN_GAP).then(function(){ return step(L, u); });
  }, function(e){
    var code = errCode(e);
    if(/not-found/.test(code)){ ST.joined = false; ST.pending = []; save(); return null; }      // entry removed (left on another device, or reset)
    if(/permission-denied|PERMISSION_DENIED/.test(code)){                                            // most likely a win less than 20 s after the last write: wait and retry
      it.tries = (it.tries | 0) + 1;
      if(it.tries > 3){ ST.pending.shift(); save(); return step(L, u); }
      save(); return wait(MIN_WIN_GAP).then(function(){ return step(L, u); });
    }
    throw e;   // offline or a server hiccup: keep it for later
  });
}
function record(r){
  if(!ST.joined) return Promise.resolve(null);
  var score = (r && typeof r.score === 'number' && isFinite(r.score)) ? Math.max(0, Math.min(10000000, Math.floor(r.score))) : null;
  ST.pending.push({ won: !!(r && r.won), score: score, at: Date.now(), tries: 0 }); save();
  return flush();
}
window.addEventListener('online', function(){ flush(); });

/* ---------- panel ---------- */
var css = ''+
'#djppBoard{position:fixed;inset:0;z-index:5000;display:flex;flex-direction:column;align-items:center;justify-content:flex-start;padding:22px 14px 30px;overflow-y:auto;text-align:center;'+
'  color:'+(TH.text||'#faf6ea')+';font-family:'+(TH.font||'"Segoe UI",Roboto,Helvetica,Arial,sans-serif')+';background:'+(TH.bg||'radial-gradient(ellipse at 50% 30%,rgba(8,52,27,.985),rgba(3,20,10,.995))')+';}'+
'#djppBoard *{box-sizing:border-box;}'+
'#djppBoard .bd-kick{font-size:'+(13*SCALE)+'px;letter-spacing:3px;color:'+(TH.accent2||TH.accent||'#f6c945')+';font-weight:800;margin-bottom:6px;}'+
'#djppBoard h2{font-size:'+(clampPx(28,40))+';margin:0 0 12px;font-weight:900;color:'+(TH.title||'#fff')+';}'+
'#djppBoard .bd-tabs{display:flex;gap:8px;margin-bottom:12px;}'+
'#djppBoard .bd-tab{cursor:pointer;border:2px solid '+(TH.border||'rgba(255,255,255,.25)')+';border-radius:12px;background:transparent;color:inherit;font:800 '+(17*SCALE)+'px/1 inherit;padding:'+(11*SCALE)+'px '+(18*SCALE)+'px;font-family:inherit;}'+
'#djppBoard .bd-tab.on{background:'+(TH.accent||'#f6c945')+';color:'+(TH.onAccent||'#241800')+';border-color:transparent;}'+
'#djppBoard .bd-box{background:'+(TH.card||'rgba(255,255,255,.07)')+';border:1px solid '+(TH.border||'rgba(255,255,255,.14)')+';border-radius:16px;padding:'+(10*SCALE)+'px '+(18*SCALE)+'px;margin:0 0 12px;text-align:left;max-width:560px;width:100%;font-size:'+(clampPx(17,20))+';line-height:1.45;}'+
'#djppBoard .bd-row{display:flex;align-items:center;gap:10px;padding:'+(9*SCALE)+'px 0;border-bottom:1px solid '+(TH.border||'rgba(255,255,255,.1)')+';font-size:'+(20*SCALE)+'px;}'+
'#djppBoard .bd-row:last-child{border-bottom:none;}'+
'#djppBoard .bd-row .r{width:2.2em;flex:none;font-weight:900;color:'+(TH.accent2||TH.accent||'#f6c945')+';}'+
'#djppBoard .bd-row .n{flex:1;font-weight:800;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}'+
'#djppBoard .bd-row .v{flex:none;font-weight:900;color:'+(TH.accent||'#f6c945')+';white-space:nowrap;}'+
'#djppBoard .bd-row.me{background:'+(TH.meBg||'rgba(246,201,69,.14)')+';border-radius:10px;padding-left:8px;padding-right:8px;margin:0 -8px;}'+
'#djppBoard .bd-row.me .n:after{content:" (you)";font-weight:600;opacity:.75;}'+
'#djppBoard .bd-note{text-align:center;padding:'+(14*SCALE)+'px 4px;opacity:.85;font-weight:600;}'+
'#djppBoard .bd-me{font-size:'+(clampPx(18,22))+';font-weight:800;margin:2px 0 12px;color:'+(TH.accent||'#f6c945')+';}'+
'#djppBoard .bd-acts{display:flex;flex-direction:column;gap:10px;width:100%;max-width:420px;margin-top:4px;}'+
'#djppBoard .bd-btn{cursor:pointer;border:2px solid '+(TH.border||'rgba(255,255,255,.32)')+';border-radius:14px;background:'+(TH.btn||'rgba(255,255,255,.10)')+';color:inherit;font:800 '+(19*SCALE)+'px/1 inherit;font-family:inherit;padding:'+(15*SCALE)+'px 20px;letter-spacing:.3px;width:100%;}'+
'#djppBoard .bd-btn:active{transform:scale(.97);}'+
'#djppBoard .bd-btn.gold{background:'+(TH.accentBtn||'linear-gradient(180deg,#ffe08a,#e5ad2e)')+';color:'+(TH.onAccent||'#241800')+';border-color:transparent;}'+
'#djppBoard .bd-btn.quiet{font-size:'+(15*SCALE)+'px;padding:'+(11*SCALE)+'px 16px;opacity:.85;}'+
'#djppBoard .bd-btn[disabled]{opacity:.5;cursor:default;}'+
'#djppBoard input.bd-in{width:100%;font:800 '+(22*SCALE)+'px/1.2 inherit;font-family:inherit;padding:'+(12*SCALE)+'px 14px;border-radius:12px;border:2px solid '+(TH.accent||'#f6c945')+';background:rgba(0,0,0,.25);color:inherit;text-align:center;outline:none;margin:6px 0 8px;}'+
'#djppBoard .bd-err{color:#ff8a75;font-weight:700;min-height:1.4em;font-size:'+(16*SCALE)+'px;}'+
'#djppBoard .bd-foot{margin-top:14px;font-size:'+(13*SCALE)+'px;color:'+(TH.muted||'rgba(255,255,255,.5)')+';max-width:520px;line-height:1.45;}'+
'#djppBoard .bd-spin{display:inline-block;width:22px;height:22px;border:3px solid rgba(255,255,255,.25);border-top-color:'+(TH.accent||'#f6c945')+';border-radius:50%;animation:bdspin .8s linear infinite;vertical-align:middle;margin-right:8px;}'+
'@keyframes bdspin{to{transform:rotate(360deg);}}'+
'@media (max-height:560px){#djppBoard{padding-top:10px;} #djppBoard h2{margin-bottom:6px;}}';
function clampPx(a, b){ return 'clamp(' + Math.round(a * SCALE) + 'px,' + (Math.round(a * SCALE) / 5) + 'vw,' + Math.round(b * SCALE) + 'px)'; }
var styled = false;
function style(){ if(styled) return; styled = true; var s = document.createElement('style'); s.textContent = css; document.head.appendChild(s); }

var panel = null, tab = 'week', cache = {};
function close(){ if(panel && panel.parentNode) panel.parentNode.removeChild(panel); panel = null; }
function open(){
  style(); close(); cache = {};
  panel = el('div'); panel.id = 'djppBoard';
  panel.appendChild(el('div', 'bd-kick', "DJ'S PUZZLE PALACE · " + TITLE.toUpperCase()));
  panel.appendChild(el('h2', null, 'Top 10'));
  var tabs = el('div', 'bd-tabs');
  [['week', 'This Week'], ['all', 'All Time']].forEach(function(t){
    var b = el('button', 'bd-tab' + (tab === t[0] ? ' on' : ''), t[1]); b.type = 'button'; b.setAttribute('data-tab', t[0]);
    b.onclick = function(){ tab = t[0]; tabs.querySelectorAll('.bd-tab').forEach(function(x){ x.classList.toggle('on', x.getAttribute('data-tab') === tab); }); render(); };
    tabs.appendChild(b);
  });
  panel.appendChild(tabs);
  var box = el('div', 'bd-box'); box.id = 'bdList'; panel.appendChild(box);
  var me = el('div', 'bd-me'); me.id = 'bdMe'; panel.appendChild(me);
  var acts = el('div', 'bd-acts'); acts.id = 'bdActs'; panel.appendChild(acts);
  var foot = el('div', 'bd-foot', METRIC === 'wins'
    ? 'Everyone playing ' + TITLE + ' sees this board. Only your nickname and results are shared, and your wins count from the day you join. The week starts Monday.'
    : 'Everyone playing ' + TITLE + ' sees this board. Only your nickname and best scores are shared. The week starts Monday.');
  panel.appendChild(foot);
  document.body.appendChild(panel); panel.scrollTop = 0;
  render();
}
function render(){
  if(!panel) return;
  var box = panel.querySelector('#bdList'), me = panel.querySelector('#bdMe'), acts = panel.querySelector('#bdActs');
  acts.innerHTML = '';
  if(ST.joined){
    acts.appendChild(btn('Change my name', 'quiet', function(){ joinForm(true); }));
    acts.appendChild(btn('Leave the board', 'quiet', function(){ leaveConfirm(); }));
  } else {
    acts.appendChild(btn('Join the board', 'gold', function(){ joinForm(false); }));
  }
  acts.appendChild(btn('Back', '', close));
  me.textContent = '';
  box.innerHTML = ''; var ld = el('div', 'bd-note'); ld.innerHTML = '<span class="bd-spin"></span>Loading the board…'; box.appendChild(ld);
  var myTab = tab;
  var p = cache[myTab] || (cache[myTab] = lib().then(function(L){ return Promise.all([top(L, myTab), rankInfo(L, myTab).catch(function(){ return null; })]); }));
  p.then(function(r){
    if(!panel || tab !== myTab) return;
    var rows = r[0], info = r[1];
    box.innerHTML = '';
    if(!rows.length){ box.appendChild(el('div', 'bd-note', myTab === 'week' ? 'Nobody has ' + (METRIC === 'wins' ? 'won' : 'scored') + ' yet this week — be the first!' : 'The board is empty — be the first on it!')); }
    rows.forEach(function(x, i){
      var row = el('div', 'bd-row' + (ST.joined && x.uid === ST.uid ? ' me' : ''));
      row.appendChild(el('span', 'r', (i + 1) + '.')); row.appendChild(el('span', 'n', x.name)); row.appendChild(el('span', 'v', fmtVal(x.v)));
      box.appendChild(row);
    });
    if(ST.joined){
      if(info) me.textContent = (info.mine > 0 ? ('You’re #' + fmtNum(info.rank) + ' of ' + fmtNum(info.total) + (myTab === 'week' ? ' this week' : ' all time') + ' · ' + fmtVal(info.mine))
                                            : ('No ' + (METRIC === 'wins' ? 'wins' : 'score') + (myTab === 'week' ? ' yet this week' : ' yet') + ' — your next game counts!'));
      else me.textContent = 'Playing as ' + ST.name;
    } else me.textContent = 'Join with a nickname to compete';
    if(ST.pending.length) flush().then(function(){ cache = {}; if(panel && tab === myTab) render(); });
  }, function(e){
    if(!panel || tab !== myTab) return;
    delete cache[myTab];
    box.innerHTML = ''; box.appendChild(el('div', 'bd-note', navigator.onLine === false ? 'You’re offline — the board needs a connection.' : 'Couldn’t reach the board just now. Please try again in a moment.'));
    me.textContent = '';
    var again = btn('Try again', '', function(){ render(); }); acts.insertBefore(again, acts.firstChild);
    try { console.warn('DJPP board:', errCode(e)); } catch(x){}
  });
}
function btn(label, cls, fn){ var b = el('button', 'bd-btn ' + (cls || ''), label); b.type = 'button'; b.onclick = fn; return b; }
function joinForm(rename){
  var box = panel.querySelector('#bdList'), me = panel.querySelector('#bdMe'), acts = panel.querySelector('#bdActs');
  box.innerHTML = ''; me.textContent = ''; acts.innerHTML = '';
  var lab = el('div', 'bd-note', rename ? 'Pick a new name for the board:' : 'Pick a nickname for the board (2–16 letters or numbers):'); lab.style.paddingBottom = '2px';
  var inp = document.createElement('input'); inp.className = 'bd-in'; inp.type = 'text'; inp.maxLength = 16; inp.autocomplete = 'off'; inp.autocapitalize = 'words'; inp.spellcheck = false;
  inp.value = ST.name || ''; inp.placeholder = 'Your nickname';
  var err = el('div', 'bd-err', '');
  box.appendChild(lab); box.appendChild(inp); box.appendChild(err);
  var go = btn(rename ? 'Save my name' : 'Join', 'gold', submit); var cancel = btn('Cancel', '', function(){ render(); });
  acts.appendChild(go); acts.appendChild(cancel);
  inp.onkeydown = function(ev){ if(ev.key === 'Enter'){ ev.preventDefault(); submit(); } };
  setTimeout(function(){ try { inp.focus(); inp.select(); } catch(x){} }, 50);
  function submit(){
    var n = cleanName(inp.value), e = nameError(n); if(e){ err.textContent = e; return; }
    go.disabled = true; cancel.disabled = true; err.textContent = ''; go.textContent = 'Joining…';
    join(n).then(function(){ cache = {}; render(); }, function(ex){
      go.disabled = false; cancel.disabled = false; go.textContent = rename ? 'Save my name' : 'Join';
      var code = errCode(ex);
      if(/taken/.test(code)){ err.textContent = 'Someone already has that name — try another.'; var m = n.match(/^(.*?)(\d*)$/); var next = (m[1] + ((parseInt(m[2] || '1', 10) + 1))).slice(0, 16); inp.value = next; inp.select(); }
      else if(/bad-name/.test(code)) err.textContent = ex.message || 'That name won’t work — try another.';
      else if(/permission-denied|PERMISSION_DENIED/.test(code)) err.textContent = 'The board didn’t accept that name — try another.';
      else err.textContent = navigator.onLine === false ? 'You’re offline — try again when you have a connection.' : 'Couldn’t reach the board. Please try again.';
      try { console.warn('DJPP board join:', code); } catch(x){}
    });
  }
}
function leaveConfirm(){
  var box = panel.querySelector('#bdList'), me = panel.querySelector('#bdMe'), acts = panel.querySelector('#bdActs');
  box.innerHTML = ''; me.textContent = ''; acts.innerHTML = '';
  box.appendChild(el('div', 'bd-note', 'Leave the board? Your name and results come off it for everyone. Your own stats on this device stay as they are.'));
  var err = el('div', 'bd-err', ''); box.appendChild(err);
  var go = btn('Yes, leave the board', 'gold', function(){
    go.disabled = true; go.textContent = 'Leaving…';
    leave().then(function(){ cache = {}; render(); }, function(ex){ go.disabled = false; go.textContent = 'Yes, leave the board'; err.textContent = 'Couldn’t reach the board. Please try again.'; try { console.warn('DJPP board leave:', errCode(ex)); } catch(x){} });
  });
  acts.appendChild(go); acts.appendChild(btn('Stay on the board', '', function(){ render(); }));
}

/* ---------- public API ---------- */
window.DJPPBoard = {
  version: '1.0', game: GAME, metric: METRIC,
  open: open, close: close, record: record, flush: flush,
  joined: function(){ return !!ST.joined; }, name: function(){ return ST.joined ? ST.name : ''; },
  me: function(){ return ST.me || null; }, weekId: weekId,
  _state: function(){ return ST; }, _lib: lib
};
if(ST.joined && ST.pending.length) setTimeout(flush, 3000);   // results that could not be sent last time
})();
