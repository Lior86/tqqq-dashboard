# signals.py
# Translates raw indicator values into plain-English summaries.
# Each function returns a dict with: label, status ("green"/"yellow"/"red"), and message.
# app.py renders these as colored cards — this file has no UI code.

import pandas as pd
from config import RSI_OVERBOUGHT, RSI_OVERSOLD, EMA_SHORT, EMA_LONG


def _latest(df: pd.DataFrame, col: str):
    """Return the most recent non-NaN value for a column."""
    series = df[col].dropna()
    return series.iloc[-1] if not series.empty else None


def signal_trend(df: pd.DataFrame) -> dict:
    close    = _latest(df, "Close")
    ema_s    = _latest(df, f"EMA{EMA_SHORT}")
    ema_l    = _latest(df, f"EMA{EMA_LONG}")

    if None in (close, ema_s, ema_l):
        return {"label": "Trend (EMA)", "status": "yellow",
                "message": "Not enough data to assess trend."}

    if close > ema_s > ema_l:
        return {"label": "Trend (EMA)", "status": "green",
                "message": f"Price (${close:.2f}) is above both the 50 EMA (${ema_s:.2f}) "
                           f"and 200 EMA (${ema_l:.2f}). Uptrend intact."}
    elif close < ema_s < ema_l:
        return {"label": "Trend (EMA)", "status": "red",
                "message": f"Price (${close:.2f}) is below both the 50 EMA (${ema_s:.2f}) "
                           f"and 200 EMA (${ema_l:.2f}). Downtrend in place."}
    else:
        return {"label": "Trend (EMA)", "status": "yellow",
                "message": f"Price (${close:.2f}) is between the 50 EMA (${ema_s:.2f}) "
                           f"and 200 EMA (${ema_l:.2f}). No clear trend direction."}


def signal_rsi(df: pd.DataFrame) -> dict:
    rsi = _latest(df, "RSI")

    if rsi is None:
        return {"label": "RSI", "status": "yellow", "message": "RSI not yet calculated."}

    if rsi >= RSI_OVERBOUGHT:
        return {"label": "RSI", "status": "red",
                "message": f"RSI is {rsi:.1f} — overbought territory (above {RSI_OVERBOUGHT}). "
                           "Pullback or consolidation likely."}
    elif rsi <= RSI_OVERSOLD:
        return {"label": "RSI", "status": "red",
                "message": f"RSI is {rsi:.1f} — oversold territory (below {RSI_OVERSOLD}). "
                           "Possible bounce, but downtrend could continue."}
    elif rsi >= 65:
        return {"label": "RSI", "status": "yellow",
                "message": f"RSI is {rsi:.1f} — elevated but not yet overbought. "
                           "Watch for a turn above 70."}
    elif rsi <= 40:
        return {"label": "RSI", "status": "yellow",
                "message": f"RSI is {rsi:.1f} — weak momentum. "
                           "Not oversold yet, but showing softness."}
    else:
        return {"label": "RSI", "status": "green",
                "message": f"RSI is {rsi:.1f} — healthy range. "
                           "Momentum is present without being stretched."}


def signal_macd(df: pd.DataFrame) -> dict:
    macd     = _latest(df, "MACD")
    signal   = _latest(df, "MACDSignal")
    hist_now = _latest(df, "MACDHist")

    if None in (macd, signal, hist_now):
        return {"label": "MACD", "status": "yellow", "message": "MACD not yet calculated."}

    hist_series = df["MACDHist"].dropna()
    hist_prev   = hist_series.iloc[-2] if len(hist_series) >= 2 else hist_now
    expanding   = abs(hist_now) > abs(hist_prev)

    if macd > signal and expanding:
        return {"label": "MACD", "status": "green",
                "message": f"MACD ({macd:.3f}) is above the signal line ({signal:.3f}) "
                           "and momentum is accelerating. Bullish."}
    elif macd > signal and not expanding:
        return {"label": "MACD", "status": "yellow",
                "message": f"MACD ({macd:.3f}) is above signal ({signal:.3f}) "
                           "but momentum is slowing. Possible trend fade."}
    else:
        return {"label": "MACD", "status": "red",
                "message": f"MACD ({macd:.3f}) is below the signal line ({signal:.3f}). "
                           "Bearish momentum."}


def signal_volume(df: pd.DataFrame) -> dict:
    if "VolumeSpike" not in df.columns or "VolumeRatio" not in df.columns:
        return {"label": "Volume", "status": "yellow", "message": "Volume data unavailable."}

    latest    = df.dropna(subset=["VolumeRatio"]).iloc[-1]
    is_spike  = latest["VolumeSpike"]
    ratio     = latest["VolumeRatio"]
    price_chg = (latest["Close"] - df["Close"].iloc[-2]) / df["Close"].iloc[-2] * 100 \
                if len(df) >= 2 else 0

    if not is_spike:
        return {"label": "Volume", "status": "green",
                "message": f"Volume is normal ({ratio:.1f}x the 20-day average). "
                           "No unusual activity."}
    elif is_spike and price_chg > 0.5:
        return {"label": "Volume", "status": "green",
                "message": f"Volume spike detected ({ratio:.1f}x average) on an UP day. "
                           "Bullish accumulation signal."}
    elif is_spike and price_chg < -0.5:
        return {"label": "Volume", "status": "red",
                "message": f"Volume spike ({ratio:.1f}x average) on a DOWN day. "
                           "Possible distribution — institutions may be selling."}
    else:
        return {"label": "Volume", "status": "yellow",
                "message": f"Volume spike ({ratio:.1f}x average) but price barely moved. "
                           "Could be absorption or indecision."}


