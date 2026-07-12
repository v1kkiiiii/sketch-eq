# sketch·eq (web)

Browser version of sketch-eq: draw a curve, get its equation, deployed as a
Flask app. The curve-fitting math is unchanged from the desktop version --
`fitting.py` is the exact same file, exercised through a `/api/fit` endpoint
instead of a PyQt5 GUI. Drawing and rendering stay client-side in vanilla
JS/canvas; the actual regression happens server-side.

## Run locally

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 app.py
```

Then open http://localhost:5000

## Deploy to Railway

1. Push this folder to a GitHub repo (see steps below if you haven't).
2. Go to [railway.app](https://railway.app) → New Project → Deploy from GitHub repo → pick this repo.
3. Railway auto-detects Python from `requirements.txt` and uses the `Procfile`
   to run `gunicorn app:app` -- no extra config needed.
4. Once it builds, Railway gives you a public URL under Settings → Networking
   → Generate Domain.

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

`GET /healthz` -- returns `{"status": "ok"}`, useful for Railway's health checks.

## Project layout

```
app.py            Flask routes: serves the page, exposes /api/fit
fitting.py         same math core as the desktop version (unmodified)
templates/index.html
static/style.css
static/app.js       drawing, rendering, zoom/undo -- calls /api/fit on each stroke
requirements.txt
Procfile            tells Railway how to start the app (gunicorn)
```
