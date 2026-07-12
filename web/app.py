"""
app.py
------
Flask backend for sketch-eq. Serves the drawing UI and exposes a single
/api/fit endpoint that runs fitting.process_stroke() -- no logic is
duplicated in JavaScript, the browser just sends raw stroke points and
gets equations back.
"""

import os
from flask import Flask, request, jsonify, render_template
from fitting import Point, process_stroke

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/fit", methods=["POST"])
def fit():
    data = request.get_json(force=True, silent=True) or {}
    raw_points = data.get("points", [])

    if not isinstance(raw_points, list) or len(raw_points) < 2:
        return jsonify({"equations": []})

    try:
        pts = [Point(float(p["x"]), float(p["y"])) for p in raw_points]
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "malformed points"}), 400

    equations = process_stroke(pts)
    return jsonify({
        "equations": [
            {
                "latex": eq.latex,
                "domain": eq.domain,
                "meta": eq.meta,
                "range": list(eq.index_range),
            }
            for eq in equations
        ]
    })


@app.route("/healthz")
def healthz():
    return {"status": "ok"}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
