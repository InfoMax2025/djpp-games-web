#!/usr/bin/env python3
"""Title-overlay fix for the four DJPP card games (applied 2026-09-06, kept for the record; idempotent).

Problem: #overlay was a column flexbox with justify-content:center + overflow-y:auto. When the content is
taller than the phone screen (Cribbage v1.2 with the settings row; Pinochle on 360x740), a centered flex
column clips the TOP of the content and it can't be scrolled into view — the game title and, on small
phones, the DEAL button were unreachable.

Fix 1: justify-content:flex-start + margin-top:auto on the first child / margin-bottom:auto on the last
        child (auto margins centre when there is spare room and collapse to 0 when there isn't).
Fix 2: move the how-to box BELOW the DEAL button, so the first screen is title → settings → DEAL →
        My Stats/Fair Deal/More Games, with the how-to text scrolling underneath.
"""
import re, pathlib
ROOT = pathlib.Path(__file__).parent / 'djpp-games-web'
for g in ['cribbage', 'euchre', 'ginrummy', 'pinochle']:
    p = ROOT / g / 'index.html'; s = p.read_text(encoding='utf-8')
    rule = re.search(r'#overlay\{[^}]*\}', s, re.S).group(0)
    if 'justify-content:center;' in rule:
        s = s.replace(rule, rule.replace('justify-content:center;', 'justify-content:flex-start;') +
            '\n  #overlay>*:first-child{margin-top:auto;} #overlay>*:last-child{margin-bottom:auto;} /* centers when short, scrolls from the top when tall */', 1)
    m = re.search(r'\n    <div class="how" id="howBox">.*?\n    </div>\n', s, re.S)
    sb = re.search(r'\n    <button[^>]*id="startbtn"[^>]*>DEAL</button>\n', s)
    if m and sb and m.start() < sb.start():
        how = m.group(0); s = s.replace(how, '\n', 1)
        sb = re.search(r'\n    <button[^>]*id="startbtn"[^>]*>DEAL</button>\n', s)
        s = s.replace(sb.group(0), sb.group(0) + how.lstrip('\n'), 1)
    s = re.sub(r'(#overlay \.how\{[^}]*?)margin-bottom:2[02]px;', lambda mm: mm.group(1) + ('margin:20px 0 4px;' if g == 'pinochle' else 'margin:22px 0 4px;'), s, count=1, flags=re.S)
    p.write_text(s, encoding='utf-8'); print(g, 'ok')
