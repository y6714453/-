import edge_tts
import asyncio
import subprocess
import requests
import json
import time
from requests_toolbelt.multipart.encoder import MultipartEncoder

# 🟡 טוקן קבוע
token = "2yqvFAr7E9rVPGyk"

# 📁 קריאה מקובץ JSON
with open("symbols.json", "r", encoding="utf-8") as f:
    symbols_data = json.load(f)

# 📚 פונקציית עזר להמרת מספר למילים (נקבה, ללא זכר)
def number_to_words(n):
    if isinstance(n, float):
        whole, frac = str(n).split(".")
        return f"{number_to_words(int(whole))} נקודה {number_to_words(int(frac))}"
    words = {
        0: "אפס", 1: "אחת", 2: "שתיים", 3: "שלוש", 4: "ארבע", 5: "חמש",
        6: "שש", 7: "שבע", 8: "שמונה", 9: "תשע", 10: "עשר", 11: "אחת עשרה", 12: "שתים עשרה"
    }
    if n in words:
        return words[n]
    if n < 100:
        tens = ["", "", "עשרים", "שלושים", "ארבעים", "חמישים", "שישים", "שבעים", "שמונים", "תשעים"]
        return f"{tens[n // 10]} ו{words[n % 10]}" if n % 10 != 0 else f"{tens[n // 10]}"
    if n < 1000:
        hundreds = ["", "מאה", "מאתיים", "שלוש מאות", "ארבע מאות", "חמש מאות", "שש מאות", "שבע מאות", "שמונה מאות", "תשע מאות"]
        rem = n % 100
        return f"{hundreds[n // 100]} ו{number_to_words(rem)}" if rem else f"{hundreds[n // 100]}"
    return str(n)

# 🧠 ניסוח טקסט מותאם לפי סוג
def generate_text(name, symbol, type_, current_price, price_day, price_week, price_year, year_high):
    def format_change(curr, prev):
        if prev is None or prev == 0:
            return "אין נתון זמין"
        change = ((curr - prev) / prev) * 100
        sign = "עלייה" if change > 0 else "ירידה" if change < 0 else "שינוי אפסי"
        return f"{sign} של {number_to_words(round(abs(change), 2))} אחוז"

    current_txt = number_to_words(round(current_price))
    change_day = format_change(current_price, price_day)
    change_week = format_change(current_price, price_week)
    change_year = format_change(current_price, price_year)

    dist_txt = ""
    if year_high:
        diff = ((current_price - year_high) / year_high) * 100
        dist_txt = f"המחיר הנוכחי רחוק מהשיא ב{number_to_words(round(abs(diff), 2))} אחוז."

    if type_ == "crypto":
        return f"ה{ name } נסחר בשער של {current_txt} דולר. {change_day}. {change_week}. {change_year}. {dist_txt}"
    elif type_ == "index":
        return f"מדד ה{ name } עומד כעת על {current_txt} נקודות. {change_day}. {change_week}. {change_year}. {dist_txt}"
    elif type_ == "stock_us":
        return f"מניית { name } נסחרת כעת בשווי של {current_txt} דולר. {change_day}. {change_week}. {change_year}. {dist_txt}"
    elif type_ == "stock_il":
        return f"מניית { name } נסחרת כעת בשווי של {current_txt} שקלים חדשים. {change_day}. {change_week}. {change_year}. {dist_txt}"
    else:
        return f"{ name } עומד על {current_txt}. {change_day}. {change_week}. {change_year}. {dist_txt}"

# 🔁 שליפת נתונים ליחידה אחת
def get_data(symbol):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=6mo&interval=1d"
    headers = {'User-Agent': 'Mozilla/5.0'}
    r = requests.get(url, headers=headers, timeout=10)
    data = r.json()['chart']['result'][0]
    current = data['meta']['regularMarketPrice']
    high = data['meta'].get('fiftyTwoWeekHigh', None)
    times = data['timestamp']
    prices = data['indicators']['quote'][0]['close']

    now = time.time()
    def closest(t):
        for ts, pr in zip(reversed(times), reversed(prices)):
            if ts <= t and pr is not None:
                return pr
        return None

    sod = time.mktime(time.localtime(now)[:3] + (0, 0, 0, 0, 0, -1))
    sow = now - (time.localtime(now).tm_wday * 86400)
    soy = time.mktime(time.strptime(f"{time.localtime().tm_year}-01-01", "%Y-%m-%d"))

    return current, closest(sod), closest(sow), closest(soy), high

# 🎙 יצירת MP3
async def create_mp3(text, filename):
    tts = edge_tts.Communicate(text, "he-IL-AvriNeural")
    await tts.save(filename)

# 🎛 המרה ל-WAV
def convert_to_wav(mp3_path, wav_path):
    subprocess.run([
        "ffmpeg", "-y", "-i", mp3_path,
        "-ac", "1", "-ar", "8000", "-sample_fmt", "s16", wav_path
    ])

# ⬆️ העלאה לימות המשיח
def upload_to_yemot(wav_path, target_path):
    m = MultipartEncoder(
        fields={
            'token': token,
            'path': target_path + os.path.basename(wav_path),
            'upload': (os.path.basename(wav_path), open(wav_path, 'rb'), 'audio/wav')
        }
    )
    r = requests.post(
        'https://www.call2all.co.il/ym/api/UploadFile',
        data=m,
        headers={'Content-Type': m.content_type}
    )
    if r.status_code == 200 and 'OK' in r.text:
        print(f"✅ הועלה בהצלחה: {os.path.basename(wav_path)}")
    else:
        print(f"❌ שגיאה בהעלאה ({os.path.basename(wav_path)}):", r.text)

# ▶️ ריצה כוללת
async def main():
    for item in symbols_data:
        try:
            name = item["name"]
            symbol = item["symbol"]
            type_ = item["type"]
            path = item["target_path"]

            current, day, week, year, high = get_data(symbol)
            text = generate_text(name, symbol, type_, current, day, week, year, high)

            mp3_file = f"{symbol}.mp3"
            wav_file = f"{symbol}.wav"

            print(f"🎙️ יוצר עבור {name} ({symbol})")
            await create_mp3(text, mp3_file)
            convert_to_wav(mp3_file, wav_file)
            upload_to_yemot(wav_file, path)
        except Exception as e:
            print(f"⚠️ שגיאה עם {item['name']} ({item['symbol']}):", e)

asyncio.run(main())
