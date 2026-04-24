"""
Shared helpers for all spiders.

_parse_mad_price — handles French-formatted MAD prices:
  "4 299,00 DH"   → 4299.0
  "12 500,00 MAD" → 12500.0
  "1.299,00 Dhs"  → 1299.0   (period as thousands sep)

_parse_star_width — decodes Jumia's star rating from CSS width:
  "width:80%" → 4.0  (5 stars × 80% = 4.0)
"""

import re


def _parse_mad_price(raw: str) -> float:
    """Convert a Moroccan/French-formatted price string to a float."""
    if not raw:
        return 0.0

    # Strip currency labels and non-breaking spaces
    cleaned = re.sub(r"[DdHhMmAa\s\xa0]", "", raw).strip()

    # At this point we may have:
    #   "4299,00"     (no thousands sep)
    #   "4.299,00"    (period = thousands)
    #   "4,299.00"    (rare, US-style)
    if "," in cleaned and "." in cleaned:
        # Decide which is the decimal: the one that comes last
        last_comma = cleaned.rfind(",")
        last_dot = cleaned.rfind(".")
        if last_comma > last_dot:
            # Comma is decimal: "4.299,00"
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            # Dot is decimal: "4,299.00"
            cleaned = cleaned.replace(",", "")
    elif "," in cleaned:
        # Only comma — treat as decimal separator (French convention)
        # "4299,00" but also "4 299,00" already stripped spaces above
        # Edge case: "4,299" where comma might be thousands → check if ≤ 3 digits after
        parts = cleaned.split(",")
        if len(parts) == 2 and len(parts[1]) == 3 and parts[0].isdigit():
            # Likely "4,299" (thousands) — no decimal
            cleaned = cleaned.replace(",", "")
        else:
            cleaned = cleaned.replace(",", ".")

    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def _parse_star_width(style: str) -> float | None:
    """
    Decode Jumia's star rating from inline CSS width.
    Each full star = 20%, so width:80% → 4.0 stars.
    """
    if not style:
        return None
    match = re.search(r"(\d+(?:\.\d+)?)\s*%", style)
    if not match:
        return None
    try:
        pct = float(match.group(1))
        return round(pct / 20, 1)
    except ValueError:
        return None
