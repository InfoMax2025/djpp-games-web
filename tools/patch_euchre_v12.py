#!/usr/bin/env python3
"""Euchre v1.2 — rule toggles + partner-AI fix + partner tips.
Applies to djpp-games-web/euchre/index.html (v1.1 → v1.2). Each replacement must match exactly once.

- Settings row on the title screen (persisted in localStorage['euchre.settings']):
    Stick the dealer On/Off (was hard-coded on) · Defend alone / Canadian loner On/Off ·
    Farmer's hand On/Off · Partner tips On/Off
- Farmer's hand: first player (from the dealer's left) holding three 9s/10s may swap them for the 3 buried cards.
- Defend alone: against a lone maker one defender may go alone too; a euchre then scores 4.
- Partner AI: never trumps/overtakes a partner's winning card unless it is weak (below Q, non-trump) and an
  opponent still has to play. Every partner play can be explained in one line (Partner tips).
- G.sitOut (one seat) → G.out (list) so two players can sit out.
"""
import re, pathlib
P = pathlib.Path(__file__).parent / 'djpp-games-web' / 'euchre' / 'index.html'
s = P.read_text(encoding='utf-8')
n = [0]
def rep(old, new, count=1):
    c = s.count(old)
    assert c == count, f'expected {count} match(es), found {c}:\n{old[:160]}'
    n[0] += 1
    return s.replace(old, new)

# ---------- CSS ----------
s = rep("""  #hand .card.lifted{transform:translateY(-22px);box-shadow:0 10px 22px rgba(0,0,0,.5),0 0 0 5px var(--gold,#f6c945),0 0 24px rgba(246,201,69,.6);}
</style>""", """  #hand .card.lifted{transform:translateY(-22px);box-shadow:0 10px 22px rgba(0,0,0,.5),0 0 0 5px var(--gold,#f6c945),0 0 24px rgba(246,201,69,.6);}
  /* v1.2 options row */
  #optsRow{display:flex;flex-direction:column;gap:8px;align-items:center;margin:0 0 18px;}
  .optl{display:flex;align-items:center;gap:12px;flex-wrap:wrap;justify-content:center;font-size:15px;font-weight:800;color:#bfe6cd;}
  .optl span{min-width:132px;text-align:right;}
  .seg{display:inline-flex;border:2px solid rgba(255,255,255,.3);border-radius:30px;overflow:hidden;background:rgba(0,0,0,.25);}
  .seg button{border:none;background:transparent;color:var(--cream);font-size:15px;font-weight:800;padding:8px 16px;cursor:pointer;min-width:58px;}
  .seg button.on{background:var(--gold);color:#241800;}
  .seat.loner .callbadge{display:inline-block;}
</style>""")

# ---------- HTML ----------
s = rep("""    <div id="finalline"></div>
    <button id="startbtn">DEAL</button>""", """    <div id="finalline"></div>
    <div id="optsRow">
      <div class="optl"><span>Stick the dealer</span><div class="seg" data-key="stick"><button data-v="on">On</button><button data-v="off">Off</button></div></div>
      <div class="optl"><span>Defend alone</span><div class="seg" data-key="defend"><button data-v="on">On</button><button data-v="off">Off</button></div></div>
      <div class="optl"><span>Farmer's hand</span><div class="seg" data-key="farmer"><button data-v="on">On</button><button data-v="off">Off</button></div></div>
      <div class="optl"><span>Partner tips</span><div class="seg" data-key="tips"><button data-v="on">On</button><button data-v="off">Off</button></div></div>
    </div>
    <button id="startbtn">DEAL</button>""")
s = rep("""      <div><b>Honest:</b> deals are truly random, the computer plays by the same rules you do — no rigged hands, no timers, ads only between games.</div>""",
        """      <div><b>Options:</b> <b>Stick the dealer</b> — if everyone passes twice the dealer must call. <b>Defend alone</b> (Canadian loner) — when someone goes alone, one defender may go alone too; euchre them and it's worth <b>4</b>. <b>Farmer's hand</b> — dealt three 9s/10s? Swap them for the three buried cards. <b>Partner tips</b> — your partner says why it played each card.</div>
      <div><b>Honest:</b> deals are truly random, the computer plays by the same rules you do — no rigged hands, no timers, no ads.</div>""")
s = rep('<div id="ver">Euchre for Seniors · v1.1</div>', '<div id="ver">Euchre for Seniors · v1.2</div>')

