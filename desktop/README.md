# sketch·eq (desktop)

Draw a freehand curve, get back the closed form equation for it, with domain bounds, shown in a sidebar. Click an equation and it highlights the exact part of your drawing it came from.

## Setup

pip install -r requirements.txt
python3 main.py


## Project layout

fitting.py math core, plain numpy, no GUI dependency, unit tested
canvas.py the drawing surface (PyQt5 widget, mouse capture and rendering)
main.py window setup: sidebar, toolbar, wiring it together
test_fitting.py tests against known shapes (lines, parabolas, circles, etc)


fitting.py is kept separate from Qt on purpose so it's easy to test and reason about on its own. Run `python3 test_fitting.py` to see it pass.

## How a stroke turns into an equation

1. Smoothing. Raw mouse points get averaged a bit to remove hand jitter before anything else happens.

2. Axis selection. For each stroke, check both x and y for how monotonic they are. Whichever one has fewer direction reversals becomes the independent variable. This matters because a parabola that's taller than it is wide should still come back as y = f(x), not get split into two backwards branches just because its bounding box happens to be tall.

3. Corner aware fitting. Each segment gets fit as one polynomial first. If that fit is good (R² above 0.995), it's left alone, a parabola's smooth vertex doesn't need to be split just because the curve turns. If the fit is bad, the code looks for the sharpest actual corner and splits there, then repeats on each half. This is what makes a drawn "V" turn into two line equations while a drawn parabola stays one. The difference is a real geometric corner versus a smooth bend, not just whether y stopped increasing.

4. Polynomial regression. Degrees 1 through 4, tried in order, stopping at the first one with R² of 0.995 or higher, so a straight line doesn't come back as an unnecessary degree 4 curve. Uses numpy's Polynomial.fit, which rescales x internally before solving for numerical stability, then converts back to a normal polynomial for display.

5. Closed loops become circles. If a stroke's start and end nearly meet and its bounding box is roughly square, it skips the polynomial step and fits a circle instead, using Kasa's least squares method.

## Known limitations, ideas if you want to extend it

- Only circles are special cased for closed shapes. Ellipses would need a full conic fit, that's a natural next step.
- No outlier rejection right now, a shaky hand mid stroke pulls the fit off. RANSAC or a robust loss function instead of plain least squares would help.
- The corner detection angle (35 degrees) and R² cutoff (0.995) are fixed numbers right now. Making them adapt to stroke length or noise would be a reasonable improvement to mention if asked about limitations.
