#!/usr/bin/env python3
"""Decode assets-b64/<game>.txt bundles (===== B64: <game>/<file> ===== ... ===== END =====) into game folders."""
import base64, hashlib, pathlib, re, sys

SRC = pathlib.Path('/home/claude/games/b64pull/assets-b64')
DST = pathlib.Path('/home/claude/games/djpp-games-web')
pat = re.compile(r'(?:^|\n)===== B64: ([^\n]+?) =====\n(.*?)(?=\n===== (?:B64|END))', re.S)

for f in sorted(SRC.glob('*.txt')):
    txt = f.read_text()
    n = 0
    for m in pat.finditer(txt):
        rel, b64 = m.group(1).strip(), re.sub(r'\s+', '', m.group(2))
        raw = base64.b64decode(b64, validate=True)
        out = DST / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(raw)
        sig = raw[:8]
        kind = 'PNG' if sig.startswith(b'\x89PNG') else ('JPG' if sig.startswith(b'\xff\xd8') else sig.hex())
        print(f'{rel:40s} {len(raw):8d} B  {kind}  {hashlib.sha1(raw).hexdigest()[:8]}')
        n += 1
    print(f'-- {f.name}: {n} files')
