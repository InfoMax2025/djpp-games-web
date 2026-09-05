#!/usr/bin/env python3
import sys, threading, http.server, socketserver, functools, pathlib, json, shutil, os
from playwright.sync_api import sync_playwright
# serve a folder with the patched index + the rest of the live files
folder = pathlib.Path('/home/claude/ct3d/site'); folder.mkdir(exist_ok=True)
for f in pathlib.Path('/home/claude/games/djpp-games-web/ct3d').iterdir():
    if f.name != 'index.html': shutil.copy(f, folder / f.name)
shutil.copy('/home/claude/ct3d/index.html', folder / 'index.html')
PORT = 8620
class Q(socketserver.TCPServer): allow_reuse_address = True
srv = Q(('127.0.0.1', PORT), functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(folder)))
threading.Thread(target=srv.serve_forever, daemon=True).start()
fails = []
def wait_for(page, expr, timeout=40000, step=200):
    import time
    t0=time.time()
    while time.time()-t0 < timeout/1000:
        if page.evaluate(expr): return True
        page.wait_for_timeout(step)
    return False
def check(c, m):
    print(('  ok   ' if c else '  FAIL ') + m)
    if not c: fails.append(m)
with sync_playwright() as p:
    b = p.chromium.launch(args=['--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist'])
    ctx = b.new_context(viewport={'width': 1100, 'height': 700}); page = ctx.new_page(); errs = []
    page.on('pageerror', lambda e: errs.append(str(e))); page.on('console', lambda m: errs.append(m.text) if m.type == 'error' else None)
    page.goto(f'http://127.0.0.1:{PORT}/index.html?tctest'); page.wait_for_timeout(2500)
    check(page.evaluate("typeof window.__tc") == 'object', 'test rig present (boot ok)')
    check(page.locator('#tc-tutbtn').count() == 1, 'menu shows FIRST SHIFT — GUIDED for a new player')
    check(page.locator('#tc-resume').count() == 0, 'no resume button without a save')
    check('Best · Easy' in page.evaluate("document.getElementById('tc-best').textContent"), 'stats line on menu')
    check(page.locator('#tc-adslot').count() == 0 and page.locator('#tc-lvl-sum').count() == 1, 'ad placeholder replaced by level summary')
    check(page.locator('#tc-morebtn').count() == 1, 'More games button present')
    # ---- tutorial flow ----
    page.evaluate("__tc.start('tutorial')"); page.wait_for_timeout(400)
    st = page.evaluate("__tc.state()"); check(st['tutActive'] and st['tut'] == 0 and st['running'], f"tutorial started (step {st['tut']})")
    check('Drag the view' in page.evaluate("__tc.tutText()"), 'coach text step 1')
    page.evaluate("__tc.scan()"); page.wait_for_timeout(400)
    check(page.evaluate("__tc.state().tut") == 1, 'scan completes step 1')
    wait_for(page, "__tc.state().tut===2")
    st = page.evaluate("__tc.state()"); pl = page.evaluate("__tc.planes()")
    check(st['tut'] == 2 and len(pl) == 1 and pl[0]['kind'] == 'ARR', f'arrival spawned for step 2 ({pl})')
    check(pl[0]['z'] < -1200 and pl[0]['y'] < 140, f"arrival placed ~5.5 NM out on the glideslope z={pl[0]['z']} y={pl[0]['y']}")
    page.evaluate(f"__tc.select('{pl[0]['cs']}')"); page.wait_for_timeout(300)
    check(page.evaluate("__tc.state().tut") == 3, 'selecting the aircraft advances to clear step')
    page.evaluate("__tc.scan(); __tc.click('tw-b-l1')"); page.wait_for_timeout(300)
    st = page.evaluate("__tc.state()"); check(st['tut'] == 4 and page.evaluate("__tc.planes()[0].cleared"), 'cleared to land advances')
    # fast-forward: put the arrival on the taxiway exit so it counts as landed
    page.evaluate("(function(){var p=__tc._planes()[0];p.state='TAXI';p.exitZ=75;p.obj.position.set(-45,0,75);})()"); wait_for(page, "__tc.state().tut===5", 8000)
    st = page.evaluate("__tc.state()"); pl = page.evaluate("__tc.planes()")
    check(st['landed'] == 1 and st['tut'] == 5 and len(pl) == 1 and pl[0]['kind'] == 'DEP', f"landing counted, departure spawned (landed={st['landed']} step={st['tut']} planes={pl})")
    # fast-forward the departure to hold short
    page.evaluate("(function(){var p=__tc._planes()[0];p.state='HOLD';p.obj.position.set(-26,0,-243+8);})()"); page.wait_for_timeout(200)
    page.evaluate(f"__tc.select('{pl[0]['cs']}'); __tc.scan(); __tc.click('tw-b-to')"); page.wait_for_timeout(300)
    st = page.evaluate("__tc.state()"); check(st['tut'] == 6 and page.evaluate("__tc.planes()[0].state") in ('TKROLL', 'CLIMB'), f"takeoff clearance advances (step {st['tut']})")
    page.evaluate("(function(){var p=__tc._planes()[0];p.state='CLIMB';p.obj.position.set(0,12,100);p.spd=50;})()"); wait_for(page, "__tc.state().tut===7", 8000)
    st = page.evaluate("__tc.state()"); pl = page.evaluate("__tc.planes()")
    check(st['departed'] == 1 and st['tut'] == 7, f"departure counted, two arrivals spawned (departed={st['departed']} step={st['tut']} n={len(pl)})")
    arrs = [x for x in pl if x['kind'] == 'ARR']; check(len(arrs) == 2, f'two arrivals on final ({len(arrs)})')
    near = max(arrs, key=lambda x: x['z']); far = min(arrs, key=lambda x: x['z'])
    page.evaluate(f"__tc.select('{near['cs']}'); __tc.scan(); __tc.click('tw-b-l1'); __tc.select('{far['cs']}'); __tc.scan(); __tc.click('tw-b-l2')"); page.wait_for_timeout(300)
    check(page.evaluate("__tc.state().tut") == 8, 'both cleared in sequence advances')
    page.evaluate("(function(){var i=0;__tc._planes().forEach(function(p){if(p.kind==='ARR'){p.state='TAXI';p.exitZ=75;p.obj.position.set(-45,0,75-i*140);i++;}});})()"); wait_for(page, "__tc.state().tut===9", 8000)
    st = page.evaluate("__tc.state()"); pl = page.evaluate("__tc.planes()")
    check(st['landed'] == 3 and st['tut'] == 9 and len([x for x in pl if x['kind']=='ARR']) == 1, f"go-around lesson spawned (landed={st['landed']} step={st['tut']})")
    a4 = [x for x in pl if x['kind'] == 'ARR'][0]
    page.evaluate(f"__tc.select('{a4['cs']}'); __tc.click('tw-b-around')"); page.wait_for_timeout(300)
    check(page.evaluate("__tc.state().tut") == 10 and page.evaluate("__tc.planes().find(p=>p.kind==='ARR').state") == 'PATTERN', 'go-around puts it in the pattern, step 6')
    # bring it back to final and clear
    page.evaluate("(function(){var p=__tc._planes().find(function(x){return x.kind==='ARR';});p.state='INBOUND';p.leg=null;p.obj.position.set(0,60,-243-4*243);p._grace=0;})()"); page.wait_for_timeout(200)
    page.evaluate(f"__tc.select('{a4['cs']}'); __tc.scan(); __tc.click('tw-b-l1')"); page.wait_for_timeout(300)
    check(page.evaluate("__tc.state().tut") == 11, 'final clearance advances to the last step')
    page.evaluate("(function(){var p=__tc._planes().find(function(x){return x.kind==='ARR';});p.state='TAXI';p.exitZ=75;p.obj.position.set(-45,0,75);})()"); wait_for(page, "!__tc.state().tutActive", 8000)
    st = page.evaluate("__tc.state()")
    check((not st['running']) and (not st['tutActive']) and page.evaluate("document.getElementById('tc-end').style.display") == 'flex', 'tutorial ends on the end screen')
    check(page.evaluate("document.getElementById('tc-grade').textContent") == '✓' and 'START AN EASY SHIFT' in page.evaluate("document.getElementById('tc-again').textContent"), 'tutorial end screen text')
    check(page.evaluate("localStorage.getItem('tc3d_tut')") == '1', 'tutorial marked done')
    check(page.evaluate("JSON.parse(localStorage.getItem('tc3d_scores')||'[]').length") == 0, 'tutorial did not touch the Top 100')
    page.evaluate("__tc.click('tc-tomenu')"); page.wait_for_timeout(200)
    check(page.locator('#tc-tutbtn').count() == 0 and page.locator('#tc-replay').count() == 1, 'menu: big tutorial button gone, replay link shown')
    # ---- save / resume ----
    page.evaluate("__tc.start('normal')"); wait_for(page, "__tc.planes().length>=1", 30000)
    n0 = page.evaluate("__tc.planes().length"); sc0 = page.evaluate("__tc.state().score")
    page.evaluate("__tc.pause()"); page.wait_for_timeout(200)
    check(page.evaluate("document.getElementById('tc-quit').style.display") != 'none', 'MENU button appears while paused')
    S = page.evaluate("__tc.load()")
    check(S is not None and S['diff'] == 'normal' and len(S['planes']) == n0, f"pause saved the shift ({len(S['planes']) if S else None} planes)")
    page.evaluate("__tc.click('tc-quit')"); page.wait_for_timeout(300)
    check(page.locator('#tc-resume').count() == 1 and 'RESUME SHIFT' in page.evaluate("__tc.menuText()"), 'menu offers RESUME SHIFT')
    page.reload(); page.wait_for_timeout(2500)
    check(page.locator('#tc-resume').count() == 1, 'resume survives a reload')
    page.evaluate("document.getElementById('tc-resume').click()"); page.wait_for_timeout(500)
    st = page.evaluate("__tc.state()")
    check(st['running'] and st['paused'] and st['planes'] == n0 and st['diff'] == 'normal', f"restored shift: paused, {st['planes']} planes, score {st['score']}")
    page.evaluate("__tc.pause()"); wait_for(page, f"__tc.state().shiftT>{st['shiftT']}", 8000)
    st2 = page.evaluate("__tc.state()"); check(st2['shiftT'] > st['shiftT'], 'shift runs after resume')
    page.evaluate("__tc.end()"); page.wait_for_timeout(300)
    check(page.evaluate("__tc.load()") is None, 'ending the shift clears the save')
    stt = page.evaluate("__tc.stats()"); check(stt.get('shifts') == 1 and 'normal' in stt.get('best', {}), f'lifetime stats recorded {json.dumps(stt)}')
    check(page.evaluate("document.getElementById('tc-rate').style.display") == 'none', 'no rating row outside the app')
    check(not errs, 'no console/page errors: ' + ('; '.join(errs)[:300] if errs else 'clean'))
    page.screenshot(path='/home/claude/ct3d/end.png')
    page.evaluate("__tc.click('tc-tomenu')"); page.wait_for_timeout(300); page.screenshot(path='/home/claude/ct3d/menu.png')
    b.close()
srv.shutdown(); print('RESULT:', 'PASS' if not fails else f'{len(fails)} FAILURE(S)'); sys.exit(1 if fails else 0)
