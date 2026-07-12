# sketch·eq (web)

Browser version of sketch-eq: draw a curve, get its equation. Curve-fitting
math is unchanged from the desktop version -- `fitting.py` is the exact
same file, exercised through a `/api/fit` endpoint instead of a PyQt5 GUI.
Drawing/rendering stay client-side in vanilla JS/canvas; regression happens
server-side.

Background and brush color are user-selectable via the pickers in the
sidebar. The grid automatically switches between light and dark tones
(based on the background's relative luminance) so it stays legible against
whatever color is picked.

## Run locally

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 app.py
```

Then open http://localhost:5000 (if port 5000 is taken -- common on macOS
due to AirPlay Receiver -- run `PORT=5050 python3 app.py` instead).

## Deploy to Railway

1. Push this folder to GitHub (as a `web/` subfolder alongside the desktop
   version, or as its own repo).
2. railway.app -> New Project -> Deploy from GitHub repo.
3. If it's in a subfolder, set Settings -> Root Directory to that folder
   name (e.g. `web`).
4. Railway auto-detects Python from `requirements.txt` and runs the
   `Procfile` (`gunicorn app:app`) -- no extra config needed.
5. Settings -> Networking -> Generate Domain for a public URL.

## API

`POST /api/fit`
```json
{ "points": [{"x": 0.1, "y": 0.4}, {"x": 0.2, "y": 0.6}, ...] }
```
returns
```json
{ "equations": [
  {"latex": "y = 2x + 3", "domain": "-1.0 ≤ x ≤ 4.2", "meta": "deg 1 poly · R² = 1.0", "range": [0, 14]}
]}
```

`GET /healthz` -- `{"status": "ok"}`

## Project layout

```
app.py              Flask routes: serves the page, exposes /api/fit
fitting.py            same math core as the desktop version
templates/index.html
static/style.css
static/app.js         drawing, rendering, color pickers, zoom/undo
requirements.txt
Procfile
```
