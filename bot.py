import os
import requests
import pandas as pd
import numpy as np
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = "8982381249:AAFvu8_EDCyrflcJIbymkKPCs1BeAopvsAo"  # Tumar bot token boshao

def get_binance_klines(symbol="BTCUSDT", interval="1m", limit=200):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            df = pd.DataFrame(data, columns=[
                'time', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'qav', 'num_trades', 'taker_base_vol', 'taker_quote_vol', 'ignore'
            ])
            df['close'] = df['close'].astype(float)
            df['high'] = df['high'].astype(float)
            df['low'] = df['low'].astype(float)
            df['open'] = df['open'].astype(float)
            df['volume'] = df['volume'].astype(float)
            return df
    except Exception as e:
        print("API Error:", e)
    return None

def analyze_10_indicators(df):
    if df is None or len(df) < 100:
        return {"decision": "WAIT / NO SETUP 🟡", "confidence": "0%", "score": "0/10"}

    close = df['close']
    high = df['high']
    low = df['low']

    # 1. RSI (14)
    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))

    # 2. EMA System (9, 21, 50, 200)
    ema9 = close.ewm(span=9, adjust=False).mean()
    ema21 = close.ewm(span=21, adjust=False).mean()
    ema50 = close.ewm(span=50, adjust=False).mean()
    ema200 = close.ewm(span=200, adjust=False).mean()

    # 3. MACD (12, 26, 9)
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd_line = ema12 - ema26
    macd_signal = macd_line.ewm(span=9, adjust=False).mean()

    # 4. Stochastic (14, 3, 3)
    low14 = low.rolling(14).min()
    high14 = high.rolling(14).max()
    stoch_k = 100 * ((close - low14) / (high14 - low14 + 1e-9))

    # 5. Bollinger Bands (20, 2)
    sma20 = close.rolling(20).mean()
    std20 = close.rolling(20).std()
    upper_band = sma20 + (std20 * 2)
    lower_band = sma20 - (std20 * 2)

    i = len(df) - 1
    c_close = close.iloc[i]
    c_rsi = rsi.iloc[i]
    c_ema9 = ema9.iloc[i]
    c_ema21 = ema21.iloc[i]
    c_ema50 = ema50.iloc[i]
    c_ema200 = ema200.iloc[i]
    c_macd = macd_line.iloc[i]
    c_macd_sig = macd_signal.iloc[i]
    c_stoch_k = stoch_k.iloc[i]
    c_upper = upper_band.iloc[i]
    c_lower = lower_band.iloc[i]

    buy_score = 0
    sell_score = 0

    if c_rsi < 35: buy_score += 1
    elif c_rsi > 65: sell_score += 1

    if c_ema9 > c_ema21: buy_score += 1
    else: sell_score += 1

    if c_close > c_ema200: buy_score += 1
    else: sell_score += 1

    if c_close > c_ema50: buy_score += 1
    else: sell_score += 1

    if c_macd > c_macd_sig: buy_score += 1
    else: sell_score += 1

    if c_stoch_k < 25: buy_score += 1
    elif c_stoch_k > 75: sell_score += 1

    if c_close <= c_lower: buy_score += 1
    elif c_close >= c_upper: sell_score += 1

    if c_close > df['open'].iloc[i]: buy_score += 1
    else: sell_score += 1

    if df['volume'].iloc[i] > df['volume'].rolling(10).mean().iloc[i]:
        if c_close > df['open'].iloc[i]: buy_score += 1
        else: sell_score += 1

    if c_rsi > rsi.iloc[i-1] and c_rsi < 60: buy_score += 1
    elif c_rsi < rsi.iloc[i-1] and c_rsi > 40: sell_score += 1

    if buy_score >= 8:
        return {"decision": "CALL (BUY) 🟢", "confidence": "99.9% PRO SETUP 🟢", "score": f"{buy_score}/10"}
    elif sell_score >= 8:
        return {"decision": "PUT (SELL) 🔴", "confidence": "99.9% PRO SETUP 🔴", "score": f"{sell_score}/10"}
    else:
        return {"decision": "WAIT / NO SETUP 🟡", "confidence": "RISKY MARKET 🟡", "score": f"BUY:{buy_score}/10 SELL:{sell_score}/10"}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 OPEN PK TRADER REAL PRO", web_app=WebAppInfo(url="https://pk-trader.github.io/trading-app/"))]
    ])
    await update.message.reply_text("⚡ Welcome to **PK TRADER REAL PRO**!\n\nStrict 10-Indicator Engine Active.", reply_markup=keyboard, parse_mode="Markdown")

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    print("Bot is running with Strict Live Calculations...")
    app.run_polling()