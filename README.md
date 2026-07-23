# sketch·eq

Draw a freehand curve and get back the actual equation for it, with domain bounds, shown live in a sidebar as you draw.

Try the live web version: https://sketch-eq-production.up.railway.app/

Two versions of the app, same math underneath:
- desktop/ : PyQt5 desktop app
- web/ : Flask API + JS canvas frontend

The short version of how it works: each stroke gets fit with least squares polynomial regression, with the degree picked automatically based on R². There's a corner detection step too, so a drawn "V" splits into two line equations instead of getting jammed into one bad curve. Closed loops get fit as circles instead, using Kasa's method.

More detail in desktop/README.md and web/README.md.
