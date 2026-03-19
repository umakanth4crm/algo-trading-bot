from SmartApi import SmartConnect
import pyotp
import pandas as pd
import requests
from datetime import datetime, time as dt_time
import os
import pytz

print("🚀 PRO STRATEGY V6 (GITHUB VERSION)")

# =============================
# TELEGRAM (use env variables in GitHub)
# =============================
BOT_TOKEN = "8351018777:AAGbRXXN7_uD2NwYt1dwUy5AmqjGJmjCKLQ"
CHAT_ID = "8767651873"

def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg})
    except Exception as e:
        print("Telegram Error:", e)

# =============================
# ANGEL LOGIN
# =============================

# API_KEY = "Wq2v3ZKT"
# CLIENT_ID = "S60015476"
# PASSWORD = "2121"
# TOTP_SECRET = "XB6VHHUUTT7CEPQKCWFWXNSEVU"
API_KEY = os.getenv("API_KEY")
CLIENT_ID = os.getenv("CLIENT_ID")
PIN = os.getenv("PIN")
TOTP_SECRET = os.getenv("TOTP_SECRET")
# 🔍 DEBUG (ADD HERE)
print("DEBUG API_KEY:", API_KEY)
print("DEBUG CLIENT_ID:", CLIENT_ID)
print("DEBUG PIN:", PIN)
print("DEBUG TOTP_SECRET:", TOTP_SECRET)

obj = SmartConnect(api_key=API_KEY)
totp = pyotp.TOTP(TOTP_SECRET).now()

session = obj.generateSession(CLIENT_ID, PIN, totp)

if session['status']:
    print("✅ Login Success")
    send_telegram("🤖 Bot Started Successfully")
else:
    print("❌ Login Failed")
    print(session)
    exit()

# =============================
# STOCKS
# =============================
stocks = {
    # BANKING
    "HDFCBANK": "1333",
    "ICICIBANK": "4963",
    "AXISBANK": "5900",
    "SBIN": "3045",
    "KOTAKBANK": "1922",
    "INDUSINDBK": "5258",

    # ENERGY
    "RELIANCE": "2885",
    "ADANIENT": "25",
    "ADANIPORTS": "15083",
    "TATAPOWER": "3426",
    "NTPC": "11630",
    "POWERGRID": "14977",

    # AUTO
    "MARUTI": "10999",
    "M&M": "2031",
    "BAJAJ-AUTO": "16669",
    "EICHERMOT": "910",

    # METALS / INFRA
    "LT": "11483",
    "JSWSTEEL": "11723",
    "TATASTEEL": "3499",
    "HINDALCO": "1363",
    "ULTRACEMCO": "11532",
    "GRASIM": "1232",

    # PHARMA
    "SUNPHARMA": "3351",
    "DRREDDY": "881",
    "CIPLA": "694",
    "DIVISLAB": "10940",
    "LUPIN": "10440",

    # TELECOM
    "BHARTIARTL": "10604",
    "JIOFIN": "18096"
}

# =============================
# HELPERS
# =============================
def ema(series, period):
    return series.ewm(span=period, adjust=False).mean()

def atr(df, period=14):
    high_low = df["High"] - df["Low"]
    high_close = abs(df["High"] - df["Close"].shift())
    low_close = abs(df["Low"] - df["Close"].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return tr.rolling(period).mean()

def get_ltp(symbol, token):
    try:
        data = obj.ltpData("NSE", symbol, token)
        return float(data['data']['ltp'])
    except:
        return None

def get_candles(token):
    try:
        
        ist = pytz.timezone("Asia/Kolkata")
        now = datetime.now(ist)

        params = {
            "exchange": "NSE",
            "symboltoken": token,
            "interval": "FIVE_MINUTE",
            "fromdate": (now - pd.Timedelta(days=5)).strftime('%Y-%m-%d %H:%M'),
            "todate": now.strftime('%Y-%m-%d %H:%M')
        }

        data = obj.getCandleData(params)

        df = pd.DataFrame(
            data["data"],
            columns=["Datetime","Open","High","Low","Close","Volume"]
        )
        return df
    except:
        return pd.DataFrame()

# =============================
# MARKET TIME CHECK
# =============================



ist = pytz.timezone("Asia/Kolkata")
now_time = datetime.now(ist).time()

if now_time < dt_time(9, 15) or now_time > dt_time(15, 30):
    print("⏳ Market Closed")
    exit()

# =============================
# RUN ONCE (NO LOOP)
# =============================
print("\n📊 Checking:", datetime.now())

positions = {}

for stock, token in stocks.items():

    df = get_candles(token)
    if df.empty or len(df) < 50:
        continue

    df["EMA20"] = ema(df["Close"], 20)
    df["EMA50"] = ema(df["Close"], 50)
    df["ATR"] = atr(df)

    row = df.iloc[-1]
    prev = df.iloc[-2]

    price = get_ltp(stock, token)
    if price is None:
        continue

    print(f"{stock} | Price: {price} | EMA20: {row['EMA20']:.2f} | EMA50: {row['EMA50']:.2f}")

    atr_val = row["ATR"]
    if atr_val == 0:
        continue

    # =============================
    # ENTRY SIGNALS ONLY
    # =============================
    if stock not in positions:

        if prev["EMA20"] <= prev["EMA50"] and row["EMA20"] > row["EMA50"]:
            msg = f"📈 BUY {stock} @ {price}"
            print(msg)
            send_telegram(msg)

        elif prev["EMA20"] >= prev["EMA50"] and row["EMA20"] < row["EMA50"]:
            msg = f"📉 SELL {stock} @ {price}"
            print(msg)
            send_telegram(msg)

print("✅ Run Completed")
