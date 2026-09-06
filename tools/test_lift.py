import sys, threading, http.server, socketserver, functools, pathlib
from playwright.sync_api import sync_playwright
def serve(folder, port):
    H=functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(folder))
    class Q(socketserver.TCPServer): allow_reuse_address=True
    s=Q(('127.0.0.1',port),H); threading.Thread(target=s.serve_forever,daemon=True).start(); return s
res=[]
with sync_playwright() as p:
    b=p.chromium.launch()
    # --- Cribbage pegging tap-to-lift
    s=serve('djpp-games-web/cribbage',8901); pg=b.new_page(viewport={'width':390,'height':844})
    errs=[]; pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto('http://127.0.0.1:8901/index.html'); pg.wait_for_timeout(500)
    pg.evaluate("__CRIB.newGame(); __CRIB.tap(0); __CRIB.tap(1); __CRIB.confirmDiscard();")
    for _ in range(40):
        pg.wait_for_timeout(250)
        if pg.evaluate("__CRIB.G.phase")=='pegYou': break
    ph=pg.evaluate("__CRIB.G.phase"); res.append(('crib reached pegYou', ph=='pegYou'))
    idx=pg.evaluate("(()=>{const L=__CRIB.G.left[0]; for(let i=0;i<L.length;i++) if(__CRIB.G.count+Math.min(L[i].r,10)<=31) return i; return -1;})()")
    before=pg.evaluate("__CRIB.G.left[0].length")
    pg.evaluate(f"__CRIB.tap({idx})"); pg.wait_for_timeout(100)
    res.append(('crib first tap lifts, does not play', pg.evaluate("__CRIB.G.phase")=='pegYou' and pg.evaluate("__CRIB.G.lift")==idx and pg.evaluate("__CRIB.G.left[0].length")==before))
    res.append(('crib lifted card has sel class', pg.locator('#hand .card.sel').count()==1))
    pg.evaluate(f"__CRIB.tap({idx})"); pg.wait_for_timeout(200)
    res.append(('crib second tap plays', pg.evaluate("__CRIB.G.left[0].length")==before-1))
    res.append(('crib no errors', not errs)); s.shutdown()
    # --- Gin Rummy discard tap-to-lift
    s=serve('djpp-games-web/ginrummy',8902); pg=b.new_page(viewport={'width':390,'height':844})
    errs=[]; pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto('http://127.0.0.1:8902/index.html'); pg.wait_for_timeout(500)
    pg.evaluate("__GIN.newGame()")
    for _ in range(60):
        pg.wait_for_timeout(250)
        ph=pg.evaluate("__GIN.G.phase")
        if ph=='offerYou':   # the up-card is offered to you first: pass on it — hammering the button must not run the offer twice
            for _k in range(3):
                if pg.locator('#actions button', has_text='Pass').count(): pg.locator('#actions button', has_text='Pass').first.click()
            pg.wait_for_timeout(200); continue
        if ph in ('draw','discard'): break
    ph=pg.evaluate("__GIN.G.phase")
    if ph=='draw': pg.evaluate("__GIN.pickStock()"); pg.wait_for_timeout(300)
    ph=pg.evaluate("__GIN.G.phase"); res.append(('gin reached discard phase', ph=='discard'))
    # pick a card that isn't the forbidden one
    idx=pg.evaluate("(()=>{const G=__GIN.G; for(let i=0;i<G.hand.length;i++){ const c=G.hand[i]; if(!G.forbidden || (c.r+':'+c.s)!==(G.forbidden.r+':'+G.forbidden.s)) return i;} return 0;})()")
    before=pg.evaluate("__GIN.G.hand.length")
    pg.evaluate(f"__GIN.tapCard({idx})"); pg.wait_for_timeout(100)
    res.append(('gin first tap lifts, does not discard', pg.evaluate("__GIN.G.phase")=='discard' and pg.evaluate("__GIN.G.hand.length")==before and pg.locator('#hand .card.lifted').count()==1))
    pg.evaluate(f"__GIN.tapCard({idx})"); pg.wait_for_timeout(200)
    res.append(('gin second tap discards', pg.evaluate("__GIN.G.hand.length")==before-1))
    pg.wait_for_timeout(2500)
    res.append(('gin no duplicated opponent turn after the offer', pg.evaluate("__GIN.G.hand.length")==10 and pg.evaluate("__GIN.G.opp.length") in (10,11)))
    res.append(('gin no errors', not errs)); s.shutdown()
    b.close()
bad=0
for n,ok in res:
    print(('  ok   ' if ok else '  FAIL ')+n); bad+= (not ok)
print('RESULT:', 'PASS' if not bad else f'{bad} FAIL')