# ---------- settings + stick-the-dealer toggle ----------
s = rep("""var STICK_DEALER=true; // dealer must call in round 2
""", """var SET={stick:'on', defend:'off', farmer:'off', tips:'on'};
try{ Object.assign(SET, JSON.parse(localStorage.getItem('euchre.settings')||'{}')); }catch(e){}
function saveSet(){ try{ localStorage.setItem('euchre.settings', JSON.stringify(SET)); }catch(e){} }
function stickDealer(){ return SET.stick!=='off'; } // dealer must call in round 2
function isOut(seat){ return !!(G && G.out && G.out.indexOf(seat)>=0); }
function activeCount(){ return 4-((G&&G.out)?G.out.length:0); }
""")
s = rep("  var mustCall = STICK_DEALER && p===G.dealer;", "  var mustCall = stickDealer() && p===G.dealer;")
s = rep("""    q.innerHTML='Name trump'+(STICK_DEALER&&G.dealer===0?' (you\\'re stuck — must call)':'')+':';""",
        """    q.innerHTML='Name trump'+(stickDealer()&&G.dealer===0?' (you\\'re stuck — must call)':'')+':';""")
s = rep("""    if(!(STICK_DEALER&&G.dealer===0)){""", """    if(!(stickDealer()&&G.dealer===0)){""")
s = rep("""      var must=STICK_DEALER&&p2===dealer;""", """      var must=stickDealer()&&p2===dealer;""")

# ---------- deal: reset per-hand state ----------
s = rep("""  G.trump=null; G.maker=-1; G.alone=-1; G.caller=-1;
  G.tricks=[0,0,0,0]; G.trickCount=0;""", """  G.trump=null; G.maker=-1; G.alone=-1; G.caller=-1; G.defAlone=-1; G.out=[]; G.farmer=-1;
  G.play=null; G.turn=-1; G.ledSuit=null; G.resolving=false; // nothing is playable until the first trick starts
  G.tricks=[0,0,0,0]; G.trickCount=0;""")
# a tap between the call and the first trick used to drop a card into last hand's stale trick array
s = rep("""  if(G.resolving) return;                 // ignore stray inputs during resolution""",
        """  if(G.resolving || !G.play) return;      // ignore stray inputs during resolution / before the first trick""")

# ---------- farmer's hand before bidding ----------
s = rep("""  toast(G.dealer===0?'You deal':SEATNAME[G.dealer]+' deals');
  G.bidRound=1; G.bidTurn=(G.dealer+1)%4; G.passes=0;
  setTimeout(bidStep,700);
}
""", """  toast(G.dealer===0?'You deal':SEATNAME[G.dealer]+' deals');
  G.bidRound=1; G.bidTurn=(G.dealer+1)%4; G.passes=0;
  if(SET.farmer==='on') farmerCheck(function(){ setTimeout(bidStep,700); });
  else setTimeout(bidStep,700);
}
/* ---- Farmer's hand: the first player (from the dealer's left) holding three 9s/10s may swap them for the three buried cards ---- */
function farmerCards(hand){ var idx=[]; for(var i=0;i<hand.length;i++) if(hand[i].r==='9'||hand[i].r==='10') idx.push(i); return idx; }
function farmerSwap(p){
  var h=G.hands[p], idx=farmerCards(h);
  idx.sort(function(a,b){ return RANK_VAL[h[a].r]-RANK_VAL[h[b].r]; }); idx=idx.slice(0,3).sort(function(a,b){ return b-a; });
  var outCards=[]; idx.forEach(function(i){ outCards.push(h.splice(i,1)[0]); });
  for(var k=0;k<3;k++) h.push(G.kitty[k]);
  G.kitty=outCards; G.farmer=p;
  if(p===0) sortHand(0);
  renderAll();
  bigToast((p===0?'You':SEATNAME[p])+' swapped three low cards — Farmer\\'s hand');
}
function farmerCheck(done){
  var order=[(G.dealer+1)%4,(G.dealer+2)%4,(G.dealer+3)%4,G.dealer];
  for(var i=0;i<order.length;i++){
    var p=order[i];
    if(farmerCards(G.hands[p]).length<3) continue;
    if(p===0){
      var pr=el('prompt'); pr.style.display='block'; el('alone').style.display='none';
      var q=el('promptQ'), b=el('promptBtns'); b.innerHTML='';
      q.innerHTML='<span class="up">Farmer\\'s hand!</span> You hold three 9s/10s — swap them for the three buried cards?';
      addBtn(b,'Swap them','gold',function(){ hidePrompt(); farmerSwap(0); setTimeout(done,1200); });
      addBtn(b,'Keep my hand','ghost',function(){ hidePrompt(); done(); });
      return;
    }
    farmerSwap(p); setTimeout(done,1200); return;
  }
  done();
}
""")

