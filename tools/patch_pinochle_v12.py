#!/usr/bin/env python3
"""Pinochle v1.2 — house-rule toggles.
Applies to djpp-games-web/pinochle/index.html (v1.1 → v1.2). Each replacement must match exactly once.

Options row on the title screen (persisted in localStorage['pin.settings']):
  Scoring 150 / 1500  — classic scoring multiplies every meld and counter by 10 (game to 1500, minimum bid 200)
  Stuck dealer On/Off — Off: if all four pass the hand is thrown in and redealt
  Pass 4 cards On/Off — after trump is named, the bid winner's partner passes 4 cards over and gets 4 back
  Bid help On/Off     — the "your hand is worth about N" estimate and the suggested button/suit
"""
import pathlib
P = pathlib.Path(__file__).parent / 'djpp-games-web' / 'pinochle' / 'index.html'
s = P.read_text(encoding='utf-8')
n = [0]
def rep(old, new, count=1):
    c = s.count(old)
    assert c == count, f'expected {count} match(es), found {c}:\n{old[:200]}'
    n[0] += 1
    return s.replace(old, new)

# ---------- CSS ----------
s = rep("""  #hand .card.lifted{transform:translateY(-22px);box-shadow:0 10px 22px rgba(0,0,0,.5),0 0 0 5px var(--gold,#f6c945),0 0 24px rgba(246,201,69,.6);}
</style>""", """  #hand .card.lifted{transform:translateY(-22px);box-shadow:0 10px 22px rgba(0,0,0,.5),0 0 0 5px var(--gold,#f6c945),0 0 24px rgba(246,201,69,.6);}
  /* v1.2 options row + card passing */
  #optsRow{display:flex;flex-direction:column;gap:8px;align-items:center;margin:0 0 18px;}
  .optl{display:flex;align-items:center;gap:12px;flex-wrap:wrap;justify-content:center;font-size:15px;font-weight:800;color:#f0dfd2;}
  .optl span{min-width:120px;text-align:right;}
  .seg{display:inline-flex;border:2px solid rgba(224,181,107,.45);border-radius:30px;overflow:hidden;background:rgba(0,0,0,.25);}
  .seg button{border:none;background:transparent;color:#f4e9de;font-size:15px;font-weight:800;padding:8px 16px;cursor:pointer;min-width:58px;}
  .seg button.on{background:linear-gradient(180deg,#f6dda2,#c9964e);color:#2a1600;}
  #passBtn{display:none;font-size:18px;padding:10px 26px;margin:0 auto 6px;border-radius:13px;}
  #passBtn:disabled{opacity:.45;}
</style>""")

# ---------- HTML ----------
s = rep("""<span class="sub">for seniors · first team to 150 · every meld explained</span>""",
        """<span class="sub" id="boardSub">for seniors · first team to 150 · every meld explained</span>""")
s = rep("""    <div id="hint"></div>
    <div id="hand"></div>""", """    <div id="hint"></div>
    <button class="btn" id="passBtn">PASS 4 CARDS</button>
    <div id="hand"></div>""")
s = rep("""    <div id="resultbox"></div>
    <button class="btn" id="startbtn">DEAL</button>""", """    <div id="resultbox"></div>
    <div id="optsRow">
      <div class="optl"><span>Scoring</span><div class="seg" data-key="scoring"><button data-v="150">to 150</button><button data-v="1500">to 1500</button></div></div>
      <div class="optl"><span>Stuck dealer</span><div class="seg" data-key="stuck"><button data-v="on">On</button><button data-v="off">Off</button></div></div>
      <div class="optl"><span>Pass 4 cards</span><div class="seg" data-key="pass"><button data-v="on">On</button><button data-v="off">Off</button></div></div>
      <div class="optl"><span>Bid help</span><div class="seg" data-key="help"><button data-v="on">On</button><button data-v="off">Off</button></div></div>
    </div>
    <button class="btn" id="startbtn">DEAL</button>""")
s = rep("""      <div><b>Teams:</b> you and your partner against West &amp; East. First team to <b>150 points</b> wins.</div>
      <div><b>The auction:</b> bid for the right to name trump (minimum 20). Your team must reach the bid with <b>meld + counters</b> — or lose the bid.</div>""",
        """      <div><b>Teams:</b> you and your partner against West &amp; East. First team to <b>150 points</b> wins (<b>1500</b> with classic scoring, where every meld and counter is worth ten times as much).</div>
      <div><b>The auction:</b> bid for the right to name trump (minimum 20). Your team must reach the bid with <b>meld + counters</b> — or lose the bid.</div>
      <div><b>Options:</b> <b>Stuck dealer</b> — if three players pass, the dealer must bid the minimum (turn it off to throw the hand in instead). <b>Pass 4 cards</b> — the bidder's partner passes four cards over and gets four back before meld. <b>Bid help</b> — shows what your hand is worth and marks the suggested bid and trump.</div>""")
