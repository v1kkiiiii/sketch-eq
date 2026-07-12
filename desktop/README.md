# sketch·eq

Draw a freehand curve; get back the closed-form equation(s) that describe it,
with domain bounds, shown in a sidebar. Click an equation to highlight the
exact segment of your drawing it corresponds to.

## Setup

```bash
pip install -r requirements.txt
python3 main.py
```

## Project layout

```
fitting.py       pure numpy math core — no GUI dependency, unit-tested
canvas.py        the drawing surface (PyQt5 QWidget: mouse capture, rendering)
main.py          window assembly: sidebar, toolbar, wiring
test_fitting.py  correctness tests against known synthetic shapes
```

`fitting.py` is deliberately isolated from Qt so it can be tested and
reasoned about on its own — run `python3 test_fitting.py`.

## How a stroke becomes an equation

1. **Smoothing.** The raw mouse-drag points get a moving-average pass to
   remove hand jitter before anything else happens.

2. **Axis selection.** For each stroke, both x and y are checked for
   monotonicity. Whichever axis has *fewer* direction reversals becomes the
   independent variable. This matters: a parabola that happens to be taller
   than it is wide should still be reported as `y = f(x)`, not split into two
   inverted branches just because its bounding box is tall. Ties (e.g. a
   straight line, monotonic in both) fall back to whichever axis has more
   spread.

3. **Corner-aware recursive fitting.** Within a monotonic run, the segment is
   fit as a single polynomial first. If that fit is good (R² ≥ 0.995), it's
   left alone — a parabola's smooth vertex doesn't need to be split just
   because the curve turns. If the fit is poor, the algorithm looks for the
   sharpest actual corner (largest angle between incoming/outgoing chord
   vectors) and splits there, then recurses on each half. This is what makes
   a drawn "V" become two line equations while a drawn parabola stays one
   equation — the distinction is a real geometric corner vs. a smooth bend,
   not just "is the dependent variable monotonic."

4. **Polynomial regression.** Degree 1–4 least squares, tried in increasing
   order, stopping at the first degree with R² ≥ 0.995 (so a straight line
   doesn't get reported as an unnecessary quartic). Uses
   `numpy.polynomial.Polynomial.fit`, which rescales the independent variable
   internally before solving — important for conditioning, since raw
   Vandermonde matrices at degree 4 are numerically unstable — then the
   result is converted back to the standard power basis for display.

5. **Closed loops → circles.** If a stroke's endpoints nearly meet and its
   bounding box is roughly square, it skips polynomial fitting and instead
   runs a Kasa algebraic least-squares circle fit (linear least squares on
   `x² + y² + Dx + Ey + F = 0`), reporting `(x-a)² + (y-b)² = r²`.

## Known limitations / ideas for extending it

- Only circles are special-cased for closed shapes — ellipses, in general,
  would need a full conic fit (solving a generalized eigenvalue problem
  under a normalization constraint), which is a natural next step.
- No outlier rejection — a shaky hand mid-stroke will pull the fit. RANSAC
  or a robust (Huber) loss instead of plain least squares would help.
- The corner-detection angle threshold (35°) and R² threshold (0.995) are
  fixed constants; making them adaptive to stroke length/noise would be a
  reasonable improvement to point to if asked about limitations.
