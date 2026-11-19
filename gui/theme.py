"""Visual theme: colour tokens, fonts, small styling helpers and the app-wide Qt stylesheet."""

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPalette
from PySide6.QtWidgets import QApplication, QLabel, QStyleFactory


WINDOW_BG = "#1B1E23"
SURFACE = "#23272E"
SURFACE_ALT = "#2A2F37"
SURFACE_PRESSED = "#30363F"
BORDER = "#343A44"
BORDER_STRONG = "#545C69"
TEXT = "#DCE0E4"
TEXT_MUTED = "#A3ABB6"
TEXT_FAINT = "#949CA8"

ACCENT = "#6AA4E0"
ACCENT_FILL = "#2F6CAD"
ACCENT_HOVER = "#3573B3"
ACCENT_PRESSED = "#285E98"
ACCENT_SOFT = "#243447"

CANVAS_BG = "#1F2329"
GRID_DOT = "#363C46"
INK = "#D6DBE1"
WIRE = "#A9B2BE"
SELECTED = ACCENT
SELECTED_OUTLINE = "#4B739E"
TERMINAL_RING = "#8C95A2"
TERMINAL_ACTIVE = "#62B57F"
NODE_LABEL_TEXT = "#93D3A3"
NODE_LABEL_BG = "#1E3027"
NODE_LABEL_BORDER = "#2F5239"

FRACTION = "#F0B455"
BRACKET = "#AEB5C0"

STATUS_NEUTRAL = ("#2A2F37", "#B4BCC6", "#3A404A")
STATUS_WARNING = ("#352D1E", "#E5C27C", "#56482A")
STATUS_SUCCESS = ("#1E3027", "#93D3A3", "#2F5239")
STATUS_ERROR = ("#3A2326", "#F0A6A2", "#5E3438")

UI_FONT_FAMILY = "Segoe UI"
MONO_FONT_FAMILIES = ["Cascadia Mono", "Consolas"]

SIZE_BASE = 9.5
SIZE_SMALL = 9.0
SIZE_CAPTION = 8.0
SIZE_FOCUS = 12.0
SIZE_MONO = 9.0


def status_style(variant: tuple[str, str, str]) -> str:
    """Stylesheet for the solver status banner in the given colour variant."""
    bg, fg, border = variant
    return (
        f"padding: 8px 10px; border-radius: 4px; background: {bg}; color: {fg}; "
        f"border: 1px solid {border}; font-weight: 600;"
    )


def ui_font(point_size: float = SIZE_BASE, weight: QFont.Weight = QFont.Weight.Normal) -> QFont:
    font = QFont(UI_FONT_FAMILY)
    font.setPointSizeF(point_size)
    font.setWeight(weight)
    return font


def mono_font(point_size: float = SIZE_MONO) -> QFont:
    font = QFont()
    font.setFamilies(MONO_FONT_FAMILIES)
    font.setStyleHint(QFont.StyleHint.Monospace)
    font.setPointSizeF(point_size)
    return font


def caption_font(uppercase: bool = True) -> QFont:
    """Small, letter-spaced heading font for panel sections (all caps unless told otherwise)."""
    font = ui_font(SIZE_CAPTION, QFont.Weight.DemiBold)
    font.setCapitalization(
        QFont.Capitalization.AllUppercase if uppercase else QFont.Capitalization.MixedCase
    )
    font.setLetterSpacing(QFont.SpacingType.PercentageSpacing, 112)
    return font


def label(text: str = "", name: str = "", font: QFont | None = None, wrap: bool = False) -> QLabel:
    """A QLabel with a stylesheet object name and optional font / word wrap."""
    lbl = QLabel(text)
    if name:
        lbl.setObjectName(name)
    if font is not None:
        lbl.setFont(font)
    lbl.setWordWrap(wrap)
    return lbl


def draw_text(
    painter: QPainter,
    rect: QRectF,
    text: str,
    font: QFont,
    color: str,
    align: Qt.AlignmentFlag = Qt.AlignmentFlag.AlignCenter,
) -> None:
    """Draw text in a rectangle with the given font and colour."""
    painter.setFont(font)
    painter.setPen(QColor(color))
    painter.drawText(rect, align, text)


