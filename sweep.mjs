#!/usr/bin/env node
/* Live Cams dead-link sweep.
 *
 * Tests every cam in the catalogue and writes status.json. The app hides any
 * cam marked ok:false until a later sweep finds it playing again.
 *
 *   node tools/sweep.mjs [cams.json path or https URL] [path/to/status.json]
 *
 * The catalogue can be read straight from the live site, so the check always
 * tests what the app is actually showing.
 *
 * Two modes:
 *   YT_API_KEY set  -> YouTube Data API. Knows whether a stream is live right
 *                      now and whether embedding is allowed, and can find a
 *                      channel's new stream after a restart (the cam's
 *                      yt.channel + yt.match).
 *   no key          -> YouTube's public oEmbed endpoint. Catches streams that
 *                      were removed, made private or had embedding switched
 *                      off. It cannot tell a finished stream from a live one.
 *
 * Still-picture cams (cam.img) are checked against their publisher. For the
 * National Park Service air quality webcams that is the network's own list of
 * when each camera last sent a picture; a picture more than STALE_HOURS old
 * counts as a failed check.
 *
 * Needs Node 18 or newer. No packages to install.
 */
import { readFile, writeFile } from "node:fs/promises";

const CAMS = process.argv[2] || "site/data/cams.json";
const OUT = process.argv[3] || "site/data/status.json";
const KEY = process.env.YT_API_KEY || "";
const HIDE_AFTER = 2;          // failed sweeps in a row before a cam is hidden
const MAX_BAD_SHARE = 0.6;     // more than this failing at once means the sweep itself is broken
const MAX_UNKNOWN_SHARE = 0.5; // more than this untestable means nothing was really checked
const STALE_HOURS = 3;         // a still camera whose newest picture is older than this is off

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
async function getJson(url) {
  for (let attempt = 0; attempt < 3; attempt++) {
    try {
      const r = await fetch(url, { headers: { "user-agent": "LiveCamsSweep/1.0" } });
      if (r.status === 429 || r.status >= 500) { await sleep(1500 * (attempt + 1)); continue; }
      let body = null; try { body = await r.json(); } catch { /* oEmbed errors are plain text */ }
      return { status: r.status, body };
    } catch { await sleep(1500 * (attempt + 1)); }
  }
  return { status: 0, body: null };
}

/* ---------- API mode ---------- */
async function apiVideos(ids) {
  const out = {};
  for (let i = 0; i < ids.length; i += 50) {
    const chunk = ids.slice(i, i + 50);
    const r = await getJson("https://www.googleapis.com/youtube/v3/videos?part=snippet,status&maxResults=50&id=" + chunk.join(",") + "&key=" + KEY);
    if (r.status !== 200 || !r.body) throw new Error("videos.list failed: " + r.status + " " + JSON.stringify(r.body && r.body.error && r.body.error.message));
    for (const v of r.body.items || []) out[v.id] = { live: v.snippet.liveBroadcastContent === "live", embeddable: !!v.status.embeddable, pub: v.status.privacyStatus === "public", title: v.snippet.title };
  }
  return out;
}
async function apiChannelLive(channelId) {   // costs 100 quota units; only called when a cam's stream has gone
  const r = await getJson("https://www.googleapis.com/youtube/v3/search?part=snippet&type=video&eventType=live&maxResults=50&channelId=" + channelId + "&key=" + KEY);
  if (r.status !== 200 || !r.body) return null;
  return (r.body.items || []).map((it) => ({ id: it.id.videoId, title: it.snippet.title }));
}
function matches(title, pattern) {
  if (!pattern) return true;
  try { return new RegExp(pattern, "i").test(title); } catch { return false; }
}

/* ---------- oEmbed mode ---------- */
async function oembedOk(id) {
  const r = await getJson("https://www.youtube.com/oembed?format=json&url=" + encodeURIComponent("https://www.youtube.com/watch?v=" + id));
  if (r.status === 200) return true;
  if (r.status === 401 || r.status === 403 || r.status === 404 || r.status === 400) return false;
  return null;   // could not tell; leave the cam as it was
}

/* ---------- still-picture cams ---------- */
const TZ = { EST: -5, EDT: -4, CST: -6, CDT: -5, MST: -7, MDT: -6, PST: -8, PDT: -7, AKST: -9, AKDT: -8, HST: -10 };
function npsDate(s) {   // "11/23/2026 03:30 PM PST" -> ms, or null
  const m = /(\d{1,2})\/(\d{1,2})\/(\d{4})\s+(\d{1,2}):(\d{2})\s*(AM|PM)\s+([A-Z]{2,4})/.exec(String(s || ""));
  if (!m || !(m[7] in TZ)) return null;
  let h = +m[4] % 12; if (m[6] === "PM") h += 12;
  return Date.UTC(+m[3], +m[1] - 1, +m[2], h - TZ[m[7]], +m[5]);
}
let npsList;   // undefined = not asked yet, null = could not be read
async function npsDates() {
  if (npsList !== undefined) return npsList;
  const r = await getJson("https://www.nps.gov/featurecontent/ard/webcams/json/NPSsitelist.txt");
  npsList = null;
  if (r.status === 200 && r.body && Array.isArray(r.body.parks)) { npsList = {}; for (const p of r.body.parks) npsList[String(p.abbr).toLowerCase()] = npsDate(p.imagedate); }
  return npsList;
}
async function headOk(url) {   // true = a picture is there, false = it is not, null = could not tell
  try {
    const r = await fetch(url, { method: "HEAD", headers: { "user-agent": "LiveCamsSweep/1.0" } });
    if (r.status === 200) return /^image\//.test(r.headers.get("content-type") || "");
    if (r.status === 404 || r.status === 410) return false;
    return null;
  } catch { return null; }
}
async function stillCheck(c) {   // -> {ok:true} | {ok:false, why} | null when it could not be tested
  if (c.img.feed === "nps-air") {
    const list = await npsDates();
    if (list && c.img.key in list) {
      const t = list[c.img.key];
      if (t === null) return null;
      return Date.now() - t <= STALE_HOURS * 3600 * 1000 ? { ok: true } : { ok: false, why: "stale-picture" };
    }
    return list ? { ok: false, why: "not-in-feed" } : null;   // feed unreadable: leave the cam as it was
  }
  const ok = await headOk(c.img.url);
  return ok === null ? null : ok ? { ok: true } : { ok: false, why: "picture-gone" };
}

