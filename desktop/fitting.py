"""
fitting.py
----------
Pure math core for sketch-eq: converts a freehand stroke (list of (x, y)
points in math-space) into one or more closed-form equations.

Pipeline:
    1. smooth()            - moving-average denoise of the raw stroke
    2. split_monotonic_runs() - segment the stroke at direction reversals
                                 along its dominant axis
    3. best_poly_fit()     - least-squares polynomial regression per segment,
                              degree chosen automatically via R^2
    4. fit_circle()        - Kasa algebraic least-squares circle fit, used
                              instead of (3) when the stroke is a closed loop

No GUI dependencies here on purpose: this module is independently testable
and is the part of the project worth walking an interviewer through.
"""

from dataclasses import dataclass, field
from typing import List, Tuple, Optional
import numpy as np

SUPERSCRIPT = {2: "\u00B2", 3: "\u00B3", 4: "\u2074"}


@dataclass
class Equation:
    latex: str          # e.g. "y = 2x + 3"
    domain: str          # e.g. "-1.0 <= x <= 4.2"
    meta: str            # e.g. "deg 2 poly, R^2 = 0.997"
    index_range: Tuple[int, int]  # indices into the (smoothed) point array,
                                    # used to know which part of the stroke
                                    # to highlight


@dataclass
class Point:
    x: float
    y: float


# ----------------------------------------------------------------------
# Smoothing
# ----------------------------------------------------------------------
def smooth(points: List[Point], window: int = 5) -> List[Point]:
    """Simple centered moving-average smoothing to remove mouse jitter."""
    n = len(points)
    if n < window + 2:
        return points
    half = window // 2
    xs = np.array([p.x for p in points])
    ys = np.array([p.y for p in points])
    out = []
    for i in range(n):
        lo, hi = max(0, i - half), min(n, i + half + 1)
        out.append(Point(float(xs[lo:hi].mean()), float(ys[lo:hi].mean())))
    return out


# ----------------------------------------------------------------------
# Segmentation
# ----------------------------------------------------------------------
def split_monotonic_runs(points: List[Point], axis: str) -> List[Tuple[int, int]]:
    """
    Split the point sequence into maximal runs where `axis` (x or y) is
    monotonic. A direction reversal ends one run and starts the next
    (sharing the reversal point as a boundary). This is what produces
    multiple equations from a single stroke, e.g. a "V" shape.
    """
    runs = []
    start = 0
    direction = 0
    get = (lambda p: p.x) if axis == "x" else (lambda p: p.y)
    for i in range(1, len(points)):
        delta = get(points[i]) - get(points[i - 1])
        if abs(delta) < 1e-6:
            continue
        d = 1 if delta > 0 else -1
        if direction == 0:
            direction = d
        elif d != direction:
            runs.append((start, i - 1))
            start = i - 1
            direction = d
    runs.append((start, len(points) - 1))
    return [r for r in runs if r[1] > r[0]]


# ----------------------------------------------------------------------
# Polynomial fitting
# ----------------------------------------------------------------------
def _poly_fit_degree(u: np.ndarray, v: np.ndarray, deg: int):
    """
    Least-squares fit of v ~ poly(u) of given degree, using numpy's
    Polynomial.fit which internally maps u onto [-1, 1] before solving
    (equivalent in spirit to mean-centering / rescaling) for numerical
    stability, then we convert back to the standard power basis so the
    displayed equation reads as an ordinary polynomial in x or y.
    """
    p = np.polynomial.Polynomial.fit(u, v, deg)
    standard = p.convert(kind=np.polynomial.Polynomial)
    coeffs = standard.coef  # ascending order: c0 + c1*u + c2*u^2 ...
    pred = standard(u)
    ss_res = float(np.sum((v - pred) ** 2))
    ss_tot = float(np.sum((v - v.mean()) ** 2))
    r2 = 1.0 if ss_tot < 1e-9 else 1.0 - ss_res / ss_tot
    return coeffs, r2