s = rep('<div id="ver">Pinochle Seniors · v1.1</div>', '<div id="ver">Pinochle Seniors · v1.2</div>')

# ---------- settings + scale helpers ----------
s = rep("""var GAME_TARGET=150, MIN_BID=20;
""", """var SET={scoring:'150', stuck:'on', pass:'off', help:'on'};
try{ Object.assign(SET, JSON.parse(localStorage.getItem('pin.settings')||'{}')); }catch(e){}
function saveSet(){ try{ localStorage.setItem('pin.settings', JSON.stringify(SET)); }catch(e){} }
function SF(){ return SET.scoring==='1500'?10:1; }          // score factor: classic scoring is everything x10
function minBid(){ return 20*SF(); }
function target(){ return 150*SF(); }
function stuckDealer(){ return SET.stuck!=='off'; }
""")
# meld values scale with the score factor
s = rep("""  function add(pts,text){ total+=pts; lines.push({pts:pts,text:text}); }
  var runs=Math.min(m[trump][Av],m[trump][Tv],m[trump][Kv],m[trump][Qv],m[trump][Jv]);""",
        """  function add(pts,text){ pts*=SF(); total+=pts; lines.push({pts:pts,text:text}); }
  var runs=Math.min(m[trump][Av],m[trump][Tv],m[trump][Kv],m[trump][Qv],m[trump][Jv]);""")
s = rep("""function counterPoints(cards,gotLast){ return cards.filter(isCounter).length+(gotLast?1:0); }""",
        """function counterPoints(cards,gotLast){ return (cards.filter(isCounter).length+(gotLast?1:0))*SF(); }""")
s = rep("""    var ms=meldScore(hand,s).total;
    var m=counts(hand);
    var strength=ms+m[s].reduce(function(a,b){return a+b;},0)*1.4+m[s][Av]*2+m[s][Tv]*1.2;""",
        """    var ms=meldScore(hand,s).total/SF();
    var m=counts(hand);
    var strength=ms+m[s].reduce(function(a,b){return a+b;},0)*1.4+m[s][Av]*2+m[s][Tv]*1.2;""")
s = rep("""  var est=meld+7+trumpLen*1.1+aces*1.4;
  return {trump:s, meld:meld, maxBid:Math.floor(est)};""",
        """  var est=meld+(7+trumpLen*1.1+aces*1.4)*SF();
  return {trump:s, meld:meld, maxBid:Math.floor(est/SF())*SF()};""")
s = rep("""  var need=Math.max(MIN_BID,highBid+1);
  if(e.maxBid>=need&&e.meld>=4) return need;""", """  var need=Math.max(minBid(),highBid+SF());
  if(e.maxBid>=need&&e.meld>=4*SF()) return need;""")
s = rep("""  G.active=[true,true,true,true]; G.highBid=MIN_BID-1; G.highP=-1; G.anyBid=false;""",
        """  G.active=[true,true,true,true]; G.highBid=minBid()-SF(); G.highP=-1; G.anyBid=false; G.sel=[]; G.passStage=null; hidePassBtn();""")
s = rep("""  if(guard>60){ finishAuction(G.dealer, MIN_BID); return; }
  // auction ends when 3 have passed and someone bid
  if(G.anyBid && passesCount()>=3){ finishAuction(G.highP, G.highBid); return; }
  if(!G.anyBid && passesCount()===3){ // dealer stuck
    finishAuction(G.dealer, MIN_BID, true); return;
  }""", """  if(guard>60){ finishAuction(G.dealer, minBid()); return; }
  // auction ends when 3 have passed and someone bid
  if(G.anyBid && passesCount()>=3){ finishAuction(G.highP, G.highBid); return; }
  if(!G.anyBid && passesCount()===4){ // everyone passed (stuck dealer off): throw the hand in
    pop('Everyone passed — new deal', function(){ deal(); }); return;
  }
  if(!G.anyBid && passesCount()===3 && stuckDealer()){ // dealer stuck
    finishAuction(G.dealer, minBid(), true); return;
  }""")
