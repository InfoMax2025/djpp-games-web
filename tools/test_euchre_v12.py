#!/usr/bin/env python3
"""Euchre v1.2 feature test: options row, stick-the-dealer toggle, farmer's hand, defend alone, partner AI + tips.
usage: python3 test_euchre_v12.py [--shots]"""
import sys, json, threading, http.server, socketserver, functools, pathlib, time
from playwright.sync_api import sync_playwright

folder = pathlib.Path('/home/claude/games/djpp-games-web/euchre'); shots = '--shots' in sys.argv
PORT = 8892
class H(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
class Q(socketserver.TCPServer): allow_reuse_address = True
srv = Q(('127.0.0.1', PORT), functools.partial(H, directory=str(folder))); threading.Thread(target=srv.serve_forever, daemon=True).start()
URL = f'http://127.0.0.1:{PORT}/index.html'
fails = []
def check(cond, msg):
    print(('  ok   ' if cond else '  FAIL ') + msg)
    if not cond: fails.append(msg)
C = lambda r, s: {'s': s, 'r': r}   # card helper

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=2, is_mobile=True, has_touch=True)
    page = ctx.new_page()
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.on('console', lambda m: errors.append(m.text) if m.type == 'error' else None)
    page.goto(URL); page.wait_for_timeout(600)

    # ---- options row ----
    check(page.locator('#optsRow .seg').count() == 4, 'four option groups')
    st = page.evaluate('__EU.SET')
    check(st == {'stick': 'on', 'defend': 'off', 'farmer': 'off', 'tips': 'on'}, f'defaults {st}')
    check(page.locator('#optsRow .seg[data-key=stick] button.on').get_attribute('data-v') == 'on', 'Stick the dealer highlighted On')
    page.click('#optsRow .seg[data-key=farmer] button[data-v=on]'); page.click('#optsRow .seg[data-key=defend] button[data-v=on]'); page.wait_for_timeout(100)
    check(json.loads(page.evaluate("localStorage.getItem('euchre.settings')")) == {'stick': 'on', 'defend': 'on', 'farmer': 'on', 'tips': 'on'}, 'settings persisted')
    page.reload(); page.wait_for_timeout(600)
    check(page.evaluate('__EU.SET.farmer') == 'on' and page.locator('#optsRow .seg[data-key=defend] button.on').get_attribute('data-v') == 'on', 'settings survive reload')
    check('v1.3' in page.locator('#ver').inner_text(), 'version v1.3')
    check('no ads' in page.locator('#howBox').inner_text() and 'ads only' not in page.locator('#howBox').inner_text(), 'how-to says no ads')
    if shots: page.screenshot(path='/home/claude/games/shots/euchre-v12-title.png')

    # ---- stick the dealer toggle: round-2 prompt for a human dealer ----
    page.evaluate("document.getElementById('overlay').style.display='none'; __EU.newGame(); __EU.startHand(); __EU.G.trump='S';")   # trump set => the scheduled bidStep is a no-op
    page.wait_for_timeout(800)
    page.evaluate("__EU.G.dealer=0; __EU.G.bidRound=2; __EU.G.up={s:'H',r:'9'}; __EU.humanBid();")
    txt = page.locator('#promptBtns').inner_text()
    check(page.locator('#promptBtns .btn').count() == 3 and 'Pass' not in txt and 'stuck' in page.locator('#promptQ').inner_text(), 'stick ON: dealer must call (no Pass)')
    page.evaluate("__EU.hidePrompt(); __EU.SET.stick='off'; __EU.humanBid();")
    check(page.locator('#promptBtns .btn').count() == 4 and 'Pass' in page.locator('#promptBtns').inner_text(), 'stick OFF: dealer may pass')
    page.evaluate("__EU.hidePrompt(); __EU.SET.stick='on';")

    # ---- farmer's hand ----
    page.evaluate("""(() => { const G=__EU.G; __EU.SET.farmer='on';
        G.dealer=3; G.trump=null; G.hands[0]=[{s:'H',r:'9'},{s:'D',r:'9'},{s:'C',r:'10'},{s:'S',r:'A'},{s:'S',r:'K'}];
        G.hands[1]=[{s:'H',r:'A'},{s:'D',r:'A'},{s:'C',r:'A'},{s:'S',r:'Q'},{s:'H',r:'K'}];
        G.kitty=[{s:'S',r:'J'},{s:'C',r:'J'},{s:'D',r:'Q'}]; window.__farmerDone=false;
        __EU.farmerCheck(()=>{ window.__farmerDone=true; }); })()""")
    page.wait_for_timeout(200)
    check(page.locator('#prompt').is_visible() and "Farmer" in page.locator('#promptQ').inner_text(), 'farmer prompt offered to you')
    if shots: page.screenshot(path='/home/claude/games/shots/euchre-v12-farmer.png')
    page.click('#promptBtns .btn.gold'); page.wait_for_timeout(200)
    hand = page.evaluate("__EU.G.hands[0].map(c=>c.r+c.s).sort()")
    check(sorted(hand) == sorted(['AS', 'KS', 'JS', 'JC', 'QD']), f'low cards swapped for the buried three {hand}')
    check(page.evaluate("__EU.G.kitty.map(c=>c.r+c.s).sort()") == sorted(['9H', '9D', '10C']), 'the 9s/10s went to the kitty')
    check(page.evaluate("__EU.G.farmer") == 0 and 'Farmer' in page.locator('#toast').inner_text(), 'farmer recorded + toast')
    page.wait_for_timeout(1300)
    check(page.evaluate('window.__farmerDone') is True, 'bidding continues after the swap')
    # AI farmer: West holds three 10s, you don't qualify
    page.evaluate("""(() => { const G=__EU.G; G.dealer=3; G.farmer=-1;
        G.hands[0]=[{s:'H',r:'A'},{s:'D',r:'9'},{s:'C',r:'K'},{s:'S',r:'A'},{s:'S',r:'K'}];
        G.hands[1]=[{s:'H',r:'10'},{s:'D',r:'10'},{s:'C',r:'10'},{s:'S',r:'Q'},{s:'H',r:'K'}];
        G.kitty=[{s:'S',r:'J'},{s:'C',r:'J'},{s:'D',r:'Q'}]; window.__farmerDone=false;
        __EU.farmerCheck(()=>{ window.__farmerDone=true; }); })()""")
    page.wait_for_timeout(150)
    check(page.evaluate("__EU.G.farmer") == 1 and page.evaluate("__EU.G.hands[1].map(c=>c.r).filter(r=>r==='10').length") == 0, 'AI (West) swaps its three 10s')
    check(page.locator('#prompt').is_hidden(), 'no prompt for an AI swap')
    # keep my hand
    page.evaluate("""(() => { const G=__EU.G; G.dealer=3; G.farmer=-1;
        G.hands[0]=[{s:'H',r:'9'},{s:'D',r:'9'},{s:'C',r:'10'},{s:'S',r:'A'},{s:'S',r:'K'}]; window.__farmerDone=false;
        __EU.farmerCheck(()=>{ window.__farmerDone=true; }); })()""")
    page.wait_for_timeout(150); page.click('#promptBtns .btn.ghost'); page.wait_for_timeout(100)
    check(page.evaluate("__EU.G.farmer") == -1 and page.evaluate('window.__farmerDone') is True, 'Keep my hand leaves the hand alone')

    # ---- partner AI: never overtake your winning ace ----
    r = page.evaluate("""(() => { const G=__EU.G; G.trump='S'; G.out=[]; G.ledSuit='H'; G.resolving=false;
        G.play=[{seat:0,card:{s:'H',r:'A'}},{seat:1,card:{s:'H',r:'9'}}];
        G.hands[2]=[{s:'S',r:'9'},{s:'C',r:'K'},{s:'D',r:'Q'}];
        const i=__EU.aiPlay(2); return {card:G.hands[2][i].r+G.hands[2][i].s, why:G.why}; })()""")
    check(r['card'] == 'QD' and 'your A♥ is winning' in r['why'], f'partner throws low on your winning ace ({r})')
    r = page.evaluate("""(() => { const G=__EU.G; G.play=[{seat:0,card:{s:'H',r:'J'}},{seat:1,card:{s:'H',r:'9'}}];
        const i=__EU.aiPlay(2); return {card:G.hands[2][i].r+G.hands[2][i].s, why:G.why}; })()""")
    check(r['card'] == '9S' and 'covering' in r['why'], f'partner covers a weak winner when an opponent still plays ({r})')
    r = page.evaluate("""(() => { const G=__EU.G; G.play=[{seat:3,card:{s:'H',r:'10'}},{seat:0,card:{s:'H',r:'J'}},{seat:1,card:{s:'H',r:'9'}}];
        const i=__EU.aiPlay(2); return {card:G.hands[2][i].r+G.hands[2][i].s, why:G.why}; })()""")
    check(r['card'] == 'QD' and 'winning' in r['why'], f'partner never overtakes when last to play ({r})')
    r = page.evaluate("""(() => { const G=__EU.G; G.play=[{seat:3,card:{s:'H',r:'A'}}]; G.ledSuit='H';
        const i=__EU.aiPlay(2); return {card:G.hands[2][i].r+G.hands[2][i].s, why:G.why}; })()""")
    check(r['card'] == '9S' and 'trumping in' in r['why'], f'partner trumps an opponent\'s ace ({r})')
    r = page.evaluate("""(() => { const G=__EU.G; G.play=[{seat:3,card:{s:'S',r:'A'}}]; G.ledSuit='S';
        G.hands[2]=[{s:'S',r:'9'},{s:'C',r:'K'},{s:'D',r:'Q'}];
        const i=__EU.aiPlay(2); return {card:G.hands[2][i].r+G.hands[2][i].s, why:G.why}; })()""")
    check(r['card'] == '9S' and "can't beat" in r['why'], f'must follow trump and cannot win → lowest legal ({r})')
    # partner tip toast on a real partner play
    page.evaluate("""(() => { const G=__EU.G; __EU.SET.tips='on'; G.trump='S'; G.out=[]; G.ledSuit='H'; G.resolving=false; G.turn=2;
        G.play=[{seat:0,card:{s:'H',r:'A'}},{seat:1,card:{s:'H',r:'9'}}]; G.hands[2]=[{s:'S',r:'9'},{s:'C',r:'K'},{s:'D',r:'Q'}]; G.hands[3]=[{s:'H',r:'K'},{s:'C',r:'9'},{s:'D',r:'9'}];
        __EU.playStep(); })()""")
    page.wait_for_timeout(750)
    tt = page.locator('#toast').inner_text()
    check(tt.startswith('Partner:') and 'winning' in tt, f'partner tip toast shown ({tt})')
    if shots: page.screenshot(path='/home/claude/games/shots/euchre-v12-tip.png')
    page.wait_for_timeout(2500)

    # ---- defend alone: prompt + sit-outs + scoring ----
    page.evaluate("""(() => { const G=__EU.G; __EU.SET.defend='on'; G.dealer=1; G.trump=null; G.out=[]; G.defAlone=-1; G.play=null; G.resolving=false;
        G.hands=[[{s:'S',r:'J'},{s:'C',r:'J'},{s:'S',r:'A'},{s:'H',r:'A'},{s:'D',r:'9'}],[{s:'H',r:'9'},{s:'H',r:'10'},{s:'D',r:'10'},{s:'C',r:'9'},{s:'C',r:'10'}],
                 [{s:'D',r:'J'},{s:'D',r:'Q'},{s:'C',r:'Q'},{s:'H',r:'Q'},{s:'H',r:'J'}],[{s:'S',r:'K'},{s:'S',r:'Q'},{s:'S',r:'10'},{s:'D',r:'A'},{s:'D',r:'K'}]];
        G.up={s:'C',r:'A'}; __EU.commitCall(3,'S',true,false); })()""")
    page.wait_for_timeout(300)
    check(page.evaluate("__EU.G.out") == [1] and page.locator('#backsW .cardback').count() == 0, "maker's partner (West) sits out")
    page.wait_for_timeout(900)
    check(page.locator('#prompt').is_visible() and 'ALONE' in page.locator('#promptQ').inner_text() and 'Defend alone' in page.locator('#promptBtns').inner_text(), 'defend-alone prompt offered to you')
    if shots: page.screenshot(path='/home/claude/games/shots/euchre-v12-defend.png')
    page.click('#promptBtns .btn.gold'); page.wait_for_timeout(200)
    g = page.evaluate("(() => { const G=__EU.G; return {defAlone:G.defAlone, out:G.out.slice().sort(), active:__EU.activeCount(), badge:document.querySelector('#seatS .callbadge').textContent, backsN:document.querySelectorAll('#backsN .cardback').length}; })()")
    check(g['defAlone'] == 0 and g['out'] == [1, 2] and g['active'] == 2 and g['badge'] == 'DEFENDING ALONE' and g['backsN'] == 0, f'you defend alone: both partners sit out ({g})')
    # play the 2-player hand out: you (right bower, left bower, A♠, A♥, 9♦) vs East (K♠ Q♠ 10♠ A♦ K♦) — you should take at least 3
    deadline = time.time() + 25; hands_played = 0
    while time.time() < deadline:
        s = page.evaluate("(() => { const G=__EU.G; return {turn:G.turn, res:!!G.resolving, play:G.play?G.play.length:-1, trump:G.trump, tc:G.trickCount, scores:G.scores.slice(), left:G.hands[0].length}; })()")
        if s['scores'] != [0, 0] or s['tc'] >= 5 and s['play'] == -1: break
        if s['turn'] == 0 and not s['res'] and s['trump'] and s['play'] >= 0 and s['left'] > 0:
            page.evaluate("(() => { const L=__EU.legalMoves(0); __EU.doPlay(0, L[0]); })()")
        page.wait_for_timeout(150)
    page.wait_for_timeout(2200)
    sc = page.evaluate("__EU.G.scores.slice()"); tr = page.evaluate("__EU.G.tricks ? __EU.G.tricks.slice() : null")
    check(sc[0] == 4 or (sc[0] == 0 and sc[1] in (1, 4)), f'defend-alone hand scored by the rules (scores {sc}, tricks {tr})')
    check(page.evaluate("__EU.G.tricks[1]+__EU.G.tricks[2]") == 0 or page.evaluate("__EU.G.trump") is None, 'sitting-out seats took no tricks')
    # direct scoring rules
    page.evaluate("__EU.G.trump='S'; __EU.G.maker=3; __EU.G.alone=3; __EU.G.defAlone=0; __EU.G.out=[1,2]; __EU.G.tricks=[3,0,0,2]; __EU.G.scores=[0,0]; __EU.scoreHand();")
    page.wait_for_timeout(100)
    check(page.evaluate("__EU.G.scores.slice()") == [4, 0] and 'defended alone' in page.locator('#toast').inner_text(), 'lone defender euchres a loner: 4 points')
    page.evaluate("__EU.G.maker=3; __EU.G.alone=3; __EU.G.defAlone=-1; __EU.G.out=[1]; __EU.G.tricks=[3,0,0,2]; __EU.G.scores=[0,0]; __EU.scoreHand();")
    page.wait_for_timeout(100)
    check(page.evaluate("__EU.G.scores.slice()") == [2, 0], 'ordinary euchre still 2')
    page.evaluate("__EU.G.maker=3; __EU.G.alone=3; __EU.G.defAlone=0; __EU.G.out=[1,2]; __EU.G.tricks=[0,0,0,5]; __EU.G.scores=[0,0]; __EU.scoreHand();")
    page.wait_for_timeout(100)
    check(page.evaluate("__EU.G.scores.slice()") == [0, 4], 'lone maker sweep still 4')
    st = page.evaluate('DJPP.stats()')
    check(st['extras'].get('loneDefences', 0) >= 1, f'lone defence counted in stats ({st["extras"]})')
    page.wait_for_timeout(2200)

    # ---- AI defender declines / accepts by strength ----
    page.evaluate("""(() => { const G=__EU.G; G.dealer=0; G.trump='S'; G.out=[2]; G.defAlone=-1; window.__dd=false;
        G.hands[1]=[{s:'H',r:'9'},{s:'H',r:'10'},{s:'D',r:'10'},{s:'C',r:'9'},{s:'C',r:'10'}]; G.hands[3]=[{s:'D',r:'9'},{s:'D',r:'10'},{s:'H',r:'Q'},{s:'C',r:'Q'},{s:'H',r:'K'}];
        __EU.offerDefend(0, ()=>{ window.__dd=true; }); })()""")
    page.wait_for_timeout(100)
    check(page.evaluate('window.__dd') is True and page.evaluate('__EU.G.defAlone') == -1, 'weak AI defenders play normally')
    page.evaluate("""(() => { const G=__EU.G; G.dealer=0; G.trump='S'; G.out=[2]; G.defAlone=-1; window.__dd=false;
        G.hands[1]=[{s:'S',r:'J'},{s:'C',r:'J'},{s:'S',r:'A'},{s:'H',r:'A'},{s:'D',r:'A'}];
        __EU.offerDefend(0, ()=>{ window.__dd=true; }); })()""")
    page.wait_for_timeout(1000)
    check(page.evaluate('__EU.G.defAlone') == 1 and sorted(page.evaluate('__EU.G.out')) == [2, 3] and page.evaluate('window.__dd') is True, 'strong AI defender (West) goes alone; East sits out')

    # ---- engine sim still healthy with the toggle helper ----
    sim = page.evaluate("__EU.auto(60)")
    check(sim['err'] is None and sim['hands'] > 0, f'engine sim ok ({sim})')

    # ---- full auto game with every option on, driving your seat through the UI hooks ----
    page.evaluate("document.getElementById('overlay').style.display='none'; __EU.SET.stick='on'; __EU.SET.defend='on'; __EU.SET.farmer='on'; __EU.SET.tips='on'; DJPP.reset && DJPP.reset(); __EU.newGame(); __EU.startHand();")
    deadline = time.time() + 420; prompts = 0; plays = 0; trick_sums_ok = True; last_tc = -1
    while time.time() < deadline:
        s = page.evaluate("""(() => { const G=__EU.G; const pr=document.getElementById('prompt').style.display!=='none';
            return {pr, turn:G.turn, res:!!G.resolving, play:G.play?G.play.length:-1, trump:G.trump, tc:G.trickCount, scores:G.scores.slice(), left:G.hands?G.hands[0].length:0,
                    out0:__EU.isOut(0), tricks:G.tricks?G.tricks.slice():null, over:document.getElementById('overlay').style.display==='flex'}; })()""")
        if s['over']: break
        if s['pr']:
            # take the first ghost (pass / keep / play normally) when present, else the first button
            page.evaluate("(() => { const bs=[...document.querySelectorAll('#promptBtns .btn')]; const g=bs.find(b=>/Pass|Keep|normally/.test(b.textContent))||bs[0]; if(g) g.click(); })()")
            prompts += 1
        elif s['turn'] == 0 and not s['res'] and s['trump'] and s['play'] >= 0 and s['left'] > 0 and not s['out0']:
            page.evaluate("(() => { const L=__EU.legalMoves(0); if(L.length) __EU.doPlay(0, L[Math.floor(Math.random()*L.length)]); })()")
            plays += 1
        if s['tricks'] and s['tc'] == 5 and s['tc'] != last_tc:
            if sum(s['tricks']) != 5: trick_sums_ok = False
        last_tc = s['tc']
        page.wait_for_timeout(120)
    sc = page.evaluate("__EU.G.scores.slice()")
    check(max(sc) >= 10 and page.locator('#overlay').is_visible(), f'full game with all options finished {sc} (prompts {prompts}, plays {plays})')
    check(trick_sums_ok, 'every completed hand had exactly 5 tricks')
    if shots: page.screenshot(path='/home/claude/games/shots/euchre-v12-end.png')

    check(not errors, 'no page errors: ' + ('; '.join(errors)[:300] if errors else 'clean'))
    b.close()
srv.shutdown()
print('\n' + ('ALL PASS' if not fails else f'{len(fails)} FAIL: ' + ' | '.join(fails)))
sys.exit(1 if fails else 0)
