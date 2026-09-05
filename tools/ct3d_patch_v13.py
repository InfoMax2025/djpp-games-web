#!/usr/bin/env python3
"""Control Tower 3D v1.3: guided first shift (tutorial), save/resume shift, lifetime stats + per-mode bests,
Play rating row, More Games panel, ad placeholder removed. Rebuilds index.html from the extracted parts."""
import re, pathlib
SRC = pathlib.Path('/home/claude/games/djpp-games-web/ct3d/index.html')
html = SRC.read_text(encoding='utf-8')
blocks = list(re.finditer(r'<script([^>]*)>(.*?)</script>', html, re.S))
assert len(blocks) == 4
game = blocks[2].group(2); tail = blocks[3].group(2)
assert 'GUIDED FIRST SHIFT' not in game, 'already patched'
tut = pathlib.Path('/home/claude/ct3d/tut.js').read_text(encoding='utf-8')

def rep(s, old, new, count=1):
    assert s.count(old) == count, f'expected {count} for {old[:60]!r}, got {s.count(old)}'
    return s.replace(old, new)

# --- spawns accept options, remember livery, return the record ---
game = rep(game, "function spawnArrival(){var cat=rollCat();var p=makePlane(liveries[seq%liveries.length],cat);\n      var zz=SPAWN_Z-Math.random()*40;var rm=rearmostZ();if(rm<Infinity)zz=Math.min(zz,rm-(NM3*1.35+Math.random()*0.4*NM_U));",
    "function spawnArrival(opts){opts=opts||{};var cat=opts.cat||rollCat();var lvi=seq%liveries.length;var p=makePlane(liveries[lvi],cat);\n      var zz=SPAWN_Z-Math.random()*40;var rm=rearmostZ();if(rm<Infinity)zz=Math.min(zz,rm-(NM3*1.35+Math.random()*0.4*NM_U));if(opts.nm!=null)zz=THRESH_Z-opts.nm*NM_U;")
game = rep(game, "planes.push({obj:p,kind:'ARR',state:'INBOUND',cat:cat,type:typeByCat[cat][seq%3]+(cat===3?' (H)':''),cs:mkCallsign(),cleared:false,clrType:'LAND',t:0,vref:KTA[cat]*KTF,rpt:0});var _np=planes[planes.length-1];radio(_np.cs,_mi+' mile final, inbound');seq++;}",
    "planes.push({obj:p,kind:'ARR',state:'INBOUND',cat:cat,lv:lvi,type:typeByCat[cat][seq%3]+(cat===3?' (H)':''),cs:mkCallsign(),cleared:false,clrType:'LAND',t:0,vref:KTA[cat]*KTF,rpt:0});var _np=planes[planes.length-1];if(opts.nm!=null){_np.obj.position.y=Math.min(SPAWN_Y,glideY(zz)+6);}cacheMats(_np);radio(_np.cs,_mi+' mile final, inbound');seq++;return _np;}")
game = rep(game, "function spawnDeparture(){var cat=rollCat();var p=makePlane(liveries[seq%liveries.length],cat);",
    "function spawnDeparture(opts){opts=opts||{};var cat=opts.cat||rollCat();var lvi=seq%liveries.length;var p=makePlane(liveries[lvi],cat);")
game = rep(game, "cat:cat,type:typeByCat[cat][seq%3]+(cat===3?' (H)':''),cs:mkCallsign(),spd:0,t:0,counted:false,vref:KTA[cat]*KTF,vdep:KTD[cat]*KTF,tacc:(cat===1?9:cat===2?7:5.5),vrz:THRESH_Z+(cat===1?2200:cat===2?5200:6800)/FT_PER_UNIT,dep:(Math.random()<0.6?'OUT':'PATTERN'),rpt:0});var _dp=planes[planes.length-1];radio(_dp.cs,'taxiing to runway 09');seq++;}",
    "cat:cat,lv:lvi,type:typeByCat[cat][seq%3]+(cat===3?' (H)':''),cs:mkCallsign(),spd:0,t:0,counted:false,vref:KTA[cat]*KTF,vdep:KTD[cat]*KTF,tacc:(cat===1?9:cat===2?7:5.5),vrz:THRESH_Z+(cat===1?2200:cat===2?5200:6800)/FT_PER_UNIT,dep:opts.dep||(Math.random()<0.6?'OUT':'PATTERN'),rpt:0});var _dp=planes[planes.length-1];cacheMats(_dp);radio(_dp.cs,'taxiing to runway 09');seq++;return _dp;}")
