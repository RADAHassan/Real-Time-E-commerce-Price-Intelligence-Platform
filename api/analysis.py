"""
Statistical analysis computed from the live JSONL store.
scipy is required; assumed installed (also used by the Streamlit dashboard).
"""
from __future__ import annotations

import itertools

import numpy as np
from scipy import stats as scipy_stats

from api import jsonl_store


def _load_prices() -> dict[str, np.ndarray]:
    """Return {source: price_array} keeping only sources with ≥ 3 obs."""
    df = jsonl_store._load()
    if df.empty:
        return {}
    result: dict[str, np.ndarray] = {}
    for src, grp in df.groupby("source"):
        prices = grp["price"].dropna().values.astype(float)
        if len(prices) >= 3:
            result[str(src)] = prices
    return result


def descriptive() -> list[dict]:
    groups = _load_prices()
    rows = []
    for src, prices in sorted(groups.items()):
        n = len(prices)
        rows.append({
            "source":   src,
            "n":        n,
            "mean":     round(float(prices.mean()), 2),
            "median":   round(float(np.median(prices)), 2),
            "std":      round(float(prices.std(ddof=1)), 2) if n > 1 else 0.0,
            "min":      round(float(prices.min()), 2),
            "max":      round(float(prices.max()), 2),
            "q25":      round(float(np.percentile(prices, 25)), 2),
            "q75":      round(float(np.percentile(prices, 75)), 2),
            "skew":     round(float(scipy_stats.skew(prices)), 3) if n >= 4 else None,
            "kurtosis": round(float(scipy_stats.kurtosis(prices)), 3) if n >= 4 else None,
            "cv":       round(float(prices.std(ddof=1) / prices.mean() * 100), 1)
                        if prices.mean() > 0 and n > 1 else 0.0,
        })
    return rows


def hypothesis_tests() -> dict:
    groups = _load_prices()
    if len(groups) < 2:
        return {}

    src_list = sorted(groups.keys())

    # Shapiro-Wilk (max 5000 obs per source)
    normality = []
    for src in src_list:
        prices = groups[src][:5000]
        w, p = scipy_stats.shapiro(prices)
        normality.append({
            "source":    src,
            "n":         len(groups[src]),
            "w_stat":    round(float(w), 4),
            "p_value":   float(p),
            "is_normal": bool(p >= 0.05),
        })

    # One-way ANOVA
    f_stat, p_anova = scipy_stats.f_oneway(*[groups[s] for s in src_list])
    anova = {
        "f_stat":  round(float(f_stat), 4),
        "p_value": float(p_anova),
        "reject":  bool(p_anova < 0.05),
    }

    # Kruskal-Wallis
    h_stat, p_kw = scipy_stats.kruskal(*[groups[s] for s in src_list])
    kruskal = {
        "h_stat":  round(float(h_stat), 4),
        "p_value": float(p_kw),
        "reject":  bool(p_kw < 0.05),
    }

    # Mann-Whitney pairwise
    pairwise = []
    for a, b in itertools.combinations(src_list, 2):
        u, p_mw = scipy_stats.mannwhitneyu(groups[a], groups[b], alternative="two-sided")
        n1, n2 = len(groups[a]), len(groups[b])
        r_eff = float(u) / (n1 * n2)  # rank-biserial (0–1)
        pairwise.append({
            "source_a":   a,
            "source_b":   b,
            "u_stat":     float(u),
            "p_value":    float(p_mw),
            "effect_r":   round(r_eff, 4),
            "significant": bool(p_mw < 0.05),
        })
    pairwise.sort(key=lambda r: r["p_value"])

    # 95% confidence intervals for mean price
    ci_list = []
    for src in src_list:
        prices = groups[src]
        n = len(prices)
        se = scipy_stats.sem(prices)
        lo, hi = scipy_stats.t.interval(0.95, df=n - 1, loc=prices.mean(), scale=se)
        mean = float(prices.mean())
        ci_list.append({
            "source":    src,
            "n":         n,
            "mean":      round(mean, 2),
            "ci_lower":  round(float(lo), 2),
            "ci_upper":  round(float(hi), 2),
            "ci_width":  round(float(hi - lo), 2),
            "rel_width": round(float(hi - lo) / mean * 100, 4) if mean > 0 else 0.0,
        })

    return {
        "normality":            normality,
        "anova":                anova,
        "kruskal":              kruskal,
        "pairwise":             pairwise,
        "confidence_intervals": ci_list,
        "sources":              src_list,
    }


