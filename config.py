# config.py
# Central configuration for the TQQQ dashboard.
# Change values here to affect the whole app — no hunting through other files.

TICKER = "TQQQ"
APP_TITLE = "TQQQ Trading Dashboard"
APP_ICON = "📈"

# Timeframe options shown as buttons in the UI
# Key = label on the button, Value = how far back yfinance fetches
TIMEFRAMES = {
    "1W":  "5d",
    "1M":  "1mo",
    "3M":  "3mo",
    "6M":  "6mo",
    "1Y":  "1y",
    "2Y":  "2y",
}
DEFAULT_TIMEFRAME = "3M"

# EMA periods overlaid on the candlestick chart
EMA_SHORT = 50
EMA_LONG  = 200

# Volume spike detection — flag any day where volume > this multiplier x 20-day avg
VOLUME_SPIKE_MULTIPLIER = 2.0
VOLUME_AVG_WINDOW = 20

# RSI settings
RSI_PERIOD     = 14
RSI_OVERBOUGHT = 70
RSI_OVERSOLD   = 30

# MACD settings (standard)
MACD_FAST   = 12
MACD_SLOW   = 26
MACD_SIGNAL = 9

# Dark pool approximation — looks for high-volume days with unusually small price range
DARK_POOL_VOLUME_THRESHOLD  = 1.5
DARK_POOL_RANGE_THRESHOLD   = 0.5

# Price/volume divergence — absorption signal settings
ABSORPTION_VOLUME_MULTIPLIER = 1.5
ABSORPTION_PRICE_MOVE_MAX    = 0.5

# Chaikin Money Flow (CMF) — measures buying/selling pressure weighted by position in day's range
CMF_PERIOD = 20

# OBV EMA overlay — smoothed OBV to detect crossover signals
OBV_EMA_PERIOD = 20

# Quiet drift detector — looks for slow institutional accumulation below the radar
QUIET_DRIFT_DAYS           = 3
QUIET_DRIFT_VOLUME_MAX     = 0.85
QUIET_DRIFT_PRICE_GAIN_MIN = 0.001

# Streamlit cache TTL — data refreshes every 15 minutes
CACHE_TTL_SECONDS = 900