#!/usr/bin/env python3
"""Shared Top 10 board — wiring test for the four kit games and Control Tower 3D, run offline (no Firebase reachable
from the sandbox): the board script loads, the menu button opens the panel, the panel degrades to its error state,
DJPP.record / endShift keep working joined or not, and no page errors appear.
usage: python3 test_board_wiring.py [--shots]"""
import sys, json, threading, http.server, socketserver, functools, pathlib, re
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path('/home/claude/games/djpp-games-web'); shots = '--shots' in sys.argv
fails = []
def check(cond, msg):
    print(('  ok   ' if cond else '  FAIL ') + msg)
    if not cond: fails.append(msg)

class Q(socketserver.TCPServer): allow_reuse_address = True
def serve(folder, port):
    h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(folder))
    srv = Q(('127.0.0.1', port), h); threading.Thread(target=srv.serve_forever, daemon=True).start(); return srv

def kit_game(p, name, port):
    print(f'== {name}')
    srv = serve(ROOT / name, port)
    b = p.chromium.launch(); ctx = b.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=2, is_mobile=True, has_touch=True)
    page = ctx.new_page(); errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.on('console', lambda m: errors.append(m.text) if m.type == 'error' and 'gstatic' not in m.text and 'Failed to fetch' not in m.text and 'net::ERR' not in m.text else None)
    page.goto(f'http://127.0.0.1:{port}/index.html'); page.wait_for_timeout(900)
    check(page.evaluate("!!window.DJPPBoard && DJPPBoard.game") == name, 'djpp-board.js loaded with the right board id')
    check(page.evaluate("DJPP.version") == '1.1', 'kit v1.1')
    labels = page.locator('#djppMenu .djpp-btn').all_inner_texts()
    check(labels == ['My Stats', 'Top 10', 'Fair Deal', 'More Games'], f'menu buttons {labels}')
    check(page.evaluate("DJPPBoard.joined()") is False, 'not joined by default')
    page.click('#djppMenu .djpp-btn:nth-child(2)'); page.wait_for_timeout(300)
    check(page.locator('#djppBoard').count() == 1, 'Top 10 panel opens')
    page.wait_for_function("() => document.querySelector('#djppBoard') && !/Loading the board/.test(document.querySelector('#djppBoard').innerText)", timeout=20000)
    txt = page.locator('#djppBoard').inner_text()
    check('Couldn’t reach the board' in txt or 'offline' in txt, 'degrades to the could-not-reach message when Firebase is unreachable')
    check('Try again' in txt and 'Join the board' in txt and 'Back' in txt, 'error state offers Try again / Join / Back')
    if shots: page.screenshot(path=f'/home/claude/games/shots/board-{name}-offline.png')
    page.click('#djppBoard .bd-btn:has-text("Join the board")'); page.wait_for_timeout(200)
    check(page.locator('#djppBoard input.bd-in').count() == 1, 'join form shows a nickname input')
    page.fill('#djppBoard input.bd-in', 'x'); page.click('#djppBoard .bd-btn.gold'); page.wait_for_timeout(200)
    check('at least 2' in page.locator('#djppBoard .bd-err').inner_text(), 'client-side name validation (too short)')
    page.fill('#djppBoard input.bd-in', 'Bad shit name'); page.click('#djppBoard .bd-btn.gold'); page.wait_for_timeout(200)
    check('friendlier' in page.locator('#djppBoard .bd-err').inner_text(), 'client-side name validation (profanity)')
    page.fill('#djppBoard input.bd-in', "Grandma's Ace"); page.click('#djppBoard .bd-btn.gold')
    page.wait_for_function("() => !/Joining/.test(document.querySelector('#djppBoard .bd-btn.gold').textContent)", timeout=20000)
    check('Couldn’t reach' in page.locator('#djppBoard .bd-err').inner_text() or 'offline' in page.locator('#djppBoard .bd-err').inner_text(), 'join offline → clear error, stays unjoined')
    check(page.evaluate("DJPPBoard.joined()") is False, 'still not joined after failed join')
    page.click('#djppBoard .bd-btn:has-text("Cancel")'); page.wait_for_timeout(200)
    page.click('#djppBoard .bd-btn:has-text("Back")'); page.wait_for_timeout(200)
    check(page.locator('#djppBoard').count() == 0, 'Back closes the panel')
    # record while not joined: nothing queued, nothing sent
    r = page.evaluate("DJPP.record({won:true, you:121, opp:90})")
    check(r['won'] is True and page.evaluate("DJPPBoard._state().pending.length") == 0, 'DJPP.record works, board ignores results when not joined')
    check(page.locator('#djppResult').count() == 1, 'record line rendered')
    # simulate a joined device (as if joined earlier, now offline): the result is queued locally and the line says so
    page.evaluate("localStorage.setItem('djpp.board.%s', JSON.stringify({joined:true, uid:'u1', name:'Tester', me:{name:'Tester',wins:0,streak:0,best:0,games:0,score:0,wk:DJPPBoard.weekId(new Date()),wkWins:0,wkBest:0,wkStreak:0,wkScore:0}, pending:[]}))" % name)
    page.reload(); page.wait_for_timeout(900)
    check(page.evaluate("DJPPBoard.joined() && DJPPBoard.name()") == 'Tester', 'joined state restored from localStorage')
    labels = page.locator('#djppMenu .djpp-btn').all_inner_texts(); check('Top 10' in labels, 'menu still has Top 10 when joined')
    page.evaluate("DJPP.record({won:true, you:121, opp:90})"); page.wait_for_timeout(300)
    check('Top 10 board:' in page.locator('#djppResult').inner_text(), 'joined: result line gets a Top 10 board tag')
    page.wait_for_function("() => !/sending your result/.test(document.querySelector('#djppResult').innerText)", timeout=25000)
    line = page.locator('#djppResult').inner_text()
    check('back online' in line, f'offline: result kept locally, line says so → "{line.splitlines()[-1]}"')
    check(page.evaluate("DJPPBoard._state().pending.length") == 1, 'one pending result queued')
    check(not errors, f'no page errors ({errors[:3]})')
    if shots: page.screenshot(path=f'/home/claude/games/shots/board-{name}-queued.png')
    b.close(); srv.shutdown()

