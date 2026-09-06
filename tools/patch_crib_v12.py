#!/usr/bin/env python3
"""Cribbage v1.2: HINT (discard + pegging), Coach feedback on discards, TAKE BACK during pegging,
Relaxed / Standard / Sharp opponent. Patches cribbage/index.html in place."""
import pathlib
P = pathlib.Path('/home/claude/games/djpp-games-web/cribbage/index.html')
s = P.read_text(encoding='utf-8')
assert 'crib.settings' not in s, 'already patched'
def rep(old, new, count=1):
    global s
    assert s.count(old) == count, f'expected {count}: {old[:70]!r} (got {s.count(old)})'
    s = s.replace(old, new)

# ---------- CSS ----------
rep("  #ver{position:absolute;right:10px;bottom:8px;z-index:6;color:rgba(255,255,255,.4);font-size:11px;pointer-events:none;}",
"""  #ver{position:absolute;right:10px;bottom:8px;z-index:6;color:rgba(255,255,255,.4);font-size:11px;pointer-events:none;}
  /* v1.2: settings, coach line, hint marks */
  #optsRow{display:flex;flex-direction:column;gap:10px;align-items:center;margin-bottom:18px;}
  .optl{display:flex;align-items:center;gap:12px;flex-wrap:wrap;justify-content:center;font-size:16px;font-weight:800;color:#c9ecd6;}
  .seg{display:inline-flex;border:2px solid rgba(255,255,255,.3);border-radius:30px;overflow:hidden;background:rgba(0,0,0,.25);}
  .seg button{border:none;background:transparent;color:var(--cream);font-size:16px;font-weight:800;padding:10px 16px;cursor:pointer;font-family:inherit;}
  .seg button.on{background:linear-gradient(180deg,#ffe08a,#e5ad2e);color:#241800;}
  #coach{display:none;width:fit-content;max-width:92vw;margin:0 auto 8px;font-size:16px;font-weight:700;color:#dff3ff;text-align:center;
    background:rgba(5,28,15,.86);border:1px solid rgba(127,217,255,.45);border-radius:14px;padding:8px 16px;box-shadow:0 4px 14px rgba(0,0,0,.4);pointer-events:none;line-height:1.35;}
  #coach b{color:#7fd9ff;}
  #hand .card.hintmark{box-shadow:0 6px 16px rgba(0,0,0,.45), 0 0 0 5px #7fd9ff, 0 0 22px rgba(127,217,255,.7);}
  .btn.sm{font-size:17px;padding:12px 18px;border-radius:14px;}
  #actions{flex-wrap:wrap;}""")
# ---------- HTML ----------
rep('    <div id="dwline"></div>\n    <div id="hand"></div>', '    <div id="dwline"></div>\n    <div id="coach"></div>\n    <div id="hand"></div>')
rep('    <button id="startbtn">DEAL</button>\n    <div class="foot">A DJ\'s Puzzle Palace game</div>',
"""    <div id="optsRow">
      <div class="optl"><span>Opponent</span><div class="seg" data-key="diff"><button data-v="relaxed">Relaxed</button><button data-v="standard">Standard</button><button data-v="sharp">Sharp</button></div></div>
      <div class="optl"><span>Coach tips</span><div class="seg" data-key="coach"><button data-v="on">On</button><button data-v="off">Off</button></div></div>
    </div>
    <button id="startbtn">DEAL</button>
    <div class="foot">A DJ's Puzzle Palace game</div>""")
rep('<div id="ver">Cribbage Seniors · v1.1</div>', '<div id="ver">Cribbage Seniors · v1.2</div>')
rep("      <div><b>Honest:</b> truly random shuffles. The opponent only ever sees its own cards — and every count is shown so you can check it.</div>",
    "      <div><b>Honest:</b> truly random shuffles. The opponent only ever sees its own cards — and every count is shown so you can check it.</div>\n      <div><b>Learning?</b> Tap <b>HINT</b> any time for the best discard or play. <b>Relaxed</b> opponents slip up and let you take a card back.</div>")

