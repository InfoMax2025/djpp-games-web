#!/usr/bin/env python3
"""Check the service worker installs, precaches every asset, and serves the page offline."""
import sys, threading, http.server, socketserver, functools, pathlib
from playwright.sync_api import sync_playwright
folder = pathlib.Path(sys.argv[1]).resolve()
PORT = 8900 + (hash(str(folder)) % 90)
class Q(socketserver.TCPServer): allow_reuse_address = True
srv = Q(('127.0.0.1', PORT), functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(folder)))
threading.Thread(target=srv.serve_forever, daemon=True).start()
URL = f'http://127.0.0.1:{PORT}/index.html'
fails = []
def check(c, m):
    print(('  ok   ' if c else '  FAIL ') + m)
    if not c: fails.append(m)
with sync_playwright() as p:
    b = p.chromium.launch(); ctx = b.new_context(); page = ctx.new_page()
    errs = []; page.on('pageerror', lambda e: errs.append(str(e))); page.on('console', lambda m: errs.append(m.text) if m.type == 'error' else None)
    page.goto(URL)
    page.wait_for_function('navigator.serviceWorker && navigator.serviceWorker.controller || (navigator.serviceWorker.getRegistrations().then(r=>r.length>0), false)', timeout=15000) if False else None
    page.wait_for_timeout(3000)
    info = page.evaluate('''async () => { const regs = await navigator.serviceWorker.getRegistrations(); const keys = await caches.keys();
        const out = {regs: regs.length, keys}; if (keys.length){ const c = await caches.open(keys[0]); out.cached = (await c.keys()).map(r => new URL(r.url).pathname); } return out; }''')
    check(info['regs'] == 1, f"one SW registration ({info['regs']})")
    check(len(info['keys']) == 1, f"one cache: {info['keys']}")
    cached = set(info.get('cached', []))
    want = {'/', '/index.html', '/manifest.webmanifest', '/djpp-kit.js', '/icon-192.png', '/icon-512.png', '/icon-maskable-512.png', '/favicon.png', '/icon-apple-180.png'}
    missing = want - cached
    check(not missing, f"all {len(want)} assets precached" + (f" — missing {sorted(missing)}" if missing else ''))
    # offline: reload with network blocked
    ctx.set_offline(True); page.reload(); page.wait_for_timeout(1200)
    check(page.locator('#startbtn').count() == 1, 'page serves offline from the SW cache')
    check(page.evaluate('typeof window.DJPP') == 'object', 'kit loads offline')
    ctx.set_offline(False)
    check(not errs, 'no console errors: ' + ('; '.join(errs)[:200] if errs else 'clean'))
    b.close()
srv.shutdown()
print('RESULT:', 'PASS' if not fails else f'{len(fails)} FAILURE(S)')
sys.exit(1 if fails else 0)
