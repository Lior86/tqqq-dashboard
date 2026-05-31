# indicators.py
# Calculates every technical indicator the dashboard needs.
# All functions take a DataFrame (from data.py) and return it with new columns added.
# Nothing here touches Streamlit or Plotly — pure data transformation only.

import pandas as pd
import numpy as np
from config import (
    EMA_SHORT, EMA_LONG,
    VOLUME_AVG_WINDOW, VOLUME_SPIKE_MULTIPLIER,
    RSI_PERIOD, MACD_FAST, MACD_SLOW, MACD_SIGNAL,
    DARK_POOL_VOLUME_THRESHOLD, DARK_POOL_RANGE_THRESHOLD,
    ABSORPTION_VOLUME_MULTIPLIER, ABSORPTION_PRICE_MOVE_MAX,
)


def add_emas(df: pd.DataFrame) -> pd.DataFrame:
    """Add EMA_SHORT and EMA_LONG columns."""
    df = df.copy()
    df[f"EMA{EMA_SHORT}"] = df["Close"].ewm(span=EMA_SHORT, adjust=False).mean()
    df[f"EMA{EMA_LONG}"]  = df["Close"].ewm(span=EMA_LONG,  adjust=False).mean()
    return df


def add_obv(df: pd.DataFrame) -> pd.DataFrame:
    """
    On Balance Volume: running total that adds volume on up days,
    subtracts on down days. Helps detect accumulation/distribution.
    """
    df = df.copy()
    direction = np.sign(df["Close"].diff()).fillna(0)
    df["OBV"] = (direction * df["Volume"]).cumsum()
    return df


def add_volume_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adds:
    - Volume20Avg: rolling 20-day average volume
    - VolumeRatio: today's volume / 20-day avg (ratio > 2 = spike)
    - VolumeSpike: boolean flag for days 2x+ above average
    """
    df = df.copy()
    df["Volume20Avg"] = df["Volume"].rolling(VOLUME_AVG_WINDOW).mean()
    df["VolumeRatio"] = df["Volume"] / df["Volume20Avg"]
    df["VolumeSpike"] = df["VolumeRatio"] >= VOLUME_SPIKE_MULTIPLIER
    return df


def add_rsi(df: pd.DataFrame) -> pd.DataFrame:
    """
    RSI (Relative Strength Index) using Wilder's smoothing method.
    Values above 70 = overbought, below 30 = oversold.
    """
    df = df.copy()
    delta = df["Close"].diff()
    gain  = delta.clip(lower=0)
    loss  = (-delta).clip(lower=0)

    avg_gain = gain.ewm(com=RSI_PERIOD - 1, min_periods=RSI_PERIOD).mean()
    avg_loss = loss.ewm(com=RSI_PERIOD - 1, min_periods=RSI_PERIOD).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    df["RSI"] = 100 - (100 / (1 + rs))
    return df


def add_macd(df: pd.DataFrame) -> pd.DataFrame:
    """
    MACD line, Signal line, and Histogram.
    Bullish crossover = MACD crosses above Signal.
    """
    df = df.copy()
    ema_fast   = df["Close"].ewm(span=MACD_FAST,   adjust=False).mean()
    ema_slow   = df["Close"].ewm(span=MACD_SLOW,   adjust=False).mean()
    df["MACD"]        = ema_fast - ema_slow
    df["MACDSignal"]  = df["MACD"].ewm(span=MACD_SIGNAL, adjust=False).mean()
    df["MACDHist"]    = df["MACD"] - df["MACDSignal"]
    return df


def add_dark_pool_approx(df: pd.DataFrame) -> pd.DataFrame:
    """
    Dark pool approximation: flags days with elevated volume but
    a very tight intraday price range. The logic: institutional
    orders routed off-exchange leave a fingerprint — big volume,
    little price movement. Not a direct dark pool feed, but a
    reasonable proxy for unusual institutional accumulation.
    """
    df = df.copy()
    if "Volume20Avg" not in df.columns:
        df = add_volume_metrics(df)

    intraday_range_pct = (df["High"] - df["Low"]) / df["Close"] * 100
    df["DarkPoolSignal"] = (
        (df["VolumeRatio"] >= DARK_POOL_VOLUME_THRESHOLD) &
        (intraday_range_pct <= DARK_POOL_RANGE_THRESHOLD)
    )
    return df


def add_absorption_signals(df: pd.DataFrame) -> pd.DataFrame:
    """
    Absorption / price-volume divergence:
    Flags days where volume is elevated but price barely moved.
    Absorption = large players absorbing sell pressure (or supply)
    without letting price fall (or rise). Often precedes reversals.
    """
    df = df.copy()
    if "Volume20Avg" not in df.columns:
        df = add_volume_metrics(df)

    price_move_pct = abs(df["Close"].pct_change() * 100)
    df["AbsorptionSignal"] = (
        (df["VolumeRatio"] >= ABSORPTION_VOLUME_MULTIPLIER) &
        (price_move_pct <= ABSORPTION_PRICE_MOVE_MAX)
    )
    return df


def add_institutional_activity(df: pd.DataFrame) -> pd.DataFrame:
    """
    Institutional activity approximation.
    Combines multiple volume-based signals to score each day:
    - Volume spike (2x avg): +1
    - Dark pool signal (high vol, tight range): +2
    - Absorption signal (high vol, tiny price move): +2
    Score 0 = nothing unusual, 3-5 = significant institutional footprint.
    """
    df = df.copy()
    if "VolumeSpike" not in df.columns:
        df = add_volume_metrics(df)
    if "DarkPoolSignal" not in df.columns:
        df = add_dark_pool_approx(df)
    if "AbsorptionSignal" not in df.columns:
        df = add_absorption_signals(df)

    df["InstitutionalScore"] = (
        df["VolumeSpike"].astype(int) * 1 +
        df["DarkPoolSignal"].astype(int) * 2 +
        df["AbsorptionSignal"].astype(int) * 2
    )
    return df


def compute_all(df: pd.DataFrame) -> pd.DataFrame:
    """
    Master function — runs every indicator in the correct order.
    This is the only function app.py and charts.py need to call.
    """
    df = add_emas(df)
    df = add_obv(df)
    df = add_volume_metrics(df)
    df = add_rsi(df)
    df = add_macd(df)
    df = add_dark_pool_approx(df)
    df = add_absorption_signals(df)
    df = add_institutional_activity(df)
    return df