def histogram(n_bins: int = 28) -> dict:
    """Log-scale histogram bins per source, ready for recharts stacked BarChart."""
    df = jsonl_store._load()
    if df.empty:
        return {"sources": [], "bins": []}
    pos = df[df["price"] > 0].copy()
    sources = sorted(pos["source"].unique().tolist())

    log_prices = np.log10(pos["price"].values)
    log_min = float(np.floor(log_prices.min()))
    log_max = float(np.ceil(log_prices.max()))
    edges = np.linspace(log_min, log_max, n_bins + 1)

    def _label(v: float) -> str:
        if v >= 10_000: return f"{v/1000:.0f}k"
        if v >= 1_000:  return f"{v/1000:.1f}k"
        if v >= 100:    return f"{v:.0f}"
        if v >= 10:     return f"{v:.1f}"
        return f"{v:.2f}"

    bins: list[dict] = []
    for i in range(len(edges) - 1):
        center = (edges[i] + edges[i + 1]) / 2
        row: dict = {
            "log_center":  round(float(center), 3),
            "price_label": _label(float(10 ** center)),
        }
        has_data = False
        for src in sources:
            src_log = np.log10(pos[pos["source"] == src]["price"].values)
            count = int(((src_log >= edges[i]) & (src_log < edges[i + 1])).sum())
            if count > 0:
                row[src] = count
                has_data = True
        if has_data:
            bins.append(row)

    return {"sources": sources, "bins": bins}


def regression() -> dict:
    df = jsonl_store._load()
    if df.empty or "rating" not in df.columns:
        return {"n": 0}
    reg_df = df.dropna(subset=["price", "rating"])
    reg_df = reg_df[reg_df["price"] > 0]
    if len(reg_df) < 5:
        return {"n": 0}

    slope, intercept, r, p, se = scipy_stats.linregress(reg_df["rating"], reg_df["price"])
    r2 = float(r) ** 2

    # Scatter sample (vectorised — much faster than iterrows)
    sample = reg_df.sample(min(1500, len(reg_df)), random_state=42)[["rating", "price", "source"]].copy()
    sample["rating"] = sample["rating"].round(2)
    sample["price"]  = sample["price"].round(2)
    sample["source"] = sample["source"].astype(str)
    scatter = sample.to_dict("records")

    # OLS line endpoints
    r_min = float(reg_df["rating"].min())
    r_max = float(reg_df["rating"].max())
    ols_line = [
        {"rating": round(r_min, 2), "price": round(float(slope * r_min + intercept), 2)},
        {"rating": round(r_max, 2), "price": round(float(slope * r_max + intercept), 2)},
    ]

    # Per-source regression
    per_source = []
    for src, grp in reg_df.groupby("source"):
        gf = grp.dropna(subset=["price", "rating"])
        if len(gf) < 5:
            continue
        sl, ic, rv, pv, _ = scipy_stats.linregress(gf["rating"], gf["price"])
        per_source.append({
            "source":      str(src),
            "n":           int(len(gf)),
            "slope":       round(float(sl), 4),
            "intercept":   round(float(ic), 2),
            "r":           round(float(rv), 4),
            "r2":          round(float(rv ** 2), 4),
            "p_value":     float(pv),
            "significant": bool(pv < 0.05),
        })
    per_source.sort(key=lambda r: r["source"])

    return {
        "slope":      round(float(slope), 4),
        "intercept":  round(float(intercept), 2),
        "r":          round(float(r), 4),
        "r2":         round(r2, 4),
        "p_value":    float(p),
        "se":         round(float(se), 4),
        "n":          int(len(reg_df)),
        "scatter":    scatter,
        "ols_line":   ols_line,
        "per_source": per_source,
    }
