"""
Price Intelligence Platform — Dashboard
Inspired by Linear / Vercel dark-mode aesthetic
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

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Price Intelligence",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Design tokens ──────────────────────────────────────────────────────────────
SOURCE_META = {
    "books_toscrape":     {"color": "#a78bfa", "bg": "#1e1433", "label": "Books.ToScrape", "icon": "◉"},
    "books.toscrape.com": {"color": "#a78bfa", "bg": "#1e1433", "label": "Books.ToScrape", "icon": "◉"},
    "scrapeme_live":      {"color": "#fbbf24", "bg": "#1c1407", "label": "ScrapeMe",       "icon": "◈"},
    "scrapeme.live":      {"color": "#fbbf24", "bg": "#1c1407", "label": "ScrapeMe",       "icon": "◈"},
    "jumia_ma":           {"color": "#f97316", "bg": "#1c0f07", "label": "Jumia.ma",        "icon": "◆"},
    "jumia.ma":           {"color": "#f97316", "bg": "#1c0f07", "label": "Jumia.ma",        "icon": "◆"},
    "ultrapc_ma":         {"color": "#38bdf8", "bg": "#071a1c", "label": "UltraPC.ma",     "icon": "◇"},
    "ultrapc.ma":         {"color": "#38bdf8", "bg": "#071a1c", "label": "UltraPC.ma",     "icon": "◇"},
    "micromagma_ma":      {"color": "#34d399", "bg": "#071c14", "label": "Micromagma.ma",  "icon": "○"},
    "micromagma.ma":      {"color": "#34d399", "bg": "#071c14", "label": "Micromagma.ma",  "icon": "○"},
}
DEFAULT_META = {"color": "#71717a", "bg": "#18181b", "label": "Unknown", "icon": "·"}

def src_meta(s: str) -> dict:
    return SOURCE_META.get(s, DEFAULT_META)

SOURCE_COLORS = {k: v["color"] for k, v in SOURCE_META.items()}

CHART_BASE = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="'Geist', 'Inter', system-ui, sans-serif", color="#71717a", size=12),
    title_font=dict(color="#a1a1aa", size=12, family="'Geist', 'Inter', system-ui, sans-serif"),
    legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#71717a", size=11),
                bordercolor="#27272a", borderwidth=1),
    margin=dict(l=8, r=8, t=36, b=8),
    xaxis=dict(gridcolor="#27272a", zerolinecolor="#27272a",
               tickfont=dict(color="#52525b", size=11),
               title_font=dict(color="#71717a", size=11),
               linecolor="#27272a"),
    yaxis=dict(gridcolor="#27272a", zerolinecolor="#27272a",
               tickfont=dict(color="#52525b", size=11),
               title_font=dict(color="#71717a", size=11),
               linecolor="#27272a"),
)

PAGES = [
    ("Live Feed",    "Real-time price data"),
    ("Analytics",    "Trends & aggregates"),
    ("Statistics",   "Hypothesis tests & regression"),
    ("Alerts",       "Price drops"),
]

# ── Session state ──────────────────────────────────────────────────────────────
def _init():
    for k, v in {
        "page": "Live Feed", "src_filter": "ALL", "avail_filter": "ALL",
        "search": "", "sort_by": "price_asc",
        "price_min": 0.0, "price_max": 9999.0,
    }.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init()

# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

/* ─── Reset & base ─────────────────────────────────────────────────────── */
*, *::before, *::after { box-sizing: border-box; }
html, body, [class*="css"] {
    font-family: 'Inter', system-ui, -apple-system, sans-serif;
}
.stApp {
    background: #09090b;
    color: #fafafa;
}
#MainMenu, footer { visibility: hidden; }
header[data-testid="stHeader"] { visibility: hidden; height: 0; min-height: 0; }
[data-testid="stDecoration"] { display: none; }
[data-testid="stSidebarCollapsedControl"],
[data-testid="stSidebarCollapseButton"],
button[kind="header"] { visibility: visible !important; opacity: 1 !important; }
[data-testid="stSidebar"] { background: #111113 !important; border-right: 1px solid #27272a; }
.block-container { padding: 0 !important; max-width: 100% !important; }

/* ─── Scrollbar ────────────────────────────────────────────────────────── */
::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #27272a; border-radius: 4px; }

/* ─── Top navigation ───────────────────────────────────────────────────── */
.topbar {
    display: flex;
    align-items: center;
    height: 52px;
    background: rgba(9,9,11,0.85);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border-bottom: 1px solid #18181b;
    padding: 0 24px;
    gap: 4px;
    position: sticky;
    top: 0;
    z-index: 1000;
    margin-bottom: 0;
}
.topbar-logo {
    font-size: 14px;
    font-weight: 700;
    color: #fafafa;
    letter-spacing: -0.03em;
    margin-right: 24px;
    display: flex;
    align-items: center;
    gap: 8px;
    flex-shrink: 0;
    white-space: nowrap;
}
.topbar-logo-dot {
    width: 8px; height: 8px;
    background: #6366f1;
    border-radius: 50%;
    display: inline-block;
    box-shadow: 0 0 8px rgba(99,102,241,0.6);
}
.topbar-divider {
    width: 1px; height: 24px;
    background: #27272a;
    margin: 0 16px 0 4px;
    flex-shrink: 0;
}

/* topnav tab buttons */
div[data-topnav="inactive"] > div > button {
    background: transparent !important;
    border: none !important;
    color: #71717a !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    padding: 6px 14px !important;
    border-radius: 6px !important;
    height: 32px !important;
    min-height: 32px !important;
    transition: all 0.15s ease !important;
    white-space: nowrap !important;
    letter-spacing: -0.01em !important;
}
div[data-topnav="inactive"] > div > button:hover {
    background: #18181b !important;
    color: #a1a1aa !important;
}
div[data-topnav="active"] > div > button {
    background: #18181b !important;
    border: none !important;
    border-bottom: 2px solid #6366f1 !important;
    color: #fafafa !important;
    font-size: 13px !important;
    font-weight: 600 !important;
    padding: 6px 14px !important;
    border-radius: 6px 6px 0 0 !important;
    height: 32px !important;
    min-height: 32px !important;
    white-space: nowrap !important;
    letter-spacing: -0.01em !important;
}

/* ─── Page shell ───────────────────────────────────────────────────────── */
.page-shell {
    padding: 32px 40px 64px;
    max-width: 1400px;
    margin: 0 auto;
}
.page-header {
    margin-bottom: 32px;
    padding-bottom: 24px;
    border-bottom: 1px solid #18181b;
}
.page-title {
    font-size: 22px;
    font-weight: 700;
    color: #fafafa;
    letter-spacing: -0.04em;
    margin: 0 0 4px;
    line-height: 1.2;
}
.page-sub {
    font-size: 13px;
    color: #52525b;
    margin: 0;
    font-weight: 400;
}

/* ─── KPI cards ────────────────────────────────────────────────────────── */
.kpi-card {
    background: #111113;
    border: 1px solid #1c1c1f;
    border-radius: 10px;
    padding: 20px 22px;
    position: relative;
    overflow: hidden;
    transition: border-color 0.15s;
}
.kpi-card:hover { border-color: #27272a; }
.kpi-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 1px;
    background: linear-gradient(90deg, transparent, var(--kc, #6366f1) 50%, transparent);
    opacity: 0.4;
}
.kpi-label {
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: #52525b;
    margin-bottom: 10px;
}
.kpi-value {
    font-size: 26px;
    font-weight: 700;
    color: #fafafa;
    letter-spacing: -0.04em;
    line-height: 1;
    margin-bottom: 6px;
}
.kpi-sub {
    font-size: 11px;
    color: #3f3f46;
    font-weight: 500;
}
.kpi-trend-up   { color: #22c55e; font-size: 11px; font-weight: 600; }
.kpi-trend-down { color: #ef4444; font-size: 11px; font-weight: 600; }

/* ─── Section headers ──────────────────────────────────────────────────── */
.sec-wrap {
    display: flex;
    align-items: baseline;
    gap: 10px;
    margin: 28px 0 14px;
}
.sec-title {
    font-size: 13px;
    font-weight: 600;
    color: #a1a1aa;
    letter-spacing: -0.02em;
}
.sec-badge {
    font-size: 11px;
    color: #3f3f46;
    font-weight: 500;
    background: #18181b;
    border: 1px solid #27272a;
    border-radius: 4px;
    padding: 1px 7px;
}

/* ─── Source pill ──────────────────────────────────────────────────────── */
.src-pill {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 11px;
    font-weight: 600;
    border: 1px solid;
    letter-spacing: 0.01em;
}

/* ─── Filter row ───────────────────────────────────────────────────────── */
.filter-label {
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: #3f3f46;
    margin-bottom: 6px;
}

/* pill filter buttons */
div[data-pill="active"] > div > button {
    background: var(--pb, #1a1033) !important;
    border: 1px solid var(--pc, #6366f1) !important;
    color: var(--pc, #818cf8) !important;
    font-size: 12px !important;
    font-weight: 600 !important;
    padding: 4px 12px !important;
    border-radius: 6px !important;
    height: 28px !important;
    min-height: 28px !important;
    transition: all 0.15s !important;
    white-space: nowrap !important;
    letter-spacing: -0.01em !important;
}
div[data-pill="inactive"] > div > button {
    background: transparent !important;
    border: 1px solid #27272a !important;
    color: #52525b !important;
    font-size: 12px !important;
    font-weight: 500 !important;
    padding: 4px 12px !important;
    border-radius: 6px !important;
    height: 28px !important;
    min-height: 28px !important;
    transition: all 0.15s !important;
    white-space: nowrap !important;
    letter-spacing: -0.01em !important;
}
div[data-pill="inactive"] > div > button:hover {
    background: #18181b !important;
    border-color: #3f3f46 !important;
    color: #a1a1aa !important;
}

/* sort chips */
div[data-sort="active"] > div > button {
    background: #1e1a2e !important;
    border: 1px solid #4f46e5 !important;
    color: #818cf8 !important;
    font-size: 11px !important;
    font-weight: 600 !important;
    padding: 3px 10px !important;
    border-radius: 5px !important;
    height: 26px !important;
    min-height: 26px !important;
    letter-spacing: 0.01em !important;
}
div[data-sort="inactive"] > div > button {
    background: transparent !important;
    border: 1px solid #27272a !important;
    color: #52525b !important;
    font-size: 11px !important;
    font-weight: 500 !important;
    padding: 3px 10px !important;
    border-radius: 5px !important;
    height: 26px !important;
    min-height: 26px !important;
    letter-spacing: 0.01em !important;
}
div[data-sort="inactive"] > div > button:hover {
    background: #18181b !important;
    color: #a1a1aa !important;
    border-color: #3f3f46 !important;
}

/* ─── Primary / secondary action buttons ──────────────────────────────── */
.stButton > button {
    font-family: 'Inter', system-ui, sans-serif !important;
    transition: all 0.15s ease !important;
    cursor: pointer !important;
    letter-spacing: -0.01em !important;
}
.stButton > button[kind="primary"] {
    background: #6366f1 !important;
    border: 1px solid #4f46e5 !important;
    color: #fff !important;
    font-weight: 600 !important;
    font-size: 13px !important;
    border-radius: 7px !important;
    padding: 6px 16px !important;
}
.stButton > button[kind="primary"]:hover {
    background: #4f46e5 !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 16px rgba(99,102,241,0.35) !important;
}
.stButton > button[kind="secondary"] {
    background: #18181b !important;
    border: 1px solid #27272a !important;
    color: #71717a !important;
    font-weight: 500 !important;
    font-size: 13px !important;
    border-radius: 7px !important;
    padding: 6px 16px !important;
}
.stButton > button[kind="secondary"]:hover {
    background: #1c1c1f !important;
    border-color: #3f3f46 !important;
    color: #a1a1aa !important;
}

/* ─── Inputs ───────────────────────────────────────────────────────────── */
[data-testid="stTextInput"] input {
    background: #111113 !important;
    border: 1px solid #27272a !important;
    border-radius: 7px !important;
    color: #fafafa !important;
    font-size: 13px !important;
}
[data-testid="stTextInput"] input:focus {
    border-color: #6366f1 !important;
    box-shadow: 0 0 0 2px rgba(99,102,241,0.15) !important;
}
[data-testid="stTextInput"] input::placeholder { color: #3f3f46 !important; }

/* sliders */
[data-testid="stSlider"] [data-baseweb="slider"] [data-testid="stThumbValue"] {
    color: #a1a1aa !important; font-size: 11px !important;
}
[class*="StyledThumb"] { background: #6366f1 !important; border-color: #6366f1 !important; }
[class*="StyledSliderBar"] { background: #6366f1 !important; }
[class*="StyledSliderTrack"] { background: #27272a !important; }

/* toggles */
[data-testid="stToggle"] label { color: #71717a !important; font-size: 13px !important; }

/* select box */
[data-testid="stSelectbox"] > div {
    background: #111113 !important;
    border: 1px solid #27272a !important;
    border-radius: 7px !important;
}

/* tabs */
[data-testid="stTabs"] [data-baseweb="tab-list"] {
    background: transparent !important;
    border-bottom: 1px solid #27272a !important;
    gap: 0 !important;
}
[data-testid="stTabs"] [data-baseweb="tab"] {
    background: transparent !important;
    color: #52525b !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    padding: 8px 16px !important;
    border-bottom: 2px solid transparent !important;
    letter-spacing: -0.01em !important;
}
[data-testid="stTabs"] [aria-selected="true"] {
    background: transparent !important;
    color: #fafafa !important;
    font-weight: 600 !important;
    border-bottom: 2px solid #6366f1 !important;
}
[data-testid="stTabs"] [data-baseweb="tab-highlight"] { display: none !important; }
[data-testid="stTabs"] [data-baseweb="tab-border"]    { display: none !important; }

/* dataframe */
[data-testid="stDataFrame"] {
    border: 1px solid #1c1c1f !important;
    border-radius: 8px !important;
    overflow: hidden !important;
}
[data-testid="stDataFrame"] iframe { background: #111113 !important; }

/* expander */
[data-testid="stExpander"] {
    background: #111113 !important;
    border: 1px solid #1c1c1f !important;
    border-radius: 8px !important;
}
[data-testid="stExpander"]:hover { border-color: #27272a !important; }
[data-testid="stExpander"] summary { color: #71717a !important; font-size: 13px !important; }

/* ─── Alert card ───────────────────────────────────────────────────────── */
.alert-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    background: #111113;
    border: 1px solid #1c1c1f;
    border-left: 3px solid var(--ac, #ef4444);
    border-radius: 8px;
    padding: 14px 18px;
    margin-bottom: 8px;
    transition: border-color 0.15s;
}
.alert-row:hover { border-color: #27272a; border-left-color: var(--ac, #ef4444); }
.alert-product { font-size: 13px; font-weight: 600; color: #e4e4e7; margin-bottom: 4px; }
.alert-meta    { font-size: 11px; color: #52525b; display: flex; align-items: center; gap: 8px; }
.alert-pct     {
    font-size: 15px; font-weight: 700;
    color: var(--ac, #ef4444);
    flex-shrink: 0;
    min-width: 52px;
    text-align: right;
}

/* ─── Progress bar ─────────────────────────────────────────────────────── */
.prog-wrap  { margin-bottom: 10px; }
.prog-top   { display: flex; justify-content: space-between; margin-bottom: 5px; }
.prog-name  { font-size: 12px; font-weight: 600; color: #71717a; }
.prog-val   { font-size: 12px; color: #3f3f46; }
.prog-track { height: 4px; background: #18181b; border-radius: 2px; overflow: hidden; }
.prog-fill  {
    height: 100%; border-radius: 2px;
    background: linear-gradient(90deg, var(--fc1,#6366f1), var(--fc2,#a78bfa));
    transition: width 0.5s cubic-bezier(0.4,0,0.2,1);
}

/* ─── Stat result boxes ────────────────────────────────────────────────── */
.result-box {
    background: #111113;
    border: 1px solid #1c1c1f;
    border-radius: 8px;
    padding: 16px 20px;
    margin-bottom: 10px;
}
.result-box-label {
    font-size: 11px; font-weight: 600;
    letter-spacing: 0.06em; text-transform: uppercase;
    color: #3f3f46; margin-bottom: 12px;
}
.result-stats { display: flex; gap: 28px; flex-wrap: wrap; }
.result-stat-val { font-size: 18px; font-weight: 700; color: #fafafa; letter-spacing: -0.03em; }
.result-stat-lbl { font-size: 10px; color: #52525b; font-weight: 600; letter-spacing: 0.05em;
                   text-transform: uppercase; margin-top: 2px; }
.badge-reject {
    display: inline-block; margin-top: 10px;
    background: rgba(239,68,68,0.08); border: 1px solid rgba(239,68,68,0.2);
    border-radius: 4px; padding: 2px 10px;
    font-size: 12px; font-weight: 600; color: #f87171;
}
.badge-fail {
    display: inline-block; margin-top: 10px;
    background: rgba(99,102,241,0.08); border: 1px solid rgba(99,102,241,0.2);
    border-radius: 4px; padding: 2px 10px;
    font-size: 12px; font-weight: 600; color: #818cf8;
}

/* ─── Empty state ──────────────────────────────────────────────────────── */
.empty-wrap {
    border: 1px dashed #27272a; border-radius: 10px;
    padding: 56px 40px; text-align: center; margin: 24px 0;
}
.empty-icon { font-size: 28px; margin-bottom: 12px; color: #3f3f46; }
.empty-title { font-size: 15px; font-weight: 600; color: #52525b; margin-bottom: 6px; }
.empty-sub { font-size: 13px; color: #3f3f46; }
.empty-code {
    display: inline-block; margin-top: 16px;
    background: #18181b; border: 1px solid #27272a; border-radius: 6px;
    padding: 6px 14px; font-size: 12px; color: #71717a; font-family: monospace;
}

/* ─── Live indicator ───────────────────────────────────────────────────── */
.live-dot {
    display: inline-block;
    width: 6px; height: 6px;
    background: #22c55e;
    border-radius: 50%;
    margin-right: 5px;
    animation: pulse-dot 2s infinite;
    vertical-align: middle;
}
@keyframes pulse-dot {
    0%, 100% { opacity: 1; box-shadow: 0 0 0 0 rgba(34,197,94,0.4); }
    50%       { opacity: 0.7; box-shadow: 0 0 0 4px rgba(34,197,94,0); }
}

/* ─── Sidebar ──────────────────────────────────────────────────────────── */
[data-testid="stSidebar"] .stButton > button {
    width: 100% !important;
    text-align: left !important;
    border-radius: 6px !important;
    font-size: 13px !important;
    padding: 7px 12px !important;
}

/* divider */
hr { border: none; border-top: 1px solid #18181b; margin: 16px 0; }
</style>
""", unsafe_allow_html=True)

