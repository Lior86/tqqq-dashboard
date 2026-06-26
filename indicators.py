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
    CMF_PERIOD, OBV_EMA_PERIOD,
    QUIET_DRIFT_DAYS, QUIET_DRIFT_VOLUME_MAX, QUIET_DRIFT_PRICE_GAIN_MIN,
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
    Also adds a 20-day EMA of OBV — when OBV crosses above its EMA,
    that's the cleaner accumulation signal (rather than just OBV direction).
    """
    df = df.copy()
    direction = np.sign(df["Close"].diff()).fillna(0)
    df["OBV"] = (direction * df["Volume"]).cumsum()
    df["OBVEMA"] = df["OBV"].ewm(span=OBV_EMA_PERIOD, adjust=False).mean()
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
    a very tight intraday price range.
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
    Combines multiple volume-based signals to score each day.
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


def add_cmf(df: pd.DataFrame) -> pd.DataFrame:
    """
    Chaikin Money Flow (CMF) over CMF_PERIOD days.

    How it works:
    1. For each day, calculate the Money Flow Multiplier:
       MFM = ((Close - Low) - (High - Close)) / (High - Low)
       Close near the HIGH  = MFM close to +1 (buyers in control)
       Close near the LOW   = MFM close to -1 (sellers in control)
    2. Multiply MFM by volume = Money Flow Volume
    3. CMF = sum of MFV over 20 days / sum of Volume over 20 days

    Above 0  = accumulation, Below 0 = distribution.
    Above +0.1 or below -0.1 are meaningful thresholds.
    """
    df = df.copy()
    high_low_range = (df["High"] - df["Low"]).replace(0, np.nan)
    mfm = ((df["Close"] - df["Low"]) - (df["High"] - df["Close"])) / high_low_range
    mfv = mfm * df["Volume"]
    df["CMF"] = mfv.rolling(CMF_PERIOD).sum() / df["Volume"].rolling(CMF_PERIOD).sum()
    return df


def add_quiet_drift(df: pd.DataFrame) -> pd.DataFrame:
    """
    Quiet Drift Detector: flags stretches where price drifts up on
    below-average volume for N consecutive days.

    Institutions accumulating a large position buy gradually on quiet
    days — low volume, small steady gains.

    Produces:
    - QuietDriftDay: True on any day that qualifies individually
    - QuietDriftSignal: True on the Nth day of a qualifying streak
    """
    df = df.copy()
    if "Volume20Avg" not in df.columns:
        df = add_volume_metrics(df)

    price_change_pct = df["Close"].pct_change()

    df["QuietDriftDay"] = (
        (df["Volume"] < df["Volume20Avg"] * QUIET_DRIFT_VOLUME_MAX) &
        (price_change_pct >= QUIET_DRIFT_PRICE_GAIN_MIN)
    )

    streak = df["QuietDriftDay"].astype(int).rolling(QUIET_DRIFT_DAYS).sum()
    df["QuietDriftSignal"] = streak >= QUIET_DRIFT_DAYS

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
    df = add_cmf(df)
    df = add_quiet_drift(df)
    return df