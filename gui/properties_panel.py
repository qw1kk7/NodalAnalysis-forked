"""Properties editor and mathematical results panel."""

import html
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from gui import theme
from gui.components import ComponentItem, ExtractionResult
from gui.matrix_view import MatrixPanel
from gui.number_format import fixed, fraction_suffix
from math_engine.nodal_analysis import SolutionResult


def _report_html(text: str) -> str:
    """Present a plain-text report with real headings."""
    heading_style = (
        f"font-family: '{theme.UI_FONT_FAMILY}'; font-size: {theme.SIZE_SMALL}pt; "
        f"font-weight: bold; color: {theme.TEXT_MUTED};"
    )
    mono_families = ", ".join(f"'{f}'" for f in theme.MONO_FONT_FAMILIES)
    pre_style = f"font-family: {mono_families}, monospace; font-size: {theme.SIZE_MONO}pt; color: {theme.TEXT}; margin: 0;"
    parts: list[str] = []
    block: list[str] = []
    first_heading = True

    def flush() -> None:
        while block and not block[-1].strip():
            block.pop()
        while block and not block[0].strip():
            block.pop(0)
        if block:
            parts.append(f'<pre style="{pre_style}">{html.escape(chr(10).join(block))}</pre>')
        block.clear()

    for line in text.split("\n"):
        stripped = line.strip()
        if stripped.startswith("===") and stripped.endswith("===") and len(stripped) > 6:
            flush()
            top, first_heading = (0 if first_heading else 14), False
            title = html.escape(stripped.strip("= "))
            parts.append(f'<p style="{heading_style} margin-top: {top}px; margin-bottom: 4px;">{title}</p>')
        else:
            block.append(line)
    flush()
    return "".join(parts)


