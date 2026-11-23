# Live Cams: World Webcams - cam status

This branch holds one small data file for the Live Cams app. It is separate from the
rest of this repository and shares no history with `main`.

- `status.json` - which cams are working, written each hour by the `livecams-sweep`
  workflow (`.github/workflows/livecams-sweep.yml` on `main`). The app reads it from
  `https://raw.githubusercontent.com/InfoMax2025/djpp-games-web/livecams-data/status.json`.
- `sweep.mjs` - the check itself. It reads the app's catalogue from
  `https://livecamsapp.netlify.app/data/cams.json`, so it always tests what the app is showing.

The branch is kept at a single commit that the workflow replaces each hour.
A cam is hidden only after two failed checks in a row and comes back by itself.
