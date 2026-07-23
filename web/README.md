# sketch·eq (web)

Try it live: https://sketch-eq-production.up.railway.app/

Browser version of sketch-eq. Same math as the desktop app, fitting.py is the literal same file, just called through a /api/fit endpoint instead of a PyQt5 GUI. Drawing and rendering happen in plain JS and canvas on the frontend, the actual regression runs server side.

Background and brush color are both pickable from the sidebar. The grid automatically flips between light and dark tones based on the background color's brightness, so it stays readable no matter what color you pick.

## Run locally

```
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 app.py
```

Then go to http://localhost:5000 (or if port 5000 is taken, which happens a lot on macOS because of AirPlay, run PORT=5050 python3 app.py instead).

## Deploy to Railway

1. Push this folder to GitHub.
2. railway.app, New Project, Deploy from GitHub repo.
3. Since it's in a subfolder, go to Settings, Root Directory, and set it to web.
4. Railway picks up Python automatically from requirements.txt and runs the Procfile, no extra config needed.
5. Settings, Networking, Generate Domain for a public URL.

## API

POST /api/fit returns a list of equations as JSON, each with a latex string, a domain string, and a range of point indices for highlighting.

GET /healthz returns {"status": "ok"}

## Project layout

```
app.py              Flask routes, serves the page and the /api/fit endpoint
fitting.py           same math core as the desktop version
templates/index.html
static/style.css
static/app.js         drawing, rendering, color pickers, zoom, undo
requirements.txt
Procfile
```
