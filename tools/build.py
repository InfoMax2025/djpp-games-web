#!/usr/bin/env python3
"""Stamp shared files into each card game: djpp-kit.js, fixed sw.js (with a per-game cache name), _headers.
Usage: python3 build.py            # all card games
       python3 build.py cribbage   # one game
The cache name is bumped from GAMES[...]['cache'] below — raise it on every deploy."""
import json, pathlib, sys, re

ROOT = pathlib.Path(__file__).parent
GAMES = {
    'cribbage': {'title': 'Cribbage Seniors: Big Cards', 'cache': 'crib-v2-0',
                 'icons': ['./icon-192.png','./icon-512.png','./icon-maskable-512.png','./favicon.png','./icon-apple-180.png']},
    'euchre':   {'title': 'Euchre for Seniors - Big Cards', 'cache': 'euchre-v2-0',
                 'icons': ['./icon-192.png','./icon-512.png','./icon-maskable-512.png','./favicon.png','./icon-apple-180.png']},
    'ginrummy': {'title': 'Gin Rummy Seniors: Big Cards', 'cache': 'gin-v2-0',
                 'icons': ['./icon-192.png','./icon-512.png','./icon-maskable-512.png','./favicon.png','./icon-apple-180.png']},
    'pinochle': {'title': 'Pinochle Seniors: Big Cards', 'cache': 'pin-v2-0',
                 'icons': ['./icon-192.png','./icon-512.png','./icon-maskable-512.png','./favicon.png','./icon-apple-180.png']},
}

def build(name):
    g = GAMES[name]; d = ROOT / name
    kit = (ROOT/'shared'/'djpp-kit.js').read_text(encoding='utf-8')
    (d/'djpp-kit.js').write_text(kit, encoding='utf-8')
    assets = ['./', './index.html', './manifest.webmanifest', './djpp-kit.js'] + g['icons']
    sw = (ROOT/'shared'/'sw.template.js').read_text(encoding='utf-8')
    sw = sw.replace('__TITLE__', g['title']).replace('__CACHE__', g['cache']).replace('__ASSETS__', json.dumps(assets))
    (d/'sw.js').write_text(sw, encoding='utf-8')
    (d/'_headers').write_text((ROOT/'shared'/'_headers').read_text(encoding='utf-8'), encoding='utf-8')
    idx = (d/'index.html').read_text(encoding='utf-8')
    assert 'djpp-kit.js' in idx, f'{name}/index.html does not include djpp-kit.js'
    assert 'DJPP.record' in idx, f'{name}/index.html never calls DJPP.record'
    print(f'{name}: cache={g["cache"]} kit={len(kit)}B sw={len(sw)}B ok')

for n in (sys.argv[1:] or GAMES):
    build(n)
