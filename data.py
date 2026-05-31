# data.py
# Responsible for one thing: fetching TQQQ price + volume data from yfinance.
# Uses Streamlit's cache so the app doesn't re-download on every interaction.

import yfinance as yf
import pandas as pd
import streamlit as st
from config import TICKER, CACHE_TTL_SECONDS


@st.cache_data(ttl=CACHE_TTL_SECONDS)
def fetch_data(period: str) -> pd.DataFrame:
    """
    Download OHLCV data for TQQQ for the given yfinance period string.
    Returns a clean DataFrame with columns: Open, High, Low, Close, Volume.
    Raises a descriptive error if the fetch fails or returns empty data.
    """
    try:
        df = yf.download(TICKER, period=period, auto_adjust=True, progress=False)
    except Exception as e:
        raise RuntimeError(f"Failed to download data for {TICKER}: {e}")

    if df is None or df.empty:
        raise ValueError(f"No data returned for {TICKER} with period='{period}'. "
                         "Check your internet connection or try a different timeframe.")

    # yfinance sometimes returns MultiIndex columns — flatten them
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    # Keep only the columns we need
    required = ["Open", "High", "Low", "Close", "Volume"]
    df = df[required].copy()

    # Drop any rows where Close or Volume is NaN
    df.dropna(subset=["Close", "Volume"], inplace=True)

    # Ensure the index is a proper DatetimeIndex
    df.index = pd.to_datetime(df.index)
    df.index.name = "Date"

    return df