import logging
import requests
import numpy as np
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Logging setup
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Telegram Bot Token
TOKEN = "8982381249:AAFvu8_EDCyrflcJIbymkKPCs1BeAopvsAo"

# Binance API থেকে লাইভ ক্যান্ডেল ডাটা ফেচিং
def get_klines(symbol="BTCUSDT", interval="1m", limit=200):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    try:
        response = requests.get(url, timeout=5)
        data = response.json()
        closes = np.array([float(candle[4]) for candle in data])
        highs = np.array([float(candle[2]) for candle in data])
        lows = np.array([float(candle[3]) for candle in data])
        volumes = np.array([float(candle[5]) for candle in data])
        return closes, highs, lows, volumes
    except Exception as e:
        print("API Error:", e)
        return None, None, None, None

# 1. RSI (14) - Momentum
def calculate_rsi(prices, period=14):
    deltas = np.diff(prices)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    avg_gain = np.mean(gains[-period:])
    avg_loss = np.mean(losses[-period:])
    if avg_loss == 0:
        return 100
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 2)

# 2. Bollinger Bands - Volatility
def calculate_bollinger_bands(prices, period=20, std_dev=2):
    sma = np.mean(prices[-period:])
    std = np.std(prices[-period:])
    return sma + (std * std_dev), sma, sma - (std * std_dev)

# 3. MACD - Trend Crossover
def calculate_macd(prices):
    exp1 = np.exp(np.linspace(-1., 0., 12))
    exp1 /= exp1.sum()
    ema12 = np.convolve(prices, exp1, mode='full')[:len(prices)]

    exp2 = np.exp(np.linspace(-1., 0., 26))
    exp2 /= exp2.sum()
    ema26 = np.convolve(prices, exp2, mode='full')[:len(prices)]

    macd_line = ema12 - ema26
    signal_line = np.convolve(macd_line, exp1, mode='full')[:len(prices)]
    return macd_line[-1], signal_line[-1]

# 4. EMA 200 - Baseline Major Trend
def calculate_ema(prices, period=200):
    weights = np.exp(np.linspace(-1., 0., period))
    weights /= weights.sum()
    return np.convolve(prices, weights, mode='full')[:len(prices)][-1]

# 5. Stochastic Oscillator - Reversal Timing
def calculate_stochastic(closes, highs, lows, period=14):
    lowest_low = np.min(lows[-period:])
    highest_high = np.max(highs[-period:])
    if highest_high == lowest_low:
        return 50
    return round(((closes[-1] - lowest_low) / (highest_high - lowest_low)) * 100, 2)

# 6. Money Flow Index (MFI) - Real Volume Inflow/Outflow
def calculate_mfi(closes, highs, lows, volumes, period=14):
    typical_prices = (highs + lows + closes) / 3
    money_flow = typical_prices * volumes
    
    positive_flow = 0
    negative_flow = 0
    
    for i in range(-period, 0):
        if typical_prices[i] > typical_prices[i-1]:
            positive_flow += money_flow[i]
        else:
            negative_flow += money_flow[i]
            
    if negative_flow == 0:
        return 100
    money_ratio = positive_flow / negative_flow
    return round(100 - (100 / (1 + money_ratio)), 2)

# TOP 6 INDICATOR ENGINE LOGIC
def get_top6_accurate_signal(symbol="BTCUSDT"):
    closes, highs, lows, volumes = get_klines(symbol, "1m", 200)

    if closes is None or len(closes) < 200:
        return "NO DATA ⚠️", 0, "API Error"

    rsi = calculate_rsi(closes)
    upper_b, sma_b, lower_b = calculate_bollinger_bands(closes)
    macd_line, signal_line = calculate_macd(closes)
    ema200 = calculate_ema(closes, 200)
    stoch_k = calculate_stochastic(closes, highs, lows)
    mfi = calculate_mfi(closes, highs, lows, volumes)
    current_price = closes[-1]

    # Buy / Call Conditions (6-Layer Confirmation)
    call_conditions = [
        rsi < 42,                  # 1. RSI Low/Oversold
        current_price <= lower_b, # 2. Lower BB Touch
        macd_line > signal_line,  # 3. MACD Bullish
        current_price > ema200,   # 4. Above EMA 200 (Uptrend)
        stoch_k < 35,             # 5. Stoch Reversal Zone
        mfi < 40                  # 6. MFI Inflow Starting
    ]

    # Sell / Put Conditions (6-Layer Confirmation)
    put_conditions = [
        rsi > 58,                  # 1. RSI High/Overbought
        current_price >= upper_b, # 2. Upper BB Touch
        macd_line < signal_line,  # 3. MACD Bearish
        current_price < ema200,   # 4. Below EMA 200 (Downtrend)
        stoch_k > 65,             # 5. Stoch Overbought Zone
        mfi > 60                  # 6. MFI Outflow High
    ]

    call_matches = sum(call_conditions)
    put_matches = sum(put_conditions)

    if call_matches >= 5:
        return "ULTRA CALL (BUY) 🟢", rsi, f"HIGH ACCURACY SETUP ({call_matches}/6 MATCH)"
    elif put_matches >= 5:
        return "ULTRA PUT (SELL) 🔴", rsi, f"HIGH ACCURACY SETUP ({put_matches}/6 MATCH)"
    elif call_matches == 4:
        return "MODERATE CALL 🟢", rsi, f"MEDIUM SETUP ({call_matches}/6 MATCH)"
    elif put_matches == 4:
        return "MODERATE PUT 🔴", rsi, f"MEDIUM SETUP ({put_matches}/6 MATCH)"
    else:
        return "WAIT FOR SETUP ⏳", rsi, f"MARKET CHOPPY ({max(call_matches, put_matches)}/6 MATCH)"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    first_name = user.first_name if user else "Trader"

    signal, rsi, status = get_top6_accurate_signal("BTCUSDT")

    welcome_text = (
        f"⚡ **PK TRADER TOP-6 PRO ENGINE** ⚡\n\n"
        f"Hello {first_name}!\n"
        f"Indicators: **RSI + BB + MACD + EMA200 + Stoch + MFI Volume**\n\n"
        f"📊 **Live BTC/USDT Market Status:**\n"
        f"• Calculated RSI: `{rsi}`\n"
        f"• Filter Status: `{status}`\n"
        f"• Final Signal: **{signal}**\n\n"
        f"🎯 *Tip: Trade only on 5/6 or 6/6 Matches for maximum accuracy!*\n\n"
        f"👇 *Launch Trading Mini App:* "
    )

    web_app_url = "https://pk-trader.github.io/trading-app/?v=8"

    # এখানে সাপোর্ট বাটন আপডেট করা হয়েছে
    keyboard = [
        [InlineKeyboardButton("🚀 LAUNCH TOP-6 SIGNAL APP", web_app=WebAppInfo(url=web_app_url))],
        [InlineKeyboardButton("💬 Support", url="https://t.me/noman887")]
    ]

    await update.message.reply_text(
        text=welcome_text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    print("Top 6 Indicator Engine with Updated Support Button is Running...")
    app.run_polling()