# ── Cached data ────────────────────────────────────────────────────────────────
@st.cache_data(ttl=30)
def _live() -> pd.DataFrame:
    return load_live(limit=5000)

@st.cache_data(ttl=300)
def _mart(table: str) -> pd.DataFrame:
    return load_mart(table)

# ── Reusable components ────────────────────────────────────────────────────────
def kpi(label: str, value: str, sub: str = "", color: str = "#6366f1",
        trend: str = "", trend_up: bool = True):
    t = ""
    if trend:
        cls = "kpi-trend-up" if trend_up else "kpi-trend-down"
        arrow = "↑" if trend_up else "↓"
        t = f'<div class="{cls}">{arrow} {trend}</div>'
    st.markdown(f"""
    <div class="kpi-card" style="--kc:{color}">
      <div class="kpi-label">{label}</div>
      <div class="kpi-value">{value}</div>
      {'<div class="kpi-sub">'+sub+'</div>' if sub else ''}
      {t}
    </div>""", unsafe_allow_html=True)


def sec(title: str, badge: str = ""):
    b = f'<span class="sec-badge">{badge}</span>' if badge else ""
    st.markdown(f'<div class="sec-wrap"><span class="sec-title">{title}</span>{b}</div>',
                unsafe_allow_html=True)


def empty():
    st.markdown("""
    <div class="empty-wrap">
      <div class="empty-icon">◌</div>
      <div class="empty-title">No data available</div>
      <div class="empty-sub">Run a scraper to populate the dashboard</div>
      <code class="empty-code">make scrape-books-sample</code>
    </div>""", unsafe_allow_html=True)