STYLESHEET = f"""
QMainWindow, QWidget#PaletteSidebar, QWidget#PropertiesPanel {{
    background: {WINDOW_BG};
    color: {TEXT};
}}

QToolTip {{
    background: {SURFACE};
    color: {TEXT};
    border: 1px solid {BORDER_STRONG};
    padding: 4px 6px;
}}

QToolBar {{
    background: {SURFACE};
    border: none;
    border-bottom: 1px solid {BORDER};
    padding: 6px 10px;
    spacing: 6px;
}}
QToolBar::separator {{ background: {BORDER}; width: 1px; margin: 4px 8px; }}

QPushButton {{
    background: {SURFACE};
    color: {TEXT};
    border: 1px solid {BORDER_STRONG};
    border-radius: 4px;
    padding: 5px 12px;
    min-height: 20px;
}}
QPushButton:hover {{ background: {SURFACE_ALT}; border-color: {TEXT_FAINT}; }}
QPushButton:pressed {{ background: {SURFACE_PRESSED}; }}
QPushButton:checked {{
    background: {ACCENT_SOFT};
    color: {ACCENT};
    border-color: {ACCENT};
    font-weight: 600;
}}
QPushButton:focus {{ outline: none; }}

QPushButton#PrimaryButton {{
    background: {ACCENT_FILL};
    color: #FFFFFF;
    border: 1px solid {ACCENT_FILL};
    font-weight: 600;
    padding: 5px 18px;
}}
QPushButton#PrimaryButton:hover {{ background: {ACCENT_HOVER}; border-color: {ACCENT_HOVER}; }}
QPushButton#PrimaryButton:pressed {{ background: {ACCENT_PRESSED}; }}

QWidget#PaletteSidebar {{ border-right: 1px solid {BORDER}; }}
QLabel#SectionTitle {{ color: {TEXT_MUTED}; }}
QLabel#SectionHint {{ color: {TEXT_FAINT}; font-size: {SIZE_SMALL}pt; }}
QPushButton#PaletteButton {{ text-align: left; padding: 6px 10px; min-height: 30px; }}
QPushButton#PaletteButton:hover {{ border-color: {ACCENT}; background: {SURFACE}; }}
QLabel#HelpText {{
    color: {TEXT_MUTED};
    font-size: {SIZE_SMALL}pt;
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 4px;
    padding: 8px 10px;
}}

QGroupBox {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 4px;
    margin-top: 0px;
    padding: 10px 10px 8px 10px;
}}
QLabel#FormLabel {{ color: {TEXT_MUTED}; font-size: {SIZE_SMALL}pt; }}
QLabel#SelectionId {{ font-size: {SIZE_FOCUS}pt; font-weight: 600; color: {TEXT}; }}
QLabel#SelectionType {{ color: {TEXT_MUTED}; }}

QLineEdit {{
    background: {SURFACE};
    border: 1px solid {BORDER_STRONG};
    border-radius: 4px;
    padding: 4px 6px;
    selection-background-color: {ACCENT_FILL};
}}
QLineEdit:focus {{ border-color: {ACCENT}; }}

QTabWidget::pane {{ background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 4px; top: -1px; }}
QTabBar::tab {{
    font-size: {SIZE_SMALL}pt;
    background: transparent;
    color: {TEXT_MUTED};
    border: 1px solid transparent;
    border-bottom: none;
    padding: 6px 12px;
    margin-right: 2px;
}}
QTabBar::tab:hover {{ color: {TEXT}; }}
QTabBar::tab:selected {{
    background: {SURFACE};
    color: {TEXT};
    border-color: {BORDER};
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    font-weight: 600;
}}

QTextEdit {{
    background: {SURFACE};
    color: {TEXT};
    border: none;
    padding: 6px;
    selection-background-color: {ACCENT_SOFT};
    selection-color: {TEXT};
}}
QScrollArea#MatrixPanel, QWidget#MatrixPanelBody {{ background: {SURFACE}; border: none; }}

QSplitter::handle {{ background: {BORDER}; }}
QSplitter::handle:horizontal {{ width: 1px; }}

QScrollBar {{ background: transparent; margin: 2px; }}
QScrollBar:vertical {{ width: 10px; }}
QScrollBar:horizontal {{ height: 10px; }}
QScrollBar::handle {{ background: {BORDER_STRONG}; border-radius: 3px; }}
QScrollBar::handle:vertical {{ min-height: 24px; }}
QScrollBar::handle:horizontal {{ min-width: 24px; }}
QScrollBar::handle:vertical:hover {{ background: {TEXT_FAINT}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: none; }}
"""

_PALETTE = {
    QPalette.ColorRole.Window: WINDOW_BG,
    QPalette.ColorRole.WindowText: TEXT,
    QPalette.ColorRole.Base: SURFACE,
    QPalette.ColorRole.AlternateBase: SURFACE_ALT,
    QPalette.ColorRole.Text: TEXT,
    QPalette.ColorRole.Button: SURFACE,
    QPalette.ColorRole.ButtonText: TEXT,
    QPalette.ColorRole.Highlight: ACCENT_FILL,
    QPalette.ColorRole.HighlightedText: "#FFFFFF",
    QPalette.ColorRole.ToolTipBase: SURFACE,
    QPalette.ColorRole.ToolTipText: TEXT,
    QPalette.ColorRole.PlaceholderText: TEXT_FAINT,
    QPalette.ColorRole.Light: BORDER_STRONG,
    QPalette.ColorRole.Midlight: BORDER,
    QPalette.ColorRole.Mid: BORDER,
    QPalette.ColorRole.Dark: WINDOW_BG,
    QPalette.ColorRole.Shadow: "#000000",
}


def apply_theme(app: QApplication) -> None:
    """Apply a consistent dark theme regardless of the OS light/dark setting."""
    fusion = QStyleFactory.create("Fusion")
    if fusion is not None:
        app.setStyle(fusion)

    palette = QPalette()
    for role, color in _PALETTE.items():
        palette.setColor(role, QColor(color))
    for role in (QPalette.ColorRole.Text, QPalette.ColorRole.WindowText, QPalette.ColorRole.ButtonText):
        palette.setColor(QPalette.ColorGroup.Disabled, role, QColor(TEXT_FAINT))
    app.setPalette(palette)
    app.setFont(ui_font(SIZE_BASE))
    app.setStyleSheet(STYLESHEET)
