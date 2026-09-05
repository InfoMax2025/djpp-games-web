    /* ===== v1.3: guided first shift, save/resume, stats, rating, more games ===== */
    var TUT={active:false,step:-1,t:0,a1:null,d1:null,a2:null,a3:null,a4:null,done:false,wait:0};
    try{TUT.done=localStorage.getItem('tc3d_tut')==='1';}catch(e){}
    var tutBox=document.createElement('div');tutBox.id='tc-tut';tutBox.style.cssText='position:absolute;left:50%;top:0;transform:translateX(-50%);z-index:15;width:min(560px,94%);display:none;background:#0e1622f2;border:1px solid #2a6fa8;border-radius:12px;padding:10px 14px 10px;box-shadow:0 10px 30px #0009;font-size:14px;line-height:1.45;color:#e9eef5;';
    tutBox.innerHTML='<div style="display:flex;justify-content:space-between;align-items:center;gap:10px;"><span id="tc-tut-step" style="font-size:10px;letter-spacing:1.6px;color:#5cc8ff;font-weight:800;">GUIDED FIRST SHIFT</span><button id="tc-tut-skip" style="border:1px solid #2a3a4d;background:transparent;color:#9fb4c8;border-radius:8px;padding:3px 9px;font-size:11px;font-weight:700;cursor:pointer;pointer-events:auto;">Skip</button></div><div id="tc-tut-txt" style="margin-top:5px;"></div>';
    wrap.appendChild(tutBox);
    function layoutTut(){var tb=el('tw-topbar');tutBox.style.top=((tb?tb.offsetHeight:44)+6)+'px';var r=el('tw-radio');if(r&&TUT.active)r.style.top=((tb?tb.offsetHeight:44)+tutBox.offsetHeight+12)+'px';}
    function coach(txt,say){el('tc-tut-txt').innerHTML=txt;tutBox.style.display='block';layoutTut();sfx('click');
      if(say!==false&&voiceOn&&window.speechSynthesis){try{var u=new SpeechSynthesisUtterance(txt.replace(/<[^>]+>/g,''));u.rate=1.0;u.pitch=1.0;u.volume=1;if(_voices.length)u.voice=_voices[0];window.speechSynthesis.speak(u);}catch(e){}}}
    function tutStep(n,label){TUT.step=n;TUT.t=0;TUT.wait=0;el('tc-tut-step').textContent='GUIDED FIRST SHIFT · '+label;}
    function tutStart(){TUT.active=true;TUT.a1=TUT.d1=TUT.a2=TUT.a3=TUT.a4=null;tutStep(0,'STEP 1 OF 6');
      coach('Welcome to the tower. <b>Drag the view</b> left and right to sweep the whole runway — the RUNWAY SCAN bar at the bottom fills as you look along it.');}
    function tutEnd(skipped){TUT.active=false;tutBox.style.display='none';running=false;layoutHUD();
      try{localStorage.setItem('tc3d_tut','1');}catch(e){}TUT.done=true;refreshMenu();
      if(skipped){el('tc-menu').style.display='flex';return;}
      if(window.speechSynthesis){try{window.speechSynthesis.cancel();}catch(e){}}
      el('tc-grade').textContent='✓';el('tc-sscore').textContent=score;el('tc-sland').textContent=landed;el('tc-sdep').textContent=departed;el('tc-sbust').textContent=busts;el('tc-saround').textContent=arounds;
      el('tc-rank').textContent='You have the tower. Pick a shift from the menu — EASY is a gentle first hour.';
      el('tc-hs').innerHTML='<div style="opacity:.8">Guided shift complete — not logged to the Top 100.</div>';
      el('tc-again').textContent='START AN EASY SHIFT';el('tc-end').style.display='flex';sfx('ok');}
    function tutTick(dt){if(!TUT.active||!running||paused)return;TUT.t+=dt;
      var gone=function(p){return p&&planes.indexOf(p)<0;};
      switch(TUT.step){
        case 0: if(fullyScanned()){coach('Scan complete. Every clearance you give with a <b>fresh scan</b> earns +50. Keep sweeping between calls.');tutStep(1,'STEP 1 OF 6');} break;
        case 1: if(TUT.t>3.5){TUT.a1=spawnArrival({cat:2,nm:5.5});coach('Traffic. A 737 is five miles out on final. <b>Tap the aircraft</b> — or its green data tag — to key the radio.');tutStep(2,'STEP 2 OF 6');} break;
        case 2: if(selected&&selected===TUT.a1){coach('Good. It’s the only one on final, so it is <b>number one</b>. Tap <b>CLEARED TO LAND #1</b>.');tutStep(3,'STEP 2 OF 6');} break;
        case 3: if(TUT.a1&&TUT.a1.cleared){coach('Cleared to land. Watch it down — when it exits the runway you score <b>+100</b>. Keep the runway scanned while you wait.');tutStep(4,'STEP 2 OF 6');}
          else if(gone(TUT.a1)){TUT.a1=spawnArrival({cat:2,nm:5.5});coach('It went around because it had no clearance. Here it comes again — tap it, then <b>CLEARED TO LAND #1</b>.');} break;
        case 4: if(gone(TUT.a1)){TUT.d1=spawnDeparture({dep:'OUT'});coach('Landed. Now a <b>departure</b>: it taxis to the hold-short line by itself. When it reports <i>holding short</i>, tap it and press <b>CLEARED FOR TAKEOFF</b>.');tutStep(5,'STEP 3 OF 6');} break;
        case 5: if(TUT.d1&&(TUT.d1.state==='TKROLL'||TUT.d1.state==='CLIMB')){coach('Rolling. A departure counts <b>+100</b> once it’s airborne. Rule to remember: the runway must be <b>clear</b> before an arrival crosses the threshold.');tutStep(6,'STEP 3 OF 6');} break;
        case 6: if(TUT.d1&&(TUT.d1.counted||gone(TUT.d1))){TUT.a2=spawnArrival({cat:2,nm:7.5});TUT.a3=spawnArrival({cat:1,nm:3.6});
            coach('Two arrivals. The <b>closer one is #1</b>, the farther one is <b>#2</b>. Tap each and clear it with the right number — the card shows the in-trail gap (IFR needs 3 miles).');tutStep(7,'STEP 4 OF 6');} break;
        case 7: if(TUT.a2&&TUT.a3&&TUT.a2.cleared&&TUT.a3.cleared){coach('Both cleared. Sequence numbers matter: <b>#1 is always the one nearest the runway</b>. Let them land.');tutStep(8,'STEP 4 OF 6');}
          else{if(gone(TUT.a3)&&TUT.a3&&!TUT.a3.cleared){TUT.a3=spawnArrival({cat:1,nm:3.6});cacheMats(TUT.a3);}if(gone(TUT.a2)&&TUT.a2&&!TUT.a2.cleared){TUT.a2=spawnArrival({cat:2,nm:7.5});cacheMats(TUT.a2);}} break;
        case 8: if(gone(TUT.a2)&&gone(TUT.a3)){TUT.a4=spawnArrival({cat:1,nm:4.2});cacheMats(TUT.a4);coach('Last lesson: the <b>go-around</b>. Tap this aircraft and press <b>GO AROUND</b>. It flies the left-hand pattern — upwind, crosswind, downwind, base — and comes back to final.');tutStep(9,'STEP 5 OF 6');} break;
        case 9: if(TUT.a4&&TUT.a4.state==='PATTERN'){coach('In the pattern. From its card you can <b>EXTEND DOWNWIND</b> or <b>TURN BASE</b> to fit it in. When it’s back on final, clear it to land <b>#1</b>.');tutStep(10,'STEP 6 OF 6');}
          else if(TUT.a4&&TUT.a4.cleared){coach('You cleared it instead — fine, it lands. Here is another one: tap it and press <b>GO AROUND</b>.');TUT.a4=null;TUT.wait=1;}
          else if(TUT.wait&&gone(TUT.a4)===false&&TUT.a4===null){TUT.a4=spawnArrival({cat:1,nm:4.2});cacheMats(TUT.a4);TUT.wait=0;} break;
        case 10: if(TUT.a4&&TUT.a4.state==='INBOUND'&&TUT.a4.cleared){coach('Cleared. That is the whole job: <b>scan, sequence, clear, keep them apart</b>. When it’s down, your first shift is complete.');tutStep(11,'STEP 6 OF 6');}
          else if(TUT.a4&&TUT.a4.state==='INBOUND'&&TUT.t>25&&!TUT.wait){TUT.wait=1;coach('It’s back on final. Tap it and press <b>CLEARED TO LAND #1</b>.');} break;
        case 11: if(gone(TUT.a4)){tutEnd(false);} break;
      }}
    el('tc-tut-skip').onclick=function(){tutEnd(true);};
    /* ---- save / resume ---- */
    var SAVE_KEY='tc3d_save',_saveT=0;
    function planeRec(pl){var r={};for(var k in pl){if(!pl.hasOwnProperty(k))continue;if(k==='obj'||k==='_tag'||k==='_es'||k==='_spr'||k==='_grace'||k==='_if')continue;var v=pl[k];if(typeof v==='function')continue;r[k]=v;}
      r.rpt=0;r.rpt2=0;r.pos=[pl.obj.position.x,pl.obj.position.y,pl.obj.position.z];r.rot=[pl.obj.rotation.x,pl.obj.rotation.y,pl.obj.rotation.z];return r;}
    function saveShift(){if(!running||TUT.active||curDiff==='tutorial')return;try{
      var S={v:1,ts:Date.now(),diff:curDiff,level:curLevel,opsL:opsThisLevel,opsT:opsTotal,shiftT:shiftT,shiftLen:shiftLen,baseMaxP:baseMaxP,rampMax:rampMax,spawnBase:spawnBase,spawnRand:spawnRand,
        score:score,landed:landed,departed:departed,arounds:arounds,busts:busts,seq:seq,spawnT:spawnT,wx:wxBad,planes:planes.map(planeRec)};
      localStorage.setItem(SAVE_KEY,JSON.stringify(S));}catch(e){}}
    function loadSave(){try{var S=JSON.parse(localStorage.getItem(SAVE_KEY)||'null');if(!S||S.v!==1)return null;if(Date.now()-S.ts>3*86400000)return null;return S;}catch(e){return null;}}
    function clearSave(){try{localStorage.removeItem(SAVE_KEY);}catch(e){}refreshMenu();}
    function restoreShift(S){curDiff=S.diff;curLevel=S.level||1;opsTotal=S.opsT||0;
      if(curDiff==='levels'){curCfg=levelCfg(curLevel);}else curCfg=null;
      baseMaxP=S.baseMaxP;rampMax=S.rampMax;spawnBase=S.spawnBase;spawnRand=S.spawnRand;shiftLen=S.shiftLen;
      clearWorld();shiftT=S.shiftT;opsThisLevel=S.opsL||0;score=S.score;landed=S.landed;departed=S.departed;arounds=S.arounds;busts=S.busts;seq=S.seq||0;spawnT=Math.max(1.5,S.spawnT||2);
      for(var i=0;i<(S.planes||[]).length;i++){var r=S.planes[i];var p=makePlane(liveries[(r.lv||0)%liveries.length],r.cat||2);p.position.set(r.pos[0],r.pos[1],r.pos[2]);p.rotation.set(r.rot[0],r.rot[1],r.rot[2]);scene.add(p);
        var rec={};for(var k in r){if(k==='pos'||k==='rot')continue;rec[k]=r[k];}rec.obj=p;planes.push(rec);cacheMats(rec);}
      setWx(!!S.wx);_gyOff=null;running=true;paused=true;el('tc-pause').textContent='▶';el('tc-quit').style.display='';
      el('tc-menu').style.display='none';el('tc-end').style.display='none';
      flash('SHIFT RESUMED',(curDiff==='levels'?('level '+curLevel+' · '):'')+'press ▶ or P to continue','#4f9fe0');}
    function fmtLeft(S){if(S.diff==='levels'){var c=levelCfg(S.level||1);return c.timed?('L'+S.level+' · '+Math.max(0,Math.floor((c.len-S.shiftT)/60))+' min left'):('L'+S.level+' · '+(S.opsL||0)+'/'+c.ops+' ops');}
      var tl=Math.max(0,(S.shiftLen||480)-S.shiftT);return Math.floor(tl/60)+':'+('0'+Math.floor(tl%60)).slice(-2)+' left';}
    document.addEventListener('visibilitychange',function(){if(document.hidden){if(running&&!paused&&!TUT.active)togglePause();saveShift();}});
    window.addEventListener('pagehide',saveShift);
    /* quit-to-menu while paused */
    var quitBtn=document.createElement('button');quitBtn.id='tc-quit';quitBtn.textContent='MENU';quitBtn.style.cssText='position:absolute;top:8px;right:12px;margin-top:44px;z-index:16;display:none;border:1px solid #2a3a4d;background:#0e1622cc;color:#8fb6de;border-radius:9px;padding:8px 12px;font-size:12px;font-weight:800;letter-spacing:1px;cursor:pointer;';
    wrap.appendChild(quitBtn);
    quitBtn.onclick=function(){if(TUT.active){tutEnd(true);quitBtn.style.display='none';return;}saveShift();running=false;paused=false;quitBtn.style.display='none';el('tc-pause').textContent='II';el('tc-menu').style.display='flex';refreshMenu();sfx('click');};
    /* ---- lifetime stats, per-mode bests ---- */
    function loadStats(){try{return JSON.parse(localStorage.getItem('tc3d_stats')||'{}')||{};}catch(e){return {};}}
    function recordShift(grade){try{var st=loadStats();st.shifts=(st.shifts|0)+1;st.landed=(st.landed|0)+landed;st.departed=(st.departed|0)+departed;st.busts=(st.busts|0)+busts;st.arounds=(st.arounds|0)+arounds;
      if(busts===0){st.streak=(st.streak|0)+1;st.bestStreak=Math.max(st.bestStreak|0,st.streak);}else st.streak=0;
      st.best=st.best||{};if(st.best[curDiff]===undefined||score>st.best[curDiff])st.best[curDiff]=score;if(curDiff==='levels')st.bestLevel=Math.max(st.bestLevel|0,curLevel);
      st.grades=st.grades||{};st.grades[grade]=(st.grades[grade]|0)+1;localStorage.setItem('tc3d_stats',JSON.stringify(st));}catch(e){}}
    function statsLine(){var st=loadStats();var b=st.best||{};var f=function(k){return b[k]!==undefined?b[k].toLocaleString():'—';};
      return 'Best · Easy '+f('easy')+' · Normal '+f('normal')+' · Rush '+f('rush')+' · Levels '+f('levels')+(st.bestLevel?(' (L'+st.bestLevel+')'):'')+
        '<br><span style="opacity:.7">'+(st.shifts|0)+' shifts · '+(st.landed|0)+' landed · '+(st.departed|0)+' departed · clean-shift streak '+(st.streak|0)+(st.bestStreak?(' (best '+st.bestStreak+')'):'')+'</span>';}
    /* ---- Play rating + more games (fleet items F1 / F8) ---- */
    var PKG='com.djspuzzlepalace.towercontrol3d',PLAY='https://play.google.com/store/apps/details?id=';
    var IS_APP=(function(){try{if(/^android-app:\/\//.test(document.referrer)){localStorage.setItem('tc3d_env','twa');return true;}if(localStorage.getItem('tc3d_env')==='twa')return true;return !!(window.matchMedia&&window.matchMedia('(display-mode: standalone)').matches);}catch(e){return false;}})();
    function maybeRate(grade){var row=el('tc-rate');row.style.display='none';if(!IS_APP)return;try{var r=JSON.parse(localStorage.getItem('tc3d_rate')||'{}');var st=loadStats();var now=Date.now();
      if(r.done||(r.asks|0)>=3||(r.last&&now-r.last<21*86400000))return;if((st.shifts|0)<2||!(grade==='A'||grade==='A+'||grade==='B'))return;
      r.asks=(r.asks|0)+1;r.last=now;localStorage.setItem('tc3d_rate',JSON.stringify(r));row.style.display='flex';}catch(e){}}
    var rateRow=document.createElement('div');rateRow.id='tc-rate';rateRow.style.cssText='display:none;align-items:center;justify-content:center;gap:8px;flex-wrap:wrap;margin:-6px 0 14px;font-size:12px;color:#c9d6e2;';
    rateRow.innerHTML='<span>Enjoying the tower?</span><button id="tc-rate-go" style="border:0;border-radius:8px;padding:7px 12px;font-size:12px;font-weight:800;cursor:pointer;color:#04121a;background:#f2c14e;">⭐ Rate it on Google Play</button><button id="tc-rate-no" style="border:1px solid #2a3a4d;background:transparent;color:#8fa2b6;border-radius:8px;padding:7px 10px;font-size:11px;cursor:pointer;">Don’t ask again</button>';
    (function(){var hs=el('tc-hs');hs.parentNode.insertBefore(rateRow,hs.nextSibling);})();
    el('tc-rate-go').onclick=function(){try{var r=JSON.parse(localStorage.getItem('tc3d_rate')||'{}');r.done=true;localStorage.setItem('tc3d_rate',JSON.stringify(r));}catch(e){}rateRow.style.display='none';try{window.open(PLAY+PKG,'_blank');}catch(e){}};
    el('tc-rate-no').onclick=function(){try{var r=JSON.parse(localStorage.getItem('tc3d_rate')||'{}');r.done=true;localStorage.setItem('tc3d_rate',JSON.stringify(r));}catch(e){}rateRow.style.display='none';};
    var SIBS=[['Escape the Rat King','Horror 3D — six worlds, one Rat King','com.djspuzzlepalace.escapejohnpork'],['Cribbage Seniors','Big cards, every hand counted for you','com.djspuzzlepalace.cribbage'],['Euchre for Seniors','Big cards, honest partner','com.djspuzzlepalace.euchre'],['Gin Rummy Seniors','Big cards, knock or go gin','com.djspuzzlepalace.ginrummy'],['Pinochle Seniors','Big cards, every meld explained','com.djspuzzlepalace.pinochle'],['Spades Seniors','Big cards, nil bids, bags','com.djspuzzlepalace.spades']];
    var moreOv=document.createElement('div');moreOv.id='tc-more';moreOv.style.cssText='position:absolute;inset:0;z-index:33;display:none;align-items:center;justify-content:center;background:#070b12ee;';
    moreOv.innerHTML='<div style="width:min(430px,92%);background:#0e1622;border:1px solid #2a3a4d;border-radius:16px;padding:22px;max-height:86vh;display:flex;flex-direction:column;"><div style="font-size:13px;letter-spacing:3px;color:#5cc8ff;text-align:center;margin-bottom:6px;">MORE DJ’S PUZZLE PALACE GAMES</div><div style="font-size:11px;opacity:.6;text-align:center;margin-bottom:12px;">No ads mid-game. No coins. No accounts.</div><div id="tc-more-list" style="overflow-y:auto;flex:1;display:flex;flex-direction:column;gap:8px;"></div><button id="tc-more-back" class="tc-big" style="background:#8fb6de;margin-top:14px;">BACK</button></div>';
    wrap.appendChild(moreOv);
    el('tc-more-list').innerHTML=SIBS.map(function(s){return '<a href="'+PLAY+s[2]+'" target="_blank" rel="noopener" style="display:block;text-decoration:none;background:#111c2a;border:1px solid #22303f;border-radius:10px;padding:10px 12px;color:#e9eef5;"><div style="font-size:14px;font-weight:800;">'+s[0]+' <span style="float:right;font-size:11px;color:#38d66b;">Google Play ›</span></div><div style="font-size:11px;opacity:.65;margin-top:2px;">'+s[1]+'</div></a>';}).join('');
    el('tc-more-back').onclick=function(){moreOv.style.display='none';sfx('click');};
    /* ---- menu additions: guided first shift, resume, more games ---- */
    var menuCol=el('tc-easy').parentNode.parentNode;
    var topRow=document.createElement('div');topRow.id='tc-toprow';topRow.style.cssText='display:flex;flex-direction:column;gap:10px;margin-bottom:12px;';
    menuCol.insertBefore(topRow,el('tc-easy').parentNode);
    var moreBtn=document.createElement('button');moreBtn.id='tc-morebtn';moreBtn.textContent='More games';moreBtn.style.cssText='border:1px solid #2a3a4d;background:#0e1622;color:#b48fe0;border-radius:10px;padding:10px 18px;font-size:13px;font-weight:700;cursor:pointer;';
    el('tc-comms').parentNode.appendChild(moreBtn);moreBtn.onclick=function(){moreOv.style.display='flex';sfx('click');};
    function refreshMenu(){var S=loadSave();var h='';
      if(S)h+='<button id="tc-resume" class="tc-big" style="background:#38d66b;text-align:left;padding-left:18px;">▶ RESUME SHIFT<br><span style="font-weight:600;font-size:11px;">'+({easy:'Easy',normal:'Normal',rush:'Rush',levels:'Levels'}[S.diff]||S.diff)+' · '+fmtLeft(S)+' · '+S.score+' pts · <u id="tc-discard">discard</u></span></button>';
      if(!TUT.done)h+='<button id="tc-tutbtn" class="tc-big" style="background:linear-gradient(135deg,#5cc8ff,#38d66b);box-shadow:0 0 0 3px #5cc8ff33;">▶ FIRST SHIFT — GUIDED<br><span style="font-weight:600;font-size:10px;">learn the position in a few minutes · no timer, no score</span></button>';
      topRow.innerHTML=h;topRow.style.display=h?'flex':'none';
      if(S){el('tc-resume').onclick=function(e){if(e.target&&e.target.id==='tc-discard'){e.stopPropagation();clearSave();sfx('click');return;}restoreShift(S);sfx('click');};}
      if(!TUT.done)el('tc-tutbtn').onclick=function(){startShift('tutorial');};
      var rp=el('tc-replay');if(TUT.done){if(!rp){rp=document.createElement('div');rp.id='tc-replay';rp.style.cssText='font-size:11px;color:#5cc8ff;opacity:.8;margin-top:8px;cursor:pointer;text-decoration:underline;';rp.textContent='Replay the guided first shift';rp.onclick=function(){startShift('tutorial');};el('tc-best').parentNode.insertBefore(rp,el('tc-best').nextSibling);}}
      else if(rp)rp.remove();
      el('tc-best').innerHTML=statsLine();}