s = rep("""    var b=aiBidTurn(G.hands[p], G.anyBid?G.highBid:MIN_BID-1);""", """    var b=aiBidTurn(G.hands[p], G.anyBid?G.highBid:minBid()-SF());""")
s = rep("""  var e=handEstimate(G.hands[0]);
  var need=Math.max(MIN_BID, G.highBid+1);
  el('bpSub').innerHTML=(G.anyBid?('High bid is <b>'+G.highBid+'</b> by '+SEAT_NAMES[G.highP]+'.'):'No bids yet — minimum is <b>'+MIN_BID+'</b>.')+
    '<br>Your hand is worth about <b>'+e.maxBid+'</b> (meld '+e.meld+', best suit '+SUIT_SYM[e.trump]+').';
  var wrap=el('bpBtns'); wrap.innerHTML='';
  function btn(label, cls, fn){ var b=document.createElement('button'); b.className='bigbtn'+(cls?' '+cls:''); b.innerHTML=label; b.onclick=fn; wrap.appendChild(b); return b; }
  var canBid = need<=50;
  var sugBid = e.maxBid>=need;
  if(canBid){
    btn('BID '+need, sugBid?'sug':'', function(){ youBid(need); });
    if(need+4<=50) btn('BID '+(need+4), '', function(){ youBid(need+4); });
  }
  btn('PASS', sugBid?'':'sug', function(){ youPass(); });""", """  var e=handEstimate(G.hands[0]), help=SET.help!=='off';
  var need=Math.max(minBid(), G.highBid+SF());
  el('bpSub').innerHTML=(G.anyBid?('High bid is <b>'+G.highBid+'</b> by '+SEAT_NAMES[G.highP]+'.'):'No bids yet — minimum is <b>'+minBid()+'</b>.')+
    (help?('<br>Your hand is worth about <b>'+e.maxBid+'</b> (meld '+e.meld+', best suit '+SUIT_SYM[e.trump]+').'):'');
  el('bpNote').innerHTML='The winning bidder names trump. Your team must then reach the bid with <b>meld + counters</b> — every ace, ten and king you capture is a counter'+(SF()>1?' worth 10':'')+', and the last trick is worth '+(SF()>1?'10':'one')+' more.';
  var wrap=el('bpBtns'); wrap.innerHTML='';
  function btn(label, cls, fn){ var b=document.createElement('button'); b.className='bigbtn'+(cls?' '+cls:''); b.innerHTML=label; b.onclick=fn; wrap.appendChild(b); return b; }
  var canBid = need<=50*SF();
  var sugBid = help && e.maxBid>=need;
  if(canBid){
    btn('BID '+need, sugBid?'sug':'', function(){ youBid(need); });
    if(need+4*SF()<=50*SF()) btn('BID '+(need+4*SF()), '', function(){ youBid(need+4*SF()); });
  }
  btn('PASS', (help && !sugBid)?'sug':'', function(){ youPass(); });""")
