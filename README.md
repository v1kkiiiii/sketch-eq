# sketch·eq

Draw a freehand curve, get back the closed-form equation(s) that describe it — fit via least-squares polynomial regression with automatic degree selection, corner-aware segmentation, and circle fitting for closed loops.

**[Try the live web version →](https://sketch-eq-production.up.railway.app/)**

Two interfaces sharing one math core:
- [`desktop/`](./desktop) — PyQt5 desktop app
- [`web/`](./web) — Flask API + JS canvas frontend
