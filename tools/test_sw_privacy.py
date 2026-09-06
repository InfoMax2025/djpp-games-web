"""SW: privacy.html passes through and never replaces the cached app page; the app still serves offline afterwards."""
import sys, threading, http.server, socketserver, functools, pathlib
from playwright.sync_api import sync_playwright
fails=[]
def check(c,m):
    print(('  ok   ' if c else '  FAIL ')+m)
    if not c: fails.append(m)
class Q(socketserver.TCPServer): allow_reuse_address=True
with sync_playwright() as p:
    for i,(g,marker) in enumerate([('cribbage','#startbtn'),('ct3d','#tc-easy')]):
        folder=pathlib.Path('/home/claude/games/djpp-games-web')/g; port=8960+i
        srv=Q(('127.0.0.1',port),functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(folder)))
        threading.Thread(target=srv.serve_forever,daemon=True).start()
        b=p.chromium.launch(args=['--use-gl=swiftshader']); ctx=b.new_context(); page=ctx.new_page()
        page.goto(f'http://127.0.0.1:{port}/index.html'); page.wait_for_timeout(3000)
        check(page.evaluate('!!navigator.serviceWorker.controller'), f'{g}: SW controls the page')
        page.goto(f'http://127.0.0.1:{port}/privacy.html'); page.wait_for_timeout(800)
        check('Delete your data' in page.inner_text('body'), f'{g}: privacy page shows Delete your data section')
        cached=page.evaluate('''async()=>{const ks=await caches.keys(); const c=await caches.open(ks[0]); const r=await c.match('./index.html'); const t=r?await r.text():''; return {keys:ks, isApp:/djpp|Control Tower|startbtn|tc-easy/.test(t), isPrivacy:/Privacy Policy/.test(t), n:(await c.keys()).map(k=>new URL(k.url).pathname)};}''')
        check(cached['isApp'] and not cached['isPrivacy'], f"{g}: cached index.html is still the app after visiting privacy.html ({cached['keys']})")
        check('/privacy.html' not in cached['n'], f"{g}: privacy.html not cached ({cached['n']})")
        ctx.set_offline(True); page.goto(f'http://127.0.0.1:{port}/index.html'); page.wait_for_timeout(1500)
        check(page.locator(marker).count()==1, f'{g}: app serves offline')
        ctx.set_offline(False); b.close(); srv.shutdown()
print('RESULT:','PASS' if not fails else f'{len(fails)} FAILURE(S)')