s = rep("""    b.className='suitbtn '+SUIT_COLOR[s]+(s===sug?' sug':'');""", """    b.className='suitbtn '+SUIT_COLOR[s]+((s===sug && SET.help!=='off')?' sug':'');""")
# passing phase hooks in after trump is announced
s = rep("""  pop('Trump is <b style="font-size:56px">'+SUIT_SYM[G.trump]+'</b>', function(){ showMeld(); });
}""", """  pop('Trump is <b style="font-size:56px">'+SUIT_SYM[G.trump]+'</b>', function(){ if(SET.pass==='on') startPass(); else showMeld(); });
}
/* ---- pass 4 cards: the bid winner's partner passes 4 over, the bid winner passes 4 back ---- */
function passValue(c, trump){ return (c.s===trump)?20+c.v:((c.v===Av)?10:((c.v===Kv||c.v===Qv)?3+c.v*0.1:c.v)); }
function aiPassToDeclarer(hand, trump){ return hand.slice().sort(function(a,b){ return passValue(b,trump)-passValue(a,trump); }).slice(0,4); }
function aiPassBack(hand, trump){ /* give back the four cards that cost the least meld and the least play value */
  var h=hand.slice(), out=[];
  for(var k=0;k<4;k++){
    var base=meldScore(h,trump).total, best=-1, bestCost=1e9;
    for(var i=0;i<h.length;i++){
      var rest=h.slice(0,i).concat(h.slice(i+1));
      var cost=(base-meldScore(rest,trump).total)*5+passValue(h[i],trump);
      if(cost<bestCost){ bestCost=cost; best=i; }
    }
    out.push(h.splice(best,1)[0]);
  }
  return out;
}
function moveCards(from,to,cards){ cards.forEach(function(c){ var k=G.hands[from].indexOf(c); if(k>=0){ G.hands[from].splice(k,1); G.hands[to].push(c); } }); }
function showPassBtn(label){ var b=el('passBtn'); b.textContent=label; b.style.display='inline-block'; b.disabled=true; b.onclick=confirmPass; }
function hidePassBtn(){ var b=el('passBtn'); if(b) b.style.display='none'; }
function startPass(){
  G.phase='pass'; G.sel=[]; hint('');
  var d=G.declarer, pt=(d+2)%4;
  if(d!==0 && pt!==0){ // the other team passes among themselves
    moveCards(pt,d,aiPassToDeclarer(G.hands[pt],G.trump));
    moveCards(d,pt,aiPassBack(G.hands[d],G.trump));
    renderAll(); pop(SEAT_NAMES[pt]+' and '+SEAT_NAMES[d]+' pass 4 cards', showMeld); return;
  }
  if(pt===0){ // your partner won the bid: you pass 4 over first
    G.passStage='give'; hint('Partner won the bid — pick 4 cards to pass over. Trump and aces help most.'); renderHand(); showPassBtn('PASS 4 TO PARTNER');
  } else {    // you won the bid: partner passes first, then you pass 4 back
    moveCards(2,0,aiPassToDeclarer(G.hands[2],G.trump)); G.hands[0]=sortHand(G.hands[0]); G.dealAnim=true; renderAll();
    pop('Partner passes you 4 cards', function(){ G.passStage='back'; hint('Pick 4 cards to pass back to your partner.'); renderHand(); showPassBtn('PASS 4 BACK'); });
  }
}
function confirmPass(){
  if(G.phase!=='pass' || G.sel.length!==4) return;
  var cards=G.sel.map(function(i){ return G.hands[0][i]; }); G.sel=[]; hidePassBtn(); hint('');
  moveCards(0,2,cards);
  if(G.passStage==='give'){
    moveCards(2,0,aiPassBack(G.hands[2],G.trump)); G.hands[0]=sortHand(G.hands[0]); G.dealAnim=true; renderAll();
    pop('Partner passes 4 cards back', showMeld);
  } else { G.hands[0]=sortHand(G.hands[0]); renderAll(); pop('Passed back to partner', showMeld); }
}""")
# card taps during the passing phase
s = rep("""function onCardTap(idx){
  if(G.phase!=='playYou') return;""", """function onCardTap(idx){
  if(G.phase==='pass'){
    var k=G.sel.indexOf(idx);
    if(k>=0) G.sel.splice(k,1); else if(G.sel.length<4) G.sel.push(idx);
    renderHand(); el('passBtn').disabled=(G.sel.length!==4);
    hint((G.passStage==='give'?'Pick 4 cards to pass over':'Pick 4 cards to pass back')+' ('+G.sel.length+'/4)'+(G.sel.length===4?' — tap the button below.':'.'));
    return;
  }
  if(G.phase!=='playYou') return;""")
s = rep("""      var k=c.v+':'+c.s;
      if(myTurn){
        if(legalLeft[k]>0){ c._legal=true; legalLeft[k]--; if(G.lift===idx){ elc.classList.add('lifted'); elc.style.zIndex=90; } }
        else { c._legal=false; elc.classList.add('dim'); }
      } else c._legal=false;""", """      var k=c.v+':'+c.s;
      if(myTurn){
        if(legalLeft[k]>0){ c._legal=true; legalLeft[k]--; if(G.lift===idx){ elc.classList.add('lifted'); elc.style.zIndex=90; } }
        else { c._legal=false; elc.classList.add('dim'); }
      } else if(G.phase==='pass'){ c._legal=true; if(G.sel&&G.sel.indexOf(idx)>=0){ elc.classList.add('lifted'); elc.style.zIndex=90; } }
      else c._legal=false;""")
# hand sizing: a 16-card hand (after receiving 4) must still fit the screen; the pass button takes vertical room
s = rep("""  if(hintEl.style.display!=='none'&&hintEl.textContent) nonH+=hintEl.offsetHeight+9;
  var budgetH=innerHeight-10-trickBottom-nonH+40;""", """  if(hintEl.style.display!=='none'&&hintEl.textContent) nonH+=hintEl.offsetHeight+9;
  var pb=el('passBtn'); if(pb.style.display!=='none') nonH+=pb.offsetHeight+8;
  var budgetH=innerHeight-10-trickBottom-nonH+40;""")
s = rep("""    var strip=Math.max(38, Math.min(58, Math.floor((availW-CW)/Math.max(m-1,1))));
    if(strip>CW*0.8) strip=Math.floor(CW*0.8);""", """    var strip=Math.max(30, Math.min(58, Math.floor((availW-CW)/Math.max(m-1,1))));
    if(strip>CW*0.8) strip=Math.floor(CW*0.8);
    if(CW+strip*(m-1)>availW) CW=Math.max(48, availW-strip*(m-1));""")
