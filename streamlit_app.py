"""Streamlit web UI for swimchecker amsterdam."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta

import streamlit as st

from pools.base import PoolChecker
from pools.meerkamp import MeerkampChecker
from pools.mercator import MercatorChecker
from pools.mirandabad import MirandabadChecker
from pools.zuiderbad import ZuiderbadChecker

SOURCE_BADGE = {
    "live":        "🟢 live",
    "fallback":    "🟡 fallback",
    "unavailable": "🔴 unavailable",
}


def _fetch_pool(pool: PoolChecker, d: date) -> dict:
    slots, is_live = pool.get_slots(d)
    if is_live:
        source = "live"
    elif pool.has_fallback:
        source = "fallback"
    else:
        source = "unavailable"
    return {
        "name": pool.name,
        "url": pool.url,
        "source": source,
        "slots": [{"start": s.start.strftime("%H:%M"), "end": s.end.strftime("%H:%M")} for s in slots],
    }


@st.cache_data(ttl=300, show_spinner=False)
def fetch_all_pools(d: date) -> list:
    """Fetch slots for all pools on date d; results cached for 5 minutes."""
    pools = [MirandabadChecker(), MercatorChecker(), MeerkampChecker(), ZuiderbadChecker()]
    results = [None] * len(pools)
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(_fetch_pool, pool, d): (i, pool) for i, pool in enumerate(pools)}
        for future in as_completed(futures):
            idx, pool = futures[future]
            try:
                results[idx] = future.result()
            except Exception:
                results[idx] = {
                    "name": pool.name,
                    "url": pool.url,
                    "source": "unavailable",
                    "slots": [],
                }
    return results


st.set_page_config(
    page_title="swimchecker amsterdam",
    page_icon="🏊",
    layout="centered",
)

# ── Initialise session state ──────────────────────────────────────────────────
if "selected_date" not in st.session_state:
    st.session_state.selected_date = date.today()

# ── Header ────────────────────────────────────────────────────────────────────
st.title("🏊 swimchecker amsterdam")
st.caption("Lane swimming (baanzwemmen) schedules for Amsterdam pools")

# ── Date navigation ───────────────────────────────────────────────────────────
col_prev, col_today, col_next = st.columns(3)
with col_prev:
    if st.button("← Prev", use_container_width=True):
        st.session_state.selected_date -= timedelta(days=1)
with col_today:
    if st.button("Today", use_container_width=True):
        st.session_state.selected_date = date.today()
with col_next:
    if st.button("Next →", use_container_width=True):
        st.session_state.selected_date += timedelta(days=1)

# date_input uses "selected_date" as its key — reads/writes the same session state
# as the buttons, so no reconciliation needed
d = st.date_input(
    "Select date",
    key="selected_date",
    label_visibility="collapsed",
)

# ── Day label ─────────────────────────────────────────────────────────────────
today = date.today()
if d == today:
    day_label = f"Today — {d.strftime('%A, %d %b %Y')}"
elif d == today + timedelta(days=1):
    day_label = f"Tomorrow — {d.strftime('%A, %d %b %Y')}"
else:
    day_label = d.strftime("%A, %d %b %Y")

st.subheader(day_label)
st.divider()

# ── Fetch & display ───────────────────────────────────────────────────────────
with st.spinner("Fetching schedules…"):
    pool_results = fetch_all_pools(d)

cols = st.columns(2)
for i, pool in enumerate(pool_results):
    with cols[i % 2]:
        source = pool["source"]
        with st.container(border=True):
            st.markdown(f"**[{pool['name']}]({pool['url']})**")
            st.caption(SOURCE_BADGE[source])
            if pool["slots"]:
                for slot in pool["slots"]:
                    st.write(f"🕐 {slot['start']} – {slot['end']}")
            else:
                st.write("_No lane swimming today_" if source != "unavailable" else "_Schedule unavailable_")