def chart(fig: go.Figure, h: int = 320) -> go.Figure:
    fig.update_layout(**CHART_BASE, height=h)
    return fig


def src_pill(source: str) -> str:
    m = src_meta(source)
    return (f'<span class="src-pill" '
            f'style="color:{m["color"]};border-color:{m["color"]}33;'
            f'background:{m["bg"]}">'
            f'{m["icon"]} {m["label"]}</span>')


def progress_bars(df: pd.DataFrame, name_col: str, value_col: str):
    palette = [("#6366f1","#818cf8"), ("#38bdf8","#7dd3fc"),
               ("#34d399","#6ee7b7"), ("#fbbf24","#fde68a"), ("#f97316","#fdba74")]
    total = df[value_col].sum()
    for i, (_, row) in enumerate(df.iterrows()):
        pct = row[value_col] / total * 100 if total > 0 else 0
        c1, c2 = palette[i % len(palette)]
        st.markdown(f"""
        <div class="prog-wrap">
          <div class="prog-top">
            <span class="prog-name">{row[name_col]}</span>
            <span class="prog-val">{row[value_col]:,.0f} · {pct:.1f}%</span>
          </div>
          <div class="prog-track">
            <div class="prog-fill" style="width:{pct:.1f}%;--fc1:{c1};--fc2:{c2}"></div>
          </div>
        </div>""", unsafe_allow_html=True)


