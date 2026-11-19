"""Main application window coordinating the component toolbar, canvas, and results panel."""

from typing import Optional

from PySide6.QtCore import QMimeData, QPoint, QPointF, QSize, Qt
from PySide6.QtGui import QColor, QDrag, QIcon, QMouseEvent, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import (
    QHBoxLayout,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from gui.circuit_canvas import MIME_TYPE, CircuitCanvas
from gui.components import extract_circuit_from_gui
from gui.properties_panel import PropertiesPanel
from gui import theme
from math_engine.circuit import InvalidCircuitError
from math_engine.nodal_analysis import solve_circuit


def _symbol_icon(kind: str) -> QIcon:
    """Small schematic symbol drawn with QPainter, used on the palette buttons."""
    size = 28
    pixmap = QPixmap(size * 2, size * 2)
    pixmap.setDevicePixelRatio(2.0)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(QPen(QColor(theme.INK), 1.6))
    painter.translate(size / 2, size / 2)
    if kind == "resistor":
        path = QPainterPath()
        path.moveTo(-13, 0)
        for x, y in [(-8, 0), (-6, -5), (-2, 5), (2, -5), (6, 5), (8, 0), (13, 0)]:
            path.lineTo(x, y)
        painter.drawPath(path)
        segments = []
    elif kind == "current_source":
        painter.drawEllipse(QPointF(0, 0), 8.5, 8.5)
        segments = [((-5, 0), (5, 0)), ((2, -3), (5, 0)), ((2, 3), (5, 0))]
    else:
        segments = [((0, -10), (0, -2)), ((-9, -2), (9, -2)), ((-5.5, 2.5), (5.5, 2.5)), ((-2, 7), (2, 7))]
    for a, b in segments:
        painter.drawLine(QPointF(*a), QPointF(*b))
    painter.end()
    return QIcon(pixmap)


class DraggableComponentButton(QPushButton):
    """Toolbar button that supports both drag-and-drop onto the canvas and click-to-place."""

    def __init__(self, label: str, kind: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(label, parent)
        self.kind = kind
        self._drag_start_pos: Optional[QPoint] = None
        self.setObjectName("PaletteButton")
        self.setIcon(_symbol_icon(kind))
        self.setIconSize(QSize(28, 28))
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.setToolTip("Drag onto the canvas, or click to place in the centre")

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start_pos = event.position().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if not (event.buttons() & Qt.MouseButton.LeftButton) or self._drag_start_pos is None:
            return
        if (event.position().toPoint() - self._drag_start_pos).manhattanLength() < 8:
            return
        drag = QDrag(self)
        mime = QMimeData()
        mime.setData(MIME_TYPE, self.kind.encode("utf-8"))
        drag.setMimeData(mime)
        drag.exec(Qt.DropAction.CopyAction)
        self._drag_start_pos = None


class MainWindow(QMainWindow):
    """Top-level window for the DC Nodal Analysis Circuit Simulator."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("DC Circuit Simulator — Nodal Analysis & Gaussian Elimination")
        self.resize(1320, 800)
        self.setMinimumSize(960, 600)

        self.canvas = CircuitCanvas()
        self.properties_panel = PropertiesPanel()

        self._build_top_toolbar()
        self._build_central_layout()
        self._connect_signals()

    def _build_top_toolbar(self) -> None:
        toolbar = QToolBar("Actions")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        self.btn_select_mode = QPushButton("Select / Move")
        self.btn_select_mode.setCheckable(True)
        self.btn_select_mode.setChecked(True)

        self.btn_wire_mode = QPushButton("Wire / Junction")
        self.btn_wire_mode.setCheckable(True)

        self.btn_rotate = QPushButton("Rotate (R)")
        self.btn_delete = QPushButton("Delete (Del)")
        self.btn_clear = QPushButton("Clear All")

        self.btn_solve = QPushButton("Solve Circuit")
        self.btn_solve.setObjectName("PrimaryButton")
        self.btn_solve.setToolTip("Build G·V = I and solve it with Gaussian elimination")

        self.btn_select_mode.setToolTip("Select, move and edit components")
        self.btn_wire_mode.setToolTip("Click an existing wire to branch from a new junction")

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        toolbar.addWidget(self.btn_select_mode)
        toolbar.addWidget(self.btn_wire_mode)
        toolbar.addSeparator()
        toolbar.addWidget(self.btn_rotate)
        toolbar.addWidget(self.btn_delete)
        toolbar.addWidget(self.btn_clear)
        toolbar.addWidget(spacer)
        toolbar.addWidget(self.btn_solve)

    def _build_central_layout(self) -> None:
        # Left Component Palette
        palette = QWidget()
        palette.setObjectName("PaletteSidebar")
        palette.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        palette.setFixedWidth(200)
        palette_layout = QVBoxLayout(palette)
        palette_layout.setContentsMargins(12, 14, 12, 12)
        palette_layout.setSpacing(6)

        palette_layout.addWidget(theme.label("Components", "SectionTitle", theme.caption_font()))
        palette_layout.addWidget(theme.label("Drag onto the canvas or click", "SectionHint"))
        palette_layout.addSpacing(4)

        self.btn_resistor = DraggableComponentButton("Resistor", "resistor")
        self.btn_current_source = DraggableComponentButton("Current Source", "current_source")
        self.btn_ground = DraggableComponentButton("Ground", "ground")

        palette_layout.addWidget(self.btn_resistor)
        palette_layout.addWidget(self.btn_current_source)
        palette_layout.addWidget(self.btn_ground)

        palette_layout.addSpacing(16)
        palette_layout.addWidget(theme.label("How To", "SectionTitle", theme.caption_font()))
        help_text = (
            "Click a terminal to start a wire, then click another terminal to finish it."
            "<br><br>While wiring, click an existing wire to add a junction."
            "<br><br>Scroll to zoom. Right or middle drag to pan."
            "<br><br><b>R</b> Rotate &nbsp;&middot;&nbsp; <b>Del</b> Delete"
            "<br><b>Esc</b> Cancel Wire"
        )
        palette_layout.addWidget(theme.label(help_text, "HelpText", wrap=True))
        palette_layout.addStretch(1)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)
        splitter.setChildrenCollapsible(False)
        splitter.addWidget(palette)
        splitter.addWidget(self.canvas)
        splitter.addWidget(self.properties_panel)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 0)
        splitter.setSizes([200, 720, 420])

        container = QWidget()
        container_layout = QHBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.addWidget(splitter)
        self.setCentralWidget(container)

    def _connect_signals(self) -> None:
        self.btn_select_mode.clicked.connect(lambda: self._set_mode("select"))
        self.btn_wire_mode.clicked.connect(lambda: self._set_mode("wire"))
        self.btn_rotate.clicked.connect(self.canvas.rotate_selected)
        self.btn_delete.clicked.connect(self.canvas.delete_selected)
        self.btn_clear.clicked.connect(self.canvas.clear_all)
        self.btn_solve.clicked.connect(self.solve_current_circuit)

        self.btn_resistor.clicked.connect(lambda: self._place_near_center("resistor"))
        self.btn_current_source.clicked.connect(lambda: self._place_near_center("current_source"))
        self.btn_ground.clicked.connect(lambda: self._place_near_center("ground"))

        self.canvas.selection_changed.connect(self._on_selection_changed)
        self.canvas.circuit_modified.connect(self._on_circuit_modified)
        self.properties_panel.value_changed.connect(self._on_component_value_changed)
        self.properties_panel.flip_requested.connect(self.canvas.flip_selected_current_source)

    def _set_mode(self, mode: str) -> None:
        self.btn_select_mode.setChecked(mode == "select")
        self.btn_wire_mode.setChecked(mode == "wire")
        self.canvas.set_mode(mode)

    def _place_near_center(self, kind: str) -> None:
        center = self.canvas.screen_to_world(self.canvas.rect().center().toPointF())
        self.canvas.add_component(kind, center.x(), center.y())

    def _on_selection_changed(self, kind: Optional[str], item_id: Optional[str]) -> None:
        if kind == "component" and item_id in self.canvas.components:
            self.properties_panel.show_component(
                self.canvas.components[item_id],
                self.canvas.solution,
                self.canvas.extraction,
            )
        elif kind == "wire" and item_id in self.canvas.wires:
            self.properties_panel.show_wire(
                item_id,
                self.canvas.solution,
                self.canvas.extraction,
            )
        else:
            self.properties_panel.show_empty_selection()

    def _on_circuit_modified(self) -> None:
        self.canvas.clear_solution()
        self.properties_panel.clear_results()
        self._on_selection_changed(self.canvas.selected_kind, self.canvas.selected_id)

    def _on_component_value_changed(self, component_id: str, new_value: float) -> None:
        comp = self.canvas.components.get(component_id)
        if comp is None or comp.value == new_value:
            return
        comp.value = new_value
        self.canvas.update()
        self._on_circuit_modified()

    def solve_current_circuit(self) -> None:
        try:
            extraction = extract_circuit_from_gui(
                components=list(self.canvas.components.values()),
                junctions=list(self.canvas.junctions.values()),
                wires=list(self.canvas.wires.values()),
            )
            solution = solve_circuit(extraction.circuit)
        except InvalidCircuitError as exc:
            self.canvas.clear_solution()
            self.properties_panel.show_error(str(exc))
            return

        self.canvas.set_solution(solution, extraction)
        self.properties_panel.show_solution(solution, extraction)
        self._on_selection_changed(self.canvas.selected_kind, self.canvas.selected_id)
