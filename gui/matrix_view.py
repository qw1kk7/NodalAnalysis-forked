"""Typeset matrix display for the Matrices tab."""

from typing import Optional

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QLabel, QScrollArea, QVBoxLayout, QWidget

from gui import theme
from gui.number_format import format_entry

SCALE = 2.0


def matrix_cells(matrix: list[list[float]]) -> list[list[tuple[str, bool]]]:
    """(text, is_fraction) for every entry, using the display rule in number_format."""
    return [[format_entry(val) for val in row] for row in matrix]


def render_matrix(
    matrix: list[list[float]],
    augmented: bool = False,
    unit: str = "",
    lead_label: str = "",
    side_labels: Optional[list[str]] = None,
) -> QImage:
    """Return an image of the matrix."""
    cells = matrix_cells(matrix)
    n_rows = len(cells)
    n_cols = max((len(r) for r in cells), default=0)

    num_font = theme.mono_font(10.0)
    lead_font = theme.ui_font(11.0, QFont.Weight.DemiBold)
    side_font = theme.ui_font(theme.SIZE_SMALL)
    num_m = QFontMetricsF(num_font)
    lead_m = QFontMetricsF(lead_font)
    side_m = QFontMetricsF(side_font)

    unit_text = f" {unit}" if unit else ""
    unit_w = num_m.horizontalAdvance(unit_text) if unit else 0.0

    col_gap = num_m.horizontalAdvance("0") * 2.6
    aug_gap = col_gap * 1.3
    bracket_pad = num_m.horizontalAdvance("0") * 1.9
    serif = 6.0
    bracket_w = 2.0
    row_h = num_m.height() * 1.55
    margin_v = 4.0

    col_w = [0.0] * n_cols
    for row in cells:
        for c, (text, _) in enumerate(row):
            col_w[c] = max(col_w[c], num_m.horizontalAdvance(text) + unit_w)

    gaps = [aug_gap if (augmented and c == n_cols - 2) else col_gap for c in range(max(n_cols - 1, 0))]

    lead_w = lead_m.horizontalAdvance(lead_label) + 12.0 if lead_label else 0.0
    left_x = lead_w + bracket_w
    content_x = left_x + bracket_pad
    content_w = sum(col_w) + sum(gaps)
    right_x = content_x + content_w + bracket_pad
    side_w = max((side_m.horizontalAdvance(s) for s in (side_labels or [])), default=0.0)
    width = right_x + bracket_w + (14.0 + side_w if side_labels else 2.0)
    height = margin_v * 2 + n_rows * row_h

    image = QImage(
        int(width * SCALE) + 2, int(height * SCALE) + 2, QImage.Format.Format_ARGB32_Premultiplied
    )
    image.fill(Qt.GlobalColor.transparent)
    image.setDevicePixelRatio(SCALE)

    p = QPainter(image)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setRenderHint(QPainter.RenderHint.TextAntialiasing)

    top, bottom = margin_v, height - margin_v

    left_mid = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
    right_mid = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
    if lead_label:
        theme.draw_text(p, QRectF(0, top, lead_w, bottom - top), lead_label, lead_font, theme.TEXT, left_mid)

    pen = QPen(QColor(theme.BRACKET), bracket_w)
    pen.setCapStyle(Qt.PenCapStyle.SquareCap)
    pen.setJoinStyle(Qt.PenJoinStyle.MiterJoin)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    for x, d in ((left_x, 1), (right_x, -1)):
        p.drawPolyline([QPointF(x + d * serif, top), QPointF(x, top), QPointF(x, bottom), QPointF(x + d * serif, bottom)])

    if augmented and n_cols >= 2:
        x = content_x + sum(col_w[:-1]) + sum(gaps[:-1]) + aug_gap / 2
        p.setPen(QPen(QColor(theme.ACCENT), 2.0))
        p.drawLine(QPointF(x, top + 4.0), QPointF(x, bottom - 4.0))

    for r, row in enumerate(cells):
        y = margin_v + r * row_h
        x = content_x
        for c, (text, is_fraction) in enumerate(row):
            if unit:
                theme.draw_text(p, QRectF(x, y, col_w[c], row_h), unit_text, num_font, theme.TEXT_MUTED, right_mid)
            cell = QRectF(x, y, col_w[c] - unit_w, row_h)
            theme.draw_text(p, cell, text, num_font, theme.FRACTION if is_fraction else theme.TEXT, right_mid)
            if c < len(gaps):
                x += col_w[c] + gaps[c]
        if side_labels and r < len(side_labels):
            rect = QRectF(right_x + bracket_w + 14.0, y, side_w + 2, row_h)
            theme.draw_text(p, rect, side_labels[r], side_font, theme.TEXT_FAINT, left_mid)
    p.end()
    return image


class MatrixPanel(QScrollArea):
    """Scrollable list of captioned, typeset matrices."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("MatrixPanel")
        self.setWidgetResizable(True)
        self.setFrameShape(QScrollArea.Shape.NoFrame)
        self._body = QWidget()
        self._body.setObjectName("MatrixPanelBody")
        self._layout = QVBoxLayout(self._body)
        self._layout.setContentsMargins(12, 12, 12, 12)
        self._layout.setSpacing(6)
        self._layout.addStretch(1)
        self.setWidget(self._body)

    def clear(self) -> None:
        while self._layout.count() > 1:
            item = self._layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.hide()
                widget.setParent(None)
                widget.deleteLater()

    def _add(self, widget: QWidget) -> None:
        self._layout.insertWidget(self._layout.count() - 1, widget)

    def add_matrix(self, caption: str, image: QImage, first: bool = False) -> None:
        if not first:
            self._layout.insertSpacing(self._layout.count() - 1, 12)
        self._add(theme.label(caption, "SectionTitle", theme.caption_font(uppercase=False)))
        picture = QLabel()
        picture.setPixmap(QPixmap.fromImage(image))
        picture.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self._add(picture)

    def show_matrices(
        self,
        matrix_g: list[list[float]],
        vector_i: list[float],
        upper_triangular: list[list[float]],
        node_names: list[str],
        node_voltages: list[float],
    ) -> None:
        self.clear()
        g_aug = [list(row) + [vector_i[i]] for i, row in enumerate(matrix_g)]
        self.add_matrix("AUGMENTED MATRIX [G | I]", render_matrix(g_aug, augmented=True), first=True)
        self.add_matrix("AFTER ELIMINATION [U | c]", render_matrix(upper_triangular, augmented=True))
        self.add_matrix(
            "SOLUTION",
            render_matrix([[v] for v in node_voltages], unit="V", lead_label="V =", side_labels=node_names),
        )
