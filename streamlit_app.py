"""Streamlit web UI for swimchecker amsterdam."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta

import streamlit as st

from pools.base import PoolChecker
from pools.meerkamp import MeerkampChecker
from pools.mercator import MercatorChecker
from pools.mirandabad import MirandabadChecker
from pools.zuiderbad import ZuiderbadChecker

# ── Design ────────────────────────────────────────────────────────────────────

_CSS = """
<style>
/* ── Page ────────────────────────────────────────────────────────────────── */
.stApp { background: #eef5fb; }
.main .block-container { padding-top: 2rem; max-width: 800px; }
footer { visibility: hidden; }

/* ── Header ──────────────────────────────────────────────────────────────── */
.sc-header {
  text-align: center;
  padding-bottom: 0.25rem;
}
.sc-header h1 {
  font-size: 2rem;
  font-weight: 800;
  color: #18375a;
  margin: 0 0 0.25rem;
  letter-spacing: -0.5px;
}
.sc-header p {
  color: #6a9cbd;
  font-size: 0.95rem;
  margin: 0 0 1.5rem;
}

/* ── Nav buttons ─────────────────────────────────────────────────────────── */
.stButton > button {
  border-radius: 10px;
  border: 1.5px solid #cce0ef;
  background: #ffffff;
  color: #18375a;
  font-weight: 600;
  font-size: 0.9rem;
  padding: 0.45rem 0.75rem;
  width: 100%;
  transition: background 0.15s, border-color 0.15s, color 0.15s;
}
.stButton > button:hover {
  background: #dff0f8;
  border-color: #0080a8;
  color: #005f80;
}
.stButton > button:active {
  background: #cce0ef;
}

/* ── Date input ──────────────────────────────────────────────────────────── */
.stDateInput > div > div > input {
  border-radius: 10px;
  border-color: #cce0ef;
  text-align: center;
  font-weight: 500;
  color: #18375a;
  background: #ffffff;
}

/* ── Day label ───────────────────────────────────────────────────────────── */
.sc-day-label {
  text-align: center;
  font-size: 1.1rem;
  font-weight: 600;
  color: #18375a;
  padding: 0.6rem 0 1rem;
}

/* ── Pool card ───────────────────────────────────────────────────────────── */
.sc-card {
  background: #ffffff;
  border: 1.5px solid #cce0ef;
  border-radius: 14px;
  padding: 1.1rem 1.2rem 1.15rem;
  box-shadow: 0 2px 12px rgba(0,60,100,.07), 0 1px 3px rgba(0,60,100,.05);
  margin-bottom: 1rem;
  min-height: 130px;
}
.sc-card-name {
  font-size: 1rem;
  font-weight: 700;
  margin: 0 0 0.55rem;
}
.sc-card-name a {
  color: #0080a8;
  text-decoration: none;
}
.sc-card-name a:hover { text-decoration: underline; }

/* ── Source badge ────────────────────────────────────────────────────────── */
.sc-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.74rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  padding: 0.22rem 0.65rem;
  border-radius: 20px;
  margin-bottom: 0.85rem;
}
.sc-badge-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  display: inline-block;
}
.sc-live        { background: #d9f5ed; color: #006e48; }
.sc-live        .sc-badge-dot { background: #00a87a; }
.sc-fallback    { background: #fdf0d5; color: #8a5800; }
.sc-fallback    .sc-badge-dot { background: #c07800; }
.sc-unavailable { background: #fce8e8; color: #9e2828; }
.sc-unavailable .sc-badge-dot { background: #c43a3a; }

/* ── Time-slot chips ─────────────────────────────────────────────────────── */
.sc-slots {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  margin-top: 0.1rem;
}
.sc-slot {
  background: #dff0f8;
  color: #18375a;
  border-radius: 8px;
  padding: 0.3rem 0.7rem;
  font-size: 0.88rem;
  font-weight: 500;
  white-space: nowrap;
}
.sc-no-slots {
  color: #8aaec6;
  font-size: 0.88rem;
  font-style: italic;
  padding-top: 0.1rem;
}
</style>
"""

_BADGE_CLASS = {"live": "sc-live", "fallback": "sc-fallback", "unavailable": "sc-unavailable"}
_BADGE_LABEL = {"live": "Live", "fallback": "Fallback", "unavailable": "Unavailable"}


def _pool_card(pool: dict) -> str:
    source = pool["source"]
    badge_cls = _BADGE_CLASS[source]
    badge_txt = _BADGE_LABEL[source]

    if pool["slots"]:
        chips = "".join(
            f'<span class="sc-slot">🕐 {s["start"]} – {s["end"]}</span>'
            for s in pool["slots"]
        )
        body = f'<div class="sc-slots">{chips}</div>'
    elif source == "unavailable":
        body = '<div class="sc-no-slots">Schedule unavailable</div>'
    else:
        body = '<div class="sc-no-slots">No lane swimming today</div>'

    return (
        f'<div class="sc-card">'
        f'  <div class="sc-card-name"><a href="{pool["url"]}" target="_blank">{pool["name"]}</a></div>'
        f'  <span class="sc-badge {badge_cls}"><span class="sc-badge-dot"></span>{badge_txt}</span>'
        f'  {body}'
        f'</div>'
    )


# ── Data ──────────────────────────────────────────────────────────────────────

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


# ── App ───────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="swimchecker amsterdam",
    page_icon="🏊",
    layout="centered",
)
st.markdown(_CSS, unsafe_allow_html=True)

# ── Initialise session state ──────────────────────────────────────────────────
if "selected_date" not in st.session_state:
    st.session_state.selected_date = date.today()

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(
    '<div class="sc-header">'
    "<h1>🏊 swimchecker amsterdam</h1>"
    "<p>Lane swimming (baanzwemmen) schedules for Amsterdam pools</p>"
    "</div>",
    unsafe_allow_html=True,
)

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
d = st.date_input("Select date", key="selected_date", label_visibility="collapsed")

# ── Day label ─────────────────────────────────────────────────────────────────
today = date.today()
if d == today:
    day_label = f"Today &mdash; {d.strftime('%A, %d %b %Y')}"
elif d == today + timedelta(days=1):
    day_label = f"Tomorrow &mdash; {d.strftime('%A, %d %b %Y')}"
else:
    day_label = d.strftime("%A, %d %b %Y")

st.markdown(f'<div class="sc-day-label">{day_label}</div>', unsafe_allow_html=True)

# ── Fetch & display ───────────────────────────────────────────────────────────
with st.spinner("Fetching schedules…"):
    pool_results = fetch_all_pools(d)

col_left, col_right = st.columns(2)
for i, pool in enumerate(pool_results):
    col = col_left if i % 2 == 0 else col_right
    with col:
        st.markdown(_pool_card(pool), unsafe_allow_html=True)