def ct3d(p, port):
    print('== ct3d')
    srv = serve(ROOT / 'ct3d', port)
    b = p.chromium.launch(args=['--use-gl=swiftshader', '--enable-unsafe-swiftshader']); ctx = b.new_context(viewport={'width': 900, 'height': 640})
    page = ctx.new_page(); errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.on('console', lambda m: errors.append(m.text) if m.type == 'error' and 'gstatic' not in m.text and 'Failed to fetch' not in m.text and 'net::ERR' not in m.text and 'WebGL' not in m.text else None)
    page.goto(f'http://127.0.0.1:{port}/index.html?tctest=1'); page.wait_for_timeout(2500)
    check(page.evaluate("!!window.DJPPBoard && DJPPBoard.game") == 'ct3d' and page.evaluate("DJPPBoard.metric") == 'score', 'board loaded for ct3d with score metric')
    check(page.locator('#tc-board').count() == 1 and page.locator('#tc-showscores').inner_text() == 'My Top 100', 'menu has Shared Top 10 + My Top 100')
    page.click('#tc-board'); page.wait_for_timeout(300)
    check(page.locator('#djppBoard').count() == 1, 'Shared Top 10 panel opens')
    page.wait_for_function("() => document.querySelector('#djppBoard') && !/Loading the board/.test(document.querySelector('#djppBoard').innerText)", timeout=20000)
    txt = page.locator('#djppBoard').inner_text()
    check('best scores are shared' in txt, 'score-flavoured footer text')
    if shots: page.screenshot(path='/home/claude/games/shots/board-ct3d-offline.png')
    page.click('#djppBoard .bd-btn:has-text("Back")'); page.wait_for_timeout(200)
    check(page.locator('#djppBoard').count() == 0, 'Back closes')
    # end a shift not joined → shared line hidden
    page.evaluate("localStorage.setItem('tc3d_tut','1')"); page.reload(); page.wait_for_timeout(2500)
    page.click('#tc-easy'); page.wait_for_timeout(1500)
    page.evaluate("__tc.end()")
    page.wait_for_timeout(500)
    check(page.evaluate("getComputedStyle(document.getElementById('tc-end')).display") == 'flex', 'end screen shows')
    check(page.evaluate("document.getElementById('tc-shared').style.display") == 'none', 'shared line hidden when not joined')
    # joined (offline): shared line says saved locally
    page.evaluate("localStorage.setItem('djpp.board.ct3d', JSON.stringify({joined:true, uid:'u1', name:'Tower', me:{name:'Tower',wins:0,streak:0,best:0,games:0,score:0,wk:DJPPBoard.weekId(new Date()),wkWins:0,wkBest:0,wkStreak:0,wkScore:0}, pending:[]}))")
    page.reload(); page.wait_for_timeout(2500)
    if page.locator('button:has-text("ROGER, GOT IT")').count(): page.click('button:has-text("ROGER, GOT IT")'); page.wait_for_timeout(300)   # the what's-new note
    page.click('#tc-easy'); page.wait_for_timeout(1500); page.evaluate("__tc.end()"); page.wait_for_timeout(400)
    check(page.locator('#tc-shared').inner_text().startswith('Shared Top 10:'), 'joined: shared line appears')
    page.wait_for_function("() => !/sending/.test(document.getElementById('tc-shared').textContent)", timeout=25000)
    check('back online' in page.locator('#tc-shared').inner_text(), 'offline: score kept locally, line says so')
    check(page.evaluate("DJPPBoard._state().pending.length") == 1 and page.evaluate("DJPPBoard._state().pending[0].score") is not None, 'score queued')
    check(not errors, f'no page errors ({errors[:3]})')
    if shots: page.screenshot(path='/home/claude/games/shots/board-ct3d-end.png')
    b.close(); srv.shutdown()

with sync_playwright() as p:
    for i, g in enumerate(['cribbage', 'euchre', 'ginrummy', 'pinochle']):
        kit_game(p, g, 8931 + i)
    ct3d(p, 8940)
print('\nALL PASS' if not fails else f'\n{len(fails)} FAIL: ' + '; '.join(fails))
sys.exit(1 if fails else 0)