def signal_obv(df: pd.DataFrame) -> dict:
    if "OBV" not in df.columns:
        return {"label": "OBV", "status": "yellow", "message": "OBV not calculated."}

    lookback   = min(10, len(df) - 1)
    obv_now    = df["OBV"].iloc[-1]
    obv_then   = df["OBV"].iloc[-lookback]
    price_now  = df["Close"].iloc[-1]
    price_then = df["Close"].iloc[-lookback]

    obv_rising   = obv_now > obv_then
    price_rising = price_now > price_then

    if obv_rising and price_rising:
        return {"label": "OBV", "status": "green",
                "message": "OBV and price are both rising — volume is confirming the uptrend."}
    elif not obv_rising and not price_rising:
        return {"label": "OBV", "status": "red",
                "message": "OBV and price are both falling — volume confirms the downtrend."}
    elif obv_rising and not price_rising:
        return {"label": "OBV", "status": "yellow",
                "message": "OBV is rising while price is falling. "
                           "Possible accumulation — bullish divergence."}
    else:
        return {"label": "OBV", "status": "yellow",
                "message": "OBV is falling while price is rising. "
                           "Volume not confirming the move — bearish divergence. Watch closely."}


def signal_institutional(df: pd.DataFrame) -> dict:
    if "InstitutionalScore" not in df.columns:
        return {"label": "Institutional Activity", "status": "yellow",
                "message": "Institutional score not available."}

    score  = _latest(df, "InstitutionalScore")
    dark   = _latest(df, "DarkPoolSignal")
    absorb = _latest(df, "AbsorptionSignal")

    notes = []
    if dark:
        notes.append("tight-range high-volume candle (dark pool proxy)")
    if absorb:
        notes.append("price barely moved on elevated volume (absorption)")

    note_str = " and ".join(notes) if notes else "elevated volume"

    if score >= 4:
        return {"label": "Institutional Activity", "status": "yellow",
                "message": f"Strong institutional signal detected ({note_str}). "
                           "Large players may be positioning. Direction unclear — watch price action."}
    elif score >= 2:
        return {"label": "Institutional Activity", "status": "yellow",
                "message": f"Moderate institutional activity ({note_str}). "
                           "Worth monitoring but not conclusive."}
    else:
        return {"label": "Institutional Activity", "status": "green",
                "message": "No unusual institutional footprint detected in the latest session."}


def signal_cmf(df: pd.DataFrame) -> dict:
    if "CMF" not in df.columns:
        return {"label": "CMF (20)", "status": "yellow", "message": "CMF not calculated."}

    cmf = _latest(df, "CMF")
    if cmf is None:
        return {"label": "CMF (20)", "status": "yellow", "message": "Not enough data for CMF."}

    if cmf >= 0.1:
        return {"label": "CMF (20)", "status": "green",
                "message": f"CMF is {cmf:.3f} — above +0.1. Volume is weighted toward closes "
                           "near the HIGH of the day. Accumulation signal."}
    elif cmf <= -0.1:
        return {"label": "CMF (20)", "status": "red",
                "message": f"CMF is {cmf:.3f} — below -0.1. Volume is weighted toward closes "
                           "near the LOW of the day. Distribution signal."}
    else:
        return {"label": "CMF (20)", "status": "yellow",
                "message": f"CMF is {cmf:.3f} — in neutral territory (-0.1 to +0.1). "
                           "No strong conviction from money flow. Watch for a break either way."}


def signal_quiet_drift(df: pd.DataFrame) -> dict:
    if "QuietDriftSignal" not in df.columns or "QuietDriftDay" not in df.columns:
        return {"label": "Quiet Drift", "status": "yellow",
                "message": "Quiet drift data not available."}

    signal_active = df["QuietDriftSignal"].iloc[-1]
    streak_days   = int(df["QuietDriftDay"].astype(int).iloc[-5:].sum())

    if signal_active:
        return {"label": "Quiet Drift", "status": "green",
                "message": f"Quiet drift detected — {streak_days} of the last 5 days showed "
                           "below-average volume with a small price gain. "
                           "Possible institutional stealth accumulation."}
    else:
        return {"label": "Quiet Drift", "status": "yellow",
                "message": "No quiet drift pattern detected. Volume and price action "
                           "are not showing the low-volume creep associated with stealth accumulation."}


def get_all_signals(df: pd.DataFrame) -> list:
    return [
        signal_trend(df),
        signal_rsi(df),
        signal_macd(df),
        signal_volume(df),
        signal_obv(df),
        signal_institutional(df),
        signal_cmf(df),
        signal_quiet_drift(df),
    ]