game = rep(game, "function scheduleSpawn(){if(!running)return;", "function scheduleSpawn(){if(!running||TUT.active)return;")
# --- the tutorial + save + stats module ---
game = rep(game, "    function clearWorld(){", tut + "    function clearWorld(){")
# --- tick: tutorial step machine, periodic autosave, timer label ---
game = rep(game, "spawnT-=dt;scanTick();\n", "spawnT-=dt;scanTick();if(dt>0){tutTick(dt);_saveT+=dt;if(_saveT>10){_saveT=0;saveShift();}}\n")
game = rep(game, "el('tw-time').textContent=running?tstr:'--:--';", "el('tw-time').textContent=running?(TUT.active?'GUIDED':tstr):'--:--';")
# --- level complete: no ad box, level summary + boundary save ---
game = rep(game, "      el('tc-lvl').style.display='flex';sfx('land');}",
    "      el('tc-lvl-sum').textContent='Level '+curLevel+' · '+opsThisLevel+' operations · '+busts+' bust'+(busts===1?'':'s')+' so far · '+landed+' landed · '+departed+' departed';\n"
    "      if(!last){try{localStorage.setItem(SAVE_KEY,JSON.stringify({v:1,ts:Date.now(),diff:'levels',level:curLevel+1,opsL:0,opsT:opsTotal,shiftT:0,shiftLen:999,baseMaxP:baseMaxP,rampMax:0,spawnBase:spawnBase,spawnRand:spawnRand,score:score,landed:landed,departed:departed,arounds:arounds,busts:busts,seq:seq,spawnT:1.5,wx:wxBad,planes:[]}));}catch(e){}}\n"
    "      el('tc-lvl').style.display='flex';sfx('land');}")
game = rep(game, "      loadLevel(curLevel);running=true;paused=false;\n      flash('LEVEL '+curLevel,",
    "      loadLevel(curLevel);running=true;paused=false;if(curLevel>=2&&curCfg){var _bs=null;try{_bs=JSON.parse(localStorage.getItem(SAVE_KEY)||'null');}catch(e){}if(_bs&&_bs.level===curLevel){shiftLen=curCfg.timed?curCfg.len:999;}}\n      flash('LEVEL '+curLevel,")
# --- startShift: tutorial mode, clear old save, reset labels ---
game = rep(game, "    function startShift(diff){curDiff=diff;curLevel=1;opsTotal=0;\n      if(diff==='easy'){",
    "    function startShift(diff){curDiff=diff;curLevel=1;opsTotal=0;curCfg=null;TUT.active=false;tutBox.style.display='none';el('tc-quit').style.display='none';el('tc-again').textContent='SAME SHIFT AGAIN';if(diff!=='tutorial')clearSave();\n"
    "      if(diff==='tutorial'){shiftLen=1e9;baseMaxP=0;rampMax=0;spawnBase=99;spawnRand=1;}\n      else if(diff==='easy'){")
game = rep(game, "      var bad=Math.random()<0.22;setWx(bad);\n      sfx('click');flash('SHIFT START',",
    "      var bad=(diff!=='tutorial')&&Math.random()<0.22;setWx(bad);\n      if(diff==='tutorial'){sfx('click');flash('GUIDED FIRST SHIFT','follow the coach at the top · no timer, no score','#4f9fe0');tutStart();return;}\n      sfx('click');flash('SHIFT START',")
# --- endShift: stats, rating, clear save ---
game = rep(game, "    function endShift(){running=false;\n      var grade=",
    "    function endShift(){running=false;el('tc-quit').style.display='none';if(curDiff==='tutorial'){tutEnd(false);return;}clearSave();\n      var grade=")
game = rep(game, "      el('tc-end').style.display='flex';sfx('ok');}\n    function togglePause(){if(!running)return;paused=!paused;el('tc-pause').textContent=paused?'▶':'II';if(paused)flash('PAUSED','press P or ▶ to resume','#4f9fe0');}",
    "      recordShift(grade);maybeRate(grade);el('tc-again').textContent='SAME SHIFT AGAIN';el('tc-end').style.display='flex';sfx('ok');}\n"
    "    function togglePause(){if(!running)return;paused=!paused;el('tc-pause').textContent=paused?'▶':'II';el('tc-quit').style.display=paused?'':'none';if(paused){flash('PAUSED','press P or ▶ to resume · MENU saves your shift','#4f9fe0');saveShift();}}")
