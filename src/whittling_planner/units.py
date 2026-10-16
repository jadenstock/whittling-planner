"""Writing sizes the woodshop way."""

from fractions import Fraction


def inches(mm: float) -> str:
    """Millimetres as inches to the nearest 1/16: 2 3/16."""
    frac = Fraction(round(mm / 25.4 * 16), 16)
    whole, rest = divmod(frac, 1)
    if rest == 0:
        return f"{whole}"
    return f"{whole} {rest.numerator}/{rest.denominator}" if whole else f"{rest.numerator}/{rest.denominator}"


def dims_in(v) -> str:
    return " × ".join(inches(x) for x in v) + " in"


def dims_mm(v) -> str:
    return " × ".join(f"{x:.0f}" for x in v) + " mm"
