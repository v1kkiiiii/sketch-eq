"""
Quick correctness checks for fitting.py against synthetic ground-truth
shapes. Run with: python3 test_fitting.py
"""
import numpy as np
from fitting import Point, process_stroke, fit_circle


def approx(a, b, tol=0.05):
    return abs(a - b) < tol


def test_line():
    pts = [Point(x, 2 * x + 3) for x in np.arange(-3, 3.01, 0.3)]
    eqs = process_stroke(pts)
    assert len(eqs) == 1, f"expected 1 equation, got {len(eqs)}"
    print("LINE:", eqs[0].latex, "|", eqs[0].domain, "|", eqs[0].meta)
    assert "R\u00B2 = 1.0" in eqs[0].meta

    pts2 = [Point(x, 0.5 * x + 3) for x in np.arange(-3, 3.01, 0.3)]
    eqs2 = process_stroke(pts2)
    assert len(eqs2) == 1
    print("LINE (gentle slope):", eqs2[0].latex)
    assert eqs2[0].latex.startswith("y =")
    assert "0.5" in eqs2[0].latex and "3" in eqs2[0].latex


def test_parabola():
    pts = [Point(x, x**2 - 2 * x + 1) for x in np.arange(-2, 2.01, 0.2)]
    eqs = process_stroke(pts)
    assert len(eqs) == 1
    print("PARABOLA:", eqs[0].latex, "|", eqs[0].meta)


def test_v_shape_splits_into_two_equations():
    left = [Point(x, abs(x)) for x in np.arange(-3, 0.01, 0.2)]
    right = [Point(x, abs(x)) for x in np.arange(0, 3.01, 0.2)]
    pts = left + right
    eqs = process_stroke(pts)
    print(f"V-SHAPE: {len(eqs)} equations")
    for e in eqs:
        print("  ", e.latex, "|", e.domain)
    assert len(eqs) == 2, f"expected V-shape to split into 2 equations, got {len(eqs)}"


def test_circle():
    t = np.arange(0, 2 * np.pi, 0.15)
    pts = [Point(2 + 3 * np.cos(a), -1 + 3 * np.sin(a)) for a in t]
    eqs = process_stroke(pts)
    assert len(eqs) == 1
    print("CIRCLE:", eqs[0].latex, "|", eqs[0].domain)
    assert "radius 2.9" in eqs[0].domain or "radius 3.0" in eqs[0].domain
    assert "center (2.0" in eqs[0].domain


def test_circle_fit_raw():
    t = np.linspace(0, 2 * np.pi, 40, endpoint=False)
    pts = [Point(5 + 1.5 * np.cos(a), -2 + 1.5 * np.sin(a)) for a in t]
    circ = fit_circle(pts)
    assert circ is not None
    assert approx(circ["cx"], 5) and approx(circ["cy"], -2) and approx(circ["r"], 1.5)
    print("RAW CIRCLE FIT:", circ)


if __name__ == "__main__":
    test_line()
    test_parabola()
    test_v_shape_splits_into_two_equations()
    test_circle()
    test_circle_fit_raw()
    print("\nALL TESTS PASSED")