game = rep(game, "    el('tc-again').onclick=function(){startShift(curDiff);};\n    el('tc-tomenu').onclick=function(){el('tc-end').style.display='none';el('tc-menu').style.display='flex';bestLine();};",
    "    el('tc-again').onclick=function(){startShift(curDiff==='tutorial'?'easy':curDiff);};\n    el('tc-tomenu').onclick=function(){el('tc-end').style.display='none';el('tc-menu').style.display='flex';bestLine();refreshMenu();};")
game = rep(game, "    el('tc-lvl-menu').onclick=function(){el('tc-lvl').style.display='none';running=false;el('tc-menu').style.display='flex';bestLine();sfx('click');};",
    "    el('tc-lvl-menu').onclick=function(){el('tc-lvl').style.display='none';running=false;el('tc-menu').style.display='flex';bestLine();refreshMenu();sfx('click');};")
game = rep(game, "    bestLine();setSky(false);", "    bestLine();refreshMenu();setSky(false);")
game = rep(game, "    window.addEventListener('resize',function(){var w=wrap.clientWidth,h=wrap.clientHeight;camera.aspect=w/h;camera.updateProjectionMatrix();renderer.setSize(w,h);layoutHUD();});",
    "    window.addEventListener('resize',function(){var w=wrap.clientWidth,h=wrap.clientHeight;camera.aspect=w/h;camera.updateProjectionMatrix();renderer.setSize(w,h);layoutHUD();layoutTut();});\n"
    "    if(/[?&]tctest/.test(location.search)){window.__tc={start:startShift,state:function(){return {running:running,paused:paused,diff:curDiff,level:curLevel,score:score,landed:landed,departed:departed,busts:busts,planes:planes.length,tut:TUT.step,tutActive:TUT.active,shiftT:shiftT};},planes:function(){return planes.map(function(p){return {cs:p.cs,kind:p.kind,state:p.state,cleared:!!p.cleared,z:+p.obj.position.z.toFixed(1),y:+p.obj.position.y.toFixed(1)};});},\n"
    "      select:function(cs){var p=planes.find(function(x){return x.cs===cs;});select(p||null);return !!p;},click:function(id){el(id).onclick();},scan:function(){for(var i=0;i<NSEG;i++)segSeen[i]=nowS();},tick:function(sec){var n=Math.round(sec*30);for(var i=0;i<n;i++){var dt=1/30;if(running&&!paused){shiftT+=0;} } },\n"
    "      _planes:function(){return planes;},_TUT:function(){return TUT;},save:saveShift,load:loadSave,restore:function(){var S=loadSave();if(S)restoreShift(S);return !!S;},pause:togglePause,end:endShift,stats:loadStats,setTutDone:function(v){TUT.done=!!v;refreshMenu();},tutText:function(){return el('tc-tut-txt').textContent;},menuText:function(){return el('tc-menu').textContent;}};}")
# --- HTML: ad slot → level summary, version tag ---
html_new = html[:blocks[2].start()] + '<script>' + game + '</script>' + html[blocks[2].end():blocks[3].start()]
html_new = rep(html_new, '''      <!-- ===== AD SLOT =====  Drop your interstitial/banner ad unit (e.g. AdMob) inside this box.
           It is shown between every level, while the game is paused — the natural break point. -->
      <div id="tc-adslot" style="height:120px;display:flex;align-items:center;justify-content:center;border:1px dashed #33465c;border-radius:10px;color:#4a5a6d;font-size:12px;letter-spacing:3px;margin-bottom:18px;">AD SPACE</div>''',
    '''      <div id="tc-lvl-sum" style="font-size:12px;color:#9fb4c8;border:1px solid #22303f;border-radius:10px;padding:12px;margin-bottom:18px;line-height:1.5;">&nbsp;</div>''')
