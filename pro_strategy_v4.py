import yfinance as yf
import pandas as pd
import requests
import time
from datetime import datetime, time as dt_time

print("🚀 PRO STRATEGY V4 TEST MODE STARTED")

# =============================
# TELEGRAM SETTINGS
# =============================

BOT_TOKEN = "8351018777:AAGbRXXN7_uD2NwYt1dwUy5AmqjGJmjCKLQ"
CHAT_ID = "8767651873"

def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {"chat_id": CHAT_ID, "text": msg}
        requests.post(url, data=payload)
    except Exception as e:
        print("Telegram Error:", e)

# =============================
# LIVE PRICE FUNCTION (IMPROVED)
# =============================

def get_live_price(symbol):
    try:
        data = yf.Ticker(symbol)
        return data.fast_info.get("lastPrice", None)
    except:
        return None

# =============================
# STOCK LIST
# =============================

stocks = [

# BANKING
"HDFCBANK.NS","ICICIBANK.NS","AXISBANK.NS","SBIN.NS","KOTAKBANK.NS","INDUSINDBK.NS",

# IT

# ENERGY
"RELIANCE.NS","ADANIENT.NS","ADANIPORTS.NS","TATAPOWER.NS","NTPC.NS","POWERGRID.NS",

# AUTO
"MARUTI.NS","M&M.NS","BAJAJ-AUTO.NS","EICHERMOT.NS",

# METALS / INFRA
"LT.NS","JSWSTEEL.NS","TATASTEEL.NS","HINDALCO.NS","ULTRACEMCO.NS","GRASIM.NS",

# PHARMA
"SUNPHARMA.NS","DRREDDY.NS","CIPLA.NS","DIVISLAB.NS","LUPIN.NS",

# TELECOM
"BHARTIARTL.NS","JIOFIN.NS"
]

# =============================
# INDICATORS
# =============================

def ema(series, period):
    return series.ewm(span=period, adjust=False).mean()

def atr(df, period=14):
    high_low = df["High"] - df["Low"]
    high_close = abs(df["High"] - df["Close"].shift())
    low_close = abs(df["Low"] - df["Close"].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return tr.rolling(period).mean()

# =============================
# RISK SETTINGS
# =============================

capital = 100000
equity = capital

MAX_TRADES = 5
MAX_DAILY_LOSS = -2000

positions = {}
last_candle_time = None

total_profit = 0
total_loss = 0

send_telegram("🚀 PRO STRATEGY V4 STARTED (TEST MODE)")

# =============================
# WAIT FUNCTION
# =============================

def wait_for_next_candle():
    now = datetime.now()
    seconds = 300 - (now.minute % 5) * 60 - now.second
    time.sleep(seconds + 2)

# =============================
# MAIN LOOP
# =============================

for _ in range(1):

    now_time = datetime.now().time()

    # MARKET TIME CONTROL
    if now_time < dt_time(9,15):
        print("⏳ Waiting for market open...")
        time.sleep(60)
        continue

    if now_time > dt_time(15,30):
        print("🛑 Market Closed. Stopping bot.")
        send_telegram("🛑 Market Closed. Bot Stopped.")
        break

    # DAILY LOSS CONTROL
    if (total_profit + total_loss) <= MAX_DAILY_LOSS:
        send_telegram("🛑 Max daily loss reached. Stopping bot.")
        break

    try:
        print("\n📊 Checking:", datetime.now())

        nifty = yf.download("^NSEI", period="5d", interval="5m", progress=False)

        if nifty.empty:
            wait_for_next_candle()
            continue

        nifty["EMA200"] = ema(nifty["Close"], 200)

        if len(nifty) < 200:
            wait_for_next_candle()
            continue

        current_candle_time = nifty.index[-1]

        if current_candle_time == last_candle_time:
            wait_for_next_candle()
            continue

        last_candle_time = current_candle_time

        nifty_price = float(nifty["Close"].iloc[-1])
        nifty_ema = float(nifty["EMA200"].iloc[-1])

        market_bull = nifty_price > nifty_ema
        market_bear = nifty_price < nifty_ema

        print("NIFTY:", nifty_price, "| EMA200:", nifty_ema)

        for stock in stocks:

            if len(positions) >= MAX_TRADES:
                break

            df = yf.download(stock, period="5d", interval="5m", progress=False)

            if df.empty:
                continue

            df["EMA20"] = ema(df["Close"], 20)
            df["EMA50"] = ema(df["Close"], 50)
            df["ATR"] = atr(df)
            df["VOL_AVG"] = df["Volume"].rolling(20).mean()

            df = df.dropna()

            if len(df) < 2:
                continue

            row = df.iloc[-1]
            prev = df.iloc[-2]

            price = get_live_price(stock)
            if price is None:
                continue

            ema20 = row["EMA20"]
            ema50 = row["EMA50"]
            prev_ema20 = prev["EMA20"]
            prev_ema50 = prev["EMA50"]
            atr_val = row["ATR"]
            volume = row["Volume"]
            avg_vol = row["VOL_AVG"]

            candle_body = abs(row["Close"] - row["Open"])
            candle_range = row["High"] - row["Low"]

            strong_candle = candle_body > candle_range * 0.6

            risk_per_trade = equity * 0.01

            if atr_val == 0:
                continue

            qty = int(risk_per_trade / (atr_val * 1.5))
            if qty <= 0:
                continue

            # ENTRY
            if stock not in positions and volume > avg_vol * 1.2:

                if (prev_ema20 <= prev_ema50 and ema20 > ema50 and
                    price > ema20 and price > ema50 and strong_candle and market_bull):

                    positions[stock] = {"type": "LONG", "entry": price, "stop": price - atr_val * 1.5, "qty": qty}

                    send_telegram(f"📈 LONG {stock} @ {round(price,2)} Qty:{qty}")

                elif (prev_ema20 >= prev_ema50 and ema20 < ema50 and
                      price < ema20 and price < ema50 and strong_candle and market_bear):

                    positions[stock] = {"type": "SHORT", "entry": price, "stop": price + atr_val * 1.5, "qty": qty}

                    send_telegram(f"📉 SHORT {stock} @ {round(price,2)} Qty:{qty}")

            # EXIT
            elif stock in positions:

                pos = positions[stock]

                if pos["type"] == "LONG":
                    new_stop = price - atr_val * 1.2
                    pos["stop"] = max(pos["stop"], new_stop)

                    if price <= pos["stop"]:
                        pnl = (price - pos["entry"]) * pos["qty"]
                        equity += pnl
                        total_profit += max(pnl, 0)
                        total_loss += min(pnl, 0)

                        send_telegram(f"❌ EXIT LONG {stock} PnL: ₹{round(pnl,2)}")
                        del positions[stock]

                elif pos["type"] == "SHORT":
                    new_stop = price + atr_val * 1.2
                    pos["stop"] = min(pos["stop"], new_stop)

                    if price >= pos["stop"]:
                        pnl = (pos["entry"] - price) * pos["qty"]
                        equity += pnl
                        total_profit += max(pnl, 0)
                        total_loss += min(pnl, 0)

                        send_telegram(f"❌ EXIT SHORT {stock} PnL: ₹{round(pnl,2)}")
                        del positions[stock]

        print(f"💰 Equity: {round(equity,2)} | Net: {round(total_profit+total_loss,2)}")

    except Exception as e:
        print("Error:", e)

    wait_for_next_candle()