# ---------- calling trump: sit-outs as a list + defend alone ----------
s = rep("""  toast(who+' called '+SUIT_NAME[suit]+al);
  sortHand(0);
  renderAll();
  // start play from left of dealer; if alone, partner of maker sits out
  G.leader=(G.dealer+1)%4;
  G.sitOut = alone ? (p+2)%4 : -1;
  if(G.sitOut===G.leader) G.leader=(G.leader+1)%4;
  setTimeout(startTrick,900);
}
""", """  toast(who+' called '+SUIT_NAME[suit]+al);
  sortHand(0);
  G.out = alone ? [(p+2)%4] : [];
  renderAll();
  var begin=function(){
    // start play from left of dealer; sitting-out seats are skipped
    G.leader=(G.dealer+1)%4;
    while(isOut(G.leader)) G.leader=(G.leader+1)%4;
    setTimeout(startTrick,900);
  };
  if(alone && SET.defend==='on') setTimeout(function(){ offerDefend(p, begin); }, 900);
  else begin();
}
/* ---- Defend alone (Canadian loner): against a lone maker, one defender may go alone too ---- */
function offerDefend(maker, done){
  var order=[(G.dealer+1)%4,(G.dealer+2)%4,(G.dealer+3)%4,G.dealer].filter(function(x){ return TEAM[x]!==TEAM[maker]; });
  var i=0;
  function next(){
    if(i>=order.length){ done(); return; }
    var d=order[i++];
    if(d===0){
      var pr=el('prompt'); pr.style.display='block'; el('alone').style.display='none';
      var q=el('promptQ'), b=el('promptBtns'); b.innerHTML='';
      q.innerHTML=SEATNAME[maker]+' is going <span class="up">ALONE</span>. Defend alone? Your partner sits out — euchre them and it\\'s worth <span class="up">4 points</span>.';
      addBtn(b,'Defend alone','gold',function(){ hidePrompt(); defendAlone(0); done(); });
      addBtn(b,'Play normally','ghost',function(){ hidePrompt(); next(); });
      return;
    }
    if(handStrength(G.hands[d], G.trump, false)>=23){ defendAlone(d); setTimeout(done,900); return; }
    next();
  }
  next();
}
function defendAlone(d){
  G.defAlone=d; G.out.push((d+2)%4);
  el('seat'+SEAT_TAG[d]).classList.add('loner'); el('seat'+SEAT_TAG[d]).querySelector('.callbadge').textContent='DEFENDING ALONE';
  renderAll();
  bigToast((d===0?'You defend':SEATNAME[d]+' defends')+' ALONE — a euchre is worth 4');
}
""")
s = rep("""  G.turn=G.leader;
  if(G.turn===G.sitOut) G.turn=(G.turn+1)%4;
  playStep();""", """  G.turn=G.leader;
  while(isOut(G.turn)) G.turn=(G.turn+1)%4;
  playStep();""")
s = rep("""  var activeCount = G.sitOut>=0?3:4;
  if(G.play.length>=activeCount){""", """  if(G.play.length>=activeCount()){""")
s = rep("""function nextSeat(p){
  var n=(p+1)%4;
  if(n===G.sitOut) n=(n+1)%4;
  return n;
}""", """function nextSeat(p){
  var n=(p+1)%4;
  while(isOut(n)) n=(n+1)%4;
  return n;
}""")
s = rep("""  var activeCount = G.sitOut>=0?3:4;
  if(!G.play || G.play.length<activeCount){ G.resolving=false; return; } // safety: not a full trick""",
        """  if(!G.play || G.play.length<activeCount()){ G.resolving=false; return; } // safety: not a full trick""")
s = rep("""  backs('backsN', G.hands[2].length - (G.sitOut===2?0:0));
  backs('backsW', G.hands[1].length);
  backs('backsE', G.hands[3].length);
  if(G.sitOut===2) el('backsN').innerHTML='';
  if(G.sitOut===1) el('backsW').innerHTML='';
  if(G.sitOut===3) el('backsE').innerHTML='';""", """  backs('backsN', isOut(2)?0:G.hands[2].length);
  backs('backsW', isOut(1)?0:G.hands[1].length);
  backs('backsE', isOut(3)?0:G.hands[3].length);""")

