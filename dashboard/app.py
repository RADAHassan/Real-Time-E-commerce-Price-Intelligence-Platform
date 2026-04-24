"""
Streamlit dashboard — Real-Time E-commerce Price Intelligence Platform
4 pages:
  1. Live Prices      — auto-refresh from Bigtable (or JSONL fallback)
  2. Historical KPIs  — from dbt mart tables
  3. Stats Results    — descriptive + inferential analysis in-app
  4. Price Alerts     — products with significant price drops
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from scipy import stats as scipy_stats

sys.path.insert(0, str(Path(__file__).parent.parent))
from dashboard.data_loader import load_live, load_mart

# ──────────────────────────────────────────────────────────────────────────────
# App config
# ──────────────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Price Intelligence Platform",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

SOURCES = ["books.toscrape.com", "scrapeme.live", "jumia.ma", "ultrapc.ma", "micromagma.ma"]
SOURCE_COLORS = {
    "books.toscrape.com": "#8b5cf6",
    "scrapeme.live":      "#f59e0b",
    "jumia.ma":           "#f97316",
    "ultrapc.ma":         "#06b6d4",
    "micromagma.ma":      "#10b981",
}

# ──────────────────────────────────────────────────────────────────────────────
# Sidebar
# ──────────────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.title("📊 Price Intelligence")
    st.caption("Real-Time E-commerce Platform")
    st.divider()

    page = st.radio(
        "Navigation",
        ["🔴 Live Prices", "📈 Historical KPIs", "📊 Statistical Analysis", "🔔 Price Alerts"],
        label_visibility="collapsed",
    )

    st.divider()
    auto_refresh = st.toggle("Auto-refresh (30s)", value=False)
    if st.button("🔄 Refresh now"):
        st.cache_data.clear()
        st.rerun()

    st.caption(f"Last refresh: {time.strftime('%H:%M:%S')}")


# ──────────────────────────────────────────────────────────────────────────────
# Cached loaders
# ──────────────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=30)
def _live() -> pd.DataFrame:
    return load_live(limit=5000)


@st.cache_data(ttl=300)
def _mart(table: str) -> pd.DataFrame:
    return load_mart(table)


# ──────────────────────────────────────────────────────────────────────────────
# Helper widgets
# ──────────────────────────────────────────────────────────────────────────────

def _source_pill(source: str) -> str:
    return f"`{source}`"


def _no_data():
    st.warning(
        "No data found. Run scrapers first:  \n"
        "```bash\nmake scrape-books-sample\n```"
    )


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 1 — Live Prices
# ══════════════════════════════════════════════════════════════════════════════

def page_live_prices():
    st.header("🔴 Live Prices")
    st.caption("Most recent price observation per product. Click a row to explore history.")

    df = _live()
    if df.empty:
        _no_data()
        return

    # Keep only the latest observation per product
    if "scraped_at" in df.columns:
        df = df.sort_values("scraped_at").groupby("product_id").last().reset_index()

    # ── Filters ──────────────────────────────────────────────────────────────
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        search = st.text_input("🔍 Search products", placeholder="e.g. laptop, HP, Pokémon…")
    with col2:
        source_filter = st.selectbox("Source", ["All"] + SOURCES)
    with col3:
        avail_filter = st.selectbox("Availability", ["All", "In Stock", "Out of Stock"])

    filtered = df.copy()
    if search:
        filtered = filtered[filtered["title"].str.contains(search, case=False, na=False)]
    if source_filter != "All":
        filtered = filtered[filtered["source"] == source_filter]
    if avail_filter != "All" and "availability" in filtered.columns:
        filtered = filtered[filtered["availability"] == avail_filter]

    # ── KPI row ──────────────────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Products tracked", f"{len(filtered):,}")
    c2.metric("Sources", filtered["source"].nunique() if not filtered.empty else 0)
    if not filtered.empty:
        c3.metric("Avg price", f"{filtered['price'].mean():.2f}")
        c4.metric("Price range", f"{filtered['price'].min():.2f} – {filtered['price'].max():.2f}")

    # ── Price distribution by source ─────────────────────────────────────────
    if not filtered.empty:
        fig = px.box(
            filtered,
            x="source",
            y="price",
            color="source",
            color_discrete_map=SOURCE_COLORS,
            log_y=True,
            title="Price Distribution by Source",
            labels={"price": "Price", "source": ""},
        )
        fig.update_layout(showlegend=False, height=280,
                          paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        fig.update_yaxes(gridcolor="#1e293b")
        fig.update_xaxes(gridcolor="#1e293b")
        st.plotly_chart(fig, use_container_width=True)

    # ── Product table ─────────────────────────────────────────────────────────
    cols_show = [c for c in ["title", "source", "price", "currency", "availability",
                              "category", "rating", "scraped_at"] if c in filtered.columns]
    st.dataframe(
        filtered[cols_show].sort_values("price").reset_index(drop=True),
        use_container_width=True,
        height=420,
        column_config={
            "price": st.column_config.NumberColumn("Price", format="%.2f"),
            "rating": st.column_config.NumberColumn("Rating ⭐", format="%.1f"),
            "scraped_at": st.column_config.DatetimeColumn("Scraped at", format="YYYY-MM-DD HH:mm"),
        },
    )


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 2 — Historical KPIs
# ══════════════════════════════════════════════════════════════════════════════

def page_historical_kpis():
    st.header("📈 Historical KPIs")

    stats_df  = _mart("mart_price_stats")
    hist_df   = _mart("mart_price_history")

    if stats_df.empty and hist_df.empty:
        _no_data()
        return

    # ── KPI cards ────────────────────────────────────────────────────────────
    if not stats_df.empty:
        st.subheader("Aggregate Statistics per Source")
        cols = st.columns(min(len(stats_df), 5))
        for i, (_, row) in enumerate(stats_df.iterrows()):
            with cols[i % len(cols)]:
                st.metric(
                    row.get("source", "unknown"),
                    f"{row.get('avg_price', 0):.2f} {row.get('currency','')}",
                    delta=f"σ = {row.get('stddev_price', 0):.2f}",
                )

        # ── Bar chart ─────────────────────────────────────────────────────────
        fig = px.bar(
            stats_df,
            x="source",
            y=["min_price", "avg_price", "median_price", "max_price"],
            barmode="group",
            color_discrete_sequence=["#3b82f6", "#10b981", "#f59e0b", "#ef4444"],
            title="Min / Avg / Median / Max price per source",
        )
        fig.update_layout(height=360, paper_bgcolor="rgba(0,0,0,0)",
                          plot_bgcolor="rgba(0,0,0,0)", legend_title="")
        fig.update_yaxes(gridcolor="#1e293b")
        st.plotly_chart(fig, use_container_width=True)

        st.dataframe(stats_df, use_container_width=True)

    # ── Price trend ───────────────────────────────────────────────────────────
    if not hist_df.empty and "scraped_date" in hist_df.columns:
        st.subheader("Price Trend Over Time")
        pid_options = hist_df["product_id"].unique().tolist()
        selected_pid = st.selectbox("Select product", pid_options,
                                    format_func=lambda pid: hist_df[hist_df["product_id"] == pid]["title"].iloc[0]
                                    if not hist_df[hist_df["product_id"] == pid].empty else pid)

        trend = hist_df[hist_df["product_id"] == selected_pid].sort_values("scraped_date")
        if not trend.empty:
            fig2 = px.line(trend, x="scraped_date", y="price",
                           title=f"Price history — {trend['title'].iloc[0]}",
                           markers=True)
            fig2.update_layout(height=300, paper_bgcolor="rgba(0,0,0,0)",
                               plot_bgcolor="rgba(0,0,0,0)")
            fig2.update_yaxes(gridcolor="#1e293b")
            st.plotly_chart(fig2, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 3 — Statistical Analysis
# ══════════════════════════════════════════════════════════════════════════════

def page_statistics():
    st.header("📊 Statistical Analysis")

    df = _live()
    if df.empty:
        _no_data()
        return

    tab1, tab2, tab3 = st.tabs(["Descriptive Stats", "Inferential Tests", "Regression"])

    # ── Tab 1: Descriptive ────────────────────────────────────────────────────
    with tab1:
        st.subheader("Descriptive Statistics")

        desc = df.groupby("source")["price"].agg(
            count="count",
            mean="mean",
            median="median",
            std="std",
            min="min",
            q25=lambda s: s.quantile(0.25),
            q75=lambda s: s.quantile(0.75),
            max="max",
            skewness=lambda s: float(scipy_stats.skew(s.dropna())),
            kurtosis=lambda s: float(scipy_stats.kurtosis(s.dropna())),
        ).round(3)
        st.dataframe(desc, use_container_width=True)

        st.markdown("**Price distribution (log scale)**")
        fig = px.histogram(df, x="price", color="source",
                           barmode="overlay", opacity=0.6, log_x=True,
                           color_discrete_map=SOURCE_COLORS, nbins=50)
        fig.update_layout(height=300, paper_bgcolor="rgba(0,0,0,0)",
                          plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)

        # Volatility (rolling std within each source)
        if "scraped_at" in df.columns and df["scraped_at"].notna().any():
            st.markdown("**Price volatility by source** (std of all observations)")
            vol = df.groupby("source")["price"].std().reset_index()
            vol.columns = ["source", "volatility"]
            fig2 = px.bar(vol, x="source", y="volatility",
                          color="source", color_discrete_map=SOURCE_COLORS,
                          title="Price Volatility (Std Dev)")
            fig2.update_layout(height=280, showlegend=False,
                               paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig2, use_container_width=True)

    # ── Tab 2: Inferential ────────────────────────────────────────────────────
    with tab2:
        st.subheader("Hypothesis Tests")

        groups = {s: df[df["source"] == s]["price"].dropna() for s in df["source"].unique()}
        groups = {k: v for k, v in groups.items() if len(v) >= 3}

        if len(groups) < 2:
            st.info("Need ≥ 2 sources with ≥ 3 observations each.")
        else:
            # Normality
            st.markdown("#### Shapiro-Wilk Normality Test (H₀: data is normal)")
            norm_rows = []
            for src, g in groups.items():
                sample = g.head(5000)
                w, p = scipy_stats.shapiro(sample)
                norm_rows.append({"Source": src, "W": round(w, 4), "p-value": round(p, 6),
                                   "Normal?": "✅ Yes" if p >= 0.05 else "❌ No"})
            st.dataframe(pd.DataFrame(norm_rows), use_container_width=True)

            # One-way ANOVA
            st.markdown("#### One-Way ANOVA (H₀: all source means are equal)")
            f_stat, p_anova = scipy_stats.f_oneway(*groups.values())
            col1, col2, col3 = st.columns(3)
            col1.metric("F-statistic", f"{f_stat:.4f}")
            col2.metric("p-value", f"{p_anova:.2e}")
            col3.metric("Result", "Reject H₀" if p_anova < 0.05 else "Fail to reject H₀")

            # Kruskal-Wallis (non-parametric)
            st.markdown("#### Kruskal-Wallis Test (non-parametric ANOVA)")
            h_stat, p_kw = scipy_stats.kruskal(*groups.values())
            col1, col2, col3 = st.columns(3)
            col1.metric("H-statistic", f"{h_stat:.4f}")
            col2.metric("p-value", f"{p_kw:.2e}")
            col3.metric("Result", "Reject H₀" if p_kw < 0.05 else "Fail to reject H₀")

            # Pairwise Mann-Whitney U
            src_list = list(groups.keys())
            st.markdown("#### Pairwise Mann-Whitney U Tests")
            mw_rows = []
            for i in range(len(src_list)):
                for j in range(i + 1, len(src_list)):
                    a, b = src_list[i], src_list[j]
                    u, p_mw = scipy_stats.mannwhitneyu(groups[a], groups[b], alternative="two-sided")
                    mw_rows.append({
                        "Source A": a, "Source B": b,
                        "U statistic": round(u, 1), "p-value": round(p_mw, 6),
                        "Significant?": "✅ Yes" if p_mw < 0.05 else "❌ No",
                    })
            st.dataframe(pd.DataFrame(mw_rows), use_container_width=True)

            # Confidence intervals
            st.markdown("#### 95% Confidence Intervals for Mean Price")
            ci_rows = []
            for src, g in groups.items():
                n, se = len(g), scipy_stats.sem(g)
                ci = scipy_stats.t.interval(0.95, df=n - 1, loc=g.mean(), scale=se)
                ci_rows.append({
                    "Source": src, "n": n,
                    "Mean": round(g.mean(), 2),
                    "95% CI Lower": round(ci[0], 2),
                    "95% CI Upper": round(ci[1], 2),
                })
            st.dataframe(pd.DataFrame(ci_rows), use_container_width=True)

    # ── Tab 3: Regression ─────────────────────────────────────────────────────
    with tab3:
        st.subheader("Linear Regression: Price ~ Rating")

        reg_df = df.dropna(subset=["price", "rating"]) if "rating" in df.columns else pd.DataFrame()
        if reg_df.empty or len(reg_df) < 5:
            st.info("Not enough products with rating data for regression.")
        else:
            slope, intercept, r, p, se = scipy_stats.linregress(reg_df["rating"], reg_df["price"])
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Slope (β₁)", f"{slope:.4f}")
            col2.metric("Intercept (β₀)", f"{intercept:.4f}")
            col3.metric("R²", f"{r**2:.4f}")
            col4.metric("p-value", f"{p:.4e}")

            fig = px.scatter(reg_df, x="rating", y="price", color="source",
                             color_discrete_map=SOURCE_COLORS, opacity=0.6,
                             trendline="ols", title="Price vs Rating (OLS trendline)")
            fig.update_layout(height=380, paper_bgcolor="rgba(0,0,0,0)",
                              plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 4 — Price Alerts
# ══════════════════════════════════════════════════════════════════════════════

def page_alerts():
    st.header("🔔 Price Alerts")
    st.caption("Products with a price drop ≥ 5 % detected in the most recent scrape.")

    alerts = _mart("mart_price_alerts")

    if alerts.empty:
        st.success("✅ No significant price drops detected.")
        return

    # KPI row
    c1, c2, c3 = st.columns(3)
    c1.metric("Alerts", len(alerts))
    if "price_change_pct" in alerts.columns:
        c2.metric("Biggest drop", f"{alerts['price_change_pct'].min():.1f}%")
    if "source" in alerts.columns:
        c3.metric("Sources affected", alerts["source"].nunique())

    # Chart
    if "price_change_pct" in alerts.columns and "source" in alerts.columns:
        fig = px.bar(
            alerts.head(20).sort_values("price_change_pct"),
            x="price_change_pct",
            y="title" if "title" in alerts.columns else "product_id",
            color="source",
            color_discrete_map=SOURCE_COLORS,
            orientation="h",
            title="Top price drops (%)",
        )
        fig.update_layout(height=420, paper_bgcolor="rgba(0,0,0,0)",
                          plot_bgcolor="rgba(0,0,0,0)", showlegend=True)
        st.plotly_chart(fig, use_container_width=True)

    # Table
    cols_show = [c for c in ["title", "source", "price", "prev_price",
                              "price_change_pct", "currency"] if c in alerts.columns]
    if cols_show:
        styled = alerts[cols_show].reset_index(drop=True)
        st.dataframe(
            styled,
            use_container_width=True,
            column_config={
                "price":            st.column_config.NumberColumn("Current price", format="%.2f"),
                "prev_price":       st.column_config.NumberColumn("Previous price", format="%.2f"),
                "price_change_pct": st.column_config.NumberColumn("Change %", format="%.2f"),
            },
        )


# ──────────────────────────────────────────────────────────────────────────────
# Router
# ──────────────────────────────────────────────────────────────────────────────

if page == "🔴 Live Prices":
    page_live_prices()
elif page == "📈 Historical KPIs":
    page_historical_kpis()
elif page == "📊 Statistical Analysis":
    page_statistics()
elif page == "🔔 Price Alerts":
    page_alerts()

# Auto-refresh
if auto_refresh:
    time.sleep(30)
    st.cache_data.clear()
    st.rerun()