def _find_corner_index(u: np.ndarray, v: np.ndarray) -> Optional[int]:
    """
    Find the interior point with the sharpest turn (largest angle between
    the incoming and outgoing chord vectors), scaled to look at u and v on
    comparable footing. Returns None if there's no point with a genuinely
    sharp turn (i.e. the curve just bends smoothly, like a parabola vertex,
    rather than having a real corner, like the tip of a "V").
    """
    n = len(u)
    if n < 6:
        return None
    # normalize both axes to comparable scale before measuring angles
    u_span = max(u.max() - u.min(), 1e-9)
    v_span = max(v.max() - v.min(), 1e-9)
    un, vn = u / u_span, v / v_span
    best_idx, best_angle = None, 0.0
    for i in range(2, n - 2):
        v1 = np.array([un[i] - un[i - 2], vn[i] - vn[i - 2]])
        v2 = np.array([un[i + 2] - un[i], vn[i + 2] - vn[i]])
        n1, n2 = np.linalg.norm(v1), np.linalg.norm(v2)
        if n1 < 1e-9 or n2 < 1e-9:
            continue
        cos_angle = np.clip(np.dot(v1, v2) / (n1 * n2), -1, 1)
        angle = np.degrees(np.arccos(cos_angle))
        if angle > best_angle:
            best_angle, best_idx = angle, i
    # a genuine corner (like a V) turns sharply (>35 deg); smooth bends
    # (like a parabola's vertex) stay well under that even at the vertex
    if best_idx is not None and best_angle > 35:
        return best_idx
    return None


def fit_run_recursive(pts: List[Point], axis: str, s: int, e: int, depth: int = 0, max_depth: int = 3):
    """
    Fit points[s..e] (inclusive, indices into the full point list) as a
    single polynomial if it fits well; otherwise split at the sharpest
    corner and recurse on each half. This is what lets a hard corner (a
    "V") become two equations while a smooth curve (a parabola) stays one,
    even though both are non-monotonic in the dependent variable.
    """
    dep = "y" if axis == "x" else "x"
    seg = pts[s:e + 1]
    u = np.array([getattr(p, axis) for p in seg])
    v = np.array([getattr(p, dep) for p in seg])
    fit = best_poly_fit(u, v)

    corner = None if depth >= max_depth or len(seg) < 6 else _find_corner_index(u, v)
    if corner is not None and (fit is None or fit["r2"] < 0.995):
        mid = s + corner
        left = fit_run_recursive(pts, axis, s, mid, depth + 1, max_depth)
        right = fit_run_recursive(pts, axis, mid, e, depth + 1, max_depth)
        return left + right

    if fit is None:
        return []
    return [(s, e, fit)]


def best_poly_fit(u: np.ndarray, v: np.ndarray):
    """
    Try increasing polynomial degree (1..min(len-1, 4)) and stop at the
    first degree that explains the data well (R^2 >= 0.995), so a simple
    line doesn't get reported as an unnecessary degree-4 curve.
    """
    max_deg = max(1, min(len(u) - 1, 4))
    best = None
    for deg in range(1, max_deg + 1):
        coeffs, r2 = _poly_fit_degree(u, v, deg)
        candidate = {"coeffs": coeffs, "r2": r2, "deg": deg}
        if best is None or r2 > best["r2"]:
            best = candidate
        if r2 >= 0.995:
            best = candidate
            break
    return best


# ----------------------------------------------------------------------
# Circle fitting (Kasa's algebraic method)
# ----------------------------------------------------------------------
def fit_circle(points: List[Point]) -> Optional[dict]:
    """
    Fit x^2 + y^2 + Dx + Ey + F = 0 by linear least squares (Kasa's method),
    then recover center (a, b) = (-D/2, -E/2) and radius r.
    Returns None if the fit isn't a valid circle (negative r^2) or the
    average radial error is too large relative to r (i.e. it's not
    actually circular, just closed).
    """
    xs = np.array([p.x for p in points])
    ys = np.array([p.y for p in points])
    A = np.column_stack([xs, ys, np.ones_like(xs)])
    b = -(xs ** 2 + ys ** 2)
    (D, E, F), *_ = np.linalg.lstsq(A, b, rcond=None)
    cx, cy = -D / 2, -E / 2
    r2v = cx ** 2 + cy ** 2 - F
    if r2v <= 0:
        return None
    r = float(np.sqrt(r2v))
    radial_err = float(np.mean(np.abs(np.hypot(xs - cx, ys - cy) - r)))
    if radial_err > 0.14 * r + 0.05:
        return None
    return {"cx": float(cx), "cy": float(cy), "r": r, "avg_err": radial_err}


# ----------------------------------------------------------------------
# Equation formatting
# ----------------------------------------------------------------------
def _fmt_num(n: float) -> float:
    r = round(n, 3)
    return 0.0 if r == 0 else r