# ---------- scoring: euchre of a lone maker by a lone defender = 4 ----------
s = rep("""  } else {
    pts[1-makerTeam]=2;
    msg=(makerTeam===0?'You got EUCHRED!':'You EUCHRED them!')+' — 2 points to '+(1-makerTeam===0?'you':'opponents')+'.';
  }""", """  } else {
    var ep=(G.defAlone>=0)?4:2;
    pts[1-makerTeam]=ep;
    msg=(makerTeam===0?'You got EUCHRED!':'You EUCHRED them!')+' — '+ep+' points to '+(1-makerTeam===0?'you':'opponents')+(ep===4?' (defended alone!)':'')+'.';
    if(window.DJPP && G.defAlone===0 && makerTeam===1){ try{ DJPP.stat('loneDefences',1,'count'); }catch(e){} }
  }""")
s = rep("""  clearCaller();
  bigToast(msg);""", """  clearCaller(); ['S','W','N','E'].forEach(function(tag){ var sEl=el('seat'+tag); sEl.classList.remove('loner'); sEl.querySelector('.callbadge').textContent='CALLED IT'; });
  bigToast(msg);""")

# ---------- partner AI: never overtake your partner's winner (unless it is weak and an opponent still plays) + reasons ----------
s = rep("""function aiPlay(p){
  var h=G.hands[p], t=G.trump, led=G.ledSuit;
  var legal=legalMoves(p);
  // current winning card in trick
  var win=currentTrickWinner();
  var partnerWinning = win.seat>=0 && TEAM[win.seat]===TEAM[p];
  // map legal to cards with power
  var opts=legal.map(function(i){ return {i:i, c:h[i], pw:cardPower(h[i],t,led)}; });
  if(led==null){
    // leading: lead a strong trump early if we're maker, else lead off-ace, else lowest
    opts.sort(function(a,b){return b.pw-a.pw;});
    // prefer leading an off-suit ace (power 100+14) or right bower; avoid wasting
    var ace=opts.find(function(o){return o.c.r==='A' && effSuit(o.c,t)!==t;});
    if(TEAM[p]===TEAM[G.maker] && opts[0].pw>=900) return opts[0].i; // lead bower to draw trump
    if(ace) return ace.i;
    // lead middling
    return opts[Math.floor(opts.length/2)].i;
  }
  // following
  var winners=opts.filter(function(o){return o.pw>win.power;});
  if(partnerWinning && win.power>=500){
    // partner has a strong trump/led winner — throw lowest
    opts.sort(function(a,b){return a.pw-b.pw;});
    return opts[0].i;
  }
  if(winners.length){
    // win as cheaply as possible
    winners.sort(function(a,b){return a.pw-b.pw;});
    return winners[0].i;
  }
  // can't win — throw lowest
  opts.sort(function(a,b){return a.pw-b.pw;});
  return opts[0].i;
}""", """function aiPlay(p){
  var h=G.hands[p], t=G.trump, led=G.ledSuit;
  var legal=legalMoves(p);
  // current winning card in trick
  var win=currentTrickWinner();
  var partnerWinning = win.seat>=0 && TEAM[win.seat]===TEAM[p];
  var lastToPlay = G.play.length>=activeCount()-1;
  var youMsg = !win.card ? '' : ((win.seat===0)?'your '+cardName(win.card):'my partner\\'s '+cardName(win.card));
  // map legal to cards with power
  var opts=legal.map(function(i){ return {i:i, c:h[i], pw:cardPower(h[i],t,led)}; });
  G.why='';
  if(led==null){
    // leading: lead a strong trump early if we're maker, else lead off-ace, else lowest
    opts.sort(function(a,b){return b.pw-a.pw;});
    // prefer leading an off-suit ace (power 100+14) or right bower; avoid wasting
    var ace=opts.find(function(o){return o.c.r==='A' && effSuit(o.c,t)!==t;});
    if(TEAM[p]===TEAM[G.maker] && opts[0].pw>=900){ G.why='leading the '+(opts[0].pw>=1000?'right':'left')+' bower to pull their trump'; return opts[0].i; } // lead bower to draw trump
    if(ace){ G.why='leading an off-suit ace — it usually wins'; return ace.i; }
    // lead middling
    G.why='nothing sure to win, so leading a middling card'; return opts[Math.floor(opts.length/2)].i;
  }
  // following
  var winners=opts.filter(function(o){return o.pw>win.power;});
  opts.sort(function(a,b){return a.pw-b.pw;});
  if(partnerWinning){
    // never trump or overtake a partner who already has the trick — unless the winner is a weak
    // off-suit card (below Q) and an opponent still has to play behind us
    var weak = win.power<100+RANK_VAL['Q'];
    if(win.power>=500 || lastToPlay || !weak || !winners.length){
      G.why=youMsg+' is winning — throwing my lowest';
      return opts[0].i;
    }
    winners.sort(function(a,b){return a.pw-b.pw;});
    G.why=youMsg+' might not hold against the next player — covering it'; return winners[0].i;
  }
  if(winners.length){
    // win as cheaply as possible
    winners.sort(function(a,b){return a.pw-b.pw;});
    var w=winners[0]; G.why=(effSuit(w.c,t)===t && led!==t)?'trumping in to take the trick':'taking the trick as cheaply as I can';
    return w.i;
  }
  // can't win — throw lowest
  G.why='can\\'t beat '+(win.seat>=0?cardName(win.card):'it')+' — throwing my lowest';
  return opts[0].i;
}
function cardName(c){ return c.r+SUIT_SYM[c.s]; }""")
# partner tip toast after the partner's play
s = rep("""  setTimeout(function(){
    var idx=aiPlay(p);
    doPlay(p, idx);
  }, 620);""", """  setTimeout(function(){
    if(G.turn!==p || G.resolving || !G.play || !G.hands[p].length) return;   // stale timer (seat already played / trick over)
    var idx=aiPlay(p);
    doPlay(p, idx);
    if(p===2 && SET.tips==='on' && G.why && !isOut(0)) toast('Partner: '+G.why);
  }, 620);""")
