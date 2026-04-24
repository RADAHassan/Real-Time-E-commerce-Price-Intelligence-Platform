"""
Streamlit dashboard — Real-Time E-commerce Price Intelligence Platform
Professional dark UI · animated pill filters · interactive chips · dynamic features
"""
from __future__ import annotations

import itertools
import sys
import time
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
# Page config
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Price Intelligence",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# Design tokens & constants
# ─────────────────────────────────────────────────────────────────────────────
SOURCE_META = {
    "books_toscrape":     {"color": "#818cf8", "bg": "#1e1b4b", "label": "Books.ToScrape", "icon": "📚"},
    "books.toscrape.com": {"color": "#818cf8", "bg": "#1e1b4b", "label": "Books.ToScrape", "icon": "📚"},
    "scrapeme_live":      {"color": "#fbbf24", "bg": "#1c1407", "label": "ScrapeMe",       "icon": "🛒"},
    "scrapeme.live":      {"color": "#fbbf24", "bg": "#1c1407", "label": "ScrapeMe",       "icon": "🛒"},
    "jumia_ma":           {"color": "#fb923c", "bg": "#1c0f07", "label": "Jumia.ma",        "icon": "🛍️"},
    "jumia.ma":           {"color": "#fb923c", "bg": "#1c0f07", "label": "Jumia.ma",        "icon": "🛍️"},
    "ultrapc_ma":         {"color": "#22d3ee", "bg": "#071a1c", "label": "UltraPC.ma",     "icon": "💻"},
    "ultrapc.ma":         {"color": "#22d3ee", "bg": "#071a1c", "label": "UltraPC.ma",     "icon": "💻"},
    "micromagma_ma":      {"color": "#34d399", "bg": "#071c14", "label": "Micromagma.ma",  "icon": "🖥️"},
    "micromagma.ma":      {"color": "#34d399", "bg": "#071c14", "label": "Micromagma.ma",  "icon": "🖥️"},
}
DEFAULT_META = {"color": "#94a3b8", "bg": "#1e293b", "label": "Unknown", "icon": "🔷"}

def src_meta(source: str) -> dict:
    return SOURCE_META.get(source, DEFAULT_META)

SOURCE_COLORS = {k: v["color"] for k, v in SOURCE_META.items()}

CHART_BASE = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter", color="#94a3b8"),
    title_font=dict(color="#e2e8f0", size=13, family="Inter"),
    legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#94a3b8", size=11)),
    margin=dict(l=16, r=16, t=40, b=16),
    xaxis=dict(gridcolor="#1a2640", zerolinecolor="#1a2640",
               tickfont=dict(color="#475569", size=11), title_font=dict(color="#64748b")),
    yaxis=dict(gridcolor="#1a2640", zerolinecolor="#1a2640",
               tickfont=dict(color="#475569", size=11), title_font=dict(color="#64748b")),
)

PAGES = [
    ("⚡", "Live Prices",          "Real-time price feed"),
    ("📈", "Historical KPIs",      "dbt mart aggregates"),
    ("🔬", "Statistical Analysis", "Tests & regression"),
    ("🔔", "Price Alerts",         "Significant drops"),
]