class PropertiesPanel(QWidget):
    """Right-hand panel for editing selected component values and viewing solver results."""

    value_changed = Signal(str, float)  # (component_id, new_value)
    flip_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("PropertiesPanel")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setMinimumWidth(360)
        self._current_comp_id: Optional[str] = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 14, 12, 12)
        layout.setSpacing(6)

        # --- Selected Item Properties ---
        layout.addWidget(theme.label("Selected Item", "SectionTitle", theme.caption_font()))

        self.prop_group = QGroupBox()
        self.prop_form = QFormLayout(self.prop_group)
        self.prop_form.setHorizontalSpacing(14)
        self.prop_form.setVerticalSpacing(7)
        self.prop_form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        self.lbl_id = QLabel("—")
        self.lbl_type = QLabel("—")
        self.lbl_value_title = QLabel("Value:")
        self.edit_value = QLineEdit()
        self.edit_value.setVisible(False)
        self.edit_value.editingFinished.connect(self._on_value_edited)

        self.btn_flip = QPushButton("Flip Direction (180°)")
        self.btn_flip.setVisible(False)
        self.btn_flip.clicked.connect(self.flip_requested.emit)

        self.lbl_extra_1_title = QLabel("")
        self.lbl_extra_1 = QLabel("")
        self.lbl_extra_2_title = QLabel("")
        self.lbl_extra_2 = QLabel("")
        self.lbl_extra_3_title = QLabel("")
        self.lbl_extra_3 = QLabel("")

        id_title = QLabel("ID:")
        type_title = QLabel("Type:")
        for title_lbl in (
            id_title,
            type_title,
            self.lbl_value_title,
            self.lbl_extra_1_title,
            self.lbl_extra_2_title,
            self.lbl_extra_3_title,
        ):
            title_lbl.setObjectName("FormLabel")
        self.lbl_id.setObjectName("SelectionId")
        self.lbl_type.setObjectName("SelectionType")
        for value_lbl in (self.lbl_extra_1, self.lbl_extra_2, self.lbl_extra_3):
            value_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        self.prop_form.addRow(id_title, self.lbl_id)
        self.prop_form.addRow(type_title, self.lbl_type)
        self.prop_form.addRow(self.lbl_value_title, self.edit_value)
        self.prop_form.addRow("", self.btn_flip)
        self.prop_form.addRow(self.lbl_extra_1_title, self.lbl_extra_1)
        self.prop_form.addRow(self.lbl_extra_2_title, self.lbl_extra_2)
        self.prop_form.addRow(self.lbl_extra_3_title, self.lbl_extra_3)

        layout.addWidget(self.prop_group)
        layout.addSpacing(10)

        # --- Solver Status & Results ---
        layout.addWidget(theme.label("Results", "SectionTitle", theme.caption_font()))
        self.status_label = theme.label(wrap=True)
        self._set_status("Status: Not Solved", theme.STATUS_NEUTRAL)
        layout.addWidget(self.status_label)
        layout.addSpacing(4)

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(False)
        self.summary_text, self.branches_text = QTextEdit(), QTextEdit()
        for box in (self.summary_text, self.branches_text):
            box.setReadOnly(True)
            box.setFont(theme.mono_font())
            box.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self.matrices_view = MatrixPanel()

        self.tabs.addTab(self.summary_text, "Nodes && Verify")
        self.tabs.addTab(self.branches_text, "Branches")
        self.tabs.addTab(self.matrices_view, "Matrices (G, I, U)")
        layout.addWidget(self.tabs, stretch=1)

        self.show_empty_selection()

    def _set_status(self, text: str, variant: tuple[str, str, str]) -> None:
        self.status_label.setText(text)
        self.status_label.setStyleSheet(theme.status_style(variant))

    def _on_value_edited(self) -> None:
        if self._current_comp_id is None:
            return
        try:
            val = float(self.edit_value.text().strip())
        except ValueError:
            return
        self.value_changed.emit(self._current_comp_id, val)

    def _set_extra_rows(self, rows: list[tuple[str, str]]) -> None:
        widgets = [
            (self.lbl_extra_1_title, self.lbl_extra_1),
            (self.lbl_extra_2_title, self.lbl_extra_2),
            (self.lbl_extra_3_title, self.lbl_extra_3),
        ]
        for idx, (title_lbl, val_lbl) in enumerate(widgets):
            if idx < len(rows):
                title_lbl.setText(rows[idx][0])
                val_lbl.setText(rows[idx][1])
                title_lbl.setVisible(True)
                val_lbl.setVisible(True)
            else:
                title_lbl.setVisible(False)
                val_lbl.setVisible(False)

    def show_empty_selection(self) -> None:
        self._current_comp_id = None
        self.lbl_id.setText("—")
        self.lbl_type.setText("Nothing Selected")
        self.lbl_value_title.setVisible(False)
        self.edit_value.setVisible(False)
        self.btn_flip.setVisible(False)
        self._set_extra_rows([])

    def show_component(
        self,
        comp: ComponentItem,
        solution: Optional[SolutionResult],
        extraction: Optional[ExtractionResult],
    ) -> None:
        self._current_comp_id = comp.component_id
        self.lbl_id.setText(comp.component_id)

        if comp.kind == "resistor":
            self.lbl_type.setText("Resistor")
            self.lbl_value_title.setText("Resistance (Ω):")
            self.lbl_value_title.setVisible(True)
            self.edit_value.setText(f"{comp.value:g}")
            self.edit_value.setVisible(True)
            self.btn_flip.setVisible(False)

            if solution is not None:
                res = next(
                    (r for r in solution.resistor_results if r.component_id == comp.component_id),
                    None,
                )
                if res is not None:
                    self._set_extra_rows(
                        [
                            ("Voltage Drop:", f"{fixed(res.voltage_drop, 4)} V ({res.node_a} → {res.node_b})"),
                            ("Current:", f"{fixed(res.current, 4)} A"),
                            ("Power:", f"{fixed(res.power, 4)} W"),
                        ]
                    )
                    return
            self._set_extra_rows([("Calculated:", "Click Solve Circuit to view")])

        elif comp.kind == "current_source":
            self.lbl_type.setText("DC Current Source")
            self.lbl_value_title.setText("Current (A):")
            self.lbl_value_title.setVisible(True)
            self.edit_value.setText(f"{comp.value:g}")
            self.edit_value.setVisible(True)
            self.btn_flip.setVisible(True)

            direction_str = "T1 → T2 (arrow direction)"
            if extraction is not None:
                n_from = extraction.endpoint_to_node.get(("terminal", comp.component_id, 0), "?")
                n_to = extraction.endpoint_to_node.get(("terminal", comp.component_id, 1), "?")
                direction_str = f"{n_from} → {n_to}"
            self._set_extra_rows([("Direction:", direction_str)])

        elif comp.kind == "ground":
            self.lbl_type.setText("Ground Reference")
            self.lbl_value_title.setVisible(False)
            self.edit_value.setVisible(False)
            self.btn_flip.setVisible(False)
            self._set_extra_rows([("Voltage:", "0 V")])

    def show_wire(
        self,
        wire_id: str,
        solution: Optional[SolutionResult],
        extraction: Optional[ExtractionResult],
    ) -> None:
        self._current_comp_id = None
        self.lbl_id.setText(wire_id)
        self.lbl_type.setText("Ideal Wire (0 Ω)")
        self.lbl_value_title.setVisible(False)
        self.edit_value.setVisible(False)
        self.btn_flip.setVisible(False)

        if extraction is not None and wire_id in extraction.wire_to_node:
            node_name = extraction.wire_to_node[wire_id]
            connected = ", ".join(extraction.wire_to_components.get(wire_id, [])) or "None"
            if node_name == "GND":
                voltage_str = "0 V (Ground)"
            elif solution is not None and node_name in solution.node_voltages:
                voltage = solution.node_voltages[node_name]
                voltage_str = f"{fixed(voltage, 4)} V{fraction_suffix(voltage)}"
            else:
                voltage_str = "Not Solved"
            self._set_extra_rows(
                [
                    ("Node:", node_name),
                    ("Node Voltage:", voltage_str),
                    ("Connected:", connected),
                ]
            )
        else:
            self._set_extra_rows([("Node:", "Click Solve Circuit to inspect")])

    def clear_results(self, message: str = "Status: Circuit Modified — Click Solve Circuit") -> None:
        self._set_status(message, theme.STATUS_WARNING)
        self.summary_text.clear()
        self.branches_text.clear()
        self.matrices_view.clear()

    def show_error(self, error_message: str) -> None:
        self._set_status(f"Error: {error_message}", theme.STATUS_ERROR)
        self.summary_text.setPlainText(f"Cannot solve circuit:\n{error_message}")
        self.branches_text.clear()
        self.matrices_view.clear()

    def show_solution(self, solution: SolutionResult, extraction: ExtractionResult) -> None:
        v = solution.verification
        if v.passed:
            self._set_status("Verification: PASSED (G*V = I and KCL satisfied)", theme.STATUS_SUCCESS)
        else:
            self._set_status("Verification: FAILED (numerical residual exceeded tolerance)", theme.STATUS_ERROR)

        # 1. Summary & Verification tab
        summary_lines = ["=== Node Voltages ==="]
        all_nodes = ["GND"] + solution.non_ground_nodes
        v_width = max(len(fixed(solution.node_voltages[n], 6)) for n in all_nodes)
        for node_name in all_nodes:
            voltage = solution.node_voltages[node_name]
            summary_lines.append(
                f"  {node_name:<6} : {fixed(voltage, 6, v_width)} V{fraction_suffix(voltage)}"
            )

        summary_lines.append("\n=== Verification ===")
        summary_lines.append(f"  Passed        : {v.passed}")
        summary_lines.append(f"  Max Residual  : {v.max_residual:.3e}")
        summary_lines.append(f"  Max KCL Error : {v.max_kcl_error:.3e}")
        summary_lines.append("\n  KCL Sum per Node:")
        for node_name, err in v.kcl_errors.items():
            summary_lines.append(f"    {node_name:<6} : {err:+.3e} A")
        self.summary_text.setHtml(_report_html("\n".join(summary_lines)))

        # 2. Branches tab
        branch_lines = ["=== Resistors (Ohm's Law) ==="]
        if not solution.resistor_results:
            branch_lines.append("  (None)")
        results = solution.resistor_results
        vd_w = max((len(fixed(r.voltage_drop, 4)) for r in results), default=0)
        i_w = max((len(fixed(r.current, 4)) for r in results), default=0)
        p_w = max((len(fixed(r.power, 4)) for r in results), default=0)
        for r in results:
            branch_lines.append(
                f"  {r.component_id:<4} ({r.node_a} -> {r.node_b}, R={r.resistance:g} Ω):\n"
                f"       V_drop = {fixed(r.voltage_drop, 4, vd_w)} V | I = {fixed(r.current, 4, i_w)} A"
                f" | P = {fixed(r.power, 4, p_w)} W"
            )

        branch_lines.append("\n=== DC Current Sources ===")
        if not extraction.circuit.current_sources:
            branch_lines.append("  (None)")
        sources = extraction.circuit.current_sources
        src_w = max((len(fixed(src.current, 4)) for src in sources), default=0)
        for src in sources:
            branch_lines.append(
                f"  {src.component_id:<4} ({src.node_from} -> {src.node_to}): I = {fixed(src.current, 4, src_w)} A"
            )
        self.branches_text.setHtml(_report_html("\n".join(branch_lines)))

        # 3. Matrices tab
        nodes = solution.non_ground_nodes
        self.matrices_view.show_matrices(
            matrix_g=solution.matrix_g,
            vector_i=solution.vector_i,
            upper_triangular=solution.upper_triangular,
            node_names=nodes,
            node_voltages=[solution.node_voltages[n] for n in nodes],
        )