def pill_filters(options: list[str], state_key: str,
                 color_map: dict | None = None, all_label: str = "All"):
    all_opts = [all_label] + options
    current  = st.session_state.get(state_key, all_label)
    cols     = st.columns(len(all_opts))
    for i, opt in enumerate(all_opts):
        active = opt == current
        m = SOURCE_META.get(opt, {})
        pc = m.get("color", "#6366f1") if opt != all_label else "#6366f1"
        pb = m.get("bg",    "#1a1033") if opt != all_label else "#1a1033"
        lbl = (m.get("icon","") + " " + m.get("label", opt)) if (opt != all_label and opt in SOURCE_META) else opt
        with cols[i]:
            st.markdown(f'<div data-pill="{"active" if active else "inactive"}" '
                        f'style="--pc:{pc};--pb:{pb}">', unsafe_allow_html=True)
            if st.button(lbl, key=f"pill_{state_key}_{i}", use_container_width=True):
                st.session_state[state_key] = opt
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
    return st.session_state.get(state_key, all_label)


def sort_chips(options: list[tuple[str, str]], state_key: str) -> str:
    current = st.session_state.get(state_key, options[0][0])
    cols    = st.columns(len(options))
    for col, (val, lbl) in zip(cols, options):
        with col:
            st.markdown(f'<div data-sort="{"active" if val==current else "inactive"}">', unsafe_allow_html=True)
            if st.button(lbl, key=f"sort_{state_key}_{val}", use_container_width=True):
                st.session_state[state_key] = val
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
    return current


# ── Top navigation bar ─────────────────────────────────────────────────────────
def _topnav():
    st.markdown('<div class="topbar">', unsafe_allow_html=True)
    logo_col, div_col, *nav_cols, right_col = st.columns(
        [1.8, 0.05] + [1.1] * len(PAGES) + [0.6]
    )
    with logo_col:
        st.markdown(
            '<div class="topbar-logo">'
            '<span class="topbar-logo-dot"></span>Price Intelligence'
            '</div>', unsafe_allow_html=True)
    with div_col:
        st.markdown('<div class="topbar-divider"></div>', unsafe_allow_html=True)
    for col, (label, desc) in zip(nav_cols, PAGES):
        with col:
            active = st.session_state.page == label
            st.markdown(f'<div data-topnav="{"active" if active else "inactive"}">', unsafe_allow_html=True)
            if st.button(label, key=f"topnav_{label}", help=desc, use_container_width=True):
                st.session_state.page = label
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
    with right_col:
        if st.button("↺ Refresh", key="topnav_refresh", type="secondary"):
            st.cache_data.clear()
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

_topnav()


# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="padding:16px 4px 8px">
      <div style="font-size:13px;font-weight:700;color:#fafafa;letter-spacing:-0.03em">
        ◈ Price Intelligence
      </div>
      <div style="font-size:11px;color:#3f3f46;margin-top:3px">E-commerce Platform · 2026</div>
    </div>""", unsafe_allow_html=True)
    st.markdown("<hr>", unsafe_allow_html=True)

    st.markdown('<div style="font-size:10px;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;color:#3f3f46;margin-bottom:8px">Data controls</div>', unsafe_allow_html=True)
    auto_refresh = st.toggle("Auto-refresh (30s)", value=False, key="auto_refresh")

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Refresh", type="primary", use_container_width=True):
            st.cache_data.clear(); st.rerun()
    with c2:
        if st.button("Reset", type="secondary", use_container_width=True):
            for k, v in {"src_filter":"ALL","avail_filter":"ALL","search":"",
                         "sort_by":"price_asc","price_min":0.0,"price_max":9999.0}.items():
                st.session_state[k] = v
            st.rerun()

    st.markdown("<hr>", unsafe_allow_html=True)

    _df_side = _live()
    ts = time.strftime("%H:%M:%S")
    st.markdown(f"""
    <div style="background:#0d0d10;border:1px solid #1c1c1f;border-radius:8px;padding:14px 16px">
      <div style="font-size:10px;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;color:#3f3f46;margin-bottom:8px">
        <span class="live-dot"></span>Live status
      </div>
      <div style="font-size:11px;color:#3f3f46;margin-bottom:3px">Last sync</div>
      <div style="font-size:14px;font-weight:700;color:#52525b;letter-spacing:-0.02em">{ts}</div>
    </div>""", unsafe_allow_html=True)

    if not _df_side.empty:
        st.markdown("<div style='margin-top:10px'></div>", unsafe_allow_html=True)
        recs = len(_df_side)
        srcs = _df_side["source"].nunique()
        avgp = _df_side["price"].mean()
        st.markdown(f"""
        <div style="background:#0d0d10;border:1px solid #1c1c1f;border-radius:8px;padding:14px 16px">
          <div style="font-size:10px;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;color:#3f3f46;margin-bottom:10px">Dataset</div>
          <div style="display:flex;justify-content:space-between;margin-bottom:6px">
            <span style="font-size:12px;color:#3f3f46">Records</span>
            <span style="font-size:12px;font-weight:700;color:#52525b">{recs:,}</span>
          </div>
          <div style="display:flex;justify-content:space-between;margin-bottom:6px">
            <span style="font-size:12px;color:#3f3f46">Sources</span>
            <span style="font-size:12px;font-weight:700;color:#52525b">{srcs}</span>
          </div>
          <div style="display:flex;justify-content:space-between">
            <span style="font-size:12px;color:#3f3f46">Avg price</span>
            <span style="font-size:12px;font-weight:700;color:#52525b">{avgp:.2f}</span>
          </div>
        </div>""", unsafe_allow_html=True)

    st.markdown("""
    <div style="margin-top:24px;font-size:10px;color:#27272a;text-align:center">
      Hassan RADA · Final Year Project · 2026
    </div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE SHELL WRAPPER
