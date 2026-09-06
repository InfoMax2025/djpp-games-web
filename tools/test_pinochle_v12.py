#!/usr/bin/env python3
"""Pinochle v1.2 feature test: options row, classic 1500 scoring, stuck-dealer toggle, pass-4-cards, bid help.
usage: python3 test_pinochle_v12.py [--shots] [--quick]"""
import sys, json, threading, http.server, socketserver, functools, pathlib, time
from playwright.sync_api import sync_playwright

folder = pathlib.Path('/home/claude/games/djpp-games-web/pinochle'); shots = '--shots' in sys.argv; quick = '--quick' in sys.argv
PORT = 8893
class H(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
class Q(socketserver.TCPServer): allow_reuse_address = True
srv = Q(('127.0.0.1', PORT), functools.partial(H, directory=str(folder))); threading.Thread(target=srv.serve_forever, daemon=True).start()
URL = f'http://127.0.0.1:{PORT}/index.html'
fails = []
def check(cond, msg):
    print(('  ok   ' if cond else '  FAIL ') + msg)
    if not cond: fails.append(msg)

# card literals: v 0=9 1=J 2=Q 3=K 4=10 5=A ; s 0=♠ 1=♥ 2=♦ 3=♣
def card(v, s): return {'v': v, 's': s}
RUN_S = [card(5,0), card(4,0), card(3,0), card(2,0), card(1,0)]   # A 10 K Q J of spades

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=2, is_mobile=True, has_touch=True)
    page = ctx.new_page()
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.on('console', lambda m: errors.append(m.text) if m.type == 'error' else None)
    page.goto(URL); page.wait_for_timeout(600)

    def fresh(settings):
        """reload (kills timers), apply settings, start a game and freeze its auction so tests can drive state by hand"""
        page.reload(); page.wait_for_timeout(500)
        page.evaluate(f"Object.assign(__PIN.SET, {json.dumps(settings)}); __PIN.applySet(); __PIN.newGame(); __PIN.G.over=true;")
        page.wait_for_timeout(2400)   # let the stray AI auction timer + its pop settle
        page.evaluate("(() => { const G=__PIN.G; G.over=false; G.active=[true,true,true,true]; G.anyBid=false; G.highBid=__PIN.minBid()-__PIN.SF(); G.highP=-1; G.phase='auction'; document.getElementById('bidPanel').style.display='none'; })()")

    # ---- options row ----
    check(page.locator('#optsRow .seg').count() == 4, 'four option groups')
    st = page.evaluate('__PIN.SET')
    check(st == {'scoring': '150', 'stuck': 'on', 'pass': 'off', 'help': 'on'}, f'defaults {st}')
    page.click('#optsRow .seg[data-key=scoring] button[data-v="1500"]'); page.click('#optsRow .seg[data-key=pass] button[data-v=on]'); page.wait_for_timeout(100)
    check(json.loads(page.evaluate("localStorage.getItem('pin.settings')")) == {'scoring': '1500', 'stuck': 'on', 'pass': 'on', 'help': 'on'}, 'settings persisted')
    check('1500' in page.locator('#boardSub').inner_text(), 'board line follows the scoring option')
    page.reload(); page.wait_for_timeout(600)
    check(page.evaluate('__PIN.SET.scoring') == '1500' and page.locator('#optsRow .seg[data-key=pass] button.on').get_attribute('data-v') == 'on', 'settings survive reload')
    check('v1.3' in page.locator('#ver').inner_text(), 'version v1.3')
    if shots: page.screenshot(path='/home/claude/games/shots/pinochle-v12-title.png')

    # ---- classic scoring maths ----
    r = page.evaluate(f"""(() => {{ const hand={json.dumps(RUN_S + [card(0,0), card(5,1), card(5,2), card(5,3), card(2,0), card(1,2), card(3,1)])};
        const m=__PIN.meldScore(hand, 0); return {{sf:__PIN.SF(), minBid:__PIN.minBid(), target:__PIN.target(), meld:m.total, lines:m.lines.map(l=>l.pts),
        ctr:__PIN.counterPoints([{json.dumps(card(5,0))},{json.dumps(card(4,1))},{json.dumps(card(1,1))}], true)}}; }})()""")
    # run 15 + dix 1 + aces around 10 + pinochle (J♦ Q♠) 4 + (extra Q♠ makes a 2nd royal? no: K♠ once) → 30 base
    check(r['sf'] == 10 and r['minBid'] == 200 and r['target'] == 1500, f'classic scoring: x10, min bid 200, game to 1500 ({r})')
    check(r['meld'] == 300 and all(x % 10 == 0 for x in r['lines']), f'meld x10 in classic scoring (total {r["meld"]}, lines {r["lines"]})')
    check(r['ctr'] == 30, f'counters x10 incl. last trick ({r["ctr"]})')
    page.evaluate("__PIN.SET.scoring='150'; __PIN.applySet();")
    r2 = page.evaluate(f"__PIN.meldScore({json.dumps(RUN_S + [card(0,0), card(5,1), card(5,2), card(5,3), card(2,0), card(1,2), card(3,1)])}, 0).total")
    check(r2 == 30 and page.evaluate('__PIN.target()') == 150, f'standard scoring unchanged (meld {r2})')
    check('150' in page.locator('#boardSub').inner_text(), 'board line back to 150')

    # ---- bid panel: classic increments + bid help off ----
    fresh({'scoring': '1500', 'help': 'on', 'stuck': 'on', 'pass': 'off'})
    page.evaluate("__PIN.showBidPanel()")
    btns = page.locator('#bpBtns .bigbtn').all_inner_texts()
    check(btns[:2] == ['BID 200', 'BID 240'] and 'PASS' in btns, f'classic bid buttons {btns}')
    check('worth about' in page.locator('#bpSub').inner_text() and page.locator('#bpBtns .bigbtn.sug').count() == 1, 'bid help shows the estimate + suggested button')
    check('worth 10' in page.locator('#bpNote').inner_text(), 'note explains counters are worth 10')
    if shots: page.screenshot(path='/home/claude/games/shots/pinochle-v12-bid1500.png')
    page.evaluate("__PIN.SET.help='off'; __PIN.showBidPanel()")
    check('worth about' not in page.locator('#bpSub').inner_text() and page.locator('#bpBtns .bigbtn.sug').count() == 0, 'bid help off: no estimate, no suggestion')
    page.evaluate("document.getElementById('bidPanel').style.display='none'")
    ai = page.evaluate("(() => { let hi=0; for(let i=0;i<40;i++){ const h=__PIN.G.hands[1]; const b=__PIN.aiBidTurn(h, 190+10*i); if(b>0) return b; } return -1; })()")
    check(ai == -1 or ai % 10 == 0, f'AI bids in tens under classic scoring ({ai})')

    # ---- stuck dealer ----
    fresh({'scoring': '150', 'help': 'on', 'stuck': 'on', 'pass': 'off'})
    page.evaluate("(() => { const G=__PIN.G; G.dealer=3; G.active=[false,false,false,true]; __PIN.auctionTurn(3, 0); })()")
    page.wait_for_timeout(100)
    g = page.evaluate("(() => { const G=__PIN.G; return {declarer:G.declarer, bid:G.bid, phase:G.phase}; })()")
    check(g['declarer'] == 3 and g['bid'] == 20 and g['phase'] == 'trump', f'stuck ON: dealer forced to bid 20 ({g})')
    fresh({'scoring': '150', 'help': 'on', 'stuck': 'off', 'pass': 'off'})
    page.evaluate("(() => { const G=__PIN.G; G.dealer=0; G.active=[true,false,false,false]; __PIN.auctionTurn(0, 0); })()")
    page.wait_for_timeout(100)
    check(page.locator('#bidPanel').is_visible() and page.evaluate('__PIN.G.declarer') == -1, 'stuck OFF: the dealer still gets to choose')
    d0 = page.evaluate('__PIN.G.dealer')
    page.evaluate("__PIN.youPass()")          # 4th pass → "You pass" pop → "Everyone passed" pop → new deal
    page.wait_for_timeout(1600)
    check('Everyone passed' in page.locator('#pop').inner_text(), 'everyone passed → throw-in message')
    page.wait_for_timeout(1700)
    check(page.evaluate('__PIN.G.dealer') == (d0 + 1) % 4 and page.evaluate('__PIN.G.hands[0].length') == 12, 'hand redealt to the next dealer')
    page.evaluate("__PIN.G.over=true")

    # ---- pass 4 cards ----
    # (a) you won the bid: partner passes 4, you pass 4 back
    fresh({'scoring': '150', 'help': 'on', 'stuck': 'on', 'pass': 'on'})
    page.evaluate(f"""(() => {{ const G=__PIN.G; G.declarer=0; G.bid=22; G.bidTeam=0; G.trump=0;
        G.hands[2]={json.dumps([card(5,0), card(4,0), card(5,1), card(0,3), card(0,2), card(1,3), card(2,1), card(3,2), card(1,1), card(0,0), card(2,3), card(4,3)])};
        __PIN.startPass(); }})()""")
    page.wait_for_timeout(150)
    check(page.evaluate('__PIN.G.hands[0].length') == 16 and page.evaluate('__PIN.G.hands[2].length') == 8, 'partner passed you 4 cards (16 in hand)')
    got = page.evaluate("__PIN.G.hands[0].map(c=>c.v+':'+c.s)")
    check(all(k in got for k in ['5:0', '4:0', '5:1', '0:0']), f'partner passed its trump + ace first ({sorted(set(got) - set(["1:3"]))[:6]}…)')
    page.wait_for_timeout(1500)
    st = page.evaluate('__PIN.state()')
    check(st['phase'] == 'pass' and st['passBtn'] and 'pass back' in st['hint'], f'pass-back stage: button + hint ({st["hint"]})')
    fits = page.evaluate("(() => { const cs=[...document.querySelectorAll('#hand .card')]; return cs.length===16 && cs.every(c => { const r=c.getBoundingClientRect(); return r.left>=-1 && r.right<=innerWidth+1 && r.bottom<=innerHeight+1; }); })()")
    check(fits, '16-card hand fits the phone screen')
    if shots: page.screenshot(path='/home/claude/games/shots/pinochle-v12-pass.png')
    page.evaluate("__PIN.tap(0); __PIN.tap(1); __PIN.tap(2);")
    check(page.evaluate('__PIN.state().sel') == [0, 1, 2] and page.evaluate("document.getElementById('passBtn').disabled") is True, '3 picked → button still disabled')
    page.evaluate("__PIN.tap(2);")
    check(page.evaluate('__PIN.state().sel') == [0, 1], 'tapping a picked card un-picks it')
    page.evaluate("__PIN.tap(5); __PIN.tap(9); __PIN.tap(10);")
    check(page.evaluate('__PIN.state().sel') == [0, 1, 5, 9] and page.evaluate("document.getElementById('passBtn').disabled") is False, 'max 4 picks, button enabled at 4')
    check(page.locator('#hand .card.lifted').count() == 4, 'picked cards are lifted')
    page.evaluate("__PIN.confirmPass()"); page.wait_for_timeout(150)
    check(page.evaluate('__PIN.G.hands[0].length') == 12 and page.evaluate('__PIN.G.hands[2].length') == 12 and page.evaluate('__PIN.state().passBtn') is False, 'passed 4 back: 12 + 12, button gone')
    page.wait_for_timeout(1600)
    check(page.evaluate('__PIN.state().meldPanel') is True and page.evaluate("__PIN.G.phase") == 'meld', 'meld follows the pass')
    # (b) partner won the bid: you pass 4 over, partner passes 4 back (meld-aware)
    fresh({'scoring': '150', 'help': 'on', 'stuck': 'on', 'pass': 'on'})
    page.evaluate(f"""(() => {{ const G=__PIN.G; G.declarer=2; G.bid=25; G.bidTeam=0; G.trump=0;
        G.hands[2]={json.dumps(RUN_S + [card(1,2), card(2,0), card(0,3), card(0,2), card(1,3), card(2,1), card(3,2)])};
        __PIN.startPass(); }})()""")
    page.wait_for_timeout(150)
    st = page.evaluate('__PIN.state()')
    check(st['phase'] == 'pass' and st['passBtn'] and 'pass over' in st['hint'] and page.evaluate('__PIN.G.hands[0].length') == 12, 'give stage: pick 4 to pass over')
    page.evaluate("__PIN.tap(0); __PIN.tap(1); __PIN.tap(2); __PIN.tap(3); __PIN.confirmPass();"); page.wait_for_timeout(150)
    kept = page.evaluate("__PIN.G.hands[2].map(c=>c.v+':'+c.s)")
    check(page.evaluate('__PIN.G.hands[0].length') == 12 and page.evaluate('__PIN.G.hands[2].length') == 12, 'partner passed 4 back: 12 + 12')
    check(all(k in kept for k in ['5:0', '4:0', '3:0', '2:0', '1:0', '1:2']), f'partner kept its run + pinochle when passing back')
    page.wait_for_timeout(1600)
    check(page.evaluate("__PIN.G.phase") == 'meld', 'meld follows the pass (partner declarer)')
    # (c) the other team passes among themselves
    fresh({'scoring': '150', 'help': 'on', 'stuck': 'on', 'pass': 'on'})
    page.evaluate("(() => { const G=__PIN.G; G.declarer=1; G.bid=21; G.bidTeam=1; G.trump=2; __PIN.startPass(); })()")
    page.wait_for_timeout(150)
    sizes = page.evaluate("__PIN.G.hands.map(h=>h.length)")
    check(sizes == [12, 12, 12, 12] and 'pass 4 cards' in page.locator('#pop').inner_text() and page.evaluate('__PIN.state().passBtn') is False, f'West/East pass silently ({sizes})')
    page.wait_for_timeout(1600)
    check(page.evaluate("__PIN.G.phase") == 'meld', 'meld follows the AI pass')
    # aiPassBack never breaks a run when junk is available
    r = page.evaluate(f"""(() => {{ const hand={json.dumps(RUN_S + [card(0,1), card(0,2), card(1,1), card(1,3), card(2,1), card(2,3), card(3,1), card(0,3), card(4,1), card(4,2), card(3,3)])};
        const back=__PIN.aiPassBack(hand, 0); return back.map(c=>c.v+':'+c.s); }})()""")
    check(len(r) == 4 and not any(k in r for k in ['5:0', '4:0', '3:0', '2:0', '1:0']), f'aiPassBack keeps the trump run ({r})')

    # ---- full game with passing + classic scoring, driving your seat through the hooks ----
    if not quick:
        page.reload(); page.wait_for_timeout(500)
        page.evaluate("Object.assign(__PIN.SET, {scoring:'1500', stuck:'on', pass:'on', help:'on'}); __PIN.applySet(); __PIN.newGame();")
        deadline = time.time() + 420; acts = {'bid': 0, 'pass': 0, 'trump': 0, 'passcards': 0, 'plays': 0, 'next': 0}
        last_hint = ''
        while time.time() < deadline:
            s = page.evaluate("""(() => { const S=__PIN.state(); const G=__PIN.G; S.hands=G.hands?G.hands.map(h=>h.length):null; S.mpNext=getComputedStyle(document.getElementById('mpNext')).display!=='none'; return S; })()""")
            if s['overlay'] and s['over']: break
            if s['bidPanel']:
                page.evaluate("(() => { const bs=[...document.querySelectorAll('#bpBtns .bigbtn')]; const sug=bs.find(b=>b.classList.contains('sug'))||bs[bs.length-1]; sug.click(); })()"); acts['bid'] += 1
            elif s['trumpPanel']:
                page.evaluate("(() => { const bs=[...document.querySelectorAll('#tpBtns .suitbtn')]; (bs.find(b=>b.classList.contains('sug'))||bs[0]).click(); })()"); acts['trump'] += 1
            elif s['meldPanel'] and s['mpNext']:
                page.evaluate("__PIN.next()"); acts['next'] += 1
            elif s['phase'] == 'pass' and s['passBtn']:
                page.evaluate("(() => { const G=__PIN.G; G.sel=[]; for(let i=0;i<4;i++) __PIN.tap(G.hands[0].length-1-i); __PIN.confirmPass(); })()"); acts['passcards'] += 1
            elif s['phase'] == 'playYou':
                page.evaluate("(() => { const G=__PIN.G; const L=__PIN.legalPlays(G.hands[0], G.trick, G.trump); const c=L[Math.floor(Math.random()*L.length)]; const idx=G.hands[0].findIndex(x=>x.v===c.v&&x.s===c.s); __PIN.tap(idx); __PIN.tap(idx); })()"); acts['plays'] += 1
            page.wait_for_timeout(120)
        sc = page.evaluate("__PIN.G.scores.slice()")
        check(page.evaluate('__PIN.G.over') is True and max(sc) >= 1500, f'full classic game with passing finished {sc} ({acts})')
        check(acts['passcards'] > 0, 'you passed cards at least once during the game')
        rb = page.locator('#resultbox').inner_text()
        check('Scoring to 1500' in rb and 'passing 4 cards' in rb, 'result box names the house rules in play')
        if shots: page.screenshot(path='/home/claude/games/shots/pinochle-v12-end.png')

    check(not errors, 'no page errors: ' + ('; '.join(errors)[:300] if errors else 'clean'))
    b.close()
srv.shutdown()
print('\n' + ('ALL PASS' if not fails else f'{len(fails)} FAIL: ' + ' | '.join(fails)))
sys.exit(1 if fails else 0)
