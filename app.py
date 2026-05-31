# app.py
# Main Streamlit app. Wires everything together.
# All logic lives in the other files — this file is layout and rendering only.

import streamlit as st
import pandas as pd
from config import TICKER, APP_TITLE, APP_ICON, TIMEFRAMES, DEFAULT_TIMEFRAME, EMA_SHORT, EMA_LONG
from data import fetch_data
from indicators import compute_all
from signals import get_all_signals
from charts import (
    chart_candlestick,
    chart_volume,
    chart_obv,
    chart_rsi,
    chart_macd,
)

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title=APP_TITLE,
    page_icon=APP_ICON,
    layout="wide",
)

# ── Minimal custom CSS ────────────────────────────────────────────────────────
st.markdown("""
<style>
    .signal-card {
        border-radius: 8px;
        padding: 12px 16px;
        margin-bottom: 8px;
        font-size: 14px;
        line-height: 1.5;
    }
    .signal-green  { background: rgba(0,200,150,0.12);  border-left: 4px solid #00c896; }
    .signal-yellow { background: rgba(240,192,64,0.12); border-left: 4px solid #f0c040; }
    .signal-red    { background: rgba(255,75,110,0.12); border-left: 4px solid #ff4b6e; }
    .signal-label  { font-weight: 600; margin-bottom: 4px; color: #c9d1d9; }
    .signal-msg    { color: #8b98a8; }
    div[data-testid="stHorizontalBlock"] button {
        border-radius: 6px !important;
    }
</style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────────
st.title(f"{APP_ICON} {APP_TITLE}")
st.caption("Real-time technical analysis dashboard for TQQQ. Data via Yahoo Finance.")

st.divider()

# ── Timeframe selector ────────────────────────────────────────────────────────
st.subheader("Timeframe")
tf_labels = list(TIMEFRAMES.keys())

if "selected_tf" not in st.session_state:
    st.session_state.selected_tf = DEFAULT_TIMEFRAME

cols = st.columns(len(tf_labels))
for i, label in enumerate(tf_labels):
    with cols[i]:
        if st.button(label, use_container_width=True,
                     type="primary" if label == st.session_state.selected_tf else "secondary"):
            st.session_state.selected_tf = label
            st.rerun()

selected_period = TIMEFRAMES[st.session_state.selected_tf]

# ── Data fetch + indicator computation ───────────────────────────────────────
with st.spinner("Loading TQQQ data..."):
    try:
        raw_df = fetch_data(selected_period)
        df     = compute_all(raw_df)
    except (RuntimeError, ValueError) as e:
        st.error(f"Data error: {e}")
        st.stop()

# ── Quick stats bar ───────────────────────────────────────────────────────────
latest      = df.iloc[-1]
prev        = df.iloc[-2] if len(df) >= 2 else df.iloc[-1]
price_chg   = latest["Close"] - prev["Close"]
price_chg_p = price_chg / prev["Close"] * 100
rsi_val     = df["RSI"].dropna().iloc[-1] if "RSI" in df.columns else None
vol_ratio   = df["VolumeRatio"].dropna().iloc[-1] if "VolumeRatio" in df.columns else None

stat1, stat2, stat3, stat4, stat5 = st.columns(5)
with stat1:
    st.metric("Last Price", f"${latest['Close']:.2f}",
              f"{price_chg:+.2f} ({price_chg_p:+.2f}%)")
with stat2:
    st.metric("Volume", f"{int(latest['Volume']):,}")
with stat3:
    st.metric("RSI (14)", f"{rsi_val:.1f}" if rsi_val else "—")
with stat4:
    st.metric("Vol / 20D Avg", f"{vol_ratio:.2f}x" if vol_ratio else "—",
              "SPIKE" if (vol_ratio and vol_ratio >= 2) else None,
              delta_color="off" if not (vol_ratio and vol_ratio >= 2) else "normal")
with stat5:
    inst_score = df["InstitutionalScore"].dropna().iloc[-1] \
                 if "InstitutionalScore" in df.columns else 0
    score_label = "None" if inst_score == 0 else ("Moderate" if inst_score < 4 else "Strong")
    st.metric("Institutional Signal", score_label)

st.divider()

# ── Main layout: charts left, signals right ───────────────────────────────────
chart_col, signal_col = st.columns([3, 1], gap="large")

with chart_col:

    # Candlestick + EMAs
    st.plotly_chart(chart_candlestick(df), use_container_width=True)

    # Volume
    st.plotly_chart(chart_volume(df), use_container_width=True)

    # OBV + RSI side by side
    obv_col, rsi_col = st.columns(2)
    with obv_col:
        st.plotly_chart(chart_obv(df), use_container_width=True)
    with rsi_col:
        st.plotly_chart(chart_rsi(df), use_container_width=True)

    # MACD
    st.plotly_chart(chart_macd(df), use_container_width=True)


with signal_col:
    st.subheader("📊 Daily Signals")
    st.caption(f"Based on the most recent session. Last close: ${latest['Close']:.2f}")

    signals = get_all_signals(df)

    for sig in signals:
        status = sig["status"]        # "green" / "yellow" / "red"
        label  = sig["label"]
        msg    = sig["message"]

        icon = "🟢" if status == "green" else ("🟡" if status == "yellow" else "🔴")

        st.markdown(
            f"""
            <div class="signal-card signal-{status}">
                <div class="signal-label">{icon} {label}</div>
                <div class="signal-msg">{msg}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.divider()

    # Raw data expander at the bottom of the signal column
    with st.expander("Raw Data (last 10 rows)"):
        display_cols = ["Open", "High", "Low", "Close", "Volume",
                        f"EMA{EMA_SHORT}", f"EMA{EMA_LONG}",
                        "RSI", "MACD", "VolumeRatio", "InstitutionalScore"]
        display_cols = [c for c in display_cols if c in df.columns]
        st.dataframe(
            df[display_cols].tail(10).style.format({
                "Open": "${:.2f}", "High": "${:.2f}", "Low": "${:.2f}", "Close": "${:.2f}",
                f"EMA{EMA_SHORT}": "${:.2f}", f"EMA{EMA_LONG}": "${:.2f}",
                "RSI": "{:.1f}", "MACD": "{:.4f}",
                "VolumeRatio": "{:.2f}x", "InstitutionalScore": "{:.0f}",
                "Volume": "{:,.0f}",
            }),
            use_container_width=True,
        )

# ── Footer ────────────────────────────────────────────────────────────────────
st.divider()
st.caption(
    "⚠️ This dashboard is for informational purposes only and does not constitute "
    "financial advice. TQQQ is a leveraged ETF — it carries significant risk. "
    "Always do your own research before trading."
)