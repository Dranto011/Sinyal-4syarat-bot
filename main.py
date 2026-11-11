import os
import yfinance as yf
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# ===== ISI PUNYA KAMU =====
TOKEN = os.environ.get("9279643241:AAFKOgeBc0nUaE93VjdkkQagFJzE7Za4i88")
CHAT_ID = 6194508570
# ==========================

TICKER = "GC=F"  # XAUUSD

def is_pinbar_m5(c):
    # SYARAT 3: Pin Bar di M5
    high, low, op, cl = float(c['High']), float(c['Low']), float(c['Open']), float(c['Close'])
    body = abs(cl - op)
    total = high - low
    if total == 0:
        return None
    upper = high - max(cl, op)
    lower = min(cl, op) - low
    if body > total * 0.35:
        return None
    if upper > body * 2 and upper > total * 0.4:
        return "Bearish Pin Bar M5 (sumbu atas panjang)"
    if lower > body * 2 and lower > total * 0.4:
        return "Bullish Pin Bar M5 (sumbu bawah panjang)"
    return None

def is_engulfing_m5(prev, curr, arah):
    # SYARAT 4: Engulfing di M5
    po, pc = float(prev['Open']), float(prev['Close'])
    co, cc = float(curr['Open']), float(curr['Close'])
    if arah == "BUY":
        return cc > co and pc < po and cc > po and co < pc
    if arah == "SELL":
        return cc < co and pc > po and cc < po and co > pc
    return False

def cek_sinyal():
    df15 = yf.download(TICKER, period="2d", interval="15m", progress=False)
    df5 = yf.download(TICKER, period="2d", interval="5m", progress=False)
    if df15.empty or df5.empty or len(df15) < 20 or len(df5) < 20:
        return None

    df15.columns = [c[0] if isinstance(c, tuple) else c for c in df15.columns]
    df5.columns = [c[0] if isinstance(c, tuple) else c for c in df5.columns]

    # SYARAT 1: High / Low M15 HARI INI
    today = df15.index[-1].date()
    df15_today = df15[df15.index.date == today]
    high_m15 = float(df15_today['High'].max())
    low_m15 = float(df15_today['Low'].min())
    harga = float(df5.iloc[-1]['Close'])

    dekat_high = abs(harga - high_m15) <= 3.0
    dekat_low = abs(harga - low_m15) <= 3.0

    arah = None
    level = 0

    # SYARAT 2: Gagal Sentuh 1-2 Candle M15
    if dekat_high:
        last2_high = float(df15.iloc[-2:]['High'].max())
        if last2_high <= high_m15 + 0.5:
            arah = "SELL"
            level = high_m15
    elif dekat_low:
        last2_low = float(df15.iloc[-2:]['Low'].min())
        if last2_low >= low_m15 - 0.5:
            arah = "BUY"
            level = low_m15

    if not arah:
        return None

    # SYARAT 3 & 4: Pin Bar M5 + Engulfing M5
    pin_ditemukan = None
    eng_ditemukan = False

    for i in range(len(df5)-3, len(df5)):
        c = df5.iloc[i]
        pin = is_pinbar_m5(c)
        if pin:
            pin_ditemukan = pin
        if i > 0:
            if is_engulfing_m5(df5.iloc[i-1], c, arah):
                eng_ditemukan = True

    if not pin_ditemukan or not eng_ditemukan:
        return None

    if arah == "SELL":
        sl = high_m15 + 3
        tp = harga - (sl - harga) * 2
    else:
        sl = low_m15 - 3
        tp = harga + (harga - sl) * 2

    pesan = (
        f"🔔 SINYAL XAUUSD - 4 SYARAT TERPENUHI\n\n"
        f"Arah: {arah}\n"
        f"Harga: {harga:.2f}\n"
        f"Level M15: {level:.2f}\n"
        f"High M15: {high_m15:.2f}\n"
        f"Low M15: {low_m15:.2f}\n\n"
        f"✅ 1. Nyampe High/Low M15\n"
        f"✅ 2. Gagal sentuh 1-2 candle M15\n"
        f"✅ 3. {pin_ditemukan}\n"
        f"✅ 4. Engulfing di M5 YA\n\n"
        f"SL: {sl:.2f}\n"
        f"TP: {tp:.2f} (RR 1:2)\n"
        f"Lot: 0.01\n\n"
        f"Cek lagi di MT5. Bukan jaminan profit."
    )
    return pesan

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot Scanner XAUUSD aktif.\nSyarat: High/Low M15 + Gagal Sentuh M15 + Pin Bar M5 + Engulfing M5.\nCek tiap 5 menit, tanpa RSI.")

async def tes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Lagi ngecek chart...")
    pesan = cek_sinyal()
    if pesan:
        await update.message.reply_text(pesan)
    else:
        await update.message.reply_text("Belum ada setup 4 syarat saat ini. Bot tetap mantau tiap 5 menit.")

async def job_cek(context: ContextTypes.DEFAULT_TYPE):
    try:
        pesan = cek_sinyal()
        if pesan:
            await context.bot.send_message(chat_id=CHAT_ID, text=pesan)
            print("Sinyal dikirim")
        else:
            print("Belum ada setup")
    except Exception as e:
        print(f"Error: {e}")

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("tes", tes))
    app.job_queue.run_repeating(job_cek, interval=300, first=10)
    print("Bot jalan...")
    app.run_polling()

if __name__ == "__main__":
    main()