def format_poly(coeffs: np.ndarray, indep_var: str, dep_var: str) -> str:
    terms = []
    for i in range(len(coeffs) - 1, -1, -1):
        c = _fmt_num(coeffs[i])
        if abs(c) < 0.001:
            continue
        neg = c < 0
        absval = abs(c)
        coef_str = "" if (i != 0 and abs(absval - 1) < 1e-9) else _trim(absval)
        var_str = "" if i == 0 else (indep_var if i == 1 else indep_var + SUPERSCRIPT.get(i, f"^{i}"))
        terms.append((neg, coef_str + var_str))
    if not terms:
        terms = [(False, "0")]
    out = ("-" if terms[0][0] else "") + terms[0][1]
    for neg, term in terms[1:]:
        out += (" - " if neg else " + ") + term
    return f"{dep_var} = {out}"


def _trim(x: float) -> str:
    s = f"{x:.3f}".rstrip("0").rstrip(".")
    return s if s else "0"


# ----------------------------------------------------------------------
# Top-level: stroke -> list[Equation]
# ----------------------------------------------------------------------
def process_stroke(raw_points: List[Point]) -> List[Equation]:
    if len(raw_points) < 2:
        return []
    pts = smooth(raw_points, window=5)

    xs = np.array([p.x for p in pts])
    ys = np.array([p.y for p in pts])
    range_x = float(xs.max() - xs.min())
    range_y = float(ys.max() - ys.min())
    bbox_diag = float(np.hypot(range_x, range_y))
    closed_dist = float(np.hypot(pts[0].x - pts[-1].x, pts[0].y - pts[-1].y))
    aspect = (max(range_x, range_y) / min(range_x, range_y)) if range_x > 0 and range_y > 0 else float("inf")

    # Closed, roughly-circular loop -> single circle equation
    if bbox_diag > 0.4 and closed_dist < 0.22 * bbox_diag and aspect < 1.8:
        circ = fit_circle(pts)
        if circ is not None:
            cx, cy, r = _fmt_num(circ["cx"]), _fmt_num(circ["cy"]), _fmt_num(circ["r"])
            x_term = "x\u00B2" if cx == 0 else f"(x {'-' if cx > 0 else '+'} {abs(cx)})\u00B2"
            y_term = "y\u00B2" if cy == 0 else f"(y {'-' if cy > 0 else '+'} {abs(cy)})\u00B2"
            return [Equation(
                latex=f"{x_term} + {y_term} = {_fmt_num(r * r)}",
                domain=f"radius {r}, center ({cx}, {cy})",
                meta="circle \u00B7 Kasa least-squares fit",
                index_range=(0, len(pts) - 1),
            )]

    # Pick whichever axis is monotonic (or closer to it) as the independent
    # variable -- e.g. a parabola should be reported as y = f(x) even if its
    # bounding box happens to be taller than it is wide, because x increases
    # steadily along the stroke while y doubles back at the vertex. Ties
    # (e.g. a straight line, monotonic in both) fall back to whichever axis
    # has more spread, since that's usually the more natural read.
    runs_x = split_monotonic_runs(pts, "x")
    runs_y = split_monotonic_runs(pts, "y")
    if len(runs_x) < len(runs_y):
        axis = "x"
    elif len(runs_y) < len(runs_x):
        axis = "y"
    else:
        axis = "x" if range_x >= range_y else "y"
    indep_var, dep_var = (axis, "y" if axis == "x" else "x")
    runs = runs_x if axis == "x" else runs_y

    equations = []
    for (s, e) in runs:
        if e - s < 1:
            continue
        for (rs, re, fit) in fit_run_recursive(pts, axis, s, e):
            seg = pts[rs:re + 1]
            if len(seg) < 2 or fit is None:
                continue
            u_seg = [getattr(p, axis) for p in seg]
            lo, hi = _fmt_num(min(u_seg)), _fmt_num(max(u_seg))
            equations.append(Equation(
                latex=format_poly(fit["coeffs"], indep_var, dep_var),
                domain=f"{lo} \u2264 {indep_var} \u2264 {hi}",
                meta=f"deg {fit['deg']} poly \u00B7 R\u00B2 = {_fmt_num(fit['r2'])}",
                index_range=(rs, re),
            ))
    return equations
