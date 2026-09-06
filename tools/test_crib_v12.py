#!/usr/bin/env python3
"""Cribbage v1.2 feature test: hints, coach, take back, difficulty settings.
usage: python3 test_crib_v12.py [--shots]"""
import sys, json, threading, http.server, socketserver, functools, pathlib
from playwright.sync_api import sync_playwright

folder = pathlib.Path('/home/claude/games/djpp-games-web/cribbage'); shots = '--shots' in sys.argv
PORT = 8891
Handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(folder))
class Q(socketserver.TCPServer): allow_reuse_address = True
srv = Q(('127.0.0.1', PORT), Handler); threading.Thread(target=srv.serve_forever, daemon=True).start()
URL = f'http://127.0.0.1:{PORT}/index.html'
fails = []
def check(cond, msg):
    print(('  ok   ' if cond else '  FAIL ') + msg)
    if not cond: fails.append(msg)

def wait_phase(page, phases, timeout=15000):
    page.wait_for_function(f"() => {json.dumps(phases)}.includes(__CRIB.state().phase) || __CRIB.state().over", timeout=timeout)
    return page.evaluate('__CRIB.state().phase')

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=2, is_mobile=True, has_touch=True)
    page = ctx.new_page()
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.on('console', lambda m: errors.append(m.text) if m.type == 'error' else None)
    page.goto(URL); page.wait_for_timeout(600)

    # --- settings row on the title overlay ---
    check(page.locator('#optsRow .seg').count() == 2, 'two setting groups (opponent, coach)')
    check(page.locator('#optsRow .seg[data-key=diff] button').count() == 3, 'three opponent levels')
    check(page.evaluate('__CRIB.SET.diff') == 'standard' and page.evaluate('__CRIB.SET.coach') == 'on', 'defaults standard / coach on')
    check(page.locator('#optsRow .seg[data-key=diff] button.on').inner_text().strip().lower().startswith('standard'), 'Standard button highlighted by default')
    if shots: page.screenshot(path='/home/claude/games/shots/cribbage-v12-title.png')
    page.click('#optsRow .seg[data-key=diff] button[data-v=relaxed]'); page.wait_for_timeout(100)
    check(page.evaluate('__CRIB.SET.diff') == 'relaxed', 'tapping Relaxed updates SET')
    check(json.loads(page.evaluate("localStorage.getItem('crib.settings')"))['diff'] == 'relaxed', 'setting persisted to localStorage')
    page.reload(); page.wait_for_timeout(600)
    check(page.evaluate('__CRIB.SET.diff') == 'relaxed', 'setting survives reload')
    check(page.locator('#optsRow .seg[data-key=diff] button.on').get_attribute('data-v') == 'relaxed', 'Relaxed highlighted after reload')
    page.click('#optsRow .seg[data-key=diff] button[data-v=standard]'); page.wait_for_timeout(100)
    check('v1.3' in page.locator('#ver').inner_text(), 'version label v1.3')

    # --- engine helpers ---
    r = page.evaluate("""(() => { const H=__CRIB; H.newGame(); const G=H.G;
        const opts=H.discardOptions(G.hand, G.dealer===0, H.unseenFor(0), 'sharp');
        let sorted=true; for(let i=1;i<opts.length;i++) if(opts[i].ev>opts[i-1].ev+1e-9) sorted=false;
        return {n:opts.length, sorted, keep:opts[0].keep.length, toss:opts[0].toss.length, unseen:H.unseenFor(0).length, phase:G.phase}; })()""")
    check(r['n'] == 15 and r['sorted'] and r['keep'] == 4 and r['toss'] == 2, f'discardOptions: 15 splits sorted by EV ({r})')
    check(r['unseen'] == 46, f'unseenFor(0) = 46 cards before the cut (got {r["unseen"]})')
    check(r['phase'] == 'discard', 'new game starts in discard')

    # --- hint in the discard phase ---
    st0 = page.evaluate('__CRIB.state()')
    page.evaluate('__CRIB.hint()'); page.wait_for_timeout(150)
    st = page.evaluate('__CRIB.state()')
    sel = page.evaluate('__CRIB.G.sel.slice()'); hidx = page.evaluate('__CRIB.G.hintIdx.slice()')
    check(st['hints'] == 1 and st0['hints'] == 0, 'hint counter increments')
    page.evaluate('__CRIB.hint()'); page.wait_for_timeout(50)
    check(page.evaluate('__CRIB.state().hints') == 1, 'tapping HINT again on the same decision is not counted twice')
    check(len(sel) == 2 and sel == hidx, f'hint selects the two suggested cards {sel}')
    check('Hint' in st['coach'] and 'crib' in st['coach'], 'coach line explains the discard hint')
    check(page.locator('#hand .card.hintmark').count() == 2, 'two cards carry the hint mark')
    check(page.locator('#actions .btn.gold').is_enabled(), 'SEND TO CRIB enabled after hint')
    check(page.locator('#actions .btn').count() == 2, 'discard phase shows HINT + SEND TO CRIB')
    if shots: page.screenshot(path='/home/claude/games/shots/cribbage-v12-hint-discard.png')

    # --- coach feedback after sending the hinted pair ---
    page.evaluate('__CRIB.confirmDiscard()'); page.wait_for_timeout(150)
    st = page.evaluate('__CRIB.state()')
    check('Coach' in st['coach'] and 'best possible keep' in st['coach'], 'coach confirms the best keep')
    check(page.evaluate('__CRIB.G.hintIdx') is None, 'hint marks cleared after discard')
    check(st['phase'] == 'cut', 'phase moves to cut')
    if shots: page.screenshot(path='/home/claude/games/shots/cribbage-v12-coach.png')

    # --- pegging: hint + take back (standard = 3 take-backs) ---
    ph = wait_phase(page, ['pegYou'])
    check(ph == 'pegYou', f'reached your pegging turn ({ph})')
    if ph == 'pegYou':
        before = page.evaluate("(() => { const G=__CRIB.G; return {left:G.left[0].length, oppLeft:G.left[1].length, pile:G.pile.length, count:G.count, scores:G.scores.slice()}; })()")
        page.evaluate('__CRIB.hint()'); page.wait_for_timeout(150)
        st = page.evaluate('__CRIB.state()')
        hc = page.evaluate('__CRIB.G.hintCard')
        check(st['hints'] == 2 and hc, f'pegging hint names a card ({hc})')
        check('Hint' in st['coach'] and 'play' in st['coach'], 'coach line explains the pegging hint')
        check(page.locator('#hand .card.hintmark').count() == 1, 'one card carries the hint mark')
        check(page.locator('#actions .btn').count() == 1, 'no TAKE BACK before the first play')
        if shots: page.screenshot(path='/home/claude/games/shots/cribbage-v12-hint-peg.png')
        # play the hinted card via tap-to-lift (two taps)
        idx = page.evaluate("(() => { const G=__CRIB.G; return G.left[0].findIndex(c => (c.r+':'+c.s)===G.hintCard); })()")
        check(idx >= 0, f'hinted card is in your hand (index {idx})')
        if idx < 0:
            idx = page.evaluate("(() => { const G=__CRIB.G; for(let i=0;i<G.left[0].length;i++){ if(G.left[0][i]._legal) return i; } return 0; })()")
        page.evaluate(f'__CRIB.tap({idx})'); page.wait_for_timeout(100)
        check(page.evaluate('__CRIB.state().phase') == 'pegYou' and page.evaluate('__CRIB.G.lift') == idx, 'first tap lifts the card')
        page.evaluate(f'__CRIB.tap({idx})'); page.wait_for_timeout(100)
        check(page.evaluate('__CRIB.state().undo') is True, 'snapshot stored when the card is played')
        check(page.evaluate('__CRIB.G.left[0].length') == before['left'] - 1, 'card left your hand')
        ph2 = wait_phase(page, ['pegYou'])
        st = page.evaluate('__CRIB.state()')
        if ph2 == 'pegYou' and st['undo']:
            tb = page.locator('#actions .btn', has_text='TAKE BACK')
            check(tb.count() == 1 and '(3)' in tb.inner_text(), f'TAKE BACK (3) offered on your next turn ({tb.inner_text() if tb.count() else "none"})')
            if shots: page.screenshot(path='/home/claude/games/shots/cribbage-v12-takeback.png')
            page.evaluate('__CRIB.takeBack()'); page.wait_for_timeout(150)
            after = page.evaluate("(() => { const G=__CRIB.G; return {left:G.left[0].length, oppLeft:G.left[1].length, pile:G.pile.length, count:G.count, scores:G.scores.slice(), tb:G.takebacks, undo:!!G.undo, phase:G.phase}; })()")
            check(after['left'] == before['left'] and after['oppLeft'] == before['oppLeft'], 'both hands restored')
            check(after['pile'] == before['pile'] and after['count'] == before['count'], 'pile and count restored')
            check(after['scores'] == before['scores'], 'scores restored')
            check(after['tb'] == 1 and after['undo'] is False and after['phase'] == 'pegYou', f'take-back counted, snapshot cleared, your turn again ({after})')
            check('Taken back' in page.evaluate('__CRIB.state().coach') and '2 left' in page.evaluate('__CRIB.state().coach'), 'coach reports the take-back and remaining count')
            check(page.locator('#actions .btn', has_text='TAKE BACK').count() == 0, 'TAKE BACK hidden until the next play')
            check(page.locator('#pile .card').count() == before['pile'], 'pile re-rendered')
        else:
            print(f'  skip take-back checks (phase {ph2}, undo {st["undo"]}) — opponent answer ended the round')

    # --- Sharp: no take-backs at all ---
    page.evaluate("__CRIB.SET.diff='sharp'; __CRIB.applySet();")
    page.evaluate('__CRIB.newGame()'); page.wait_for_timeout(100)
    page.evaluate('__CRIB.hint(); __CRIB.confirmDiscard();')
    ph = wait_phase(page, ['pegYou'])
    if ph == 'pegYou':
        idx = page.evaluate("(() => { const G=__CRIB.G; for(let i=0;i<G.left[0].length;i++){ if(G.left[0][i]._legal) return i; } return 0; })()")
        page.evaluate(f'__CRIB.tap({idx}); __CRIB.tap({idx});'); page.wait_for_timeout(100)
        check(page.evaluate('__CRIB.state().undo') is False, 'Sharp: no snapshot / no take-back')
        ph2 = wait_phase(page, ['pegYou'])
        if ph2 == 'pegYou':
            check(page.locator('#actions .btn', has_text='TAKE BACK').count() == 0, 'Sharp: no TAKE BACK button')
    # AI helpers behave at each level
    ok = page.evaluate("""(() => { const H=__CRIB, G=H.G; if(!G.left) return 'noleft';
        const hand=G.left[1].length?G.left[1]:G.left[0]; if(!hand.length) return 'empty';
        const pile=[], count=0;
        const a=H.aiPegPlay(hand,pile,count,'relaxed',null), b=H.aiPegPlay(hand,pile,count,'standard',null), c=H.aiPegPlay(hand,pile,count,'sharp',H.unseenFor(1));
        return (a&&b&&c&&hand.includes(a)&&hand.includes(b)&&hand.includes(c))?'ok':'bad'; })()""")
    check(ok == 'ok', f'aiPegPlay returns a legal card at every level ({ok})')

    # --- end screen + stat extras (win vs Sharp, no hints) ---
    page.evaluate("__CRIB.SET.diff='sharp'; __CRIB.newGame(); __CRIB.G.hints=0; __CRIB.G.scores=[121,70]; __CRIB.G.winner=0; __CRIB.G.over=true; __CRIB.endGame();")
    page.wait_for_timeout(300)
    rb = page.locator('#resultbox').inner_text()
    check('Opponent: Sharp' in rb and 'no hints' in rb, f'end screen names opponent level + hint use ({rb.strip()[:80]})')
    st = page.evaluate('DJPP.stats()')
    check(st['extras'].get('sharpWins') == 1 and st['extras'].get('noHintWins') == 1 and st['extras'].get('skunksGiven') == 1, f'extras recorded {st["extras"]}')
    page.evaluate("__CRIB.SET.diff='standard'; __CRIB.newGame(); __CRIB.G.hints=3; __CRIB.G.scores=[121,100]; __CRIB.G.winner=0; __CRIB.G.over=true; __CRIB.endGame();")
    page.wait_for_timeout(300)
    rb = page.locator('#resultbox').inner_text()
    check('Opponent: Standard' in rb and 'hints used: 3' in rb, 'end screen shows hint count')
    st = page.evaluate('DJPP.stats()')
    check(st['extras'].get('sharpWins') == 1 and st['extras'].get('noHintWins') == 1, 'hinted standard win does not add to sharp/no-hint tallies')
    if shots: page.screenshot(path='/home/claude/games/shots/cribbage-v12-end.png')

    # --- coach off: no feedback after discard ---
    page.evaluate("__CRIB.SET.coach='off'; __CRIB.newGame(); __CRIB.G.sel=[0,1]; __CRIB.confirmDiscard();"); page.wait_for_timeout(100)
    check(page.evaluate('__CRIB.state().coach') == '', 'coach off: silent after discard')
    page.evaluate("__CRIB.SET.coach='on'; __CRIB.newGame(); __CRIB.G.sel=[0,1]; __CRIB.confirmDiscard();"); page.wait_for_timeout(100)
    check('Coach' in page.evaluate('__CRIB.state().coach'), 'coach on: feedback after an un-hinted discard')

    # short viewport (landscape phone) — hint/coach must not push the hand off-screen
    page.set_viewport_size({'width': 844, 'height': 390}); page.evaluate('__CRIB.newGame(); __CRIB.hint();'); page.wait_for_timeout(200)
    fits = page.evaluate("(() => { const cs=[...document.querySelectorAll('#hand .card')]; if(!cs.length) return false; return cs.every(c => { const r=c.getBoundingClientRect(); return r.bottom <= innerHeight+1 && r.top >= 0; }); })()")
    check(fits, 'landscape: hinted hand stays on screen')
    if shots: page.screenshot(path='/home/claude/games/shots/cribbage-v12-landscape.png')

    check(not errors, 'no page errors: ' + ('; '.join(errors)[:300] if errors else 'clean'))
    b.close()
srv.shutdown()
print('\n' + ('ALL PASS' if not fails else f'{len(fails)} FAIL: ' + ' | '.join(fails)))
sys.exit(1 if fails else 0)