# ---------- JS: settings + AI levels ----------
rep("var GAME_TARGET=121;",
"""var GAME_TARGET=121;
var SET={diff:'standard',coach:'on'};try{Object.assign(SET,JSON.parse(localStorage.getItem('crib.settings')||'{}'));}catch(e){}
function saveSet(){try{localStorage.setItem('crib.settings',JSON.stringify(SET));}catch(e){}}
function takebacksAllowed(){return SET.diff==='relaxed'?99:(SET.diff==='sharp'?0:3);}""")
rep("function aiDiscard(hand6, isDealer, deckUnseen){\n  var bestIdx=null, bestVal=-1e9;\n  for(var a=0;a<6;a++) for(var b=a+1;b<6;b++){",
"""function aiDiscard(hand6, isDealer, deckUnseen, level){
  var opts=discardOptions(hand6,isDealer,deckUnseen,level||'standard');
  if((level||'standard')==='relaxed'){ var top=opts.slice(0,4); return top[Math.floor(Math.random()*top.length)].idx; }
  return opts[0].idx;
}
/* every keep/toss split ranked by expected hand value (+/- what the toss gives the crib) */
function discardOptions(hand6, isDealer, deckUnseen, level){
  var out=[]; var cw=(level==='sharp')?(isDealer?1.0:-1.2):(isDealer?0.6:-0.8);
  for(var a=0;a<6;a++) for(var b=a+1;b<6;b++){""")
rep("""    ev+=(isDealer?0.6:-0.8)*crib;
    if(ev>bestVal){ bestVal=ev; bestIdx=[a,b]; }
  }
  return bestIdx;
}""",
"""    if(level==='sharp'){ if(toss[0].r===5&&toss[1].r===5) crib+=1.5; if(Math.abs(toss[0].r-toss[1].r)===2) crib+=0.3; if(toss[0].s===toss[1].s) crib+=0.2; }
    out.push({idx:[a,b], keep:keep, toss:toss, handEv:ev, ev:ev+cw*crib});
  }
  out.sort(function(x,y){ return y.ev-x.ev; });
  return out;
}""")
rep("function aiPegPlay(handLeft, pile, count){\n  var legal=handLeft.filter(function(c){ return count+val(c)<=31; });\n  if(!legal.length) return null;\n  var best=null, bestScore=-1e9;",
"""function aiPegPlay(handLeft, pile, count, level, unseen){
  var legal=handLeft.filter(function(c){ return count+val(c)<=31; });
  if(!legal.length) return null;
  if(level==='relaxed' && Math.random()<0.35) return legal[Math.floor(Math.random()*legal.length)];
  var best=null, bestScore=-1e9;""")
