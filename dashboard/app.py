"""
Streamlit dashboard — placeholder (Phase 7).
"""

import streamlit as st

st.set_page_config(
    page_title="Price Intelligence Platform",
    page_icon="📊",
    layout="wide",
)

st.title("📊 Real-Time E-commerce Price Intelligence Platform")
st.info("Dashboard coming in Phase 7. Run `make up` to start backend services.")

st.markdown("""
### Planned Pages
- **Page 1** — Live prices (auto-refresh from Bigtable)
- **Page 2** — Historical KPIs from dbt marts
- **Page 3** — Statistical analysis results
- **Page 4** — Price alerts (>5% change in 24h)
""")
