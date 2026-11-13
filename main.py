import os, time, requests
import yfinance as yf
import pandas as pd

TOKEN = os.environ.get("TOKEN")
CHAT_ID = "6194508570"
SYMBOL = "GC=F"

last_signal_time = 0
last_signal_level = 0

def send_tele(pesan):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": CHAT_ID, "text": pesan, "parse_mode": "HTML"}, timeout=10)
    except Exception as e:
        print("Gagal kirim tele:", e)

def ambil_data(tf, period="2d"):
    df = yf.download(SYMBOL, interval=tf, period=period, progress=False, auto_adjust=False)
    if df.empty:
        return None
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.dropna()
    return df

def is_pinbar(candle):
    o, h, l, c = candle['Open'], candle['High'], candle['Low'], candle['Close']
    body = abs(c - o)
    upper = h - max(o, c)
    lower = min(o, c) - l
    total = h - l
    if total == 0:
        return False
    return (upper > body * 2 or lower > body * 2) and body < total * 0.4

def is_engulfing(prev, curr):
    if prev['Close'] < prev['Open'] and curr['Close'] > curr['Open']:
        if curr['Open'] <= prev['Close'] and curr['Close'] >= prev['Open']:
            return "BULLISH"
    if prev['Close'] > prev['Open'] and curr['Close'] < curr['Open']:
        if curr['Open'] >= prev['Close'] and curr['Close'] <= prev['Open']:
            return "BEARISH"
    return None

def cek_sinyal():
    global last_signal_time, last_signal_level
    df15 = ambil_data("15m")
    if df15 is None or len(df15) < 25:
        return
    # TEMBOK DINAMIS: High/Low dari 12 candle M15 terakhir, tembok pindah terus
    data_tembok = df15.iloc[-21:-1]
    tembok_high = float(data_tembok['High'].max())
    tembok_low = float(data_tembok['Low'].min())
    harga_skrg = float(df15.iloc[-1]['Close'])
    print(f"Harga: {harga_skrg:.2f} | HIGH baru: {tembok_high:.2f} | LOW baru: {tembok_low:.2f}")
    if time.time() - last_signal_time < 3600 and abs(harga_skrg - last_signal_level) < 5:
        return
    df5 = ambil_data("5m")
    if df5 is None or len(df5) < 5:
        return
    c2 = df5.iloc[-2]
    c3 = df5.iloc[-1]
    toleransi = 2.0
    # SELL - Gagal sentuh HIGH baru
    if abs(float(c3['High']) - tembok_high) <= toleransi or (float(c3['High']) < tembok_high and float(c3['High']) > tembok_high - 3):
        pin = is_pinbar(c2) or is_pinbar(c3)
        eng = is_engulfing(c2, c3)
        print(f"  -> Deket HIGH {tembok_high:.2f}, Pin:{pin}, Eng:{eng}")
        if pin and eng == "BEARISH":
            send_tele(f"🔴 <b>SELL XAUUSD</b>\n\n1. M15 High baru: {tembok_high:.2f}\n2. Gagal sentuh High\n3. Pin Bar M5 ✅\n4. Engulfing Bearish M5 ✅\n\nHarga: {harga_skrg:.2f}")
            last_signal_time = time.time()
            last_signal_level = tembok_high
            return
    # BUY - Gagal sentuh LOW baru
    if abs(float(c3['Low']) - tembok_low) <= toleransi or (float(c3['Low']) > tembok_low and float(c3['Low']) < tembok_low + 3):
        pin = is_pinbar(c2) or is_pinbar(c3)
        eng = is_engulfing(c2, c3)
        print(f"  -> Deket LOW {tembok_low:.2f}, Pin:{pin}, Eng:{eng}")
        if pin and eng == "BULLISH":
            send_tele(f"🟢 <b>BUY XAUUSD</b>\n\n1. M15 Low baru: {tembok_low:.2f}\n2. Gagal sentuh Low\n3. Pin Bar M5 ✅\n4. Engulfing Bullish M5 ✅\n\nHarga: {harga_skrg:.2f}")
            last_signal_time = time.time()
            last_signal_level = tembok_low
            return

print("Bot jalan... Tembok M15 DINAMIS aktif...")
send_tele("✅ Bot BARU jalan! Tembok High/Low sekarang pindah-pindah ngikutin M15 terdekat.")
while True:
    try:
        cek_sinyal()
    except Exception as e:
        print("Error:", e)
    time.sleep(60)