rep("""    if(pile.length===0 && c.r<=4) s+=6;
    s+=val(c)*0.1;
    if(s>bestScore){ bestScore=s; best=c; }
  }
  return best;
}""",
"""    if(pile.length===0 && c.r<=4) s+=6;
    s+=val(c)*0.1;
    if(level==='sharp' && unseen && unseen.length){ /* what can the opponent peg back on this count? */
      var np=pile.concat([c]), risk=0, n=0;
      for(var u=0;u<unseen.length;u++){ if(nc+val(unseen[u])>31) continue; risk+=pegScore(np.concat([unseen[u]])).pts; n++; }
      if(n) s-=(risk/n)*45;
      var mine=handLeft.filter(function(x){ return x!==c && nc+val(x)<=31; }).length; if(!mine && handLeft.length>1) s-=8; /* don't strand yourself */
    }
    if(s>bestScore){ bestScore=s; best=c; }
  }
  return best;
}
function unseenFor(who){ /* cards a player has never seen: the deck minus their dealt six, the starter and the pile */
  var seen={}; (who===0?G.handDealt:G.oppDealt).forEach(function(c){ seen[cardKey(c)]=1; });
  if(G.starter) seen[cardKey(G.starter)]=1; (G.pile||[]).forEach(function(c){ seen[cardKey(c)]=1; }); (G.played||[]).forEach(function(c){ seen[cardKey(c)]=1; });
  return makeDeck().filter(function(c){ return !seen[cardKey(c)]; });
}
/* ---- hints & coach (always computed at Sharp level) ---- */
function coach(msg){ var c=el('coach'); c.innerHTML=msg||''; c.style.display=msg?'block':'none'; }
function showHint(){
  if(!G) return;
  var again=(G.phase==='discard' && G.hintIdx) || (G.phase==='pegYou' && G.hintCard);   // re-tapping HINT on the same decision is free
  if(!again) G.hints=(G.hints||0)+1;
  if(G.phase==='discard'){
    var opts=discardOptions(G.hand, G.dealer===0, unseenFor(0), 'sharp'); var b=opts[0];
    G.hintIdx=b.idx.slice(); G.sel=b.idx.slice();
    coach('<b>Hint:</b> keep '+b.keep.map(cardStr).join(' ')+' — send <b>'+b.toss.map(cardStr).join(' ')+'</b> to the crib'+
      ' <span style="opacity:.75">(averages '+b.handEv.toFixed(1)+' pts'+(G.dealer===0?', and helps your crib':', gives their crib little')+')</span>');
    renderHand(); renderActions();
  } else if(G.phase==='pegYou'){
    var c=aiPegPlay(G.left[0], G.pile, G.count, 'sharp', unseenFor(0)); if(!c) return;
    var ps=pegScore(G.pile.concat([c])); var why=ps.pts>0?ps.lines.join(', ').toLowerCase():'safest count ('+(G.count+val(c))+')';
    G.hintCard=cardKey(c); coach('<b>Hint:</b> play <b>'+cardStr(c)+'</b> — '+why); renderHand();
  }
}
function coachDiscard(chosen){ /* after SEND TO CRIB: how did the keep compare? */
  if(SET.coach!=='on') return;
  var opts=discardOptions(G.handDealt, G.dealer===0, unseenFor(0), 'sharp'); var best=opts[0];
  var mine=null; for(var i=0;i<opts.length;i++){ var t=opts[i].toss; if((cardKey(t[0])===cardKey(chosen[0])&&cardKey(t[1])===cardKey(chosen[1]))||(cardKey(t[0])===cardKey(chosen[1])&&cardKey(t[1])===cardKey(chosen[0]))){ mine=opts[i]; break; } }
  if(!mine) return;
  if(mine===best) coach('<b>Coach:</b> that was the best possible keep — averages '+mine.handEv.toFixed(1)+' pts.');
  else if(best.ev-mine.ev<0.6) coach('<b>Coach:</b> good keep ('+mine.handEv.toFixed(1)+' avg). Sending '+best.toss.map(cardStr).join(' ')+' was a hair better.');
  else coach('<b>Coach:</b> your keep averages '+mine.handEv.toFixed(1)+' pts; keeping '+best.keep.map(cardStr).join(' ')+' (toss '+best.toss.map(cardStr).join(' ')+') would average '+best.handEv.toFixed(1)+'.');
}
/* ---- take back: rewind your last pegging play and the opponent's answer ---- */
function pegSnapshot(){ return JSON.stringify({left:G.left, pile:G.pile, count:G.count, lastPlayer:G.lastPlayer, scores:G.scores, prev:G.prevScores, goSaid:G.goSaid, played:G.played||[]}); }
function takeBack(){
  if(!G || G.phase!=='pegYou' || !G.undo || G.takebacks>=takebacksAllowed()) return;
  var S=JSON.parse(G.undo); G.undo=null; G.takebacks=(G.takebacks||0)+1;
  G.left=S.left; G.pile=S.pile; G.count=S.count; G.lastPlayer=S.lastPlayer; G.scores=S.scores; G.prevScores=S.prev; G.goSaid=S.goSaid; G.played=S.played; G.lift=-1; G.hintCard=null;
  el('ptsYou').textContent=G.scores[0]; el('ptsOpp').textContent=G.scores[1]; movePegs(); renderPile(); updateCount();
  coach('<b>Taken back.</b> Your play and the opponent\\'s answer were undone'+(takebacksAllowed()<99?(' · '+(takebacksAllowed()-G.takebacks)+' left this game'):'')+'.');
  nextPegTurn(0, true);
}""")
# ---------- game state ----------
rep("  left:null, pile:null, count:0, lastPlayer:-1, turn:0, deckRest:null };",
    "  left:null, pile:null, count:0, lastPlayer:-1, turn:0, deckRest:null, hints:0, takebacks:0, undo:null, played:[] };")
