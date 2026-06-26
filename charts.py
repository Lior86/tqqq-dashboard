# charts.py
# Builds every Plotly chart. Returns fig objects — no Streamlit calls here.
# app.py calls these and passes the figs to st.plotly_chart().

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from config import EMA_SHORT, EMA_LONG, VOLUME_SPIKE_MULTIPLIER


# Shared dark theme colors
BG_COLOR       = "#0e1117"
PAPER_COLOR    = "#0e1117"
GRID_COLOR     = "#1e2530"
TEXT_COLOR     = "#c9d1d9"
GREEN          = "#00c896"
RED            = "#ff4b6e"
YELLOW         = "#f0c040"
BLUE           = "#4da6ff"
ORANGE         = "#ff9f43"
PURPLE         = "#a78bfa"

CANDLE_UP      = "#00c896"
CANDLE_DOWN    = "#ff4b6e"
EMA_SHORT_CLR  = "#f0c040"
EMA_LONG_CLR   = "#a78bfa"


def _base_layout(title: str, height: int = 420) -> dict:
    """Shared Plotly layout settings for dark theme consistency."""
    return dict(
        title=dict(text=title, font=dict(color=TEXT_COLOR, size=14)),
        paper_bgcolor=PAPER_COLOR,
        plot_bgcolor=BG_COLOR,
        font=dict(color=TEXT_COLOR),
        height=height,
        margin=dict(l=10, r=10, t=40, b=10),
        xaxis=dict(
            gridcolor=GRID_COLOR,
            showgrid=True,
            rangeslider=dict(visible=False),
            color=TEXT_COLOR,
        ),
        yaxis=dict(
            gridcolor=GRID_COLOR,
            showgrid=True,
            color=TEXT_COLOR,
            side="right",
        ),
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            bordercolor=GRID_COLOR,
            font=dict(color=TEXT_COLOR),
        ),
        hovermode="x unified",
    )


def chart_candlestick(df: pd.DataFrame) -> go.Figure:
    """
    Candlestick chart with EMA50 and EMA200 overlaid.
    Volume spike days are marked with triangle markers at the top.
    """
    fig = go.Figure()

    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df["Open"], high=df["High"],
        low=df["Low"],   close=df["Close"],
        increasing_line_color=CANDLE_UP,
        decreasing_line_color=CANDLE_DOWN,
        name="TQQQ",
        increasing_fillcolor=CANDLE_UP,
        decreasing_fillcolor=CANDLE_DOWN,
    ))

    ema_s_col = f"EMA{EMA_SHORT}"
    if ema_s_col in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index, y=df[ema_s_col],
            line=dict(color=EMA_SHORT_CLR, width=1.5),
            name=f"EMA {EMA_SHORT}",
        ))

    ema_l_col = f"EMA{EMA_LONG}"
    if ema_l_col in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index, y=df[ema_l_col],
            line=dict(color=EMA_LONG_CLR, width=1.5),
            name=f"EMA {EMA_LONG}",
        ))

    if "VolumeSpike" in df.columns:
        spikes = df[df["VolumeSpike"]]
        if not spikes.empty:
            fig.add_trace(go.Scatter(
                x=spikes.index,
                y=spikes["High"] * 1.015,
                mode="markers",
                marker=dict(symbol="triangle-down", color=ORANGE, size=10),
                name="Volume Spike",
                hovertemplate="Volume Spike<br>%{x}<extra></extra>",
            ))

    if "DarkPoolSignal" in df.columns:
        dp = df[df["DarkPoolSignal"]]
        if not dp.empty:
            fig.add_trace(go.Scatter(
                x=dp.index,
                y=dp["Low"] * 0.985,
                mode="markers",
                marker=dict(symbol="circle", color=PURPLE, size=8, opacity=0.85),
                name="Dark Pool Signal",
                hovertemplate="Dark Pool Signal<br>%{x}<extra></extra>",
            ))

    layout = _base_layout("TQQQ — Price & EMAs", height=500)
    layout["xaxis"]["rangeslider"] = dict(visible=False)
    fig.update_layout(**layout)
    return fig


def chart_volume(df: pd.DataFrame) -> go.Figure:
    """
    Volume bar chart.
    Spike days are highlighted in orange, normal days in a muted blue.
    20-day average volume shown as a line.
    """
    fig = go.Figure()

    colors = [ORANGE if spike else "#3a4a6b"
              for spike in df.get("VolumeSpike", [False] * len(df))]

    fig.add_trace(go.Bar(
        x=df.index, y=df["Volume"],
        marker_color=colors,
        name="Volume",
        hovertemplate="%{x}<br>Volume: %{y:,.0f}<extra></extra>",
    ))

    if "Volume20Avg" in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index, y=df["Volume20Avg"],
            line=dict(color=YELLOW, width=1.5, dash="dot"),
            name="20-Day Avg",
            hovertemplate="%{x}<br>Avg: %{y:,.0f}<extra></extra>",
        ))

    fig.update_layout(**_base_layout("Volume — Spikes Highlighted", height=280))
    return fig


