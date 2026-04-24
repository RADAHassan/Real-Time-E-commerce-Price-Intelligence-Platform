"""
Tests for scrapers/utils.py — price parsing and rating helpers.
All edge cases encountered on Jumia.ma and UltraPC.ma are covered.
"""

import pytest
from scrapers.utils import _parse_mad_price, _parse_star_width


# ---------------------------------------------------------------------------
# _parse_mad_price
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw, expected",
    [
        # Formats Jumia
        ("4 299,00 DH", 4299.0),
        ("12 500,00 DH", 12500.0),
        ("599,00 DH", 599.0),
        ("1 000 DH", 1000.0),
        # Formats UltraPC / PrestaShop
        ("12 500,00 MAD", 12500.0),
        ("3 299,00 MAD", 3299.0),
        ("850 MAD", 850.0),
        # Period as thousands separator
        ("1.299,00 DH", 1299.0),
        ("10.999,00 MAD", 10999.0),
        # No decimal
        ("4299 DH", 4299.0),
        # Edge cases
        ("0 DH", 0.0),
        ("", 0.0),
        ("Prix sur devis", 0.0),
    ],
)
def test_parse_mad_price(raw, expected):
    assert _parse_mad_price(raw) == pytest.approx(expected, rel=1e-3)


# ---------------------------------------------------------------------------
# _parse_star_width (Jumia rating)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "style, expected",
    [
        ("width:100%", 5.0),
        ("width:80%", 4.0),
        ("width:60%", 3.0),
        ("width:40%", 2.0),
        ("width:20%", 1.0),
        ("width:0%", 0.0),
        ("width:76%", 3.8),    # fractional rating
        ("width: 80%", 4.0),   # space before %
        ("", None),
        ("no-width-here", None),
    ],
)
def test_parse_star_width(style, expected):
    result = _parse_star_width(style)
    if expected is None:
        assert result is None
    else:
        assert result == pytest.approx(expected, rel=1e-3)