html_new = rep(html_new, '<div id="tc-menu" style="position:absolute;inset:0;z-index:30;display:flex;align-items:center;justify-content:center;background:radial-gradient(ellipse at 50% 30%, #14202fee, #070b12f5);">\n    <div style="width:min(440px,92%);text-align:center;">',
    '<div id="tc-menu" style="position:absolute;inset:0;z-index:30;display:flex;align-items:flex-start;justify-content:center;overflow-y:auto;background:radial-gradient(ellipse at 50% 30%, #14202fee, #070b12f5);">\n    <div style="width:min(440px,92%);text-align:center;margin:auto;padding:14px 0 18px;">')
html_new = rep(html_new, '@media (max-height:560px){ #tc-logo{display:none;} }', '@media (max-height:560px){ #tc-logo{display:none;} }\n@media (max-height:500px){ #tc-tut{font-size:12px !important;padding:5px 10px 6px !important;line-height:1.3 !important;width:min(640px,96%) !important;} #tc-tut-step{font-size:9px !important;} #tc-tut-txt{margin-top:2px !important;} }\n#tc-tut b{color:#7fe0ff;}')
html_new = rep(html_new, 'A DJ\'s Puzzle Palace game &middot; rules per FAA Order JO 7110.65BB</div>', 'A DJ\'s Puzzle Palace game &middot; rules per FAA Order JO 7110.65BB &middot; v1.3</div>')
html_new = rep(html_new, '<div style="font-size:11px;opacity:.62;line-height:1.7;text-align:left;background:#0d1420aa;border:1px solid #22303f;border-radius:10px;padding:10px 14px;">\n        <b style="color:#5cc8ff;">HOW TO WORK THE POSITION</b><br>',
    '<div style="font-size:11px;opacity:.62;line-height:1.7;text-align:left;background:#0d1420aa;border:1px solid #22303f;border-radius:10px;padding:10px 14px;">\n        <b style="color:#5cc8ff;">HOW TO WORK THE POSITION</b> <span style="opacity:.7">(new here? take the guided first shift above)</span><br>')
# --- what's new (existing players only) ---
tail_new = tail.replace("var NOTE_ID='tc3d_whatsnew_v121';\n  try{ if(localStorage.getItem(NOTE_ID)) return; }catch(e){ return; }",
    "var NOTE_ID='tc3d_whatsnew_v130';\n  try{ if(localStorage.getItem(NOTE_ID)) return; if(!localStorage.getItem('tc3d_scores')) return; }catch(e){ return; }")
assert tail_new != tail
tail_new = rep(tail_new, "'<div style=\"font-size:21px;font-weight:800;color:#fff;margin:6px 0 12px;\">The tower got a new view</div>'+", "'<div style=\"font-size:21px;font-weight:800;color:#fff;margin:6px 0 12px;\">Leave the tower, come back later</div>'+")
start = tail_new.index("'<div style=\"font-size:13px;line-height:1.62;color:#b8c6d6;\">'+")
end = tail_new.index("'<div style=\"font-size:11px;color:#7f8fa2;margin:13px 0 14px;line-height:1.5;\">")
tail_new = tail_new[:start] + '''\'<div style="font-size:13px;line-height:1.62;color:#b8c6d6;">\'+
        \'<div style="margin-bottom:7px;">&#9679; <b style="color:#e8f0f8;">Resume a shift</b> &mdash; pause, tap MENU, and your shift is waiting on the front page (it also saves itself when the app goes to the background).</div>\'+
        \'<div style="margin-bottom:7px;">&#9679; <b style="color:#e8f0f8;">Guided first shift</b> &mdash; a coached walk through scanning, clearing, departures, sequencing and the go-around. Replay it any time from the menu.</div>\'+
        \'<div style="margin-bottom:7px;">&#9679; <b style="color:#e8f0f8;">Your record</b> &mdash; best score per mode, shifts worked, landings, departures and your clean-shift streak, right on the menu.</div>\'+
        \'<div>&#9679; <b style="color:#e8f0f8;">More games</b> &mdash; the other DJ\\'s Puzzle Palace titles, one tap away.</div>\'+
      \'</div>\'+
      ''' + tail_new[end:]
tail_new = rep(tail_new, "Same rules, same scoring &mdash; your Top 100 board is untouched. Runs slower on older phones? It scales itself back automatically.", "Same rules, same scoring &mdash; your Top 100 board is untouched.")
html_new += '<script>' + tail_new + '</script>' + html[blocks[3].end():]
out = pathlib.Path('/home/claude/ct3d/index.html'); out.write_text(html_new, encoding='utf-8')
print('written', len(html_new), 'bytes; game script', len(game))
