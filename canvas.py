"""
canvas.py
---------
The drawing surface: a QWidget subclass that captures freehand mouse
strokes, converts them to math-space coordinates, hands each finished
stroke to fitting.process_stroke(), and renders the grid / strokes /
selection highlight.
"""

from dataclasses import dataclass, field
from typing import List, Optional
from PyQt5 import QtCore, QtGui, QtWidgets

from fitting import Point, Equation, process_stroke

PALETTE = ["#5EEAD4", "#F2B84B", "#F87171", "#818CF8", "#4ADE80",
           "#F472B6", "#60A5FA", "#FBBF24", "#C084FC", "#2DD4BF"]

BG = QtGui.QColor("#0A0E1A")
GRID = QtGui.QColor("#161D38")
AXIS = QtGui.QColor("#313C67")
TICK_TEXT = QtGui.QColor("#545F87")
INK = QtGui.QColor("#E7ECFA")
ACCENT = QtGui.QColor("#F2B84B")


@dataclass
class Stroke:
    color: QtGui.QColor
    points: List[Point] = field(default_factory=list)   # math-space
    equations: List[Equation] = field(default_factory=list)


class Canvas(QtWidgets.QWidget):
    strokeFinished = QtCore.pyqtSignal()
    selectionChanged = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(False)
        self.setCursor(QtCore.Qt.CrossCursor)
        self.strokes: List[Stroke] = []
        self._raw_pixel_points: List[QtCore.QPointF] = []
        self._drawing = False
        self.base_scale = 40.0   # px per math unit at zoom = 1
        self.zoom = 1.0
        self.selected_eq: Optional[Equation] = None
        self.selected_stroke: Optional[Stroke] = None

        self._dash_offset = 0.0
        self._timer = QtCore.QTimer(self)
        self._timer.timeout.connect(self._tick)

    # ---------------------------------------------------------- coords
    def origin(self):
        return QtCore.QPointF(self.width() / 2, self.height() / 2)

    def to_math(self, px: QtCore.QPointF) -> Point:
        o = self.origin()
        s = self.base_scale * self.zoom
        return Point((px.x() - o.x()) / s, -(px.y() - o.y()) / s)

    def to_pixel(self, p: Point) -> QtCore.QPointF:
        o = self.origin()
        s = self.base_scale * self.zoom
        return QtCore.QPointF(o.x() + p.x * s, o.y() - p.y * s)

    # ---------------------------------------------------------- mouse
    def mousePressEvent(self, e: QtGui.QMouseEvent):
        if e.button() == QtCore.Qt.LeftButton:
            self._drawing = True
            self._raw_pixel_points = [QtCore.QPointF(e.pos())]
            self.update()

    def mouseMoveEvent(self, e: QtGui.QMouseEvent):
        if self._drawing:
            self._raw_pixel_points.append(QtCore.QPointF(e.pos()))
            self.update()

    def mouseReleaseEvent(self, e: QtGui.QMouseEvent):
        if self._drawing:
            self._drawing = False
            self._finish_stroke()

    def wheelEvent(self, e: QtGui.QWheelEvent):
        factor = 1.08 if e.angleDelta().y() > 0 else 1 / 1.08
        self.zoom = min(4.0, max(0.25, self.zoom * factor))
        self.update()

    def _finish_stroke(self):
        if len(self._raw_pixel_points) < 4:
            self._raw_pixel_points = []
            self.update()
            return
        math_pts = [self.to_math(p) for p in self._raw_pixel_points]
        color = QtGui.QColor(PALETTE[len(self.strokes) % len(PALETTE)])
        stroke = Stroke(color=color, points=math_pts)
        stroke.equations = process_stroke(math_pts)
        self.strokes.append(stroke)
        self._raw_pixel_points = []
        self.strokeFinished.emit()
        self.update()

    # ---------------------------------------------------------- actions
    def undo(self):
        if not self.strokes:
            return
        removed = self.strokes.pop()
        if self.selected_stroke is removed:
            self.selected_eq = None
            self.selected_stroke = None
            self._timer.stop()
        self.update()

    def clear_all(self):
        self.strokes = []
        self.selected_eq = None
        self.selected_stroke = None
        self._timer.stop()
        self.update()

    def select_equation(self, stroke: Stroke, eq: Optional[Equation]):
        if self.selected_eq is eq:
            self.selected_eq = None
            self.selected_stroke = None
            self._timer.stop()
        else:
            self.selected_eq = eq
            self.selected_stroke = stroke
            self._timer.start(30)
        self.selectionChanged.emit()
        self.update()

    def reset_view(self):
        self.zoom = 1.0
        self.update()

    def set_zoom(self, factor_or_value, absolute=False):
        self.zoom = factor_or_value if absolute else min(4.0, max(0.25, self.zoom * factor_or_value))
        self.update()

    def _tick(self):
        self._dash_offset = (self._dash_offset - 0.6) % 1000
        self.update()

    # ---------------------------------------------------------- paint
    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.fillRect(self.rect(), BG)
        self._draw_grid(painter)
        self._draw_strokes(painter)
        self._draw_highlight(painter)
        self._draw_in_progress(painter)
        painter.end()

    def _draw_grid(self, painter: QtGui.QPainter):
        w, h = self.width(), self.height()
        o = self.origin()
        s = self.base_scale * self.zoom

        painter.setPen(QtGui.QPen(GRID, 1))
        x = o.x() % s
        while x < w:
            painter.drawLine(QtCore.QPointF(x, 0), QtCore.QPointF(x, h))
            x += s
        y = o.y() % s
        while y < h:
            painter.drawLine(QtCore.QPointF(0, y), QtCore.QPointF(w, y))
            y += s

        painter.setPen(QtGui.QPen(AXIS, 1.4))
        painter.drawLine(QtCore.QPointF(0, o.y()), QtCore.QPointF(w, o.y()))
        painter.drawLine(QtCore.QPointF(o.x(), 0), QtCore.QPointF(o.x(), h))

        painter.setPen(QtGui.QPen(TICK_TEXT))
        font = QtGui.QFont("JetBrains Mono", 8)
        painter.setFont(font)
        step = 5 if self.zoom < 0.6 else (1 if self.zoom > 1.8 else 2)
        for ux in range(-40, 41, step):
            if ux == 0:
                continue
            px = self.to_pixel(Point(ux, 0))
            if 0 <= px.x() <= w:
                painter.drawText(QtCore.QPointF(px.x() + 3, o.y() + 13), str(ux))
        for uy in range(-40, 41, step):
            if uy == 0:
                continue
            px = self.to_pixel(Point(0, uy))
            if 0 <= px.y() <= h:
                painter.drawText(QtCore.QPointF(o.x() + 5, px.y() - 3), str(uy))

    def _draw_strokes(self, painter: QtGui.QPainter):
        for stroke in self.strokes:
            pen = QtGui.QPen(stroke.color, 2.25)
            pen.setCapStyle(QtCore.Qt.RoundCap)
            pen.setJoinStyle(QtCore.Qt.RoundJoin)
            painter.setPen(pen)
            path = QtGui.QPainterPath()
            pix = [self.to_pixel(p) for p in stroke.points]
            if pix:
                path.moveTo(pix[0])
                for p in pix[1:]:
                    path.lineTo(p)
                painter.drawPath(path)

    def _draw_highlight(self, painter: QtGui.QPainter):
        if self.selected_eq is None or self.selected_stroke is None:
            return
        s, e = self.selected_eq.index_range
        pts = self.selected_stroke.points[s:e + 1]
        if len(pts) < 2:
            return
        pix = [self.to_pixel(p) for p in pts]
        path = QtGui.QPainterPath()
        path.moveTo(pix[0])
        for p in pix[1:]:
            path.lineTo(p)

        painter.save()
        glow = QtGui.QPen(ACCENT, 9)
        glow.setCapStyle(QtCore.Qt.RoundCap)
        c = QtGui.QColor(ACCENT)
        c.setAlpha(60)
        glow.setColor(c)
        painter.setPen(glow)
        painter.drawPath(path)

        pen = QtGui.QPen(ACCENT, 4.5)
        pen.setCapStyle(QtCore.Qt.RoundCap)
        pen.setJoinStyle(QtCore.Qt.RoundJoin)
        pen.setStyle(QtCore.Qt.CustomDashLine)
        pen.setDashPattern([6, 5])
        pen.setDashOffset(self._dash_offset)
        painter.setPen(pen)
        painter.drawPath(path)
        painter.restore()

    def _draw_in_progress(self, painter: QtGui.QPainter):
        if not self._drawing or len(self._raw_pixel_points) < 2:
            return
        pen = QtGui.QPen(INK, 2.25)
        pen.setCapStyle(QtCore.Qt.RoundCap)
        c = QtGui.QColor(INK)
        c.setAlpha(150)
        pen.setColor(c)
        painter.setPen(pen)
        path = QtGui.QPainterPath()
        path.moveTo(self._raw_pixel_points[0])
        for p in self._raw_pixel_points[1:]:
            path.lineTo(p)
        painter.drawPath(path)