# ─────────────────────────────────────────────────────────────────────────────
# Session state defaults
# ─────────────────────────────────────────────────────────────────────────────
def _init():
    defaults = {
        "page":           "Live Prices",
        "src_filter":     "ALL",
        "avail_filter":   "ALL",
        "search":         "",
        "sort_by":        "price_asc",
        "price_min":      0.0,
        "price_max":      9999.0,
        "show_filters":   True,
        "tab_stats":      0,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init()

# ─────────────────────────────────────────────────────────────────────────────
# Global CSS + JS
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

/* ── Base ─────────────────────────────────────────────────── */
html, body, [class*="css"] { font-family:'Inter',sans-serif; }
.stApp { background:#07101f; color:#e2e8f0; }
#MainMenu,footer,header { visibility:hidden; }
[data-testid="stDecoration"] { display:none; }

/* ── Sidebar ──────────────────────────────────────────────── */
[data-testid="stSidebar"] {
    background:linear-gradient(180deg,#0a1426 0%,#07101f 100%) !important;
    border-right:1px solid #1a2640;
}

/* ── All Streamlit buttons base reset ────────────────────── */
.stButton > button {
    font-family:'Inter',sans-serif !important;
    font-weight:600 !important;
    letter-spacing:0.01em;
    transition: all 0.18s cubic-bezier(0.4,0,0.2,1) !important;
    border-radius:8px !important;
    cursor:pointer !important;
}

/* ── Nav buttons (sidebar) ───────────────────────────────── */
div[data-nav-btn="inactive"] > div > button {
    width:100% !important;
    text-align:left !important;
    background:transparent !important;
    border:1px solid transparent !important;
    color:#64748b !important;
    font-size:0.83rem !important;
    font-weight:500 !important;
    padding:0.6rem 1rem !important;
    border-radius:10px !important;
    margin-bottom:3px !important;
}
div[data-nav-btn="inactive"] > div > button:hover {
    background:#111f38 !important;
    border-color:#1a2d4a !important;
    color:#cbd5e1 !important;
    transform:translateX(2px) !important;
}
div[data-nav-btn="active"] > div > button {
    width:100% !important;
    text-align:left !important;
    background:linear-gradient(90deg,#1a3a6c 0%,#112d5a 100%) !important;
    border:1px solid #1e4080 !important;
    border-left:3px solid #3b82f6 !important;
    color:#93c5fd !important;
    font-size:0.83rem !important;
    font-weight:600 !important;
    padding:0.6rem 1rem 0.6rem 0.85rem !important;
    border-radius:10px !important;
    margin-bottom:3px !important;
    box-shadow:0 0 14px rgba(59,130,246,0.15) !important;
}

/* ── Primary action button ───────────────────────────────── */
.stButton > button[kind="primary"] {
    background:linear-gradient(135deg,#2563eb 0%,#1d4ed8 100%) !important;
    border:1px solid #3b82f6 !important;
    color:#fff !important;
    font-size:0.82rem !important;
    padding:0.55rem 1.1rem !important;
    box-shadow:0 2px 12px rgba(59,130,246,0.3) !important;
}
.stButton > button[kind="primary"]:hover {
    background:linear-gradient(135deg,#1d4ed8 0%,#1e40af 100%) !important;
    box-shadow:0 4px 20px rgba(59,130,246,0.45) !important;
    transform:translateY(-1px) !important;
}
.stButton > button[kind="primary"]:active {
    transform:translateY(0) !important;
    box-shadow:0 1px 6px rgba(59,130,246,0.3) !important;
}

/* ── Secondary button ────────────────────────────────────── */
.stButton > button[kind="secondary"] {
    background:#111827 !important;
    border:1px solid #1e2d45 !important;
    color:#94a3b8 !important;
    font-size:0.82rem !important;
    padding:0.52rem 1rem !important;
}
.stButton > button[kind="secondary"]:hover {
    background:#1a2640 !important;
    border-color:#2d4a6e !important;
    color:#e2e8f0 !important;
    transform:translateY(-1px) !important;
}

/* ── Pill filter buttons ─────────────────────────────────── */
div[data-pill="active"] > div > button {
    background:var(--pill-bg, #1a3a6c) !important;
    border:1px solid var(--pill-color, #3b82f6) !important;
    color:var(--pill-color, #93c5fd) !important;
    font-size:0.75rem !important;
    font-weight:600 !important;
    padding:0.3rem 0.85rem !important;
    border-radius:20px !important;
    box-shadow:0 0 10px rgba(59,130,246,0.2) !important;
    letter-spacing:0.02em !important;
}
div[data-pill="inactive"] > div > button {
    background:#111827 !important;
    border:1px solid #1e2d45 !important;
    color:#475569 !important;
    font-size:0.75rem !important;
    font-weight:500 !important;
    padding:0.3rem 0.85rem !important;
    border-radius:20px !important;
}
div[data-pill="inactive"] > div > button:hover {
    background:#1a2640 !important;
    border-color:#2d4a6e !important;
    color:#94a3b8 !important;
    transform:translateY(-1px) !important;
}

/* ── Sort chip buttons ───────────────────────────────────── */
div[data-sort="active"] > div > button {
    background:#0c1a30 !important;
    border:1px solid #1e4080 !important;
    color:#60a5fa !important;
    font-size:0.72rem !important;
    padding:0.25rem 0.7rem !important;
    border-radius:6px !important;
}
div[data-sort="inactive"] > div > button {
    background:transparent !important;
    border:1px solid #1a2640 !important;
    color:#475569 !important;
    font-size:0.72rem !important;
    padding:0.25rem 0.7rem !important;
    border-radius:6px !important;
}
div[data-sort="inactive"] > div > button:hover {
    border-color:#2d4a6e !important;
    color:#94a3b8 !important;
}

/* ── Toggle ──────────────────────────────────────────────── */
.stToggle label { color:#64748b !important; font-size:0.8rem !important; }

/* ── Inputs ──────────────────────────────────────────────── */
[data-testid="stTextInput"] input {
    background:#0d1829 !important;
    border:1px solid #1a2d4a !important;
    border-radius:8px !important;
    color:#e2e8f0 !important;
    font-size:0.85rem !important;
    font-family:'Inter',sans-serif !important;
    transition:border-color 0.15s !important;
}
[data-testid="stTextInput"] input:focus {
    border-color:#3b82f6 !important;
    box-shadow:0 0 0 3px rgba(59,130,246,0.12) !important;
}

/* ── Slider ──────────────────────────────────────────────── */
[data-testid="stSlider"] .st-emotion-cache-1dx1gwv,
[data-testid="stSlider"] [role="slider"] {
    background:#3b82f6 !important;
}
[data-testid="stSlider"] .st-emotion-cache-1wqrzgl {
    color:#60a5fa !important;
}

/* ── Selectbox ───────────────────────────────────────────── */
div[data-baseweb="select"] > div {
    background:#0d1829 !important;
    border:1px solid #1a2d4a !important;
    border-radius:8px !important;
    color:#e2e8f0 !important;
}
div[data-baseweb="select"] > div:focus-within {
    border-color:#3b82f6 !important;
    box-shadow:0 0 0 3px rgba(59,130,246,0.12) !important;
}
div[data-baseweb="popover"] {
    background:#0d1829 !important;
    border:1px solid #1a2d4a !important;
}

/* ── Tabs ────────────────────────────────────────────────── */
[data-testid="stTabs"] [data-baseweb="tab-list"] {
    background:#0a1426;
    border-bottom:1px solid #1a2640;
    gap:4px;
    padding:0 4px;
}
[data-testid="stTabs"] [data-baseweb="tab"] {
    color:#475569;
    font-size:0.8rem;
    font-weight:500;
    padding:0.65rem 1.2rem;
    border-radius:6px 6px 0 0;
    transition:all 0.15s;
}
[data-testid="stTabs"] [data-baseweb="tab"]:hover { color:#94a3b8; }
[data-testid="stTabs"] [aria-selected="true"] {
    color:#60a5fa !important;
    background:#0d1829 !important;
    border-bottom:2px solid #3b82f6 !important;
}

/* ── Plotly chart containers ─────────────────────────────── */
[data-testid="stPlotlyChart"] {
    background:#0d1422 !important;
    border:1px solid #1a2640 !important;
    border-radius:14px !important;
    padding:4px !important;
    transition:border-color 0.2s !important;
}
[data-testid="stPlotlyChart"]:hover {
    border-color:#2d4a6e !important;
}

/* ── DataFrame ───────────────────────────────────────────── */
[data-testid="stDataFrame"] {
    border:1px solid #1a2640 !important;
    border-radius:12px !important;
    overflow:hidden !important;
}
.dvn-scroller { background:#0d1422 !important; }

/* ── Expander ────────────────────────────────────────────── */
[data-testid="stExpander"] {
    background:#0d1422 !important;
    border:1px solid #1a2640 !important;
    border-radius:10px !important;
}
[data-testid="stExpander"] summary {
    color:#94a3b8 !important;
    font-size:0.82rem !important;
    font-weight:600 !important;
}

/* ── KPI card ────────────────────────────────────────────── */
.kpi {
    background:linear-gradient(145deg,#0f1e38 0%,#0a1426 100%);
    border:1px solid #1a2640;
    border-radius:14px;
    padding:1.1rem 1.3rem 1rem;
    position:relative;
    overflow:hidden;
    transition:border-color 0.2s, transform 0.18s, box-shadow 0.18s;
    cursor:default;
}
.kpi:hover {
    border-color:var(--c,#3b82f6);
    transform:translateY(-2px);
    box-shadow:0 8px 24px rgba(0,0,0,0.3), 0 0 0 1px var(--c,#3b82f6)22;
}
.kpi::after {
    content:'';
    position:absolute;
    top:0;left:0;right:0;height:2px;
    background:var(--c,#3b82f6);
    border-radius:14px 14px 0 0;
}
.kpi-icon {
    position:absolute;
    top:0.9rem;right:1rem;
    font-size:1.4rem;
    opacity:0.12;
}
.kpi-label {
    font-size:0.68rem;font-weight:700;
    letter-spacing:0.1em;text-transform:uppercase;
    color:#475569;margin-bottom:0.5rem;
}
.kpi-val {
    font-size:1.8rem;font-weight:800;
    color:#f1f5f9;line-height:1;
    font-variant-numeric:tabular-nums;
}
.kpi-sub {
    font-size:0.72rem;color:#475569;
    margin-top:0.35rem;
}
.kpi-delta-pos { color:#34d399;font-size:0.73rem;font-weight:600;margin-top:0.3rem; }
.kpi-delta-neg { color:#f87171;font-size:0.73rem;font-weight:600;margin-top:0.3rem; }

/* ── Section header ──────────────────────────────────────── */
.sec {
    display:flex;align-items:center;gap:0.6rem;
    margin:1.5rem 0 0.8rem;
    padding-bottom:0.55rem;
    border-bottom:1px solid #1a2640;
}
.sec h3 { font-size:0.95rem;font-weight:600;color:#e2e8f0;margin:0; }
.sec-badge {
    font-size:0.65rem;font-weight:700;letter-spacing:0.07em;
    text-transform:uppercase;
    background:#111f38;color:#60a5fa;
    border:1px solid #1e3a6e;
    border-radius:4px;padding:1px 7px;
}

/* ── Page title ──────────────────────────────────────────── */
.ptitle { font-size:1.45rem;font-weight:800;color:#f1f5f9;margin-bottom:0.15rem; }
.psub   { font-size:0.8rem;color:#475569;margin-bottom:1.2rem; }

/* ── Live badge ──────────────────────────────────────────── */
@keyframes pulse {
    0%,100% { opacity:1; transform:scale(1); }
    50%      { opacity:0.35; transform:scale(0.8); }
}
.live-dot {
    display:inline-block;width:7px;height:7px;
    background:#34d399;border-radius:50%;
    animation:pulse 1.8s ease-in-out infinite;
    margin-right:5px;vertical-align:middle;
}
.live-badge {
    display:inline-flex;align-items:center;
    background:#052e16;border:1px solid #065f46;
    border-radius:20px;padding:2px 10px 2px 6px;
    font-size:0.68rem;font-weight:700;color:#34d399;letter-spacing:0.07em;
}

/* ── Filter panel ────────────────────────────────────────── */
.filter-panel {
    background:#0a1426;
    border:1px solid #1a2640;
    border-radius:14px;
    padding:1rem 1.25rem;
    margin-bottom:1.1rem;
}

/* ── Pill group label ────────────────────────────────────── */
.pill-label {
    font-size:0.65rem;font-weight:700;letter-spacing:0.09em;
    text-transform:uppercase;color:#334155;
    margin-bottom:0.35rem;
}

/* ── Alert card ──────────────────────────────────────────── */
@keyframes slideIn {
    from { opacity:0; transform:translateX(-8px); }
    to   { opacity:1; transform:translateX(0); }
}
.alert-card {
    display:flex;justify-content:space-between;align-items:center;
    background:#0d1829;
    border:1px solid #1a2640;
    border-left:4px solid var(--ac,#ef4444);
    border-radius:0 12px 12px 0;
    padding:0.85rem 1.2rem;
    margin-bottom:0.55rem;
    animation:slideIn 0.25s ease;
    transition:border-color 0.15s, transform 0.15s;
}
.alert-card:hover { transform:translateX(3px); border-color:var(--ac); }
.alert-title { font-size:0.85rem;font-weight:500;color:#e2e8f0; }
.alert-meta  { font-size:0.7rem;color:#475569;margin-top:2px; }
.alert-pct   { font-size:1.15rem;font-weight:800;color:var(--ac,#ef4444); }

/* ── Stat result ─────────────────────────────────────────── */
@keyframes fadeUp {
    from { opacity:0; transform:translateY(6px); }
    to   { opacity:1; transform:translateY(0); }
}
.stat-box {
    background:#0d1829;border:1px solid #1a2640;
    border-radius:12px;padding:1rem 1.25rem;
    margin-bottom:0.7rem;
    animation:fadeUp 0.2s ease;
}
.stat-box-title {
    font-size:0.68rem;font-weight:700;color:#334155;
    text-transform:uppercase;letter-spacing:0.08em;margin-bottom:0.6rem;
}
.stat-row { display:flex;gap:2rem;flex-wrap:wrap;align-items:flex-end; }
.stat-val { font-size:1.15rem;font-weight:700;color:#f1f5f9; }
.stat-lbl { font-size:0.65rem;color:#475569;font-weight:600;letter-spacing:0.05em;text-transform:uppercase; }
.tag-reject {
    display:inline-block;background:#1c0a0a;
    border:1px solid #ef4444;border-radius:6px;
    padding:2px 10px;font-size:0.73rem;font-weight:700;
    color:#f87171;margin-top:0.45rem;
}
.tag-fail {
    display:inline-block;background:#0c1829;
    border:1px solid #3b82f6;border-radius:6px;
    padding:2px 10px;font-size:0.73rem;font-weight:700;
    color:#60a5fa;margin-top:0.45rem;
}

/* ── Trend indicator ─────────────────────────────────────── */
.trend-up   { color:#34d399;font-weight:700; }
.trend-down { color:#f87171;font-weight:700; }

/* ── No-data placeholder ─────────────────────────────────── */
.empty-state {
    background:#0a1426;border:1px dashed #1a2640;
    border-radius:16px;padding:3.5rem;text-align:center;margin:2rem 0;
}

/* ── Progress bar ────────────────────────────────────────── */
.prog-row { margin-bottom:0.55rem; }
.prog-label { display:flex;justify-content:space-between;margin-bottom:4px; }
.prog-name  { font-size:0.75rem;font-weight:600;color:#94a3b8; }
.prog-val   { font-size:0.75rem;color:#475569; }
.prog-track { height:6px;background:#1a2640;border-radius:3px;overflow:hidden; }
.prog-fill  {
    height:100%;border-radius:3px;
    background:linear-gradient(90deg,var(--fc1,#3b82f6),var(--fc2,#818cf8));
    transition:width 0.6s cubic-bezier(0.4,0,0.2,1);
}

/* ── Tooltip chip ────────────────────────────────────────── */
.src-chip {
    display:inline-flex;align-items:center;gap:4px;
    padding:2px 9px;border-radius:20px;
    font-size:0.7rem;font-weight:600;
    border:1px solid;
}

/* ── Divider ─────────────────────────────────────────────── */
hr { border:none;border-top:1px solid #1a2640;margin:1rem 0; }

/* ── Scrollbar ───────────────────────────────────────────── */
::-webkit-scrollbar { width:5px;height:5px; }
::-webkit-scrollbar-track { background:#07101f; }
::-webkit-scrollbar-thumb { background:#1a2640;border-radius:3px; }
::-webkit-scrollbar-thumb:hover { background:#2d4a6e; }

/* ── Collapse animation helper ───────────────────────────── */
.block-container { padding-top:1.5rem !important; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# Cached data
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=30)
def _live() -> pd.DataFrame:
    return load_live(limit=5000)

@st.cache_data(ttl=300)
def _mart(table: str) -> pd.DataFrame:
    return load_mart(table)

# ─────────────────────────────────────────────────────────────────────────────
# Reusable components
# ─────────────────────────────────────────────────────────────────────────────
def kpi(label, value, sub="", icon="", color="#3b82f6", delta="", delta_pos=True):
    d = ""
    if delta:
        cls = "kpi-delta-pos" if delta_pos else "kpi-delta-neg"
        arrow = "▲" if delta_pos else "▼"
        d = f'<div class="{cls}">{arrow} {delta}</div>'
    st.markdown(f"""
    <div class="kpi" style="--c:{color}">
      <div class="kpi-icon">{icon}</div>
      <div class="kpi-label">{label}</div>
      <div class="kpi-val">{value}</div>
      {'<div class="kpi-sub">'+sub+'</div>' if sub else ''}
      {d}
    </div>""", unsafe_allow_html=True)


def sec(title, badge="", icon=""):
    b = f'<span class="sec-badge">{badge}</span>' if badge else ""
    st.markdown(f'<div class="sec"><h3>{icon} {title}</h3>{b}</div>', unsafe_allow_html=True)


def empty():
    st.markdown("""
    <div class="empty-state">
      <div style="font-size:2.2rem;margin-bottom:0.75rem">📭</div>
      <div style="font-size:1rem;font-weight:700;color:#e2e8f0;margin-bottom:0.35rem">No data yet</div>
      <div style="font-size:0.82rem;color:#475569;margin-bottom:1.1rem">Run a scraper to populate the dashboard</div>
      <code style="background:#0a1426;border:1px solid #1a2640;border-radius:6px;
                   padding:0.45rem 0.9rem;font-size:0.8rem;color:#60a5fa">
        make scrape-books-sample
      </code>
    </div>""", unsafe_allow_html=True)


def src_chip(source: str) -> str:
    m = src_meta(source)
    return (f'<span class="src-chip" '
            f'style="color:{m["color"]};border-color:{m["color"]}44;'
            f'background:{m["bg"]}">'
            f'{m["icon"]} {m["label"]}</span>')


def chart(fig: go.Figure, h: int = 340) -> go.Figure:
    fig.update_layout(**CHART_BASE, height=h)
    return fig


def pill_filters(label: str, options: list[str], state_key: str,
                 color_map: dict | None = None, all_label: str = "All") -> str:
    """Render pill-style filter buttons. Returns selected value."""
    st.markdown(f'<div class="pill-label">{label}</div>', unsafe_allow_html=True)
    all_opts = [all_label] + options
    current  = st.session_state.get(state_key, all_label)
    cols     = st.columns(len(all_opts))
    for i, opt in enumerate(all_opts):
        active = (opt == current)
        c = color_map.get(opt, "#3b82f6") if (color_map and opt != all_label) else "#3b82f6"
        bg = c + "22"
        attr = "active" if active else "inactive"
        with cols[i]:
            st.markdown(
                f'<div data-pill="{attr}" style="--pill-color:{c};--pill-bg:{bg}">',
                unsafe_allow_html=True,
            )
            lbl = src_meta(opt)["icon"] + " " + src_meta(opt)["label"] if (opt != all_label and opt in SOURCE_META) else opt
            if st.button(lbl, key=f"pill_{state_key}_{i}", use_container_width=False):
                st.session_state[state_key] = opt
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
    return st.session_state.get(state_key, all_label)


def sort_chips(options: list[tuple[str, str]], state_key: str) -> str:
    """Render small sort chip buttons. options = [(value, label), ...]"""
    current = st.session_state.get(state_key, options[0][0])
    cols = st.columns(len(options))
    for i, (val, lbl) in enumerate(options):
        active = val == current
        with cols[i]:
            st.markdown(f'<div data-sort="{"active" if active else "inactive"}">', unsafe_allow_html=True)
            if st.button(lbl, key=f"sort_{state_key}_{i}"):
                st.session_state[state_key] = val
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
    return current


def progress_bars(df: pd.DataFrame, name_col: str, value_col: str, title: str,
                  colors: list[tuple[str, str]] | None = None):
    sec(title, icon="📊")
    total = df[value_col].sum()
    default_colors = [("#3b82f6","#818cf8"),("#06b6d4","#22d3ee"),
                      ("#10b981","#34d399"),("#f59e0b","#fbbf24"),("#f97316","#fb923c")]
    for i, (_, row) in enumerate(df.iterrows()):
        pct = row[value_col] / total * 100 if total > 0 else 0
        c1, c2 = (colors[i] if colors else default_colors[i % len(default_colors)])
        st.markdown(f"""
        <div class="prog-row">
          <div class="prog-label">
            <span class="prog-name">{row[name_col]}</span>
            <span class="prog-val">{row[value_col]:,.0f} &nbsp;·&nbsp; {pct:.1f}%</span>
          </div>
          <div class="prog-track">
            <div class="prog-fill" style="width:{pct:.1f}%;--fc1:{c1};--fc2:{c2}"></div>
          </div>
        </div>""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="padding:1.1rem 0.4rem 0.3rem">
      <div style="font-size:1.1rem;font-weight:800;color:#f1f5f9;letter-spacing:-0.02em">
        ⚡ Price Intelligence
      </div>
      <div style="font-size:0.7rem;color:#334155;margin-top:2px;font-weight:500">
        Real-Time E-commerce Platform
      </div>
    </div>
    <hr>
    """, unsafe_allow_html=True)

    st.markdown('<div style="font-size:0.65rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;color:#334155;margin-bottom:0.4rem">Navigation</div>', unsafe_allow_html=True)

    for icon, label, desc in PAGES:
        active = st.session_state.page == label
        st.markdown(f'<div data-nav-btn="{"active" if active else "inactive"}">', unsafe_allow_html=True)
        if st.button(f"{icon}  {label}", key=f"nav_{label}", use_container_width=True,
                     help=desc):
            st.session_state.page = label
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<hr>", unsafe_allow_html=True)

    st.markdown('<div style="font-size:0.65rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;color:#334155;margin-bottom:0.5rem">Controls</div>', unsafe_allow_html=True)

    auto_refresh = st.toggle("Auto-refresh every 30s", value=False, key="auto_refresh")

    c_ref, c_clr = st.columns(2)
    with c_ref:
        if st.button("↺ Refresh", type="primary", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
    with c_clr:
        if st.button("⊘ Reset", type="secondary", use_container_width=True):
            for k in ["src_filter","avail_filter","search","sort_by","price_min","price_max"]:
                st.session_state[k] = {"src_filter":"ALL","avail_filter":"ALL","search":"",
                                        "sort_by":"price_asc","price_min":0.0,"price_max":9999.0}[k]
            st.rerun()

    st.markdown(f"""
    <div style="margin-top:1rem;background:#0a1426;border:1px solid #1a2640;border-radius:10px;padding:0.85rem">
      <div class="live-badge"><span class="live-dot"></span> LIVE FEED</div>
      <div style="margin-top:0.6rem;font-size:0.68rem;color:#334155">
        Last refresh<br/>
        <span style="color:#94a3b8;font-weight:600;font-size:0.78rem">{time.strftime('%H:%M:%S')}</span>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # Data stats in sidebar
    _df_side = _live()
    if not _df_side.empty:
        st.markdown(f"""
        <div style="margin-top:0.75rem;background:#0a1426;border:1px solid #1a2640;
                    border-radius:10px;padding:0.85rem">
          <div style="font-size:0.65rem;font-weight:700;letter-spacing:0.08em;
                      text-transform:uppercase;color:#334155;margin-bottom:0.6rem">Dataset</div>
          <div style="display:flex;justify-content:space-between;margin-bottom:4px">
            <span style="font-size:0.75rem;color:#64748b">Records</span>
            <span style="font-size:0.75rem;font-weight:700;color:#94a3b8">{len(_df_side):,}</span>
          </div>
          <div style="display:flex;justify-content:space-between;margin-bottom:4px">
            <span style="font-size:0.75rem;color:#64748b">Sources</span>
            <span style="font-size:0.75rem;font-weight:700;color:#94a3b8">{_df_side['source'].nunique()}</span>
          </div>
          <div style="display:flex;justify-content:space-between">
            <span style="font-size:0.75rem;color:#64748b">Avg price</span>
            <span style="font-size:0.75rem;font-weight:700;color:#94a3b8">{_df_side['price'].mean():.2f}</span>
          </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("""
    <div style="margin-top:1.5rem;font-size:0.62rem;color:#1e2d45;text-align:center;padding-bottom:1rem">
      Hassan RADA · Final Year Project · 2026
    </div>
    """, unsafe_allow_html=True)


# ═════════════════════════════════════════════════════════════════════════════
# PAGE 1 — Live Prices
# ═════════════════════════════════════════════════════════════════════════════
def page_live():
    st.markdown('<div class="ptitle">⚡ Live Prices</div>', unsafe_allow_html=True)
    st.markdown('<div class="psub">Most recent observation per product · deduped by product_id</div>', unsafe_allow_html=True)

    df = _live()
    if df.empty:
        empty(); return

    if "scraped_at" in df.columns:
        df = df.sort_values("scraped_at").groupby("product_id").last().reset_index()

    all_sources = sorted(df["source"].dropna().unique().tolist())
    price_floor = float(df["price"].min())
    price_ceil  = float(df["price"].max())

    # ── Filter panel ──────────────────────────────────────────────────────────
    with st.expander("🎛️  Filters & Sort", expanded=st.session_state.show_filters):
        st.markdown('<div class="filter-panel">', unsafe_allow_html=True)

        # Row 1: Search + price range
        fa, fb = st.columns([2, 2])
        with fa:
            search = st.text_input("", placeholder="🔍  Search title or category…",
                                   value=st.session_state.search,
                                   key="search_input", label_visibility="collapsed")
            st.session_state.search = search
        with fb:
            p_range = st.slider("Price range", min_value=price_floor,
                                max_value=max(price_ceil, price_floor + 1),
                                value=(price_floor, price_ceil),
                                format="%.0f", label_visibility="collapsed")

        st.markdown("<div style='margin:0.6rem 0'></div>", unsafe_allow_html=True)

        # Row 2: Source pills
        selected_src = pill_filters(
            "Source", all_sources, "src_filter",
            color_map=SOURCE_COLORS, all_label="ALL",
        )

        st.markdown("<div style='margin:0.5rem 0 0.25rem'></div>", unsafe_allow_html=True)

        # Row 3: Availability chips + Sort chips
        av_col, sort_col = st.columns([2, 3])
        with av_col:
            avail_opts = ["ALL"]
            if "availability" in df.columns:
                avail_opts += sorted(df["availability"].dropna().unique().tolist())
            selected_avail = pill_filters("Availability", avail_opts[1:], "avail_filter", all_label="ALL")
        with sort_col:
            st.markdown('<div class="pill-label">Sort by</div>', unsafe_allow_html=True)
            sort_map = {
                "price_asc":  "Price ↑",
                "price_desc": "Price ↓",
                "rating_desc":"Rating ↓",
                "title_asc":  "Name A→Z",
            }
            sort_val = sort_chips(list(sort_map.items()), "sort_by")

        st.markdown("</div>", unsafe_allow_html=True)

    # Apply filters
    filtered = df.copy()
    if st.session_state.search:
        q = st.session_state.search.lower()
        filtered = filtered[filtered.apply(
            lambda r: q in str(r.get("title","")).lower() or q in str(r.get("category","")).lower(), axis=1)]
    if st.session_state.src_filter != "ALL":
        filtered = filtered[filtered["source"] == st.session_state.src_filter]
    if st.session_state.avail_filter != "ALL" and "availability" in filtered.columns:
        filtered = filtered[filtered["availability"] == st.session_state.avail_filter]
    filtered = filtered[(filtered["price"] >= p_range[0]) & (filtered["price"] <= p_range[1])]

    sort_cfg = {"price_asc":("price",True),"price_desc":("price",False),
                "rating_desc":("rating",False),"title_asc":("title",True)}
    sc, sa = sort_cfg.get(sort_val, ("price", True))
    if sc in filtered.columns:
        filtered = filtered.sort_values(sc, ascending=sa)

    # Active filter badges
    badges = []
    if st.session_state.search:
        badges.append(f'<span style="background:#1a3a6c;color:#60a5fa;padding:2px 9px;border-radius:20px;font-size:0.7rem;font-weight:600">🔍 "{st.session_state.search}"</span>')
    if st.session_state.src_filter != "ALL":
        m = src_meta(st.session_state.src_filter)
        badges.append(f'<span style="background:{m["bg"]};color:{m["color"]};padding:2px 9px;border-radius:20px;font-size:0.7rem;font-weight:600;border:1px solid {m["color"]}44">{m["icon"]} {m["label"]}</span>')
    if badges:
        st.markdown(f'<div style="margin-bottom:0.6rem;display:flex;gap:6px;align-items:center">'
                    f'<span style="font-size:0.68rem;color:#334155">Active filters:</span>'
                    + "".join(badges) + "</div>", unsafe_allow_html=True)

    # ── KPI row ───────────────────────────────────────────────────────────────
    k1,k2,k3,k4,k5 = st.columns(5)
    with k1: kpi("Products",    f"{len(filtered):,}",                icon="📦", color="#6366f1")
    with k2: kpi("Sources",     str(filtered["source"].nunique()),    icon="🌐", color="#06b6d4")
    with k3: kpi("Avg price",   f"{filtered['price'].mean():.2f}" if not filtered.empty else "—",
                                icon="💰", color="#10b981")
    with k4: kpi("Lowest",      f"{filtered['price'].min():.2f}" if not filtered.empty else "—",
                                icon="📉", color="#3b82f6")
    with k5: kpi("Highest",     f"{filtered['price'].max():.2f}" if not filtered.empty else "—",
                                icon="📈", color="#f59e0b")

    st.markdown("<div style='margin:1rem 0'></div>", unsafe_allow_html=True)

    if filtered.empty:
        st.markdown('<div style="text-align:center;color:#475569;padding:2rem">No products match the current filters.</div>', unsafe_allow_html=True)
        return

    # ── Charts ─────────────────────────────────────────────────────────────────
    ch1, ch2 = st.columns([3, 2])
    with ch1:
        sec("Price distribution", badge="violin · log scale", icon="📊")
        fig = px.violin(filtered, x="source", y="price", color="source",
                        color_discrete_map=SOURCE_COLORS, box=True, points="outliers",
                        log_y=True, labels={"price":"Price (log)","source":""})
        fig.update_traces(meanline_visible=True, line_width=1.5)
        fig.update_layout(showlegend=False)
        st.plotly_chart(chart(fig, 320), use_container_width=True)

    with ch2:
        sec("Market share", badge="by source", icon="🍩")
        share = filtered.groupby("source").size().reset_index(name="n")
        fig2 = px.pie(share, values="n", names="source",
                      color="source", color_discrete_map=SOURCE_COLORS, hole=0.6)
        fig2.update_traces(textposition="outside", textinfo="percent+label",
                           textfont=dict(size=11, color="#94a3b8"),
                           marker_line_color="#07101f", marker_line_width=2,
                           pull=[0.04]*len(share))
        fig2.update_layout(showlegend=False)
        st.plotly_chart(chart(fig2, 320), use_container_width=True)

    # ── Progress bars (source breakdown) ─────────────────────────────────────
    src_counts = filtered.groupby("source").size().reset_index(name="count").sort_values("count", ascending=False)
    progress_bars(src_counts, "source", "count", "Source breakdown")

    # ── Product table ─────────────────────────────────────────────────────────
    sec("Product catalogue", badge=f"{len(filtered):,} results", icon="🗂️")
    show = [c for c in ["title","source","price","currency","availability","category","rating","scraped_at"]
            if c in filtered.columns]
    st.dataframe(
        filtered[show].reset_index(drop=True),
        use_container_width=True, height=420, hide_index=True,
        column_config={
            "title":      st.column_config.TextColumn("Product", width="large"),
            "source":     st.column_config.TextColumn("Source"),
            "price":      st.column_config.NumberColumn("Price", format="%.2f"),
            "rating":     st.column_config.NumberColumn("⭐ Rating", format="%.1f"),
            "scraped_at": st.column_config.DatetimeColumn("Scraped", format="MMM D, HH:mm"),
            "availability": st.column_config.TextColumn("Stock"),
        },
    )


# ═════════════════════════════════════════════════════════════════════════════
# PAGE 2 — Historical KPIs
# ═════════════════════════════════════════════════════════════════════════════
def page_kpis():
    st.markdown('<div class="ptitle">📈 Historical KPIs</div>', unsafe_allow_html=True)
    st.markdown('<div class="psub">Aggregated dbt mart metrics · BigQuery or JSONL fallback</div>', unsafe_allow_html=True)

    stats_df = _mart("mart_price_stats")
    hist_df  = _mart("mart_price_history")

    if stats_df.empty and hist_df.empty:
        empty(); return

    if not stats_df.empty:
        sec("Aggregate statistics", badge="per source", icon="📊")
        accent_seq = ["#6366f1","#22d3ee","#34d399","#fbbf24","#fb923c"]
        icon_seq   = ["📚","🛒","🛍️","💻","🖥️"]
        cols = st.columns(min(len(stats_df), 5))
        for i, (_, row) in enumerate(stats_df.iterrows()):
            with cols[i % len(cols)]:
                src = str(row.get("source","?"))
                avg = row.get("avg_price", 0)
                med = row.get("median_price", row.get("avg_price", 0))
                sd  = row.get("stddev_price", 0)
                cur = row.get("currency","")
                kpi(src.replace("_"," ").title(), f"{avg:.2f} {cur}",
                    sub=f"median {med:.2f} · σ {sd:.2f}",
                    icon=icon_seq[i % len(icon_seq)],
                    color=accent_seq[i % len(accent_seq)])

        st.markdown("<div style='margin:1.1rem 0'></div>", unsafe_allow_html=True)

        # ── Grouped bar ───────────────────────────────────────────────────────
        sec("Price ranges", badge="min · avg · median · max", icon="📉")
        pcols = [c for c in ["min_price","avg_price","median_price","max_price"] if c in stats_df.columns]
        if pcols and "source" in stats_df.columns:
            melted = stats_df.melt(id_vars="source", value_vars=pcols,
                                   var_name="metric", value_name="price")
            label_map = {"min_price":"Min","avg_price":"Avg","median_price":"Median","max_price":"Max"}
            melted["metric"] = melted["metric"].map(label_map)
            fig = px.bar(melted, x="source", y="price", color="metric",
                         barmode="group",
                         color_discrete_sequence=["#3b82f6","#10b981","#f59e0b","#ef4444"],
                         labels={"price":"Price","source":"","metric":""})
            fig.update_traces(marker_line_width=0)
            st.plotly_chart(chart(fig, 360), use_container_width=True)

        # ── Product count bars ─────────────────────────────────────────────
        if "product_count" in stats_df.columns and "source" in stats_df.columns:
            sec("Products per source", icon="📦")
            cnt = stats_df[["source","product_count"]].sort_values("product_count", ascending=False)
            progress_bars(cnt, "source", "product_count", "")

        sec("Full statistics table", icon="🗂️")
        st.dataframe(stats_df.reset_index(drop=True), use_container_width=True, hide_index=True,
                     column_config={c: st.column_config.NumberColumn(c, format="%.2f")
                                    for c in stats_df.select_dtypes("number").columns})

    # ── Trend explorer ─────────────────────────────────────────────────────────
    if not hist_df.empty and "scraped_date" in hist_df.columns and "product_id" in hist_df.columns:
        sec("Price trend explorer", badge="interactive", icon="🔍")

        te_col1, te_col2 = st.columns([3, 1])
        with te_col1:
            def _lbl(pid):
                r = hist_df[hist_df["product_id"] == pid]
                return r["title"].iloc[0] if (not r.empty and "title" in r.columns) else pid
            pid_list = hist_df["product_id"].unique().tolist()
            sel_pid  = st.selectbox("Select product", pid_list, format_func=_lbl,
                                    label_visibility="collapsed")
        with te_col2:
            show_drops = st.toggle("Highlight drops", value=True)

        trend = hist_df[hist_df["product_id"] == sel_pid].sort_values("scraped_date")
        if not trend.empty:
            # KPI trio
            ka, kb, kc = st.columns(3)
            with ka: kpi("High", f"{trend['price'].max():.2f}", icon="⬆️", color="#ef4444")
            with kb: kpi("Low",  f"{trend['price'].min():.2f}", icon="⬇️", color="#10b981")
            with kc:
                chg = trend['price'].iloc[-1] - trend['price'].iloc[0] if len(trend) > 1 else 0
                kpi("Total Δ", f"{'+'if chg>=0 else ''}{chg:.2f}", icon="📊",
                    color="#10b981" if chg >= 0 else "#ef4444")

            st.markdown("<div style='margin:0.6rem 0'></div>", unsafe_allow_html=True)
            fig3 = px.line(trend, x="scraped_date", y="price", markers=True,
                           color_discrete_sequence=["#6366f1"],
                           labels={"price":"Price","scraped_date":"Date"})
            fig3.update_traces(line_width=2.5, marker_size=6)
            if show_drops and "price_change_pct" in trend.columns:
                drops = trend[trend["price_change_pct"] <= -5]
                if not drops.empty:
                    fig3.add_scatter(x=drops["scraped_date"], y=drops["price"],
                                     mode="markers",
                                     marker=dict(color="#ef4444", size=12, symbol="triangle-down",
                                                 line=dict(color="#07101f", width=1.5)),
                                     name="Drop ≥5%")
            st.plotly_chart(chart(fig3, 300), use_container_width=True)


# ═════════════════════════════════════════════════════════════════════════════
# PAGE 3 — Statistical Analysis
# ═════════════════════════════════════════════════════════════════════════════
def page_stats():
    st.markdown('<div class="ptitle">🔬 Statistical Analysis</div>', unsafe_allow_html=True)
    st.markdown('<div class="psub">Live descriptive stats · hypothesis tests · regression · confidence intervals</div>', unsafe_allow_html=True)

    df = _live()
    if df.empty:
        empty(); return

    tab1, tab2, tab3 = st.tabs(["📊  Descriptive", "🧪  Hypothesis Tests", "📐  Regression"])

    # ── Descriptive ───────────────────────────────────────────────────────────
    with tab1:
        sec("Summary statistics", badge="per source", icon="📋")
        desc = (df.groupby("source")["price"].agg(
            n="count",
            mean=lambda s: round(s.mean(),2),
            median=lambda s: round(s.median(),2),
            std=lambda s: round(s.std(),2),
            min="min", max="max",
            q25=lambda s: round(s.quantile(0.25),2),
            q75=lambda s: round(s.quantile(0.75),2),
            skew=lambda s: round(float(scipy_stats.skew(s.dropna())),3),
            kurt=lambda s: round(float(scipy_stats.kurtosis(s.dropna())),3),
        ).reset_index())
        st.dataframe(desc, use_container_width=True, hide_index=True,
                     column_config={c: st.column_config.NumberColumn(c, format="%.2f")
                                    for c in desc.select_dtypes("number").columns})

        ca, cb = st.columns(2)
        with ca:
            sec("Distribution", badge="log scale", icon="📉")
            fh = px.histogram(df, x="price", color="source", barmode="overlay",
                              opacity=0.65, log_x=True, nbins=55,
                              color_discrete_map=SOURCE_COLORS,
                              labels={"price":"Price (log)"})
            st.plotly_chart(chart(fh, 290), use_container_width=True)
        with cb:
            sec("Coefficient of variation", badge="volatility %", icon="📊")
            vol = df.groupby("source")["price"].apply(
                lambda s: round(s.std()/s.mean()*100,1) if s.mean()>0 else 0
            ).reset_index()
            vol.columns = ["source","cv"]
            vol = vol.sort_values("cv", ascending=False)
            fv = px.bar(vol, x="source", y="cv", color="source",
                        color_discrete_map=SOURCE_COLORS, text="cv",
                        labels={"cv":"CV (%)","source":""})
            fv.update_traces(texttemplate="%{text:.1f}%", textposition="outside", marker_line_width=0)
            fv.update_layout(showlegend=False)
            st.plotly_chart(chart(fv, 290), use_container_width=True)

        # Box plot
        sec("Box plots", badge="all sources", icon="📦")
        fb2 = px.box(df, x="source", y="price", color="source",
                     color_discrete_map=SOURCE_COLORS, points="outliers",
                     log_y=True, labels={"price":"Price (log)","source":""})
        fb2.update_layout(showlegend=False)
        st.plotly_chart(chart(fb2, 320), use_container_width=True)

    # ── Inferential ───────────────────────────────────────────────────────────
    with tab2:
        groups = {s: df[df["source"]==s]["price"].dropna() for s in df["source"].unique()}
        groups = {k:v for k,v in groups.items() if len(v)>=3}
        if len(groups) < 2:
            st.info("Need ≥ 2 sources with ≥ 3 observations each.")
        else:
            # Shapiro-Wilk
            sec("Normality test", badge="Shapiro-Wilk", icon="📐")
            norm_rows = []
            for src, g in groups.items():
                w, p = scipy_stats.shapiro(g.head(5000))
                norm_rows.append({"Source":src,"n":len(g),"W":round(w,4),
                                   "p-value":round(p,6),
                                   "Normal":"✅  Yes" if p>=0.05 else "❌  No"})
            st.dataframe(pd.DataFrame(norm_rows), use_container_width=True, hide_index=True)

            # ANOVA
            sec("One-Way ANOVA", badge="H₀ : all means equal", icon="⚖️")
            f_stat, p_anova = scipy_stats.f_oneway(*groups.values())
            rej_a = p_anova < 0.05
            st.markdown(f"""
            <div class="stat-box">
              <div class="stat-box-title">ANOVA result</div>
              <div class="stat-row">
                <div><div class="stat-val">{f_stat:.4f}</div><div class="stat-lbl">F-statistic</div></div>
                <div><div class="stat-val">{p_anova:.2e}</div><div class="stat-lbl">p-value</div></div>
                <div><div class="stat-val">α = 0.05</div><div class="stat-lbl">threshold</div></div>
              </div>
              <div class="{'tag-reject' if rej_a else 'tag-fail'}">
                {'🔴 Reject H₀ — means differ significantly' if rej_a else '🔵 Fail to reject H₀'}
              </div>
            </div>""", unsafe_allow_html=True)

            # Kruskal-Wallis
            sec("Kruskal-Wallis", badge="non-parametric ANOVA", icon="🧮")
            h_stat, p_kw = scipy_stats.kruskal(*groups.values())
            rej_k = p_kw < 0.05
            st.markdown(f"""
            <div class="stat-box">
              <div class="stat-box-title">Kruskal-Wallis result</div>
              <div class="stat-row">
                <div><div class="stat-val">{h_stat:.4f}</div><div class="stat-lbl">H-statistic</div></div>
                <div><div class="stat-val">{p_kw:.2e}</div><div class="stat-lbl">p-value</div></div>
              </div>
              <div class="{'tag-reject' if rej_k else 'tag-fail'}">
                {'🔴 Reject H₀ — distributions differ' if rej_k else '🔵 Fail to reject H₀'}
              </div>
            </div>""", unsafe_allow_html=True)

            # Mann-Whitney pairwise + heatmap
            sec("Pairwise Mann-Whitney U", badge="two-sided", icon="🔗")
            src_list  = list(groups.keys())
            mw_rows   = []
            heat_data = {s:{s2:1.0 for s2 in src_list} for s in src_list}
            for a, b in itertools.combinations(src_list, 2):
                u, p_mw = scipy_stats.mannwhitneyu(groups[a], groups[b], alternative="two-sided")
                n1, n2  = len(groups[a]), len(groups[b])
                r_eff   = round(1 - (2*u)/(n1*n2), 3)
                mw_rows.append({"Source A":a,"Source B":b,"U":round(u,0),
                                 "p-value":round(p_mw,6),"Effect r":r_eff,
                                 "Significant":"✅" if p_mw<0.05 else "❌"})
                heat_data[a][b] = p_mw
                heat_data[b][a] = p_mw

            col_mw, col_heat = st.columns([2, 1])
            with col_mw:
                st.dataframe(pd.DataFrame(mw_rows).sort_values("p-value"),
                             use_container_width=True, hide_index=True)
            with col_heat:
                z    = [[heat_data[r][c] for c in src_list] for r in src_list]
                f_hm = go.Figure(go.Heatmap(
                    z=np.log10(np.array(z)+1e-10),
                    x=src_list, y=src_list,
                    colorscale="RdBu",
                    hovertemplate="%{y} vs %{x}<br>log10(p)=%{z:.2f}<extra></extra>",
                    colorbar=dict(tickfont=dict(color="#64748b",size=10),
                                  title=dict(text="log10(p)",font=dict(color="#64748b")))
                ))
                f_hm.update_layout(title="p-value heatmap",
                                   xaxis_tickangle=-30)
                st.plotly_chart(chart(f_hm, 260), use_container_width=True)

            # Confidence intervals
            sec("95% Confidence Intervals", badge="mean price", icon="📏")
            ci_rows = []
            for src, g in groups.items():
                n, se   = len(g), scipy_stats.sem(g)
                lo, hi  = scipy_stats.t.interval(0.95, df=n-1, loc=g.mean(), scale=se)
                ci_rows.append({"Source":src,"n":n,"Mean":round(g.mean(),2),
                                 "Lower":round(lo,2),"Upper":round(hi,2),
                                 "Width":round(hi-lo,2)})
            ci_df = pd.DataFrame(ci_rows)

            col_ci, col_forest = st.columns([1, 2])
            with col_ci:
                st.dataframe(ci_df, use_container_width=True, hide_index=True)
            with col_forest:
                fig_ci = go.Figure()
                for _, row in ci_df.iterrows():
                    col = SOURCE_COLORS.get(row["Source"], "#6366f1")
                    fig_ci.add_trace(go.Scatter(
                        x=[row["Lower"], row["Upper"]], y=[row["Source"],row["Source"]],
                        mode="lines", line=dict(width=6, color=col), showlegend=False))
                    fig_ci.add_trace(go.Scatter(
                        x=[row["Mean"]], y=[row["Source"]],
                        mode="markers",
                        marker=dict(size=13, color=col, symbol="diamond",
                                    line=dict(color="#07101f",width=2)),
                        name=row["Source"], showlegend=False))
                fig_ci.update_layout(title="Forest plot — 95% CI",
                                     xaxis_title="Price", yaxis_title="")
                st.plotly_chart(chart(fig_ci, 260), use_container_width=True)

    # ── Regression ─────────────────────────────────────────────────────────────
    with tab3:
        sec("Linear Regression", badge="price ~ rating", icon="📐")
        reg_df = df.dropna(subset=["price","rating"]) if "rating" in df.columns else pd.DataFrame()
        if reg_df.empty or len(reg_df) < 5:
            st.info("Not enough data with rating values.")
        else:
            slope, intercept, r, p, se = scipy_stats.linregress(reg_df["rating"], reg_df["price"])
            r2 = r**2
            ra, rb, rc, rd = st.columns(4)
            with ra: kpi("Slope β₁",     f"{slope:.4f}",  sub="per rating unit",
                          icon="📈", color="#6366f1" if slope>0 else "#ef4444")
            with rb: kpi("Intercept β₀", f"{intercept:.2f}", icon="🎯", color="#06b6d4")
            with rc: kpi("R²",            f"{r2:.4f}",    sub="variance explained",
                          icon="📊", color="#10b981" if r2>0.3 else "#f59e0b")
            with rd: kpi("p-value",       f"{p:.2e}",
                          sub="significant" if p<0.05 else "not significant",
                          icon="🔬", color="#10b981" if p<0.05 else "#ef4444")

            st.markdown("<div style='margin:0.8rem 0'></div>", unsafe_allow_html=True)

            # Scatter with OLS
            fig_r = px.scatter(reg_df, x="rating", y="price", color="source",
                               color_discrete_map=SOURCE_COLORS, opacity=0.5,
                               trendline="ols", labels={"price":"Price","rating":"Rating"})
            fig_r.update_traces(marker_size=6)
            st.plotly_chart(chart(fig_r, 400), use_container_width=True)

            # Per-source table
            sec("Regression per source", icon="📋")
            reg_rows = []
            for src, g in df.groupby("source"):
                gf = g.dropna(subset=["price","rating"])
                if len(gf) < 5: continue
                sl,ic,rv,pv,sv = scipy_stats.linregress(gf["rating"], gf["price"])
                reg_rows.append({"Source":src,"n":len(gf),"Slope":round(sl,4),
                                  "Intercept":round(ic,2),"R":round(rv,4),
                                  "R²":round(rv**2,4),"p-value":round(pv,6),
                                  "Sig":"✅" if pv<0.05 else "❌"})
            if reg_rows:
                st.dataframe(pd.DataFrame(reg_rows), use_container_width=True, hide_index=True)


# ═════════════════════════════════════════════════════════════════════════════
# PAGE 4 — Price Alerts
# ═════════════════════════════════════════════════════════════════════════════
def page_alerts():
    st.markdown('<div class="ptitle">🔔 Price Alerts</div>', unsafe_allow_html=True)
    st.markdown('<div class="psub">Products with a price drop ≥ 5% across all scraped sources</div>', unsafe_allow_html=True)

    alerts = _mart("mart_price_alerts")

    if alerts.empty:
        st.markdown("""
        <div style="background:#052e16;border:1px solid #065f46;border-radius:14px;
                    padding:2.5rem;text-align:center;margin:2rem 0">
          <div style="font-size:1.8rem;margin-bottom:0.5rem">✅</div>
          <div style="font-size:1rem;font-weight:700;color:#34d399">All prices are stable</div>
          <div style="font-size:0.8rem;color:#065f46;margin-top:0.3rem">No significant drops detected</div>
        </div>""", unsafe_allow_html=True)
        return

    # ── KPI row ───────────────────────────────────────────────────────────────
    a1,a2,a3,a4 = st.columns(4)
    pcp = "price_change_pct"
    with a1: kpi("Alerts",       str(len(alerts)),                             icon="🚨", color="#ef4444")
    with a2: kpi("Biggest drop", f"{alerts[pcp].min():.1f}%" if pcp in alerts.columns else "—",
                                  icon="📉", color="#f97316")
    with a3: kpi("Sources hit",  str(alerts["source"].nunique()) if "source" in alerts.columns else "—",
                                  icon="🌐", color="#f59e0b")
    with a4:
        severe = len(alerts[alerts[pcp]<=-20]) if pcp in alerts.columns else 0
        kpi("Severe ≥20%", str(severe), icon="⚠️", color="#ef4444")

    st.markdown("<div style='margin:1.1rem 0'></div>", unsafe_allow_html=True)

    # ── Severity filter ───────────────────────────────────────────────────────
    if pcp in alerts.columns:
        sev_col, _ = st.columns([3,1])
        with sev_col:
            threshold = st.select_slider(
                "Minimum drop to show",
                options=[-5,-10,-15,-20,-25,-30,-50],
                value=-5,
                format_func=lambda v: f"{v}%",
                label_visibility="visible",
            )
        alerts_shown = alerts[alerts[pcp] <= threshold].copy()
    else:
        alerts_shown = alerts.copy()

    st.markdown(f'<div style="font-size:0.75rem;color:#475569;margin-bottom:0.9rem">Showing <b style="color:#94a3b8">{len(alerts_shown)}</b> alerts with drop ≥ {abs(threshold) if pcp in alerts.columns else 5}%</div>', unsafe_allow_html=True)

    # ── Alert cards ───────────────────────────────────────────────────────────
    if pcp in alerts.columns:
        sec("Top drops", badge="worst first", icon="🏆")
        for _, row in alerts_shown.sort_values(pcp).head(12).iterrows():
            pct   = row.get(pcp, 0)
            title = str(row.get("title", row.get("product_id","?")))[:62]
            src   = str(row.get("source",""))
            cur_p = row.get("price","")
            prv_p = row.get("prev_price","")
            color = "#ef4444" if pct<=-20 else ("#f97316" if pct<=-10 else "#fbbf24")
            m     = src_meta(src)
            st.markdown(f"""
            <div class="alert-card" style="--ac:{color}">
              <div>
                <div class="alert-title">{title}</div>
                <div class="alert-meta">
                  <span class="src-chip" style="color:{m['color']};border-color:{m['color']}44;
                                                background:{m['bg']}">{m['icon']} {m['label']}</span>
                  &nbsp;·&nbsp; {prv_p:.2f} → {cur_p:.2f}
                </div>
              </div>
              <div class="alert-pct">{pct:.1f}%</div>
            </div>""", unsafe_allow_html=True)

    # ── Chart ─────────────────────────────────────────────────────────────────
    if pcp in alerts.columns and "source" in alerts.columns and not alerts_shown.empty:
        ca, cb = st.columns([3,2])
        with ca:
            sec("Price drop chart", badge="top 20", icon="📊")
            y_col = "title" if "title" in alerts_shown.columns else "product_id"
            pdata = alerts_shown.head(20).sort_values(pcp).copy()
            pdata[y_col] = pdata[y_col].astype(str).str[:38]
            fig = px.bar(pdata, x=pcp, y=y_col, color="source",
                         color_discrete_map=SOURCE_COLORS, orientation="h",
                         text=pcp, labels={pcp:"Change (%)","":""})
            fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside",
                              marker_line_width=0)
            st.plotly_chart(chart(fig, 440), use_container_width=True)

        with cb:
            sec("Severity distribution", icon="🍩")
            bins = {"Mild (5–10%)":  len(alerts_shown[(alerts_shown[pcp]>-10) & (alerts_shown[pcp]<=-5)]),
                    "Mod (10–20%)":  len(alerts_shown[(alerts_shown[pcp]>-20) & (alerts_shown[pcp]<=-10)]),
                    "Severe (≥20%)": len(alerts_shown[alerts_shown[pcp]<=-20])}
            bins = {k:v for k,v in bins.items() if v>0}
            if bins:
                fp = px.pie(names=list(bins.keys()), values=list(bins.values()),
                            color_discrete_sequence=["#fbbf24","#f97316","#ef4444"],
                            hole=0.55)
                fp.update_traces(textposition="outside", textinfo="percent+label",
                                 textfont=dict(size=11,color="#94a3b8"),
                                 marker_line_color="#07101f", marker_line_width=2)
                fp.update_layout(showlegend=False)
                st.plotly_chart(chart(fp, 300), use_container_width=True)

    # ── Table ─────────────────────────────────────────────────────────────────
    sec("Full alert table", badge=f"{len(alerts_shown)} rows", icon="🗂️")
    show = [c for c in ["title","source","price","prev_price",pcp,"currency"] if c in alerts_shown.columns]
    st.dataframe(
        alerts_shown[show].reset_index(drop=True) if show else alerts_shown.reset_index(drop=True),
        use_container_width=True, height=360, hide_index=True,
        column_config={
            "price":     st.column_config.NumberColumn("Current price", format="%.2f"),
            "prev_price":st.column_config.NumberColumn("Prev price",    format="%.2f"),
            pcp:         st.column_config.NumberColumn("Change %",       format="%.2f"),
        },
    )


# ─────────────────────────────────────────────────────────────────────────────
# Router
# ─────────────────────────────────────────────────────────────────────────────
{
    "Live Prices":          page_live,
    "Historical KPIs":      page_kpis,
    "Statistical Analysis": page_stats,
    "Price Alerts":         page_alerts,
}.get(st.session_state.page, page_live)()

if auto_refresh:
    time.sleep(30)
    st.cache_data.clear()
    st.rerun()