def chart_obv(df: pd.DataFrame) -> go.Figure:
    """
    OBV line chart with a 20-day EMA overlay.
    When OBV crosses above its EMA = accumulation confirmed.
    When OBV crosses below its EMA = distribution signal.
    """
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df.index, y=df["OBV"],
        line=dict(color=BLUE, width=2),
        fill="tozeroy",
        fillcolor="rgba(77,166,255,0.08)",
        name="OBV",
    ))
    if "OBVEMA" in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index, y=df["OBVEMA"],
            line=dict(color=ORANGE, width=1.5, dash="dot"),
            name="OBV EMA (20)",
        ))
    fig.update_layout(**_base_layout("On Balance Volume (OBV) + EMA", height=260))
    return fig


def chart_rsi(df: pd.DataFrame) -> go.Figure:
    """RSI with overbought/oversold reference lines."""
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df.index, y=df["RSI"],
        line=dict(color=GREEN, width=2),
        name="RSI",
    ))

    fig.add_hrect(y0=70, y1=100, fillcolor="rgba(255,75,110,0.08)",
                  line_width=0, annotation_text="Overbought",
                  annotation_position="top right",
                  annotation=dict(font_color=RED, font_size=11))
    fig.add_hrect(y0=0, y1=30, fillcolor="rgba(0,200,150,0.08)",
                  line_width=0, annotation_text="Oversold",
                  annotation_position="bottom right",
                  annotation=dict(font_color=GREEN, font_size=11))
    fig.add_hline(y=70, line_dash="dot", line_color=RED,   line_width=1)
    fig.add_hline(y=30, line_dash="dot", line_color=GREEN, line_width=1)

    layout = _base_layout("RSI (14)", height=260)
    layout["yaxis"]["range"] = [0, 100]
    fig.update_layout(**layout)
    return fig


def chart_macd(df: pd.DataFrame) -> go.Figure:
    """
    MACD with signal line and histogram.
    Positive histogram bars = green, negative = red.
    """
    fig = go.Figure()

    hist_colors = [GREEN if v >= 0 else RED for v in df["MACDHist"].fillna(0)]

    fig.add_trace(go.Bar(
        x=df.index, y=df["MACDHist"],
        marker_color=hist_colors,
        name="Histogram",
        opacity=0.7,
    ))
    fig.add_trace(go.Scatter(
        x=df.index, y=df["MACD"],
        line=dict(color=BLUE, width=2),
        name="MACD",
    ))
    fig.add_trace(go.Scatter(
        x=df.index, y=df["MACDSignal"],
        line=dict(color=ORANGE, width=1.5),
        name="Signal",
    ))
    fig.add_hline(y=0, line_color=GRID_COLOR, line_width=1)

    fig.update_layout(**_base_layout("MACD (12, 26, 9)", height=260))
    return fig


def chart_cmf(df: pd.DataFrame) -> go.Figure:
    """
    Chaikin Money Flow chart.
    Bars above zero = buying pressure (accumulation).
    Bars below zero = selling pressure (distribution).
    +0.1 / -0.1 reference lines mark meaningful thresholds.
    """
    fig = go.Figure()

    cmf_colors = [GREEN if v >= 0 else RED for v in df["CMF"].fillna(0)]

    fig.add_trace(go.Bar(
        x=df.index,
        y=df["CMF"],
        marker_color=cmf_colors,
        opacity=0.75,
        name="CMF (20)",
        hovertemplate="%{x}<br>CMF: %{y:.3f}<extra></extra>",
    ))

    fig.add_hline(y=0, line_color=GRID_COLOR, line_width=1)

    fig.add_hline(y=0.1,  line_dash="dot", line_color=GREEN, line_width=1,
                  annotation_text="+0.1 Accumulation", annotation_position="top left",
                  annotation=dict(font_color=GREEN, font_size=10))
    fig.add_hline(y=-0.1, line_dash="dot", line_color=RED, line_width=1,
                  annotation_text="-0.1 Distribution", annotation_position="bottom left",
                  annotation=dict(font_color=RED, font_size=10))

    layout = _base_layout("Chaikin Money Flow (CMF 20)", height=260)
    layout["yaxis"]["range"] = [-1, 1]
    fig.update_layout(**layout)
    return fig