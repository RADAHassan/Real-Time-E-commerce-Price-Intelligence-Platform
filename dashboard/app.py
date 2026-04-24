"""
Streamlit dashboard — Real-Time E-commerce Price Intelligence Platform
Professional dark-mode UI with custom CSS components.
"""
from __future__ import annotations

import sys
import time
import itertools
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from scipy import stats as scipy_stats

sys.path.insert(0, str(Path(__file__).parent.parent))
from dashboard.data_loader import load_live, load_mart

# ─────────────────────────────────────────────────────────────────────────────
# Page config  (must be first Streamlit call)
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Price Intelligence",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# Global CSS
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* ── Reset & base ───────────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

.stApp {
    background: #080d1a;
    color: #e2e8f0;
}

/* ── Sidebar ─────────────────────────────────────────────── */
[data-testid="stSidebar"] {
    background: #0d1322 !important;
    border-right: 1px solid #1e2d45;
}

[data-testid="stSidebar"] .stMarkdown p {
    color: #94a3b8;
    font-size: 0.78rem;
}

/* ── Hide Streamlit chrome ──────────────────────────────── */
#MainMenu, footer, header { visibility: hidden; }
[data-testid="stDecoration"] { display: none; }

/* ── Nav buttons ─────────────────────────────────────────── */
div.nav-btn button {
    width: 100%;
    text-align: left !important;
    background: transparent !important;
    border: none !important;
    border-radius: 8px !important;
    color: #94a3b8 !important;
    font-size: 0.875rem !important;
    font-weight: 500 !important;
    padding: 0.55rem 0.9rem !important;
    margin-bottom: 2px !important;
    transition: all 0.15s ease;
}
div.nav-btn button:hover {
    background: #1e2d45 !important;
    color: #e2e8f0 !important;
}
div.nav-btn-active button {
    width: 100%;
    text-align: left !important;
    background: linear-gradient(90deg,#1e3a5f,#1e2d45) !important;
    border: none !important;
    border-left: 3px solid #3b82f6 !important;
    border-radius: 8px !important;
    color: #60a5fa !important;
    font-size: 0.875rem !important;
    font-weight: 600 !important;
    padding: 0.55rem 0.9rem !important;
    margin-bottom: 2px !important;
}

/* ── KPI cards ───────────────────────────────────────────── */
.kpi-card {
    background: linear-gradient(135deg, #111827 0%, #0f172a 100%);
    border: 1px solid #1e2d45;
    border-radius: 12px;
    padding: 1.2rem 1.4rem;
    position: relative;
    overflow: hidden;
    transition: border-color 0.2s;
}
.kpi-card:hover { border-color: #3b4f6b; }
.kpi-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: var(--accent, #3b82f6);
    border-radius: 12px 12px 0 0;
}
.kpi-label {
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #64748b;
    margin-bottom: 0.4rem;
}
.kpi-value {
    font-size: 1.75rem;
    font-weight: 700;
    color: #f1f5f9;
    line-height: 1.1;
}
.kpi-sub {
    font-size: 0.75rem;
    color: #64748b;
    margin-top: 0.35rem;
}
.kpi-icon {
    position: absolute;
    top: 1rem; right: 1.1rem;
    font-size: 1.5rem;
    opacity: 0.18;
}
.kpi-delta-pos { color: #10b981; font-size: 0.78rem; font-weight: 600; }
.kpi-delta-neg { color: #ef4444; font-size: 0.78rem; font-weight: 600; }

/* ── Section headers ─────────────────────────────────────── */
.section-header {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    margin: 1.6rem 0 0.9rem;
    padding-bottom: 0.6rem;
    border-bottom: 1px solid #1e2d45;
}
.section-header h2 {
    font-size: 1.05rem;
    font-weight: 600;
    color: #e2e8f0;
    margin: 0;
}
.section-badge {
    font-size: 0.68rem;
    font-weight: 600;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    background: #1e3a5f;
    color: #60a5fa;
    border-radius: 4px;
    padding: 2px 7px;
}

/* ── Source tags ─────────────────────────────────────────── */
.source-tag {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 0.7rem;
    font-weight: 600;
    letter-spacing: 0.04em;
}

/* ── Alert cards ─────────────────────────────────────────── */
.alert-card {
    background: #111827;
    border: 1px solid #1e2d45;
    border-left: 4px solid var(--alert-color, #ef4444);
    border-radius: 0 10px 10px 0;
    padding: 0.9rem 1.2rem;
    margin-bottom: 0.6rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
}
.alert-title { font-size: 0.875rem; font-weight: 500; color: #e2e8f0; }
.alert-source { font-size: 0.72rem; color: #64748b; margin-top: 2px; }
.alert-pct {
    font-size: 1.1rem;
    font-weight: 700;
    color: var(--alert-color, #ef4444);
}

/* ── Live pulse ──────────────────────────────────────────── */
@keyframes pulse {
    0%, 100% { opacity: 1; transform: scale(1); }
    50%       { opacity: 0.4; transform: scale(0.85); }
}
.live-dot {
    display: inline-block;
    width: 7px; height: 7px;
    background: #10b981;
    border-radius: 50%;
    animation: pulse 1.8s ease-in-out infinite;
    margin-right: 6px;
    vertical-align: middle;
}
.live-badge {
    display: inline-flex;
    align-items: center;
    background: #052e16;
    border: 1px solid #065f46;
    border-radius: 20px;
    padding: 2px 10px 2px 6px;
    font-size: 0.72rem;
    font-weight: 600;
    color: #10b981;
    letter-spacing: 0.06em;
}

/* ── Stat result cards ───────────────────────────────────── */
.stat-result {
    background: #111827;
    border: 1px solid #1e2d45;
    border-radius: 10px;
    padding: 1rem 1.2rem;
    margin-bottom: 0.75rem;
}
.stat-result-title {
    font-size: 0.8rem;
    font-weight: 600;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-bottom: 0.5rem;
}
.stat-result-row {
    display: flex;
    gap: 2rem;
    flex-wrap: wrap;
}
.stat-result-item { }
.stat-result-item .val {
    font-size: 1.1rem;
    font-weight: 700;
    color: #f1f5f9;
}
.stat-result-item .lbl {
    font-size: 0.68rem;
    color: #64748b;
    font-weight: 500;
    letter-spacing: 0.04em;
    text-transform: uppercase;
}
.verdict-reject {
    display: inline-block;
    background: #1c1917;
    border: 1px solid #ef4444;
    border-radius: 6px;
    padding: 2px 10px;
    font-size: 0.75rem;
    font-weight: 700;
    color: #ef4444;
    margin-top: 0.4rem;
}
.verdict-fail {
    display: inline-block;
    background: #0f1e2e;
    border: 1px solid #3b82f6;
    border-radius: 6px;
    padding: 2px 10px;
    font-size: 0.75rem;
    font-weight: 700;
    color: #60a5fa;
    margin-top: 0.4rem;
}

/* ── Page title ──────────────────────────────────────────── */
.page-title {
    font-size: 1.5rem;
    font-weight: 700;
    color: #f1f5f9;
    margin-bottom: 0.2rem;
}
.page-subtitle {
    font-size: 0.82rem;
    color: #64748b;
    margin-bottom: 1.4rem;
}

/* ── Plotly chart containers ─────────────────────────────── */
[data-testid="stPlotlyChart"] {
    background: #111827 !important;
    border: 1px solid #1e2d45 !important;
    border-radius: 12px !important;
    padding: 4px !important;
}

/* ── DataFrame ───────────────────────────────────────────── */
[data-testid="stDataFrame"] {
    border: 1px solid #1e2d45 !important;
    border-radius: 10px !important;
    overflow: hidden;
}

/* ── Filter bar ──────────────────────────────────────────── */
.filter-bar {
    background: #111827;
    border: 1px solid #1e2d45;
    border-radius: 12px;
    padding: 1rem 1.2rem;
    margin-bottom: 1rem;
}

/* ── Streamlit elements override ─────────────────────────── */
[data-testid="stTextInput"] input,
[data-testid="stSelectbox"] select,
div[data-baseweb="select"] {
    background: #0d1322 !important;
    border-color: #1e2d45 !important;
    color: #e2e8f0 !important;
}

/* ── Tabs ─────────────────────────────────────────────────── */
[data-testid="stTabs"] [data-baseweb="tab-list"] {
    background: #0d1322;
    border-bottom: 1px solid #1e2d45;
    gap: 0;
}
[data-testid="stTabs"] [data-baseweb="tab"] {
    color: #64748b;
    font-size: 0.82rem;
    font-weight: 500;
    padding: 0.6rem 1.1rem;
}
[data-testid="stTabs"] [aria-selected="true"] {
    color: #60a5fa !important;
    border-bottom: 2px solid #3b82f6 !important;
    background: transparent !important;
}

/* ── Divider ─────────────────────────────────────────────── */
hr {
    border: none;
    border-top: 1px solid #1e2d45;
    margin: 1rem 0;
}

/* ── Scrollbar ───────────────────────────────────────────── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #0d1322; }
::-webkit-scrollbar-thumb { background: #1e2d45; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #2d4a6e; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────
PAGES = [
    ("⚡", "Live Prices",          "Real-time scraped prices"),
    ("📈", "Historical KPIs",      "dbt mart aggregates"),
    ("🔬", "Statistical Analysis", "Hypothesis tests & regression"),
    ("🔔", "Price Alerts",         "Significant price drops"),
]

SOURCE_COLORS = {
    "books_toscrape":     "#6366f1",
    "books.toscrape.com": "#6366f1",
    "scrapeme_live":      "#f59e0b",
    "scrapeme.live":      "#f59e0b",
    "jumia_ma":           "#f97316",
    "jumia.ma":           "#f97316",
    "ultrapc_ma":         "#06b6d4",
    "ultrapc.ma":         "#06b6d4",
    "micromagma_ma":      "#10b981",
    "micromagma.ma":      "#10b981",
}

CHART_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font_color="#94a3b8",
    title_font_color="#e2e8f0",
    title_font_size=13,
    title_font_family="Inter",
    legend=dict(bgcolor="rgba(0,0,0,0)", font_color="#94a3b8"),
    margin=dict(l=16, r=16, t=40, b=16),
    xaxis=dict(gridcolor="#1e2d45", zerolinecolor="#1e2d45", tickfont_color="#64748b"),
    yaxis=dict(gridcolor="#1e2d45", zerolinecolor="#1e2d45", tickfont_color="#64748b"),
)

# ─────────────────────────────────────────────────────────────────────────────
# Session state — active page
# ─────────────────────────────────────────────────────────────────────────────
if "page" not in st.session_state:
    st.session_state.page = "Live Prices"

# ─────────────────────────────────────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="padding:1rem 0.5rem 0.5rem">
      <div style="font-size:1.15rem;font-weight:700;color:#f1f5f9;letter-spacing:-0.01em">
        ⚡ Price Intelligence
      </div>
      <div style="font-size:0.72rem;color:#475569;margin-top:3px">
        Real-Time E-commerce Platform
      </div>
    </div>
    <hr style="border-top:1px solid #1e2d45;margin:0.75rem 0 1rem"/>
    """, unsafe_allow_html=True)

    st.markdown("<div style='font-size:0.68rem;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;color:#475569;margin-bottom:0.5rem'>Navigation</div>", unsafe_allow_html=True)

    for icon, label, _ in PAGES:
        active = st.session_state.page == label
        css_class = "nav-btn-active" if active else "nav-btn"
        with st.container():
            st.markdown(f"<div class='{css_class}'>", unsafe_allow_html=True)
            if st.button(f"{icon}  {label}", key=f"nav_{label}", use_container_width=True):
                st.session_state.page = label
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<hr style='border-top:1px solid #1e2d45;margin:1rem 0'/>", unsafe_allow_html=True)

    st.markdown("<div style='font-size:0.68rem;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;color:#475569;margin-bottom:0.6rem'>Controls</div>", unsafe_allow_html=True)

    auto_refresh = st.toggle("Auto-refresh every 30s", value=False)

    if st.button("↺  Refresh data", use_container_width=True, type="primary"):
        st.cache_data.clear()
        st.rerun()

    st.markdown(f"""
    <div style="margin-top:1rem;padding:0.75rem;background:#0d1322;border:1px solid #1e2d45;border-radius:8px">
      <div style="font-size:0.68rem;color:#475569;font-weight:600;letter-spacing:0.06em;text-transform:uppercase;margin-bottom:0.4rem">Status</div>
      <div class="live-badge"><span class="live-dot"></span> LIVE</div>
      <div style="font-size:0.68rem;color:#475569;margin-top:0.5rem">Last refresh<br/><span style="color:#94a3b8;font-weight:600">{time.strftime('%H:%M:%S')}</span></div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div style="position:absolute;bottom:1.5rem;left:0;right:0;padding:0 1rem">
      <div style="font-size:0.65rem;color:#334155;text-align:center">
        Final Year Data Engineering Project<br/>
        <span style="color:#475569">Hassan RADA • 2026</span>
      </div>
    </div>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# Cached loaders
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=30)
def _live() -> pd.DataFrame:
    return load_live(limit=5000)

@st.cache_data(ttl=300)
def _mart(table: str) -> pd.DataFrame:
    return load_mart(table)

# ─────────────────────────────────────────────────────────────────────────────
# Reusable UI components
# ─────────────────────────────────────────────────────────────────────────────
def kpi_card(label: str, value: str, sub: str = "", icon: str = "", accent: str = "#3b82f6", delta: str = "", delta_positive: bool = True):
    delta_html = ""
    if delta:
        cls = "kpi-delta-pos" if delta_positive else "kpi-delta-neg"
        arrow = "▲" if delta_positive else "▼"
        delta_html = f'<div class="{cls}">{arrow} {delta}</div>'
    st.markdown(f"""
    <div class="kpi-card" style="--accent:{accent}">
      <div class="kpi-label">{label}</div>
      <div class="kpi-value">{value}</div>
      {f'<div class="kpi-sub">{sub}</div>' if sub else ''}
      {delta_html}
      <div class="kpi-icon">{icon}</div>
    </div>
    """, unsafe_allow_html=True)


def section_header(title: str, badge: str = "", icon: str = ""):
    badge_html = f'<span class="section-badge">{badge}</span>' if badge else ""
    st.markdown(f"""
    <div class="section-header">
      <h2>{icon} {title}</h2>
      {badge_html}
    </div>
    """, unsafe_allow_html=True)


def no_data_card():
    st.markdown("""
    <div style="background:#111827;border:1px dashed #1e2d45;border-radius:12px;
                padding:3rem;text-align:center;margin:2rem 0">
      <div style="font-size:2rem;margin-bottom:0.75rem">📭</div>
      <div style="font-size:1rem;font-weight:600;color:#e2e8f0;margin-bottom:0.4rem">No data found</div>
      <div style="font-size:0.82rem;color:#64748b;margin-bottom:1.2rem">
        Run a spider to populate the dashboard
      </div>
      <code style="background:#0d1322;border:1px solid #1e2d45;border-radius:6px;
                   padding:0.5rem 1rem;font-size:0.8rem;color:#60a5fa">
        make scrape-books-sample
      </code>
    </div>
    """, unsafe_allow_html=True)


def chart_fig(fig: go.Figure, height: int = 340) -> go.Figure:
    fig.update_layout(**CHART_LAYOUT, height=height)
    return fig


# ═════════════════════════════════════════════════════════════════════════════
# PAGE 1 — Live Prices
# ═════════════════════════════════════════════════════════════════════════════
def page_live_prices():
    st.markdown("""
    <div class="page-title">⚡ Live Prices</div>
    <div class="page-subtitle">Most recent observation per product — auto-deduped by product_id</div>
    """, unsafe_allow_html=True)

    df = _live()
    if df.empty:
        no_data_card()
        return

    # Latest observation per product
    if "scraped_at" in df.columns:
        df = df.sort_values("scraped_at").groupby("product_id").last().reset_index()

    # ── Filter bar ────────────────────────────────────────────────────────────
    st.markdown('<div class="filter-bar">', unsafe_allow_html=True)
    fc1, fc2, fc3, fc4 = st.columns([3, 2, 2, 1])
    with fc1:
        search = st.text_input("", placeholder="🔍  Search by title, category…", label_visibility="collapsed")
    with fc2:
        sources_available = ["All sources"] + sorted(df["source"].dropna().unique().tolist())
        source_filter = st.selectbox("", sources_available, label_visibility="collapsed")
    with fc3:
        avail_opts = ["All availability"]
        if "availability" in df.columns:
            avail_opts += sorted(df["availability"].dropna().unique().tolist())
        avail_filter = st.selectbox("", avail_opts, label_visibility="collapsed")
    with fc4:
        sort_by = st.selectbox("", ["Price ↑", "Price ↓", "Rating ↓"], label_visibility="collapsed")
    st.markdown('</div>', unsafe_allow_html=True)

    # Apply filters
    filtered = df.copy()
    if search:
        mask = filtered.apply(lambda r: search.lower() in str(r.get("title","")).lower()
                              or search.lower() in str(r.get("category","")).lower(), axis=1)
        filtered = filtered[mask]
    if source_filter != "All sources":
        filtered = filtered[filtered["source"] == source_filter]
    if avail_filter != "All availability" and "availability" in filtered.columns:
        filtered = filtered[filtered["availability"] == avail_filter]

    sort_map = {"Price ↑": ("price", True), "Price ↓": ("price", False), "Rating ↓": ("rating", False)}
    s_col, s_asc = sort_map[sort_by]
    if s_col in filtered.columns:
        filtered = filtered.sort_values(s_col, ascending=s_asc)

    # ── KPI row ───────────────────────────────────────────────────────────────
    k1, k2, k3, k4, k5 = st.columns(5)
    with k1:
        kpi_card("Products tracked", f"{len(filtered):,}", icon="📦", accent="#6366f1")
    with k2:
        kpi_card("Sources active", str(filtered["source"].nunique()), icon="🌐", accent="#06b6d4")
    with k3:
        avg = filtered["price"].mean() if not filtered.empty else 0
        kpi_card("Avg price", f"{avg:.2f}", icon="💰", accent="#10b981")
    with k4:
        low = filtered["price"].min() if not filtered.empty else 0
        kpi_card("Lowest price", f"{low:.2f}", icon="📉", accent="#3b82f6")
    with k5:
        hi = filtered["price"].max() if not filtered.empty else 0
        kpi_card("Highest price", f"{hi:.2f}", icon="📈", accent="#f59e0b")

    st.markdown("<div style='margin:1.2rem 0'></div>", unsafe_allow_html=True)

    # ── Charts row ────────────────────────────────────────────────────────────
    ch1, ch2 = st.columns([3, 2])

    with ch1:
        section_header("Price Distribution", badge="per source", icon="📦")
        if not filtered.empty:
            fig = px.violin(
                filtered, x="source", y="price",
                color="source", color_discrete_map=SOURCE_COLORS,
                box=True, points="outliers",
                log_y=True,
                labels={"price": "Price (log)", "source": ""},
            )
            fig.update_traces(meanline_visible=True)
            fig = chart_fig(fig, 320)
            fig.update_layout(showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

    with ch2:
        section_header("Market share", badge="by source", icon="🌐")
        if not filtered.empty:
            share = filtered.groupby("source").size().reset_index(name="count")
            fig2 = px.pie(
                share, values="count", names="source",
                color="source", color_discrete_map=SOURCE_COLORS,
                hole=0.55,
            )
            fig2.update_traces(textposition="outside", textinfo="percent+label",
                               textfont_size=11, textfont_color="#94a3b8",
                               marker_line_color="#0d1322", marker_line_width=2)
            fig2 = chart_fig(fig2, 320)
            fig2.update_layout(showlegend=False)
            st.plotly_chart(fig2, use_container_width=True)

    # ── Product table ─────────────────────────────────────────────────────────
    section_header("Product catalogue", badge=f"{len(filtered):,} items", icon="🗂️")

    def _source_color(val):
        c = SOURCE_COLORS.get(val, "#475569")
        return f"background-color:{c}22;color:{c};padding:2px 8px;border-radius:4px;font-size:0.75rem;font-weight:600"

    show_cols = [c for c in ["title","source","price","currency",
                              "availability","category","rating","scraped_at"]
                 if c in filtered.columns]
    st.dataframe(
        filtered[show_cols].reset_index(drop=True),
        use_container_width=True,
        height=400,
        column_config={
            "price":      st.column_config.NumberColumn("Price", format="%.2f", help="Latest scraped price"),
            "rating":     st.column_config.NumberColumn("Rating ⭐", format="%.1f"),
            "scraped_at": st.column_config.DatetimeColumn("Scraped at", format="MMM DD, HH:mm"),
            "source":     st.column_config.TextColumn("Source"),
            "title":      st.column_config.TextColumn("Product", width="large"),
        },
        hide_index=True,
    )


# ═════════════════════════════════════════════════════════════════════════════
# PAGE 2 — Historical KPIs
# ═════════════════════════════════════════════════════════════════════════════
def page_historical_kpis():
    st.markdown("""
    <div class="page-title">📈 Historical KPIs</div>
    <div class="page-subtitle">Aggregated metrics from dbt mart tables — BigQuery or JSONL fallback</div>
    """, unsafe_allow_html=True)

    stats_df = _mart("mart_price_stats")
    hist_df  = _mart("mart_price_history")

    if stats_df.empty and hist_df.empty:
        no_data_card()
        return

    # ── Source KPI cards ──────────────────────────────────────────────────────
    if not stats_df.empty:
        section_header("Aggregate statistics", badge="per source", icon="📊")
        accents = ["#6366f1","#06b6d4","#10b981","#f59e0b","#f97316"]
        icons   = ["📚","🛒","🛍️","💻","🖥️"]
        cols = st.columns(min(len(stats_df), 5))
        for i, (_, row) in enumerate(stats_df.iterrows()):
            with cols[i % len(cols)]:
                src   = str(row.get("source", "?"))
                avg   = row.get("avg_price", 0)
                med   = row.get("median_price", 0)
                sd    = row.get("stddev_price", 0)
                cnt   = row.get("product_count", 0)
                cur   = row.get("currency", "")
                kpi_card(
                    label=src.replace("_", " ").title(),
                    value=f"{avg:.2f} {cur}",
                    sub=f"median {med:.2f} · σ {sd:.2f}",
                    icon=icons[i % len(icons)],
                    accent=accents[i % len(accents)],
                )

        st.markdown("<div style='margin:1.2rem 0'></div>", unsafe_allow_html=True)

        # ── Grouped bar chart ─────────────────────────────────────────────────
        section_header("Price ranges", badge="min / avg / median / max", icon="📉")
        price_cols = [c for c in ["min_price","avg_price","median_price","max_price"] if c in stats_df.columns]
        if price_cols and "source" in stats_df.columns:
            melted = stats_df.melt(id_vars="source", value_vars=price_cols,
                                   var_name="metric", value_name="price")
            label_map = {"min_price":"Min","avg_price":"Avg","median_price":"Median","max_price":"Max"}
            melted["metric"] = melted["metric"].map(label_map)
            fig = px.bar(
                melted, x="source", y="price", color="metric",
                barmode="group",
                color_discrete_sequence=["#3b82f6","#10b981","#f59e0b","#ef4444"],
                labels={"price":"Price","source":"","metric":""},
            )
            fig.update_traces(marker_line_width=0)
            st.plotly_chart(chart_fig(fig, 360), use_container_width=True)

        # ── Stats table ───────────────────────────────────────────────────────
        section_header("Full statistics table", icon="🗂️")
        st.dataframe(
            stats_df.reset_index(drop=True),
            use_container_width=True,
            column_config={c: st.column_config.NumberColumn(c, format="%.2f")
                           for c in stats_df.select_dtypes("number").columns},
            hide_index=True,
        )

    # ── Price trend selector ──────────────────────────────────────────────────
    if not hist_df.empty and "scraped_date" in hist_df.columns and "product_id" in hist_df.columns:
        section_header("Price trend explorer", badge="per product", icon="📈")

        def _label(pid):
            rows = hist_df[hist_df["product_id"] == pid]
            return rows["title"].iloc[0] if not rows.empty and "title" in rows.columns else pid

        pid_list = hist_df["product_id"].unique().tolist()
        sel_pid  = st.selectbox("Select a product", pid_list, format_func=_label)

        trend = hist_df[hist_df["product_id"] == sel_pid].sort_values("scraped_date")
        if not trend.empty:
            fig3 = px.line(
                trend, x="scraped_date", y="price",
                markers=True,
                labels={"price": "Price", "scraped_date": "Date"},
                color_discrete_sequence=["#6366f1"],
            )
            if "price_change_pct" in trend.columns:
                drops = trend[trend["price_change_pct"] <= -5]
                if not drops.empty:
                    fig3.add_scatter(
                        x=drops["scraped_date"], y=drops["price"],
                        mode="markers",
                        marker=dict(color="#ef4444", size=10, symbol="triangle-down"),
                        name="Price drop ≥5%",
                    )
            fig3.update_traces(line_width=2.5)
            st.plotly_chart(chart_fig(fig3, 300), use_container_width=True)

            if "price_change_pct" in trend.columns:
                tc1, tc2, tc3 = st.columns(3)
                with tc1:
                    kpi_card("Price high", f"{trend['price'].max():.2f}", icon="⬆️", accent="#ef4444")
                with tc2:
                    kpi_card("Price low", f"{trend['price'].min():.2f}", icon="⬇️", accent="#10b981")
                with tc3:
                    total_chg = trend["price"].iloc[-1] - trend["price"].iloc[0] if len(trend) > 1 else 0
                    pos = total_chg >= 0
                    kpi_card("Total change",
                             f"{'+'if pos else ''}{total_chg:.2f}",
                             icon="📊",
                             accent="#10b981" if pos else "#ef4444")


# ═════════════════════════════════════════════════════════════════════════════
# PAGE 3 — Statistical Analysis
# ═════════════════════════════════════════════════════════════════════════════
def page_statistics():
    st.markdown("""
    <div class="page-title">🔬 Statistical Analysis</div>
    <div class="page-subtitle">Descriptive statistics, hypothesis tests, and regression — computed live on scraped data</div>
    """, unsafe_allow_html=True)

    df = _live()
    if df.empty:
        no_data_card()
        return

    tab1, tab2, tab3 = st.tabs(["📊  Descriptive", "🧪  Inferential Tests", "📐  Regression"])

    # ── Tab 1: Descriptive ────────────────────────────────────────────────────
    with tab1:
        section_header("Summary statistics", badge="per source", icon="📊")
        desc = (
            df.groupby("source")["price"]
            .agg(
                n="count",
                mean=lambda s: round(s.mean(), 2),
                median=lambda s: round(s.median(), 2),
                std=lambda s: round(s.std(), 2),
                min="min",
                q25=lambda s: round(s.quantile(0.25), 2),
                q75=lambda s: round(s.quantile(0.75), 2),
                max="max",
                skewness=lambda s: round(float(scipy_stats.skew(s.dropna())), 3),
                kurtosis=lambda s: round(float(scipy_stats.kurtosis(s.dropna())), 3),
            )
            .reset_index()
        )
        st.dataframe(
            desc, use_container_width=True, hide_index=True,
            column_config={c: st.column_config.NumberColumn(c, format="%.2f")
                           for c in desc.select_dtypes("number").columns},
        )

        ch_a, ch_b = st.columns(2)
        with ch_a:
            section_header("Distribution (log scale)", icon="📉")
            fig_h = px.histogram(
                df, x="price", color="source",
                barmode="overlay", opacity=0.65, log_x=True, nbins=55,
                color_discrete_map=SOURCE_COLORS,
                labels={"price": "Price (log)", "count": "Count"},
            )
            st.plotly_chart(chart_fig(fig_h, 300), use_container_width=True)

        with ch_b:
            section_header("Volatility (CV %)", icon="📊")
            vol = df.groupby("source")["price"].apply(
                lambda s: round(s.std() / s.mean() * 100, 1) if s.mean() > 0 else 0
            ).reset_index()
            vol.columns = ["source", "cv_pct"]
            vol = vol.sort_values("cv_pct", ascending=False)
            fig_v = px.bar(
                vol, x="source", y="cv_pct",
                color="source", color_discrete_map=SOURCE_COLORS,
                text="cv_pct",
                labels={"cv_pct": "CV (%)", "source": ""},
            )
            fig_v.update_traces(texttemplate="%{text:.1f}%", textposition="outside",
                                marker_line_width=0)
            fig_v.update_layout(showlegend=False)
            st.plotly_chart(chart_fig(fig_v, 300), use_container_width=True)

    # ── Tab 2: Inferential ────────────────────────────────────────────────────
    with tab2:
        groups = {s: df[df["source"] == s]["price"].dropna()
                  for s in df["source"].unique()}
        groups = {k: v for k, v in groups.items() if len(v) >= 3}

        if len(groups) < 2:
            st.info("Need ≥ 2 sources with ≥ 3 observations.")
        else:
            # Shapiro-Wilk
            section_header("Normality — Shapiro-Wilk", badge="H₀: data is normal", icon="📐")
            norm_rows = []
            for src, g in groups.items():
                w, p = scipy_stats.shapiro(g.head(5000))
                norm_rows.append({
                    "Source": src,
                    "n": len(g),
                    "W statistic": round(w, 4),
                    "p-value": round(p, 6),
                    "Normal?": "✅  Yes" if p >= 0.05 else "❌  No",
                })
            st.dataframe(pd.DataFrame(norm_rows), use_container_width=True, hide_index=True)

            # ANOVA
            section_header("One-Way ANOVA", badge="H₀: all means equal", icon="📊")
            f_stat, p_anova = scipy_stats.f_oneway(*groups.values())
            reject_anova = p_anova < 0.05
            verdict_cls  = "verdict-reject" if reject_anova else "verdict-fail"
            verdict_txt  = "Reject H₀ — means differ" if reject_anova else "Fail to reject H₀"
            st.markdown(f"""
            <div class="stat-result">
              <div class="stat-result-title">One-Way ANOVA result</div>
              <div class="stat-result-row">
                <div class="stat-result-item"><div class="val">{f_stat:.4f}</div><div class="lbl">F-statistic</div></div>
                <div class="stat-result-item"><div class="val">{p_anova:.2e}</div><div class="lbl">p-value</div></div>
                <div class="stat-result-item"><div class="val">α = 0.05</div><div class="lbl">threshold</div></div>
              </div>
              <div class="{verdict_cls}">{verdict_txt}</div>
            </div>
            """, unsafe_allow_html=True)

            # Kruskal-Wallis
            section_header("Kruskal-Wallis", badge="non-parametric ANOVA", icon="🔬")
            h_stat, p_kw = scipy_stats.kruskal(*groups.values())
            reject_kw = p_kw < 0.05
            verdict_cls_kw = "verdict-reject" if reject_kw else "verdict-fail"
            verdict_txt_kw = "Reject H₀ — distributions differ" if reject_kw else "Fail to reject H₀"
            st.markdown(f"""
            <div class="stat-result">
              <div class="stat-result-title">Kruskal-Wallis result</div>
              <div class="stat-result-row">
                <div class="stat-result-item"><div class="val">{h_stat:.4f}</div><div class="lbl">H-statistic</div></div>
                <div class="stat-result-item"><div class="val">{p_kw:.2e}</div><div class="lbl">p-value</div></div>
              </div>
              <div class="{verdict_cls_kw}">{verdict_txt_kw}</div>
            </div>
            """, unsafe_allow_html=True)

            # Pairwise Mann-Whitney U
            section_header("Pairwise Mann-Whitney U", badge="non-parametric", icon="🔗")
            src_list = list(groups.keys())
            mw_rows  = []
            for a, b in itertools.combinations(src_list, 2):
                u, p_mw = scipy_stats.mannwhitneyu(groups[a], groups[b], alternative="two-sided")
                n1, n2  = len(groups[a]), len(groups[b])
                r_eff   = round(1 - (2 * u) / (n1 * n2), 3)
                mw_rows.append({
                    "Source A": a, "Source B": b,
                    "U statistic": round(u, 0),
                    "p-value": round(p_mw, 6),
                    "Effect r": r_eff,
                    "Significant": "✅  Yes" if p_mw < 0.05 else "❌  No",
                })
            st.dataframe(pd.DataFrame(mw_rows).sort_values("p-value"),
                         use_container_width=True, hide_index=True)

            # 95% CI
            section_header("95% Confidence Intervals", badge="mean price", icon="📏")
            ci_rows = []
            for src, g in groups.items():
                n, se = len(g), scipy_stats.sem(g)
                lo, hi = scipy_stats.t.interval(0.95, df=n - 1, loc=g.mean(), scale=se)
                ci_rows.append({
                    "Source": src, "n": n,
                    "Mean": round(g.mean(), 2),
                    "95% CI Lower": round(lo, 2),
                    "95% CI Upper": round(hi, 2),
                    "Width": round(hi - lo, 2),
                })
            ci_df = pd.DataFrame(ci_rows)
            st.dataframe(ci_df, use_container_width=True, hide_index=True)

            # CI Forest plot
            fig_ci = go.Figure()
            for _, row in ci_df.iterrows():
                color = SOURCE_COLORS.get(row["Source"], "#6366f1")
                fig_ci.add_trace(go.Scatter(
                    x=[row["95% CI Lower"], row["95% CI Upper"]],
                    y=[row["Source"], row["Source"]],
                    mode="lines", line=dict(width=5, color=color),
                    showlegend=False,
                ))
                fig_ci.add_trace(go.Scatter(
                    x=[row["Mean"]], y=[row["Source"]],
                    mode="markers",
                    marker=dict(size=12, color=color, symbol="diamond",
                                line=dict(color="#080d1a", width=2)),
                    showlegend=False,
                ))
            fig_ci.update_layout(
                **CHART_LAYOUT,
                height=280,
                xaxis_title="Price",
                yaxis_title="",
            )
            st.plotly_chart(fig_ci, use_container_width=True)

    # ── Tab 3: Regression ─────────────────────────────────────────────────────
    with tab3:
        section_header("Linear Regression", badge="price ~ rating", icon="📐")
        reg_df = df.dropna(subset=["price", "rating"]) if "rating" in df.columns else pd.DataFrame()
        if reg_df.empty or len(reg_df) < 5:
            st.info("Not enough products with rating data.")
        else:
            slope, intercept, r, p, se = scipy_stats.linregress(reg_df["rating"], reg_df["price"])
            r2 = r ** 2
            r1, r2c, r3, r4 = st.columns(4)
            with r1:
                kpi_card("Slope (β₁)", f"{slope:.4f}", sub="price per rating unit",
                         accent="#6366f1" if slope > 0 else "#ef4444", icon="📈")
            with r2c:
                kpi_card("Intercept (β₀)", f"{intercept:.2f}", icon="🎯", accent="#06b6d4")
            with r3:
                kpi_card("R²", f"{r2:.4f}", sub="variance explained", icon="📊",
                         accent="#10b981" if r2 > 0.3 else "#f59e0b")
            with r4:
                kpi_card("p-value", f"{p:.2e}",
                         sub="significant" if p < 0.05 else "not significant",
                         icon="🔬",
                         accent="#10b981" if p < 0.05 else "#ef4444")

            st.markdown("<div style='margin:1rem 0'></div>", unsafe_allow_html=True)

            fig_r = px.scatter(
                reg_df, x="rating", y="price",
                color="source", color_discrete_map=SOURCE_COLORS,
                opacity=0.55, trendline="ols",
                labels={"price": "Price", "rating": "Rating"},
            )
            fig_r.update_traces(marker_size=6)
            st.plotly_chart(chart_fig(fig_r, 400), use_container_width=True)

            # Per-source regression table
            section_header("Regression per source", icon="📋")
            reg_rows = []
            for src, g in df.groupby("source"):
                gf = g.dropna(subset=["price","rating"])
                if len(gf) < 5:
                    continue
                sl, ic, rv, pv, sv = scipy_stats.linregress(gf["rating"], gf["price"])
                reg_rows.append({
                    "Source": src, "n": len(gf),
                    "Slope": round(sl, 4), "Intercept": round(ic, 2),
                    "R": round(rv, 4), "R²": round(rv**2, 4),
                    "p-value": round(pv, 6),
                    "Significant": "✅" if pv < 0.05 else "❌",
                })
            if reg_rows:
                st.dataframe(pd.DataFrame(reg_rows), use_container_width=True, hide_index=True)


# ═════════════════════════════════════════════════════════════════════════════
# PAGE 4 — Price Alerts
# ═════════════════════════════════════════════════════════════════════════════
def page_alerts():
    st.markdown("""
    <div class="page-title">🔔 Price Alerts</div>
    <div class="page-subtitle">Products with a price drop ≥ 5% detected across all sources</div>
    """, unsafe_allow_html=True)

    alerts = _mart("mart_price_alerts")

    if alerts.empty:
        st.markdown("""
        <div style="background:#052e16;border:1px solid #065f46;border-radius:12px;
                    padding:2rem;text-align:center;margin:2rem 0">
          <div style="font-size:1.5rem;margin-bottom:0.5rem">✅</div>
          <div style="font-size:1rem;font-weight:600;color:#10b981">No significant price drops detected</div>
          <div style="font-size:0.8rem;color:#065f46;margin-top:0.3rem">All prices are stable</div>
        </div>
        """, unsafe_allow_html=True)
        return

    # ── KPI row ───────────────────────────────────────────────────────────────
    a1, a2, a3, a4 = st.columns(4)
    with a1:
        kpi_card("Total alerts", str(len(alerts)), icon="🚨", accent="#ef4444")
    with a2:
        big = alerts["price_change_pct"].min() if "price_change_pct" in alerts.columns else 0
        kpi_card("Biggest drop", f"{big:.1f}%", icon="📉", accent="#f97316")
    with a3:
        srcs = alerts["source"].nunique() if "source" in alerts.columns else 0
        kpi_card("Sources affected", str(srcs), icon="🌐", accent="#f59e0b")
    with a4:
        severe = len(alerts[alerts["price_change_pct"] <= -20]) if "price_change_pct" in alerts.columns else 0
        kpi_card("Severe (≥20%)", str(severe), icon="⚠️", accent="#ef4444")

    st.markdown("<div style='margin:1.2rem 0'></div>", unsafe_allow_html=True)

    # ── Alert cards ───────────────────────────────────────────────────────────
    if "price_change_pct" in alerts.columns:
        section_header("Top price drops", badge="worst first", icon="📉")
        top = alerts.sort_values("price_change_pct").head(10)
        for _, row in top.iterrows():
            pct  = row.get("price_change_pct", 0)
            title = str(row.get("title", row.get("product_id", "Unknown")))[:60]
            src  = str(row.get("source", ""))
            cur  = str(row.get("price", ""))
            prev = str(row.get("prev_price", ""))
            if pct <= -20:
                color = "#ef4444"
            elif pct <= -10:
                color = "#f97316"
            else:
                color = "#f59e0b"
            st.markdown(f"""
            <div class="alert-card" style="--alert-color:{color}">
              <div>
                <div class="alert-title">{title}</div>
                <div class="alert-source">{src} &nbsp;·&nbsp; {prev} → {cur}</div>
              </div>
              <div class="alert-pct" style="color:{color}">{pct:.1f}%</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<div style='margin:1rem 0'></div>", unsafe_allow_html=True)

    # ── Chart ─────────────────────────────────────────────────────────────────
    if "price_change_pct" in alerts.columns and "source" in alerts.columns:
        section_header("Price drop chart", badge="top 20", icon="📊")
        y_col = "title" if "title" in alerts.columns else "product_id"
        plot_df = alerts.head(20).sort_values("price_change_pct").copy()
        if y_col in plot_df.columns:
            plot_df[y_col] = plot_df[y_col].astype(str).str[:40]
        fig = px.bar(
            plot_df, x="price_change_pct", y=y_col,
            color="source", color_discrete_map=SOURCE_COLORS,
            orientation="h",
            labels={"price_change_pct": "Price change (%)", y_col: ""},
            text="price_change_pct",
        )
        fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside",
                          marker_line_width=0)
        st.plotly_chart(chart_fig(fig, 460), use_container_width=True)

    # ── Full table ────────────────────────────────────────────────────────────
    section_header("All alerts", badge=f"{len(alerts)} rows", icon="🗂️")
    show = [c for c in ["title","source","price","prev_price","price_change_pct","currency"]
            if c in alerts.columns]
    st.dataframe(
        alerts[show].reset_index(drop=True),
        use_container_width=True,
        height=360,
        column_config={
            "price":            st.column_config.NumberColumn("Current price", format="%.2f"),
            "prev_price":       st.column_config.NumberColumn("Prev price", format="%.2f"),
            "price_change_pct": st.column_config.NumberColumn("Change %", format="%.2f"),
        },
        hide_index=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Router
# ─────────────────────────────────────────────────────────────────────────────
page_map = {
    "Live Prices":          page_live_prices,
    "Historical KPIs":      page_historical_kpis,
    "Statistical Analysis": page_statistics,
    "Price Alerts":         page_alerts,
}
page_map.get(st.session_state.page, page_live_prices)()

if auto_refresh:
    time.sleep(30)
    st.cache_data.clear()
    st.rerun()