# one scheduler chain per trick: a play that lands inside the 140 ms hand-off window must not start a second chain
s = rep("""    G.turn=nextSeat(p);
    setTimeout(playStep,140);""", """    G.turn=nextSeat(p);
    var tok=(G.stepTok=(G.stepTok||0)+1);
    setTimeout(function(){ if(G.stepTok===tok) playStep(); },140);""")

# ---------- settings wiring + test hook ----------
s = rep("""// ---- test hook ----
window.__EU={
  get G(){return G;}, newGame:newGame, endGame:endGame,
  state:function(){return G;},""", """// ---- options row ----
function applySet(){ document.querySelectorAll('#optsRow .seg').forEach(function(seg){ var k=seg.getAttribute('data-key'); seg.querySelectorAll('button').forEach(function(b){ b.classList.toggle('on', b.getAttribute('data-v')===SET[k]); }); }); }
document.querySelectorAll('#optsRow .seg button').forEach(function(b){ b.onclick=function(){ SET[b.parentNode.getAttribute('data-key')]=b.getAttribute('data-v'); saveSet(); applySet(); }; });
applySet();

// ---- test hook ----
window.__EU={
  get G(){return G;}, newGame:newGame, endGame:endGame, SET:SET, applySet:applySet, startHand:startHand, commitCall:commitCall,
  aiPlay:aiPlay, doPlay:doPlay, farmerCards:farmerCards, farmerCheck:farmerCheck, offerDefend:offerDefend, isOut:isOut, activeCount:activeCount, scoreHand:scoreHand,
  bidStep:bidStep, humanBid:humanBid, advanceBid:advanceBid, playStep:playStep, legalMoves:legalMoves, hidePrompt:hidePrompt,
  state:function(){return G;},""")
s = rep("""  extras:[ {key:'marches',label:'Marches (all 5 tricks)'}, {key:'lonersMade',label:'Loners made'},
           {key:'euchresGiven',label:'Times you euchred them'}, {key:'euchresTaken',label:'Times you got euchred'} ] };""",
        """  extras:[ {key:'marches',label:'Marches (all 5 tricks)'}, {key:'lonersMade',label:'Loners made'},
           {key:'euchresGiven',label:'Times you euchred them'}, {key:'euchresTaken',label:'Times you got euchred'},
           {key:'loneDefences',label:'Loners you euchred alone'} ] };""")

P.write_text(s, encoding='utf-8')
print('patched', n[0], 'replacements;', len(s), 'chars')