/* ---------- run ---------- */
async function readCatalogue(src) {
  if (!/^https?:\/\//.test(src)) return JSON.parse(await readFile(src, "utf8"));
  const r = await getJson(src + (src.includes("?") ? "&" : "?") + "t=" + Date.now());
  if (r.status !== 200 || !r.body || !Array.isArray(r.body.cams)) { console.error("Could not read the catalogue from " + src + " (" + r.status + "). status.json left unchanged."); process.exit(2); }
  return r.body;
}
const catalogue = await readCatalogue(CAMS);
const all = (catalogue.cams || []).filter((c) => c && c.id && (c.yt || (c.img && c.img.url)) && !c.hidden);
const cams = all.filter((c) => c.yt), stills = all.filter((c) => !c.yt);
let unknown = 0;
let prev = { cams: {} };
try { prev = JSON.parse(await readFile(OUT, "utf8")); } catch { /* first run */ }

const result = {};
const current = (c) => (prev.cams[c.id] && prev.cams[c.id].video) || c.yt.video || null;
const channelCache = {};

if (KEY) {
  const info = await apiVideos([...new Set(cams.map(current).filter(Boolean))]);
  for (const c of cams) {
    const id = current(c), v = id && info[id];
    if (v && v.live && v.embeddable && v.pub) { result[c.id] = { ok: true, video: id }; continue; }
    let found = null;
    if (c.yt.channel) {
      if (!(c.yt.channel in channelCache)) channelCache[c.yt.channel] = await apiChannelLive(c.yt.channel);
      const lives = channelCache[c.yt.channel] || [];
      const hit = lives.find((l) => matches(l.title, c.yt.match));
      if (hit) { const chk = await apiVideos([hit.id]); if (chk[hit.id] && chk[hit.id].embeddable && chk[hit.id].pub) found = hit.id; }
    }
    result[c.id] = found ? { ok: true, video: found, moved: true } : { ok: false, why: !v ? "gone" : !v.embeddable ? "embed-off" : !v.pub ? "private" : "not-live" };
  }
} else {
  for (const c of cams) {
    const id = current(c);
    if (!id) { result[c.id] = { ok: true }; continue; }            // channel-only cam: cannot be checked without a key
    const ok = await oembedOk(id);
    if (ok === null) { unknown++; result[c.id] = { keep: true }; await sleep(120); continue; }
    result[c.id] = ok === null ? (prev.cams[c.id] || { ok: true, video: id }) : ok ? { ok: true, video: id } : { ok: false, why: "gone-or-embed-off" };
    await sleep(120);
  }
}

for (const c of stills) {
  const r = await stillCheck(c);
  if (r === null) unknown++;
  result[c.id] = r === null ? { keep: true } : r;
}

/* a cam is only hidden after HIDE_AFTER failed sweeps in a row */
const out = {};
for (const c of all) {
  const r = result[c.id], before = prev.cams[c.id] || {};
  if (r.keep) { out[c.id] = prev.cams[c.id] || { ok: true }; continue; }   // could not be tested this time
  if (r.ok) { out[c.id] = { ok: true }; if (c.yt && r.video && r.video !== c.yt.video) out[c.id].video = r.video; continue; }
  const fails = (before.fails || 0) + 1;
  out[c.id] = { ok: fails < HIDE_AFTER, fails, why: r.why };
  if (before.video) out[c.id].video = before.video;
}

const bad = all.filter((c) => result[c.id].ok === false).length;
const summary = { checked: new Date().toISOString(), mode: KEY ? "api" : "oembed", total: all.length, video: cams.length, stills: stills.length, failing: bad, untested: unknown, hidden: Object.values(out).filter((s) => !s.ok).length };
if (all.length >= 5 && bad / all.length > MAX_BAD_SHARE) {
  console.error("Sweep aborted: " + bad + " of " + all.length + " cams failed at once, which points at the sweep, not the cams. status.json left unchanged.");
  process.exit(2);
}
if (all.length >= 5 && unknown / all.length > MAX_UNKNOWN_SHARE) {
  console.error("Sweep aborted: " + unknown + " of " + all.length + " cams could not be tested, so nothing was really checked. status.json left unchanged.");
  process.exit(2);
}
await writeFile(OUT, JSON.stringify({ ...summary, cams: out }, null, 1) + "\n");
console.log(JSON.stringify(summary));
for (const c of all) { const s = out[c.id]; if (!s.ok || s.fails || s.video) console.log((s.ok ? "  warn " : "  HIDE ") + c.id + " " + JSON.stringify(s)); }
