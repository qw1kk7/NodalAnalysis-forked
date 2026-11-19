"""Display-only number formatting: exact fractions for repeating decimals."""

import math
from fractions import Fraction

MAX_DENOMINATOR = 1000
TOLERANCE = 1e-9
MAX_FRACTION_CHARS = 7
MINUS = "−"


def exact_fraction(value: float) -> Fraction | None:
    """Return the exact fraction for a repeating decimal, or None if not applicable."""
    if not math.isfinite(value):
        return None
    frac = Fraction(value).limit_denominator(MAX_DENOMINATOR)
    if frac.denominator == 1:
        return None
    if abs(float(frac) - value) > TOLERANCE * max(1.0, abs(value)):
        return None
    d = frac.denominator
    for p in (2, 5):
        while d % p == 0:
            d //= p
    if d == 1:
        return None  # terminating decimal: the decimal is already exact
    if len(f"{frac.numerator}/{frac.denominator}") > MAX_FRACTION_CHARS:
        return None
    return frac


def fraction_suffix(value: float) -> str:
    """" (7/6)" for repeating decimals, "" otherwise. Used next to a decimal."""
    frac = exact_fraction(value)
    if frac is None:
        return ""
    return f" ({frac.numerator}/{frac.denominator})"


def fixed(value: float, decimals: int, width: int = 0) -> str:
    """Format to `decimals` places, then cut trailing zeros (100.000000 -> "100")."""
    text = f"{value:.{decimals}f}"
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    if text in ("-0", ""):
        text = "0"
    return text.rjust(width)


def format_entry(value: float) -> tuple[str, bool]:
    """Text for one matrix entry and whether it is an exact fraction."""
    frac = exact_fraction(value)
    if frac is not None:
        text = f"{abs(frac.numerator)}/{frac.denominator}"
        return (MINUS + text if frac < 0 else text), True
    return fixed(value, 4).replace("-", MINUS), False
