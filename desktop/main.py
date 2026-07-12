"""
main.py
-------
Entry point. Assembles the QMainWindow: canvas on the left, an equation
sidebar on the right with undo / clear / zoom controls. Run with:

    python3 main.py
"""

import sys
from PyQt5 import QtCore, QtGui, QtWidgets

from canvas import Canvas, Stroke

STYLE = """
QWidget { background: #0A0E1A; color: #E7ECFA; font-family: 'JetBrains Mono'; }
#Sidebar { background: #0D1224; border-left: 1px solid #1E2645; }
#Header { border-bottom: 1px solid #1E2645; }
#Wordmark { font-family: 'Fraunces', serif; font-size: 22px; font-weight: 600; }
#Tagline { color: #545F87; font-size: 10px; letter-spacing: 1px; }
#EqHeader { color: #545F87; font-size: 10px; letter-spacing: 1px; padding: 10px 4px 4px 4px; }
QScrollArea { border: none; }
#FooterNote { color: #545F87; font-size: 9px; padding: 8px 12px; border-top: 1px solid #1E2645; }
#EqCard { border-radius: 4px; padding: 2px; }
#EqCard:hover { background: #131A33; }
#EqMain { font-size: 13px; font-weight: 500; }
#EqDomain { color: #545F87; font-size: 10px; }
#EqMeta { color: #545F87; font-size: 9px; }
#StrokeLabel { color: #545F87; font-size: 10px; padding-top: 6px; }
#EmptyState { color: #545F87; font-size: 12px; padding: 30px 20px; }
#EmptyBig { color: #8993B8; font-family: 'Fraunces', serif; font-style: italic; font-size: 14px; }
"""


TOOL_BTN_STYLE = """
QPushButton {{
    background: transparent; border: 1px solid #1E2645; color: #8993B8;
    font-size: 10px; padding: 7px 4px; border-radius: 5px;
}}
QPushButton:hover {{ border-color: {hover}; color: {hover}; }}
QPushButton:disabled {{ color: #3A4266; border-color: #1E2645; }}
"""

ZOOM_BTN_STYLE = """
QPushButton {
    background: #0D1224; border: 1px solid #1E2645; color: #8993B8;
    border-radius: 4px; font-size: 13px; min-width: 26px; max-width: 26px;
    min-height: 26px; max-height: 26px;
}
QPushButton:hover { border-color: #7A6231; color: #F2B84B; }
"""


def style_tool_button(btn, danger=False):
    btn.setStyleSheet(TOOL_BTN_STYLE.format(hover="#E8687A" if danger else "#F2B84B"))