rep("  G.hand=d.slice(0,6).sort(byRank); G.opp=d.slice(6,12);",
    "  G.hand=d.slice(0,6).sort(byRank); G.opp=d.slice(6,12); G.handDealt=G.hand.slice(); G.oppDealt=G.opp.slice(); G.hintIdx=null; G.hintCard=null; G.undo=null; G.played=[]; coach('');")
# discard: opponent level, coach feedback
rep("  var idx=aiDiscard(G.opp, G.dealer===1, unseen);", "  var idx=aiDiscard(G.opp, G.dealer===1, unseen, SET.diff);\n  G.hintIdx=null; coachDiscard(toss);")
# pegging: opponent level + unseen for sharp; snapshot before your play; record played cards
rep("      var c=aiPegPlay(G.left[1], G.pile, G.count);\n      playCard(1, c);",
    "      var c=aiPegPlay(G.left[1], G.pile, G.count, SET.diff, SET.diff==='sharp'?unseenFor(1):null);\n      playCard(1, c);")
rep("function youPlay(c){\n  G.phase='pegWait';\n  playCard(0, c);\n}",
    "function youPlay(c){\n  G.phase='pegWait'; G.hintCard=null; if(G.takebacks<takebacksAllowed()) G.undo=pegSnapshot(); coach('');\n  playCard(0, c);\n}")
rep("function resetPile(){ G.pile=[]; G.count=0; G.lastPlayer=-1; G.goSaid=[false,false]; renderPile(); updateCount(); }",
    "function resetPile(){ G.played=(G.played||[]).concat(G.pile); G.pile=[]; G.count=0; G.lastPlayer=-1; G.goSaid=[false,false]; renderPile(); updateCount(); }")
rep("function finishPegging(){\n  var lp=G.lastPlayer;", "function finishPegging(){\n  var lp=G.lastPlayer; G.undo=null; coach('');")
# hint marks in renderHand
rep("      if(G.phase==='discard' && G.sel.indexOf(idx)>=0) elc.classList.add('sel');",
    "      if(G.phase==='discard' && G.sel.indexOf(idx)>=0) elc.classList.add('sel');\n      if(G.phase==='discard' && G.hintIdx && G.hintIdx.indexOf(idx)>=0) elc.classList.add('hintmark');\n      if(G.phase==='pegYou' && G.hintCard===cardKey(c)) elc.classList.add('hintmark');")
rep("  if(hintEl.style.display!=='none' && hintEl.textContent) nonH+=hintEl.offsetHeight+10;",
    "  if(hintEl.style.display!=='none' && hintEl.textContent) nonH+=hintEl.offsetHeight+10;\n  var coachEl=el('coach'); if(coachEl.style.display!=='none' && coachEl.textContent) nonH+=coachEl.offsetHeight+8;")
