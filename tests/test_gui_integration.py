"""Integration tests for GUI-to-math conversion, multiple grounds, and solution invalidation."""

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from gui.components import (
    ComponentItem,
    WireJunction,
    WireSegment,
    extract_circuit_from_gui,
)
from gui.main_window import MainWindow
from math_engine.circuit import InvalidCircuitError
from math_engine.nodal_analysis import solve_circuit


class TestGuiIntegration(unittest.TestCase):
    """Verify GUI circuit extraction and MainWindow solve/invalidation lifecycle."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_6_multiple_grounds_on_same_node_vs_disconnected(self) -> None:
        """Multiple grounds wired to the same node act as one GND; disconnected grounds fail."""
        components = [
            ComponentItem("I1", "current_source", 0, 0, value=2.0),
            ComponentItem("R1", "resistor", 100, 0, value=4.0),
            ComponentItem("GND1", "ground", 0, 100),
            ComponentItem("GND2", "ground", 100, 100),
        ]
        # Both grounds connect to I1.T0 and R1.T1 -> same electrical node.
        wires = [
            WireSegment("W1", ("terminal", "I1", 1), ("terminal", "R1", 0)),
            WireSegment("W2", ("terminal", "I1", 0), ("terminal", "GND1", 0)),
            WireSegment("W3", ("terminal", "R1", 1), ("terminal", "GND2", 0)),
            WireSegment("W4", ("terminal", "GND1", 0), ("terminal", "GND2", 0)),
        ]
        extraction = extract_circuit_from_gui(components, [], wires)
        result = solve_circuit(extraction.circuit)
        self.assertAlmostEqual(result.node_voltages["N1"], 8.0, places=9)
        self.assertTrue(result.verification.passed)

        # Remove W4 and W3 so GND2 is disconnected from GND1.
        disconnected_wires = [
            WireSegment("W1", ("terminal", "I1", 1), ("terminal", "R1", 0)),
            WireSegment("W2", ("terminal", "I1", 0), ("terminal", "GND1", 0)),
        ]
        with self.assertRaises(InvalidCircuitError):
            extract_circuit_from_gui(components, [], disconnected_wires)

    def test_wire_junction_connects_three_branches(self) -> None:
        """Parallel resistors joined via an explicit WireJunction solve to 4.8 V."""
        components = [
            ComponentItem("I1", "current_source", 0, 0, value=2.0),
            ComponentItem("R1", "resistor", 100, -40, value=4.0),
            ComponentItem("R2", "resistor", 100, 40, value=6.0),
            ComponentItem("GND1", "ground", 0, 120),
        ]
        junctions = [
            WireJunction("J1", 40, 0),
            WireJunction("J2", 160, 120),
        ]
        wires = [
            WireSegment("W1", ("terminal", "I1", 1), ("junction", "J1", 0)),
            WireSegment("W2", ("junction", "J1", 0), ("terminal", "R1", 0)),
            WireSegment("W3", ("junction", "J1", 0), ("terminal", "R2", 0)),
            WireSegment("W4", ("terminal", "R1", 1), ("junction", "J2", 0)),
            WireSegment("W5", ("terminal", "R2", 1), ("junction", "J2", 0)),
            WireSegment("W6", ("junction", "J2", 0), ("terminal", "GND1", 0)),
            WireSegment("W7", ("terminal", "I1", 0), ("terminal", "GND1", 0)),
        ]
        extraction = extract_circuit_from_gui(components, junctions, wires)
        result = solve_circuit(extraction.circuit)
        self.assertAlmostEqual(result.node_voltages["N1"], 4.8, places=9)
        self.assertTrue(result.verification.passed)

    def test_7_main_window_solve_and_invalidation_on_edit(self) -> None:
        """Modifying a resistor value in MainWindow invalidates previous results until re-solved."""
        window = MainWindow()
        i1 = window.canvas.add_component("current_source", 0, 0)
        i1.value = 2.0
        r1 = window.canvas.add_component("resistor", 140, 0)
        r1.value = 4.0
        gnd = window.canvas.add_component("ground", 0, 100)

        window.canvas._create_wire(("terminal", i1.component_id, 1), ("terminal", r1.component_id, 0))
        window.canvas._create_wire(("terminal", i1.component_id, 0), ("terminal", gnd.component_id, 0))
        window.canvas._create_wire(("terminal", r1.component_id, 1), ("terminal", gnd.component_id, 0))

        window.solve_current_circuit()
        self.assertIsNotNone(window.canvas.solution)
        self.assertAlmostEqual(window.canvas.solution.node_voltages["N1"], 8.0, places=9)

        # Modify resistor value -> previous solution must be invalidated.
        window._on_component_value_changed(r1.component_id, 10.0)
        self.assertIsNone(window.canvas.solution)
        self.assertIn("modified", window.properties_panel.status_label.text().lower())

        # Re-solve -> new voltage = 2 A * 10 ohm = 20 V.
        window.solve_current_circuit()
        self.assertIsNotNone(window.canvas.solution)
        self.assertAlmostEqual(window.canvas.solution.node_voltages["N1"], 20.0, places=9)
        window.close()

    def test_flip_direction_reverses_current_source(self) -> None:
        """Flip Direction reverses the current the solver sees, not just the drawing."""
        window = MainWindow()
        i1 = window.canvas.add_component("current_source", 0, 0)
        i1.value = 2.0
        r1 = window.canvas.add_component("resistor", 140, 0)
        r1.value = 4.0
        gnd = window.canvas.add_component("ground", 0, 100)

        window.canvas._create_wire(("terminal", i1.component_id, 1), ("terminal", r1.component_id, 0))
        window.canvas._create_wire(("terminal", i1.component_id, 0), ("terminal", gnd.component_id, 0))
        window.canvas._create_wire(("terminal", r1.component_id, 1), ("terminal", gnd.component_id, 0))

        def wire_positions() -> list:
            return [
                (
                    window.canvas.components[w.start[1]].terminal_positions()[w.start[2]],
                    window.canvas.components[w.end[1]].terminal_positions()[w.end[2]],
                )
                for w in window.canvas.wires.values()
            ]

        window.solve_current_circuit()
        self.assertAlmostEqual(window.canvas.solution.node_voltages["N1"], 8.0, places=9)
        positions_before = wire_positions()

        window.canvas._select("component", i1.component_id)
        window.canvas.flip_selected_current_source()
        self.assertIsNone(window.canvas.solution)
        # Wires stay where they were drawn.
        self.assertEqual(wire_positions(), positions_before)

        window.solve_current_circuit()
        self.assertAlmostEqual(window.canvas.solution.node_voltages["N1"], -8.0, places=9)

        # Flipping again restores the original direction.
        window.canvas.flip_selected_current_source()
        window.solve_current_circuit()
        self.assertAlmostEqual(window.canvas.solution.node_voltages["N1"], 8.0, places=9)
        window.close()


class TestNumberFormat(unittest.TestCase):
    """Display-only fraction labels for repeating decimals."""

    def test_repeating_decimals_show_fraction_terminating_do_not(self) -> None:
        from gui.number_format import fraction_suffix

        for value, expected in [
            (7 / 6, " (7/6)"),
            (9 / 7, " (9/7)"),
            (27 / 7, " (27/7)"),
            (-5 / 3, " (-5/3)"),
            (0.5, ""),
            (0.25, ""),
            (1.25, ""),
            (0.75, ""),
            (9.0, ""),
            (2 ** 0.5, ""),
        ]:
            self.assertEqual(fraction_suffix(value), expected, value)

    def test_worked_example_upper_triangular_shows_exact_fractions(self) -> None:
        from gui.matrix_view import matrix_cells
        from math_engine.circuit import Circuit, CurrentSource, Resistor

        circuit = Circuit(
            nodes=["GND", "N1", "N2", "N3"],
            ground_node="GND",
            resistors=[
                Resistor("R1", "N1", "GND", 2.0),
                Resistor("R2", "N1", "N2", 4.0),
                Resistor("R3", "N2", "GND", 2.0),
                Resistor("R4", "N2", "N3", 2.0),
                Resistor("R5", "N3", "GND", 1.0),
            ],
            current_sources=[
                CurrentSource("I1", "GND", "N1", 6.0),
                CurrentSource("I2", "GND", "N3", 3.0),
            ],
        )
        result = solve_circuit(circuit)
        cells = matrix_cells(result.upper_triangular)
        # Repeating values become fractions only; everything else has its trailing zeros cut.
        self.assertEqual(cells[0], [("0.75", False), ("−0.25", False), ("0", False), ("6", False)])
        self.assertEqual(cells[1], [("0", False), ("7/6", True), ("−0.5", False), ("2", False)])
        self.assertEqual(cells[2], [("0", False), ("0", False), ("9/7", True), ("27/7", True)])

    def test_entry_format_rules(self) -> None:
        from gui.number_format import format_entry

        self.assertEqual(format_entry(-7 / 6), ("−7/6", True))
        self.assertEqual(format_entry(1.5), ("1.5", False))
        self.assertEqual(format_entry(-0.0), ("0", False))
        self.assertEqual(format_entry(2 ** 0.5), ("1.4142", False))      # irrational: decimal
        self.assertEqual(format_entry(1234 / 567), ("2.1764", False))   # unwieldy fraction: decimal

    def test_trailing_zero_cutting_keeps_every_rounded_digit(self) -> None:
        from gui.number_format import fixed

        self.assertEqual(fixed(100.0, 6), "100")
        self.assertEqual(fixed(8.333333333, 6), "8.333333")   # nothing but zeros is ever removed
        self.assertEqual(fixed(-1.6666666667, 6), "-1.666667")
        self.assertEqual(fixed(0.0012, 4), "0.0012")
        self.assertEqual(fixed(-0.0, 4), "0")
        self.assertEqual(fixed(1.5, 4, 9), "      1.5")


if __name__ == "__main__":
    unittest.main()
