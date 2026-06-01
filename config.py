# config.py
# Central configuration for the TQQQ dashboard.
# Change values here to affect the whole app — no hunting through other files.

TICKER = "TQQQ"
APP_TITLE = "TQQQ Trading Dashboard"
APP_ICON = "📈"

# Timeframe options shown as buttons in the UI
# Key = label on the button, Value = how far back yfinance fetches
TIMEFRAMES = {
    "1D":  "1d",
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
# A narrow price range + big volume = possible institutional accumulation off-exchange
DARK_POOL_VOLUME_THRESHOLD  = 1.5   # x above 20-day avg volume
DARK_POOL_RANGE_THRESHOLD   = 0.5   # price range must be < this % of price (very tight candle)

# Price/volume divergence — absorption signal settings
# Flags days where price moved little but volume was elevated (absorption)
ABSORPTION_VOLUME_MULTIPLIER = 1.5  # volume > 1.5x 20-day avg
ABSORPTION_PRICE_MOVE_MAX    = 0.5  # price move < 0.5% despite high volume

# Streamlit cache TTL — data refreshes every 15 minutes
CACHE_TTL_SECONDS = 900