# meld panel / scoring texts scale
s = rep("""      el('mpTotalLine').textContent='Now the play — 25 counters on the table.';""",
        """      el('mpTotalLine').textContent='Now the play — '+(25*SF())+' counters on the table.';""")
s = rep("""      if(window.DJPP){ try{ DJPP.stat('bestMeld', G.meldT[0], 'max');""", """      if(window.DJPP){ try{ DJPP.stat('bestMeld', G.meldT[0]/SF(), 'max');""")
s = rep("""      if(G.scores[0]>=GAME_TARGET||G.scores[1]>=GAME_TARGET){
        ended=true;
        if(G.scores[0]>=GAME_TARGET&&G.scores[1]>=GAME_TARGET) winTeam=G.bidTeam; // bidder goes out
        else winTeam=G.scores[0]>=GAME_TARGET?0:1;""", """      if(G.scores[0]>=target()||G.scores[1]>=target()){
        ended=true;
        if(G.scores[0]>=target()&&G.scores[1]>=target()) winTeam=G.bidTeam; // bidder goes out
        else winTeam=G.scores[0]>=target()?0:1;""")
s = rep("""    ((G.scores[0]>=GAME_TARGET&&G.scores[1]>=GAME_TARGET)?'<br>Both teams crossed 150 — the bidding team goes out first.':'');""",
        """    ((G.scores[0]>=target()&&G.scores[1]>=target())?'<br>Both teams crossed '+target()+' — the bidding team goes out first.':'')+
    '<br><span style="opacity:.75">Scoring to '+target()+(SET.pass==='on'?' · passing 4 cards':'')+(SET.stuck==='off'?' · no stuck dealer':'')+'</span>';""")
s = rep("""function updBoard(){
  el('scoreUs').textContent=G?G.scores[0]:0;""", """function updBoard(){
  el('boardSub').textContent='for seniors · first team to '+target()+' · every meld explained';
  el('scoreUs').textContent=G?G.scores[0]:0;""")

# ---------- options wiring + test hook ----------
s = rep("""el('startbtn').onclick=function(){ newGame(); };

/* test hook */
window.__PIN={ get G(){return G;}, newGame:newGame, deal:deal, meldScore:meldScore, endGame:endGame,
  legalPlays:legalPlays, trickWinner:trickWinner, handEstimate:handEstimate,
  tap:onCardTap, youBid:youBid, youPass:youPass,""", """el('startbtn').onclick=function(){ newGame(); };
function applySet(){ document.querySelectorAll('#optsRow .seg').forEach(function(seg){ var k=seg.getAttribute('data-key'); seg.querySelectorAll('button').forEach(function(b){ b.classList.toggle('on', b.getAttribute('data-v')===SET[k]); }); }); updBoard(); }
document.querySelectorAll('#optsRow .seg button').forEach(function(b){ b.onclick=function(){ SET[b.parentNode.getAttribute('data-key')]=b.getAttribute('data-v'); saveSet(); applySet(); }; });
applySet();

/* test hook */
window.__PIN={ get G(){return G;}, newGame:newGame, deal:deal, meldScore:meldScore, endGame:endGame, SET:SET, applySet:applySet, SF:SF, minBid:minBid, target:target,
  legalPlays:legalPlays, trickWinner:trickWinner, handEstimate:handEstimate, aiBidTurn:aiBidTurn, counterPoints:counterPoints, scoreHand:scoreHand,
  startPass:startPass, confirmPass:confirmPass, aiPassToDeclarer:aiPassToDeclarer, aiPassBack:aiPassBack, announceTrump:announceTrump, showBidPanel:showBidPanel,
  auctionTurn:auctionTurn, finishAuction:finishAuction, showMeld:showMeld,
  tap:onCardTap, youBid:youBid, youPass:youPass,""")
s = rep("""    hand:G&&G.hands?G.hands[0].length:0, trick:G?G.trick.length:0,""", """    hand:G&&G.hands?G.hands[0].length:0, trick:G?G.trick.length:0, sel:G&&G.sel?G.sel.slice():[], passBtn:vis('passBtn'), hint:el('hint').textContent,""")

assert 'GAME_TARGET' not in s.replace("var GAME_TARGET", ""), 'GAME_TARGET still referenced: ' + str([l for l in s.split('\n') if 'GAME_TARGET' in l][:3])
assert 'MIN_BID' not in s, 'MIN_BID still referenced: ' + str([l for l in s.split('\n') if 'MIN_BID' in l][:3])
P.write_text(s, encoding='utf-8')
print('patched', n[0], 'replacements;', len(s), 'chars')
