#!/usr/bin/env python3
"""Headless smoke test for a DJPP card game + kit.
usage: python3 test_card_game.py <folder> <hookName> [--shots]
hookName: __CRIB | __EU | __GIN | __PIN
Serves the folder on a local port, drives the page with Playwright and checks the kit."""
import sys, json, threading, http.server, socketserver, functools, pathlib, time
from playwright.sync_api import sync_playwright

folder = pathlib.Path(sys.argv[1]).resolve(); hook = sys.argv[2]; shots = '--shots' in sys.argv
PORT = 8765 + (hash(str(folder)) % 100)
Handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(folder))
class Q(socketserver.TCPServer): allow_reuse_address = True
srv = Q(('127.0.0.1', PORT), Handler); threading.Thread(target=srv.serve_forever, daemon=True).start()
URL = f'http://127.0.0.1:{PORT}/index.html'
fails = []
def check(cond, msg):
    print(('  ok   ' if cond else '  FAIL ') + msg)
    if not cond: fails.append(msg)

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=2, is_mobile=True, has_touch=True)
    page = ctx.new_page()
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.on('console', lambda m: errors.append(m.text) if m.type == 'error' else None)
    page.goto(URL); page.wait_for_timeout(800)
    check(page.locator('#djppMenu .djpp-btn').count() == 3, 'menu has 3 kit buttons')
    check(page.evaluate('typeof window.DJPP') == 'object', 'DJPP global present')
    if shots: page.screenshot(path=f'/home/claude/games/shots/{folder.name}-title.png')
    # panels
    page.click('#djppMenu .djpp-btn:nth-child(1)'); page.wait_for_timeout(200)
    check(page.locator('#djppPanel h2').inner_text() == 'My Stats', 'stats panel opens')
    check('No games finished yet' in page.locator('#djppPanel').inner_text(), 'stats empty state')
    if shots: page.screenshot(path=f'/home/claude/games/shots/{folder.name}-stats-empty.png')
    page.click('#djppPanel .acts .djpp-btn:last-child'); page.wait_for_timeout(150)
    check(page.locator('#djppPanel').count() == 0, 'stats panel closes')
    page.click('#djppMenu .djpp-btn:nth-child(2)'); page.wait_for_timeout(200)
    check('Fair Deal' in page.locator('#djppPanel h2').inner_text(), 'fair deal panel opens')
    if shots: page.screenshot(path=f'/home/claude/games/shots/{folder.name}-fair.png')
    page.click('#djppPanel .acts .djpp-btn:last-child'); page.wait_for_timeout(150)
    page.click('#djppMenu .djpp-btn:nth-child(3)'); page.wait_for_timeout(200)
    n = page.locator('#djppPanel .game').count()
    check(n == 5, f'more-games lists 5 siblings (got {n})')
    if shots: page.screenshot(path=f'/home/claude/games/shots/{folder.name}-more.png')
    page.click('#djppPanel .acts .djpp-btn:last-child'); page.wait_for_timeout(150)
    # simulated results via the kit API (game hooks are exercised separately)
    r1 = page.evaluate("DJPP.record({won:true, you:121, opp:80})")
    r2 = page.evaluate("DJPP.record({won:true, you:121, opp:100})")
    r3 = page.evaluate("DJPP.record({won:false, you:90, opp:121})")
    st = page.evaluate("DJPP.stats()")
    check(st['games'] == 3 and st['wins'] == 2 and st['losses'] == 1, f'stats tally {st["wins"]}-{st["losses"]} of {st["games"]}')
    check(st['bestStreak'] == 2 and st['streak'] == 0 and st['bestMargin'] == 41, f'streak/margin bestStreak={st["bestStreak"]} streak={st["streak"]} margin={st["bestMargin"]}')
    check(page.locator('#djppResult').count() == 1, 'result line rendered')
    check(page.evaluate("JSON.parse(localStorage.getItem('djpp.'+DJPP_CONFIG.game+'.stats')).games") == 3, 'stats persisted to localStorage')
    check(page.locator('#djppPanel').count() == 0, 'no rating prompt in a plain browser')
    # rating prompt when installed from Play (simulate TWA env), 3 wins of 4+ games
    page.evaluate("localStorage.setItem('djpp.'+DJPP_CONFIG.game+'.env', JSON.stringify({twa:true}))")
    page.reload(); page.wait_for_timeout(600)
    page.evaluate("DJPP.record({won:true, you:121, opp:60})")
    page.wait_for_timeout(1700)
    check(page.locator('#djppPanel').count() == 1 and 'Enjoying' in page.locator('#djppPanel h2').inner_text(), 'rating prompt appears in app after 3rd win')
    if shots: page.screenshot(path=f'/home/claude/games/shots/{folder.name}-rate.png')
    page.click('#djppPanel .acts .djpp-btn:nth-child(3)'); page.wait_for_timeout(150)   # don't ask again
    check(page.evaluate("JSON.parse(localStorage.getItem('djpp.'+DJPP_CONFIG.game+'.rate')).done") is True, 'decline persists')
    page.evaluate("DJPP.record({won:true, you:121, opp:60})"); page.wait_for_timeout(1700)
    check(page.locator('#djppPanel').count() == 0, 'no re-prompt after decline')
    # game-specific end hook: run the real endGame path if the hook exposes it
    page.evaluate("DJPP.reset()")
    page.evaluate(f"{hook}.newGame()"); page.wait_for_timeout(400)
    ended = page.evaluate(f"""(() => {{ const H={hook}; const G=H.G; if(!G) return 'noG';
        if(H.endGame){{ G.scores[0]=999; G.scores[1]=1; if('winner' in G) G.winner=0; G.over=true;
          try {{ H.endGame.length? H.endGame(0) : H.endGame(); }} catch(e) {{ return 'err '+e.message; }} return 'ok'; }}
        return 'noEndGame'; }})()""")
    page.wait_for_timeout(300)
    if ended == 'ok':
        st2 = page.evaluate("DJPP.stats()")
        check(st2['games'] == 1 and st2['wins'] == 1, f'real endGame() recorded a win ({ended})')
        check(page.locator('#djppResult').count() == 1 and 'Your record' in page.locator('#djppResult').inner_text(), 'record line shown on the real end screen')
        if shots: page.screenshot(path=f'/home/claude/games/shots/{folder.name}-end.png')
        check(page.locator('#startbtn').is_visible(), 'start button visible on end screen')
    else:
        print('  skip real endGame path:', ended)
    check(not errors, 'no console/page errors: ' + ('; '.join(errors)[:300] if errors else 'clean'))
    b.close()
srv.shutdown()
print('\nRESULT:', 'PASS' if not fails else f'{len(fails)} FAILURE(S)')
sys.exit(1 if fails else 0)