class EquationCard(QtWidgets.QFrame):
    clicked = QtCore.pyqtSignal()

    def __init__(self, eq, color_hex, selected):
        super().__init__()
        self.setObjectName("EqCard")
        self.setCursor(QtCore.Qt.PointingHandCursor)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(2)

        main_color = "#F2B84B" if selected else "#E7ECFA"
        main = QtWidgets.QLabel(eq.latex)
        main.setObjectName("EqMain")
        main.setStyleSheet(f"color: {main_color};")
        main.setWordWrap(True)

        domain = QtWidgets.QLabel(eq.domain)
        domain.setObjectName("EqDomain")

        meta = QtWidgets.QLabel(eq.meta.upper())
        meta.setObjectName("EqMeta")

        border_color = color_hex if selected else "transparent"
        bg = "#16203F" if selected else "transparent"
        self.setStyleSheet(
            f"#EqCard {{ border-left: 2px solid {border_color}; background: {bg}; }}"
            f"#EqCard:hover {{ background: #131A33; }}"
        )

        layout.addWidget(main)
        layout.addWidget(domain)
        layout.addWidget(meta)

    def mousePressEvent(self, e):
        self.clicked.emit()


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("sketch\u00B7eq")
        self.resize(1180, 760)

        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        root = QtWidgets.QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_header())

        body = QtWidgets.QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        root.addLayout(body)

        self.canvas = Canvas()
        self.canvas.strokeFinished.connect(self.refresh_sidebar)
        self.canvas.selectionChanged.connect(self.refresh_sidebar)
        body.addWidget(self.canvas, stretch=1)

        body.addWidget(self._build_sidebar())

        self._build_zoom_overlay()

    # ------------------------------------------------------------ header
    def _build_header(self):
        header = QtWidgets.QWidget()
        header.setObjectName("Header")
        h = QtWidgets.QVBoxLayout(header)
        h.setContentsMargins(24, 14, 24, 12)
        h.setSpacing(2)
        word = QtWidgets.QLabel('sketch<span style="color:#F2B84B;font-style:italic;font-weight:400;">\u00B7</span>eq')
        word.setObjectName("Wordmark")
        word.setTextFormat(QtCore.Qt.RichText)
        tagline = QtWidgets.QLabel("DRAW A LINE, GET ITS FUNCTION")
        tagline.setObjectName("Tagline")
        h.addWidget(word)
        h.addWidget(tagline)
        return header

    # ------------------------------------------------------------ sidebar
    def _build_sidebar(self):
        sidebar = QtWidgets.QWidget()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(340)
        v = QtWidgets.QVBoxLayout(sidebar)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        # toolbar
        toolbar = QtWidgets.QWidget()
        tl = QtWidgets.QHBoxLayout(toolbar)
        tl.setContentsMargins(14, 12, 14, 12)
        self.undo_btn = QtWidgets.QPushButton("\u21B6 undo")
        style_tool_button(self.undo_btn)
        self.undo_btn.clicked.connect(self._undo)
        self.clear_btn = QtWidgets.QPushButton("clear all")
        style_tool_button(self.clear_btn, danger=True)
        self.clear_btn.clicked.connect(self._clear)
        tl.addWidget(self.undo_btn)
        tl.addWidget(self.clear_btn)
        v.addWidget(toolbar)

        eq_header = QtWidgets.QLabel("EQUATIONS")
        eq_header.setObjectName("EqHeader")
        v.addWidget(eq_header)

        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        self.list_container = QtWidgets.QWidget()
        self.list_layout = QtWidgets.QVBoxLayout(self.list_container)
        self.list_layout.setContentsMargins(10, 0, 10, 10)
        self.list_layout.setSpacing(3)
        self.list_layout.addStretch()
        scroll.setWidget(self.list_container)
        v.addWidget(scroll, stretch=1)

        footer = QtWidgets.QLabel(
            "Fit via least-squares polynomial regression (deg. 1\u20134, "
            "R\u00B2-selected) with corner-aware segmentation \u00B7 closed "
            "loops fit as circles via Kasa's method"
        )
        footer.setObjectName("FooterNote")
        footer.setWordWrap(True)
        v.addWidget(footer)

        self.refresh_sidebar()
        return sidebar

    def _build_zoom_overlay(self):
        overlay = QtWidgets.QWidget(self.canvas)
        layout = QtWidgets.QHBoxLayout(overlay)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        zoom_out = QtWidgets.QPushButton("\u2013")
        zoom_out.setStyleSheet(ZOOM_BTN_STYLE)
        zoom_out.clicked.connect(lambda: self._zoom(1 / 1.2))
        self.zoom_label = QtWidgets.QLabel("100%")
        self.zoom_label.setStyleSheet("color:#545F87; font-size:11px;")
        self.zoom_label.setFixedWidth(40)
        self.zoom_label.setAlignment(QtCore.Qt.AlignCenter)
        zoom_in = QtWidgets.QPushButton("+")
        zoom_in.setStyleSheet(ZOOM_BTN_STYLE)
        zoom_in.clicked.connect(lambda: self._zoom(1.2))
        zoom_reset = QtWidgets.QPushButton("\u27F2")
        zoom_reset.setStyleSheet(ZOOM_BTN_STYLE)
        zoom_reset.clicked.connect(self._zoom_reset)

        layout.addWidget(zoom_out)
        layout.addWidget(self.zoom_label)
        layout.addWidget(zoom_in)
        layout.addWidget(zoom_reset)
        overlay.adjustSize()
        self._zoom_overlay = overlay
        self._position_zoom_overlay()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._position_zoom_overlay()

    def _position_zoom_overlay(self):
        if hasattr(self, "_zoom_overlay"):
            m = 18
            self._zoom_overlay.move(
                self.canvas.width() - self._zoom_overlay.width() - m,
                self.canvas.height() - self._zoom_overlay.height() - m,
            )

    # ------------------------------------------------------------ actions
    def _undo(self):
        self.canvas.undo()
        self.refresh_sidebar()

    def _clear(self):
        self.canvas.clear_all()
        self.refresh_sidebar()

    def _zoom(self, factor):
        self.canvas.set_zoom(factor)
        self.zoom_label.setText(f"{round(self.canvas.zoom * 100)}%")

    def _zoom_reset(self):
        self.canvas.reset_view()
        self.zoom_label.setText("100%")

    def refresh_sidebar(self):
        # clear existing cards
        while self.list_layout.count() > 1:
            item = self.list_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        self.undo_btn.setEnabled(bool(self.canvas.strokes))
        self.clear_btn.setEnabled(bool(self.canvas.strokes))

        if not self.canvas.strokes:
            empty = QtWidgets.QWidget()
            el = QtWidgets.QVBoxLayout(empty)
            big = QtWidgets.QLabel("nothing plotted yet")
            big.setObjectName("EmptyBig")
            desc = QtWidgets.QLabel(
                "draw a curve on the canvas and its equation will show up "
                "here. click an equation to highlight its line."
            )
            desc.setWordWrap(True)
            desc.setStyleSheet("color:#545F87; font-size:12px; margin-top:6px;")
            el.addWidget(big)
            el.addWidget(desc)
            container = QtWidgets.QWidget()
            container.setObjectName("EmptyState")
            outer = QtWidgets.QVBoxLayout(container)
            outer.addWidget(empty)
            self.list_layout.insertWidget(0, container)
            return

        for i, stroke in enumerate(self.canvas.strokes):
            label_text = f"LINE {i + 1}"
            if len(stroke.equations) > 1:
                label_text += f" \u00B7 {len(stroke.equations)} SEGMENTS"
            label = QtWidgets.QLabel(label_text)
            label.setObjectName("StrokeLabel")
            self.list_layout.insertWidget(self.list_layout.count() - 1, label)

            for eq in stroke.equations:
                selected = self.canvas.selected_eq is eq
                card = EquationCard(eq, stroke.color.name(), selected)
                card.clicked.connect(lambda s=stroke, e=eq: self._select(s, e))
                self.list_layout.insertWidget(self.list_layout.count() - 1, card)

    def _select(self, stroke: Stroke, eq):
        self.canvas.select_equation(stroke, eq)
        self.refresh_sidebar()

    def keyPressEvent(self, e):
        if e.modifiers() & QtCore.Qt.ControlModifier and e.key() == QtCore.Qt.Key_Z:
            self._undo()
        else:
            super().keyPressEvent(e)


def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setStyleSheet(STYLE)
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
