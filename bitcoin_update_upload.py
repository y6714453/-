import edge_tts
import asyncio
import subprocess
import requests
from requests_toolbelt.multipart.encoder import MultipartEncoder
import time

# ✅ טוקן קבוע של ימות המשיח
token = "2yqvFAr7E9rVPGyk"

# 🔁 פונקציה לשליפת טקסט עבור נייר ערך
def get_text(name, symbol, type_):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=6mo&interval=1d"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        data = response.json()['chart']['result'][0]

        current_price = data['meta']['regularMarketPrice']
        year_high = data['meta'].get('fiftyTwoWeekHigh', None)
        timestamps = data['timestamp']
        prices = data['indicators']['quote'][0]['close']

        now = time.time()

        def closest_price(target):
            for t, p in zip(reversed(timestamps), reversed(prices)):
                if t <= target and p is not None:
                    return p
            return None

        start_of_day = time.mktime(time.localtime(now)[:3] + (0, 0, 0, 0, 0, -1))
        start_of_week = now - (time.localtime(now).tm_wday * 86400)
        start_of_year = time.mktime(time.strptime(f"{time.localtime().tm_year}-01-01", "%Y-%m-%d"))

        price_day = closest_price(start_of_day)
        price_week = closest_price(start_of_week)
        price_year = closest_price(start_of_year)

        def format_change(current, previous):
            if previous is None or previous == 0:
                return "אין נתון זמין"
            change = ((current - previous) / previous) * 100
            sign = "עלייה" if change > 0 else "ירידה" if change < 0 else "שינוי אפסי"
            abs_change = abs(change)
            change_text = "אחוז" if round(abs_change, 2) == 1.00 else f"{abs_change:.2f}".replace(".", " נקודה ") + " אחוז"
            return f"{sign} של {change_text}"

        def spell_price(p):
            p = round(p)
            th = p // 1000
            r = p % 1000
            if th == 0:
                return f"{r}"
            elif th == 1:
                return f"אלף ו{r}" if r else "אלף"
            elif th == 2:
                return f"אלפיים ו{r}" if r else "אלפיים"
            else:
                return f"{th} אלף ו{r}" if r else f"{th} אלף"

        price_txt = spell_price(current_price)
        change_day = format_change(current_price, price_day)
        change_week = format_change(current_price, price_week)
        change_year = format_change(current_price, price_year)

        dist_txt = ""
        if year_high:
            diff = ((current_price - year_high) / year_high) * 100
            abs_diff = abs(diff)
            dist_txt = f"{abs_diff:.2f}".replace(".", " נקודה ") + " אחוז"

        if type_ == "קריפטו":
            text = (
                f"ה{ name } נסחר בשער של {price_txt} דולר. "
                f"מאז תחילת היום נרשמה {change_day}. "
                f"מתחילת השבוע נרשמה {change_week}. "
                f"מתחילת השנה נרשמה {change_year}. "
                f"המחיר הנוכחי רחוק מהשיא ב{dist_txt}."
            )
        elif type_ == "stock_us":
            text = (
                f"מניית { name } נסחרת כעת בשווי של {price_txt} דולר. "
                f"מאז תחילת היום נרשמה {change_day}. "
                f"מתחילת השבוע נרשמה {change_week}. "
                f"מתחילת השנה נרשמה {change_year}. "
                f"המחיר הנוכחי רחוק מהשיא ב{dist_txt}."
            )
        else:
            text = f"{ name } עומד על {price_txt}."

        return text

    except Exception as e:
        print(f"שגיאה עם {name} ({symbol}):", e)
        return f"{name} – הנתון אינו זמין כרגע."

# 🧠 רשימת ניירות ערך (ישירות בתוך הקוד)
items = [
    {"name": "ביטקוין", "symbol": "BTC-USD", "type": "קריפטו", "target_path": "ivr2:/8/"},
    {"name": "אנבידיה", "symbol": "NVDA", "type": "stock_us", "target_path": "ivr2:/7/"}
]

# 📤 העלאה לימות
def upload_to_yemot(wav_path, target_path, symbol):
    print(f"📤 מעלה לימות ({symbol})...")
    m = MultipartEncoder(
        fields={
            'token': token,
            'path': target_path + f"{symbol}.wav",
            'upload': (f"{symbol}.wav", open(wav_path, 'rb'), 'audio/wav')
        }
    )
    response = requests.post(
        'https://www.call2all.co.il/ym/api/UploadFile',
        data=m,
        headers={'Content-Type': m.content_type}
    )
    if response.status_code == 200 and 'OK' in response.text:
        print(f"✅ הועלה בהצלחה ({symbol})!")
    else:
        print("❌ שגיאה בהעלאה:", response.text)

# 🎙 יצירת MP3
async def create_mp3(text, filename):
    print("🎙️ מייצר MP3...")
    tts = edge_tts.Communicate(text, "he-IL-AvriNeural")
    await tts.save(filename)
    print("✅ MP3 נוצר:", filename)

# 🎛 המרה ל-WAV
def convert_to_wav(mp3_path, wav_path):
    print("🔁 ממיר ל-WAV...")
    subprocess.run([
        "ffmpeg",
        "-y",
        "-i", mp3_path,
        "-ac", "1",
        "-ar", "8000",
        "-sample_fmt", "s16",
        wav_path
    ])
    print("✅ WAV מוכן:", wav_path)

# ▶️ הפעלת התהליך
async def main():
    for item in items:
        symbol = item["symbol"]
        text = get_text(item["name"], symbol, item["type"])
        print(f"📝 טקסט עבור {item['name']}:\n{text}\n")
        mp3_file = f"{symbol}.mp3"
        wav_file = f"{symbol}.wav"
        await create_mp3(text, mp3_file)
        convert_to_wav(mp3_file, wav_file)
        upload_to_yemot(wav_file, item["target_path"], symbol)

asyncio.run(main())