# ══════════════════════════════════════════════════════════════════════════════
def shell_start(title: str, subtitle: str):
    st.markdown(f"""
    <div class="page-shell">
      <div class="page-header">
        <div class="page-title">{title}</div>
        <div class="page-sub">{subtitle}</div>
      </div>""", unsafe_allow_html=True)

def shell_end():
    st.markdown("</div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 1 — Live Feed
# ══════════════════════════════════════════════════════════════════════════════
def page_live():
    st.markdown("""
    <div style="padding:32px 40px 0;max-width:1400px;margin:0 auto">
      <div style="padding-bottom:24px;border-bottom:1px solid #18181b;margin-bottom:0">
        <div class="page-title">Live Feed</div>
        <div class="page-sub">Most recent observation per product</div>
      </div>
    </div>""", unsafe_allow_html=True)

    df = _live()
    if df.empty:
        st.markdown('<div style="padding:0 40px;max-width:1400px;margin:0 auto">', unsafe_allow_html=True)
        empty()
        st.markdown("</div>", unsafe_allow_html=True)
        return

    if "scraped_at" in df.columns:
        df = df.sort_values("scraped_at").groupby("product_id").last().reset_index()

    all_sources = sorted(df["source"].dropna().unique().tolist())
    price_floor = float(df["price"].min())
    price_ceil  = float(df["price"].max())

    st.markdown('<div style="padding:0 40px 64px;max-width:1400px;margin:0 auto">', unsafe_allow_html=True)

    # ── KPI strip ─────────────────────────────────────────────────────────────
    st.markdown("<div style='margin-top:24px'></div>", unsafe_allow_html=True)
    k1,k2,k3,k4,k5 = st.columns(5)
    with k1: kpi("Products",     f"{len(df):,}",                         color="#6366f1")
    with k2: kpi("Sources",      str(df["source"].nunique()),             color="#38bdf8")
    with k3: kpi("Avg price",    f"{df['price'].mean():.2f}",            color="#22c55e")
    with k4: kpi("Lowest",       f"{df['price'].min():.2f}",             color="#a78bfa")
    with k5: kpi("Highest",      f"{df['price'].max():.2f}",             color="#f97316")

    # ── Filter section ────────────────────────────────────────────────────────
    with st.expander("Filters & Sort", expanded=True):
        fa, fb = st.columns([2, 2])
        with fa:
            search = st.text_input("", placeholder="Search product or category…",
                                   value=st.session_state.search,
                                   key="search_input", label_visibility="collapsed")
            st.session_state.search = search
        with fb:
            p_range = st.slider("Price range", min_value=price_floor,
                                max_value=max(price_ceil, price_floor + 1),
                                value=(price_floor, price_ceil),
                                format="%.0f", label_visibility="collapsed")

        st.markdown('<div class="filter-label" style="margin-top:10px">Source</div>', unsafe_allow_html=True)
        selected_src = pill_filters(all_sources, "src_filter", all_label="All")

        av_col, sort_col = st.columns([2, 3])
        with av_col:
            avail_opts = []
            if "availability" in df.columns:
                avail_opts = sorted(df["availability"].dropna().unique().tolist())
            if avail_opts:
                st.markdown('<div class="filter-label">Availability</div>', unsafe_allow_html=True)
                pill_filters(avail_opts, "avail_filter", all_label="All")
        with sort_col:
            st.markdown('<div class="filter-label">Sort by</div>', unsafe_allow_html=True)
            sort_chips([("price_asc","Price ↑"),("price_desc","Price ↓"),
                        ("rating_desc","Rating ↓"),("title_asc","A → Z")], "sort_by")

    # Apply filters
    filtered = df.copy()
    if st.session_state.search:
        q = st.session_state.search.lower()
        filtered = filtered[filtered.apply(
            lambda r: q in str(r.get("title","")).lower() or q in str(r.get("category","")).lower(), axis=1)]
    if st.session_state.src_filter not in ("ALL", "All"):
        filtered = filtered[filtered["source"] == st.session_state.src_filter]
    if st.session_state.avail_filter not in ("ALL", "All") and "availability" in filtered.columns:
        filtered = filtered[filtered["availability"] == st.session_state.avail_filter]
    filtered = filtered[(filtered["price"] >= p_range[0]) & (filtered["price"] <= p_range[1])]

    sc, sa = {"price_asc":("price",True),"price_desc":("price",False),
              "rating_desc":("rating",False),"title_asc":("title",True)}.get(
        st.session_state.sort_by, ("price",True))
    if sc in filtered.columns:
        filtered = filtered.sort_values(sc, ascending=sa)

    st.markdown(f'<div style="font-size:12px;color:#3f3f46;margin:12px 0 0">'
                f'{len(filtered):,} products</div>', unsafe_allow_html=True)

    if filtered.empty:
        st.markdown('<div style="font-size:13px;color:#52525b;padding:24px 0">No products match the current filters.</div>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        return

    # ── Charts ────────────────────────────────────────────────────────────────
    ch1, ch2 = st.columns([3, 2])
    with ch1:
        sec("Price distribution", "by source")
        fig = px.violin(filtered, x="source", y="price", color="source",
                        color_discrete_map=SOURCE_COLORS, box=True, points="outliers",
                        log_y=True, labels={"price":"Price (log)","source":""})
        fig.update_traces(meanline_visible=True, line_width=1.2, opacity=0.85)
        fig.update_layout(showlegend=False)
        st.plotly_chart(chart(fig, 300), use_container_width=True)
    with ch2:
        sec("Market share")
        share = filtered.groupby("source").size().reset_index(name="n")
        fig2  = px.pie(share, values="n", names="source",
                       color="source", color_discrete_map=SOURCE_COLORS, hole=0.65)
        fig2.update_traces(textposition="outside", textinfo="percent+label",
                           textfont=dict(size=10, color="#71717a"),
                           marker_line_color="#09090b", marker_line_width=2,
                           pull=[0.03]*len(share))
        fig2.update_layout(showlegend=False)
        st.plotly_chart(chart(fig2, 300), use_container_width=True)

    sec("Volume by source")
    src_cnt = filtered.groupby("source").size().reset_index(name="n").sort_values("n", ascending=False)
    progress_bars(src_cnt, "source", "n")

    # ── Table ─────────────────────────────────────────────────────────────────
    sec("Product catalogue", f"{len(filtered):,} results")
    show_cols = [c for c in ["title","source","price","currency","availability","category","rating","scraped_at"]
                 if c in filtered.columns]
    st.dataframe(
        filtered[show_cols].reset_index(drop=True),
        use_container_width=True, height=400, hide_index=True,
        column_config={
            "title":        st.column_config.TextColumn("Product", width="large"),
            "source":       st.column_config.TextColumn("Source"),
            "price":        st.column_config.NumberColumn("Price",    format="%.2f"),
            "rating":       st.column_config.NumberColumn("Rating",   format="%.1f"),
            "scraped_at":   st.column_config.DatetimeColumn("Scraped", format="MMM D, HH:mm"),
            "availability": st.column_config.TextColumn("Stock"),
        },
    )
    st.markdown("</div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 2 — Analytics
# ══════════════════════════════════════════════════════════════════════════════
def page_kpis():
    st.markdown("""
    <div style="padding:32px 40px 0;max-width:1400px;margin:0 auto">
      <div style="padding-bottom:24px;border-bottom:1px solid #18181b">
        <div class="page-title">Analytics</div>
        <div class="page-sub">Aggregated metrics from dbt marts</div>
      </div>
    </div>""", unsafe_allow_html=True)

    st.markdown('<div style="padding:0 40px 64px;max-width:1400px;margin:0 auto">', unsafe_allow_html=True)

    stats_df = _mart("mart_price_stats")
    hist_df  = _mart("mart_price_history")

    if stats_df.empty and hist_df.empty:
        empty(); st.markdown("</div>", unsafe_allow_html=True); return

    if not stats_df.empty:
        accent = ["#6366f1","#38bdf8","#34d399","#fbbf24","#f97316"]
        sec("Price statistics per source")
        cols = st.columns(min(len(stats_df), 5))
        for i, (_, row) in enumerate(stats_df.iterrows()):
            with cols[i % len(cols)]:
                src = str(row.get("source","?"))
                avg = row.get("avg_price", 0)
                med = row.get("median_price", avg)
                sd  = row.get("stddev_price", 0)
                cur = row.get("currency","")
                kpi(src.replace("_"," ").title(), f"{avg:.2f} {cur}",
                    sub=f"median {med:.2f} · σ {sd:.2f}",
                    color=accent[i % len(accent)])

        sec("Price ranges", "min · avg · median · max")
        pcols = [c for c in ["min_price","avg_price","median_price","max_price"] if c in stats_df.columns]
        if pcols and "source" in stats_df.columns:
            melted = stats_df.melt(id_vars="source", value_vars=pcols, var_name="metric", value_name="price")
            melted["metric"] = melted["metric"].map({"min_price":"Min","avg_price":"Avg",
                                                     "median_price":"Median","max_price":"Max"})
            fig = px.bar(melted, x="source", y="price", color="metric", barmode="group",
                         color_discrete_sequence=["#6366f1","#22c55e","#f59e0b","#ef4444"],
                         labels={"price":"Price","source":"","metric":""})
            fig.update_traces(marker_line_width=0, opacity=0.9)
            st.plotly_chart(chart(fig, 340), use_container_width=True)

        if "product_count" in stats_df.columns and "source" in stats_df.columns:
            sec("Volume per source")
            cnt = stats_df[["source","product_count"]].sort_values("product_count", ascending=False)
            progress_bars(cnt, "source", "product_count")

        sec("Full statistics table")
        st.dataframe(stats_df.reset_index(drop=True), use_container_width=True, hide_index=True,
                     column_config={c: st.column_config.NumberColumn(c, format="%.2f")
                                    for c in stats_df.select_dtypes("number").columns})

    if not hist_df.empty and "scraped_date" in hist_df.columns and "product_id" in hist_df.columns:
        sec("Price trend explorer", "interactive")
        te_col1, te_col2 = st.columns([4, 1])
        with te_col1:
            def _lbl(pid):
                r = hist_df[hist_df["product_id"] == pid]
                return r["title"].iloc[0] if (not r.empty and "title" in r.columns) else pid
            sel_pid = st.selectbox("Select product", hist_df["product_id"].unique().tolist(),
                                   format_func=_lbl, label_visibility="collapsed")
        with te_col2:
            show_drops = st.toggle("Show drops", value=True)

        trend = hist_df[hist_df["product_id"] == sel_pid].sort_values("scraped_date")
        if not trend.empty:
            ka, kb, kc = st.columns(3)
            with ka: kpi("High", f"{trend['price'].max():.2f}", color="#ef4444")
            with kb: kpi("Low",  f"{trend['price'].min():.2f}", color="#22c55e")
            with kc:
                chg = trend["price"].iloc[-1] - trend["price"].iloc[0] if len(trend) > 1 else 0
                kpi("Change", f"{'+'if chg>=0 else ''}{chg:.2f}",
                    color="#22c55e" if chg >= 0 else "#ef4444")
            fig3 = px.line(trend, x="scraped_date", y="price", markers=True,
                           color_discrete_sequence=["#6366f1"],
                           labels={"price":"Price","scraped_date":"Date"})
            fig3.update_traces(line_width=2, marker_size=5)
            if show_drops and "price_change_pct" in trend.columns:
                drops = trend[trend["price_change_pct"] <= -5]
                if not drops.empty:
                    fig3.add_scatter(x=drops["scraped_date"], y=drops["price"],
                                     mode="markers",
                                     marker=dict(color="#ef4444", size=10, symbol="triangle-down",
                                                 line=dict(color="#09090b", width=1.5)),
                                     name="Drop ≥5%")
            st.plotly_chart(chart(fig3, 300), use_container_width=True)

    st.markdown("</div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 3 — Statistics
# ══════════════════════════════════════════════════════════════════════════════
def page_stats():
    st.markdown("""
    <div style="padding:32px 40px 0;max-width:1400px;margin:0 auto">
      <div style="padding-bottom:24px;border-bottom:1px solid #18181b">
        <div class="page-title">Statistics</div>
        <div class="page-sub">Hypothesis tests · regression · confidence intervals</div>
      </div>
    </div>""", unsafe_allow_html=True)

    st.markdown('<div style="padding:0 40px 64px;max-width:1400px;margin:0 auto">', unsafe_allow_html=True)

    df = _live()
    if df.empty:
        empty(); st.markdown("</div>", unsafe_allow_html=True); return

    tab1, tab2, tab3 = st.tabs(["Descriptive", "Hypothesis tests", "Regression"])

    with tab1:
        sec("Summary statistics", "per source")
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
            sec("Distribution", "log scale")
            fh = px.histogram(df, x="price", color="source", barmode="overlay",
                              opacity=0.6, log_x=True, nbins=55,
                              color_discrete_map=SOURCE_COLORS,
                              labels={"price":"Price (log)"})
            fh.update_traces(marker_line_width=0)
            st.plotly_chart(chart(fh, 280), use_container_width=True)
        with cb:
            sec("Coefficient of variation", "price volatility %")
            vol = df.groupby("source")["price"].apply(
                lambda s: round(s.std()/s.mean()*100,1) if s.mean()>0 else 0
            ).reset_index()
            vol.columns = ["source","cv"]
            fv = px.bar(vol.sort_values("cv", ascending=False), x="source", y="cv",
                        color="source", color_discrete_map=SOURCE_COLORS, text="cv",
                        labels={"cv":"CV (%)","source":""})
            fv.update_traces(texttemplate="%{text:.1f}%", textposition="outside",
                             marker_line_width=0, opacity=0.9)
            fv.update_layout(showlegend=False)
            st.plotly_chart(chart(fv, 280), use_container_width=True)

        sec("Box plots")
        fb = px.box(df, x="source", y="price", color="source",
                    color_discrete_map=SOURCE_COLORS, points="outliers",
                    log_y=True, labels={"price":"Price (log)","source":""})
        fb.update_layout(showlegend=False)
        st.plotly_chart(chart(fb, 300), use_container_width=True)

    with tab2:
        groups = {s: df[df["source"]==s]["price"].dropna() for s in df["source"].unique()}
        groups = {k:v for k,v in groups.items() if len(v)>=3}
        if len(groups) < 2:
            st.info("Need ≥ 2 sources with ≥ 3 observations each.")
        else:
            sec("Normality", "Shapiro-Wilk")
            norm_rows = []
            for src, g in groups.items():
                w, p = scipy_stats.shapiro(g.head(5000))
                norm_rows.append({"Source":src,"n":len(g),"W":round(w,4),
                                   "p-value":round(p,6),
                                   "Normal":"Yes" if p>=0.05 else "No"})
            st.dataframe(pd.DataFrame(norm_rows), use_container_width=True, hide_index=True)

            sec("One-Way ANOVA", "H₀: all means equal")
            f_stat, p_anova = scipy_stats.f_oneway(*groups.values())
            rej_a = p_anova < 0.05
            st.markdown(f"""
            <div class="result-box">
              <div class="result-box-label">ANOVA result</div>
              <div class="result-stats">
                <div>
                  <div class="result-stat-val">{f_stat:.4f}</div>
                  <div class="result-stat-lbl">F-statistic</div>
                </div>
                <div>
                  <div class="result-stat-val">{p_anova:.2e}</div>
                  <div class="result-stat-lbl">p-value</div>
                </div>
                <div>
                  <div class="result-stat-val">α = 0.05</div>
                  <div class="result-stat-lbl">threshold</div>
                </div>
              </div>
              <div class="{'badge-reject' if rej_a else 'badge-fail'}">
                {'Reject H₀ — means differ significantly' if rej_a else 'Fail to reject H₀'}
              </div>
            </div>""", unsafe_allow_html=True)

            sec("Kruskal-Wallis", "non-parametric")
            h_stat, p_kw = scipy_stats.kruskal(*groups.values())
            rej_k = p_kw < 0.05
            st.markdown(f"""
            <div class="result-box">
              <div class="result-box-label">Kruskal-Wallis result</div>
              <div class="result-stats">
                <div>
                  <div class="result-stat-val">{h_stat:.4f}</div>
                  <div class="result-stat-lbl">H-statistic</div>
                </div>
                <div>
                  <div class="result-stat-val">{p_kw:.2e}</div>
                  <div class="result-stat-lbl">p-value</div>
                </div>
              </div>
              <div class="{'badge-reject' if rej_k else 'badge-fail'}">
                {'Reject H₀ — distributions differ' if rej_k else 'Fail to reject H₀'}
              </div>
            </div>""", unsafe_allow_html=True)

            sec("Mann-Whitney pairwise", "two-sided")
            src_list  = list(groups.keys())
            mw_rows   = []
            heat_data = {s:{s2:1.0 for s2 in src_list} for s in src_list}
            for a, b in itertools.combinations(src_list, 2):
                u, p_mw = scipy_stats.mannwhitneyu(groups[a], groups[b], alternative="two-sided")
                n1, n2  = len(groups[a]), len(groups[b])
                r_eff   = round(1 - (2*u)/(n1*n2), 3)
                mw_rows.append({"A":a,"B":b,"U":round(u,0),
                                 "p-value":round(p_mw,6),"Effect r":r_eff,
                                 "Sig":"✓" if p_mw<0.05 else "✗"})
                heat_data[a][b] = heat_data[b][a] = p_mw

            col_mw, col_heat = st.columns([2, 1])
            with col_mw:
                st.dataframe(pd.DataFrame(mw_rows).sort_values("p-value"),
                             use_container_width=True, hide_index=True)
            with col_heat:
                z    = [[heat_data[r][c] for c in src_list] for r in src_list]
                f_hm = go.Figure(go.Heatmap(
                    z=np.log10(np.array(z)+1e-10), x=src_list, y=src_list,
                    colorscale=[[0,"#6366f1"],[0.5,"#18181b"],[1,"#ef4444"]],
                    hovertemplate="%{y} vs %{x}<br>log10(p)=%{z:.2f}<extra></extra>",
                    colorbar=dict(tickfont=dict(color="#52525b",size=9),
                                  title=dict(text="log10(p)",font=dict(color="#52525b",size=9)),
                                  thickness=10)
                ))
                f_hm.update_layout(title="p-value heatmap", xaxis_tickangle=-30)
                st.plotly_chart(chart(f_hm, 260), use_container_width=True)

            sec("95% Confidence Intervals", "mean price per source")
            ci_rows = []
            for src, g in groups.items():
                n, se  = len(g), scipy_stats.sem(g)
                lo, hi = scipy_stats.t.interval(0.95, df=n-1, loc=g.mean(), scale=se)
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
                        mode="lines", line=dict(width=5, color=col), showlegend=False,
                        opacity=0.6))
                    fig_ci.add_trace(go.Scatter(
                        x=[row["Mean"]], y=[row["Source"]],
                        mode="markers",
                        marker=dict(size=11, color=col, symbol="diamond",
                                    line=dict(color="#09090b",width=2)),
                        name=row["Source"], showlegend=False))
                fig_ci.update_layout(title="Forest plot — 95% CI", xaxis_title="Price", yaxis_title="")
                st.plotly_chart(chart(fig_ci, 260), use_container_width=True)

    with tab3:
        sec("Regression", "price ~ rating")
        reg_df = df.dropna(subset=["price","rating"]) if "rating" in df.columns else pd.DataFrame()
        if reg_df.empty or len(reg_df) < 5:
            st.info("Not enough data with rating values.")
        else:
            slope, intercept, r, p, se = scipy_stats.linregress(reg_df["rating"], reg_df["price"])
            r2 = r**2
            ra,rb,rc,rd = st.columns(4)
            with ra: kpi("Slope β₁",     f"{slope:.4f}",    sub="per rating unit",
                          color="#6366f1" if slope>0 else "#ef4444")
            with rb: kpi("Intercept β₀", f"{intercept:.2f}", color="#38bdf8")
            with rc: kpi("R²",            f"{r2:.4f}",        sub="variance explained",
                          color="#22c55e" if r2>0.3 else "#f59e0b")
            with rd: kpi("p-value",       f"{p:.2e}",
                          sub="significant" if p<0.05 else "not significant",
                          color="#22c55e" if p<0.05 else "#ef4444")

            fig_r = px.scatter(reg_df, x="rating", y="price", color="source",
                               color_discrete_map=SOURCE_COLORS, opacity=0.45,
                               trendline="ols", labels={"price":"Price","rating":"Rating"})
            fig_r.update_traces(marker_size=5)
            st.plotly_chart(chart(fig_r, 380), use_container_width=True)

            sec("Per-source regression")
            reg_rows = []
            for src, g in df.groupby("source"):
                gf = g.dropna(subset=["price","rating"])
                if len(gf) < 5: continue
                sl,ic,rv,pv,sv = scipy_stats.linregress(gf["rating"], gf["price"])
                reg_rows.append({"Source":src,"n":len(gf),"Slope":round(sl,4),
                                  "Intercept":round(ic,2),"R":round(rv,4),
                                  "R²":round(rv**2,4),"p":round(pv,6),
                                  "Sig":"✓" if pv<0.05 else "✗"})
            if reg_rows:
                st.dataframe(pd.DataFrame(reg_rows), use_container_width=True, hide_index=True)

    st.markdown("</div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 4 — Alerts
# ══════════════════════════════════════════════════════════════════════════════
def page_alerts():
    st.markdown("""
    <div style="padding:32px 40px 0;max-width:1400px;margin:0 auto">
      <div style="padding-bottom:24px;border-bottom:1px solid #18181b">
        <div class="page-title">Alerts</div>
        <div class="page-sub">Products with significant price drops</div>
      </div>
    </div>""", unsafe_allow_html=True)

    st.markdown('<div style="padding:0 40px 64px;max-width:1400px;margin:0 auto">', unsafe_allow_html=True)

    alerts = _mart("mart_price_alerts")
    if alerts.empty:
        st.markdown("""
        <div style="background:#0d180d;border:1px solid #166534;border-radius:10px;
                    padding:40px;text-align:center;margin:24px 0">
          <div style="font-size:24px;margin-bottom:10px;color:#22c55e">✓</div>
          <div style="font-size:15px;font-weight:600;color:#22c55e;margin-bottom:4px">All prices stable</div>
          <div style="font-size:13px;color:#166534">No significant drops detected</div>
        </div>""", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        return

    pcp = "price_change_pct"
    a1,a2,a3,a4 = st.columns(4)
    with a1: kpi("Total alerts",  str(len(alerts)),                           color="#ef4444")
    with a2: kpi("Biggest drop",  f"{alerts[pcp].min():.1f}%" if pcp in alerts.columns else "—",
                                   color="#f97316")
    with a3: kpi("Sources hit",   str(alerts["source"].nunique()) if "source" in alerts.columns else "—",
                                   color="#fbbf24")
    with a4:
        severe = len(alerts[alerts[pcp]<=-20]) if pcp in alerts.columns else 0
        kpi("Severe ≥20%", str(severe), color="#ef4444")

    if pcp in alerts.columns:
        thr_col, _ = st.columns([2,2])
        with thr_col:
            threshold = st.select_slider(
                "Minimum drop", options=[-5,-10,-15,-20,-25,-30,-50],
                value=-5, format_func=lambda v: f"{v}%")
        alerts_shown = alerts[alerts[pcp] <= threshold].copy()
    else:
        threshold    = -5
        alerts_shown = alerts.copy()

    st.markdown(f'<div style="font-size:12px;color:#3f3f46;margin-bottom:16px">'
                f'{len(alerts_shown)} alerts with drop ≥ {abs(threshold)}%</div>', unsafe_allow_html=True)

    if pcp in alerts.columns:
        sec("Price drops", "worst first")
        for _, row in alerts_shown.sort_values(pcp).head(15).iterrows():
            pct   = row.get(pcp, 0)
            title = str(row.get("title", row.get("product_id","?")))[:70]
            src   = str(row.get("source",""))
            cur_p = row.get("price","")
            prv_p = row.get("prev_price","")
            ac    = "#ef4444" if pct<=-20 else ("#f97316" if pct<=-10 else "#fbbf24")
            m     = src_meta(src)
            prev_str = f"{prv_p:.2f} → {cur_p:.2f}" if isinstance(prv_p, (int,float)) else ""
            st.markdown(f"""
            <div class="alert-row" style="--ac:{ac}">
              <div>
                <div class="alert-product">{title}</div>
                <div class="alert-meta">
                  <span class="src-pill" style="color:{m['color']};border-color:{m['color']}33;background:{m['bg']}">{m['icon']} {m['label']}</span>
                  {('· ' + prev_str) if prev_str else ''}
                </div>
              </div>
              <div class="alert-pct">{pct:.1f}%</div>
            </div>""", unsafe_allow_html=True)

    if pcp in alerts.columns and "source" in alerts.columns and not alerts_shown.empty:
        ca, cb = st.columns([3,2])
        with ca:
            sec("Drop chart", "top 20")
            y_col = "title" if "title" in alerts_shown.columns else "product_id"
            pdata = alerts_shown.head(20).sort_values(pcp).copy()
            pdata[y_col] = pdata[y_col].astype(str).str[:40]
            fig = px.bar(pdata, x=pcp, y=y_col, color="source",
                         color_discrete_map=SOURCE_COLORS, orientation="h",
                         text=pcp, labels={pcp:"Change (%)","":""})
            fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside",
                              marker_line_width=0, opacity=0.85)
            st.plotly_chart(chart(fig, 420), use_container_width=True)

        with cb:
            sec("Severity")
            bins = {
                "Mild (5–10%)":   len(alerts_shown[(alerts_shown[pcp]>-10)  & (alerts_shown[pcp]<=-5)]),
                "Moderate (10–20%)": len(alerts_shown[(alerts_shown[pcp]>-20) & (alerts_shown[pcp]<=-10)]),
                "Severe (≥20%)":  len(alerts_shown[alerts_shown[pcp]<=-20]),
            }
            bins = {k:v for k,v in bins.items() if v>0}
            if bins:
                fp = px.pie(names=list(bins.keys()), values=list(bins.values()),
                            color_discrete_sequence=["#fbbf24","#f97316","#ef4444"], hole=0.6)
                fp.update_traces(textposition="outside", textinfo="percent+label",
                                 textfont=dict(size=10,color="#71717a"),
                                 marker_line_color="#09090b", marker_line_width=2)
                fp.update_layout(showlegend=False)
                st.plotly_chart(chart(fp, 280), use_container_width=True)

    sec("Full alert table", f"{len(alerts_shown)} rows")
    show = [c for c in ["title","source","price","prev_price",pcp,"currency"] if c in alerts_shown.columns]
    st.dataframe(
        alerts_shown[show].reset_index(drop=True) if show else alerts_shown.reset_index(drop=True),
        use_container_width=True, height=340, hide_index=True,
        column_config={
            "price":      st.column_config.NumberColumn("Current", format="%.2f"),
            "prev_price": st.column_config.NumberColumn("Previous", format="%.2f"),
            pcp:          st.column_config.NumberColumn("Change %", format="%.2f"),
        },
    )
    st.markdown("</div>", unsafe_allow_html=True)


# ── Router ─────────────────────────────────────────────────────────────────────
{
    "Live Feed":   page_live,
    "Analytics":   page_kpis,
    "Statistics":  page_stats,
    "Alerts":      page_alerts,
}.get(st.session_state.page, page_live)()

if auto_refresh:
    time.sleep(30)
    st.cache_data.clear()
    st.rerun()