# actions: HINT + TAKE BACK
rep("""function renderActions(){
  var a=el('actions'); a.innerHTML='';
  if(G.phase==='discard'){
    var b=document.createElement('button'); b.className='btn gold'; b.textContent='SEND TO CRIB';
    b.disabled=(G.sel.length!==2);
    b.onclick=confirmDiscard; a.appendChild(b);
  }
}""",
"""function renderActions(){
  var a=el('actions'); a.innerHTML='';
  function mk(cls,txt,fn,dis){ var b=document.createElement('button'); b.className='btn '+cls; b.textContent=txt; b.disabled=!!dis; b.onclick=fn; a.appendChild(b); return b; }
  if(G.phase==='discard'){
    mk('ghost sm','💡 HINT',showHint);
    mk('gold','SEND TO CRIB',confirmDiscard,G.sel.length!==2);
  } else if(G.phase==='pegYou'){
    mk('ghost sm','💡 HINT',showHint);
    if(G.undo && G.takebacks<takebacksAllowed()) mk('ghost sm','↩ TAKE BACK'+(takebacksAllowed()<99?' ('+(takebacksAllowed()-G.takebacks)+')':''),takeBack);
  }
}""")
# end game: level in result + stats
rep("  el('resultbox').innerHTML='<b>Final:</b> You '+G.scores[0]+' · Opponent '+G.scores[1]+skunk;",
    "  el('resultbox').innerHTML='<b>Final:</b> You '+G.scores[0]+' · Opponent '+G.scores[1]+skunk+'<br><span style=\"opacity:.75\">Opponent: '+({relaxed:'Relaxed',standard:'Standard',sharp:'Sharp'}[SET.diff])+(G.hints?(' · hints used: '+G.hints):' · no hints')+'</span>';")
rep("    extra:{ skunksGiven: youWin && G.scores[1]<91, skunksTaken: !youWin && G.scores[0]<91 }}); }catch(e){} }",
    "    extra:{ skunksGiven: youWin && G.scores[1]<91, skunksTaken: !youWin && G.scores[0]<91, sharpWins: youWin && SET.diff==='sharp', noHintWins: youWin && !G.hints }}); }catch(e){} }")
# settings UI wiring (before test hook)
rep("el('startbtn').onclick=function(){ newGame(); };\n\n/* test hook */",
"""el('startbtn').onclick=function(){ newGame(); };
function applySet(){ document.querySelectorAll('#optsRow .seg').forEach(function(seg){ var k=seg.getAttribute('data-key'); seg.querySelectorAll('button').forEach(function(b){ b.classList.toggle('on', b.getAttribute('data-v')===SET[k]); }); }); }
document.querySelectorAll('#optsRow .seg button').forEach(function(b){ b.onclick=function(){ SET[b.parentNode.getAttribute('data-key')]=b.getAttribute('data-v'); saveSet(); applySet(); }; });
applySet();

/* test hook */""")
rep("  tap:onCardTap, confirmDiscard:confirmDiscard, endGame:endGame, award:award,",
    "  tap:onCardTap, confirmDiscard:confirmDiscard, endGame:endGame, award:award, hint:showHint, takeBack:takeBack, SET:SET, applySet:applySet, discardOptions:discardOptions, aiPegPlay:aiPegPlay, unseenFor:unseenFor,")
rep("    count:G?G.count:0, over:G?G.over:false,", "    count:G?G.count:0, over:G?G.over:false, hints:G?G.hints:0, takebacks:G?G.takebacks:0, undo:!!(G&&G.undo), coach:el('coach').textContent,")
rep("           {key:'perfect29',label:'Perfect 29 hands'}, {key:'skunksGiven',label:'Skunks given'}, {key:'skunksTaken',label:'Skunks taken'} ] };",
    "           {key:'perfect29',label:'Perfect 29 hands'}, {key:'skunksGiven',label:'Skunks given'}, {key:'skunksTaken',label:'Skunks taken'},\n           {key:'sharpWins',label:'Wins vs Sharp opponent'}, {key:'noHintWins',label:'Wins without a hint'} ] };")
P.write_text(s, encoding='utf-8')
print('patched', len(s))
