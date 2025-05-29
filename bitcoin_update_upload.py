import edge_tts
import asyncio
import subprocess
import requests
import json
from requests_toolbelt.multipart.encoder import MultipartEncoder
import time
import os

# 🟡 טוקן קבוע (מתעדכן אם צריך)
token = '2yqvFAr7E9rVPGyk'

def refresh_token_if_needed():
    global token
    test_upload = requests.post(
        'https://www.call2all.co.il/ym/api/UploadFile',
        data={'token': token, 'path': 'ivr2:/test', 'upload': ('test.wav', b'abc', 'audio/wav')}
    )
    if 'User not found or token expired' in test_upload.text:
        print("♻️ טוקן לא תקין – מנסה לשלוף חדש...")
        try:
            response = requests.get("https://www.call2all.co.il/ym/api/Login?username=0733181201&password=6714453")
            token = response.json().get("token")
            print("✅ טוקן עודכן:", token)
        except:
            print("❌ שגיאה בשליפת טוקן חדש")

# 🔄 פונקציית שליפת נתונים
def get_yahoo_text(symbol, name, item_type):
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
            change_text = f"{abs_change:.2f}".replace(".", " נקודה ") + " אחוז"
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

        # ניסוח לפי סוג
        if item_type == "crypto":
            text = f"ה{ name } עומד כעת על {price_txt} דולר. "
        elif item_type == "stock_us":
            text = f"מניית { name } נסחרת כעת בשווי של {price_txt} דולר. "
        elif item_type == "stock_il":
            text = f"מניית { name } נסחרת כעת בשווי של {price_txt} שקלים חדשים. "
        else:
            text = f"{ name } בשווי {price_txt}."

        text += (
            f"מאז תחילת היום נרשמה {change_day}. "
            f"מתחילת השבוע נרשמה {change_week}. "
            f"מתחילת השנה נרשמה {change_year}. "
            f"המחיר הנוכחי רחוק מהשיא ב{dist_txt}."
        )
        return text

    except Exception as e:
        print("❌ שגיאה בשליפת נתונים:", e)
        return f"{name} - נתון לא זמין כרגע."

# 🎙 יצירת MP3
async def create_mp3(text, filename):
    tts = edge_tts.Communicate(text, "he-IL-AvriNeural")
    await tts.save(filename)

# 🎛 המרה ל-WAV
def convert_to_wav(mp3_file, wav_file):
    subprocess.run([
        "ffmpeg", "-y",
        "-i", mp3_file,
        "-ac", "1",
        "-ar", "8000",
        "-sample_fmt", "s16",
        wav_file
    ])

# 📤 העלאה לימות
def upload_to_yemot(wav_file, path):
    m = MultipartEncoder(
        fields={
            'token': token,
            'path': path + "000.wav",
            'upload': (wav_file, open(wav_file, 'rb'), 'audio/wav')
        }
    )
    response = requests.post(
        'https://www.call2all.co.il/ym/api/UploadFile',
        data=m,
        headers={'Content-Type': m.content_type}
    )
    if response.status_code == 200 and 'OK' in response.text:
        print(f"✅ הועלה בהצלחה ל־{path}")
    else:
        print("❌ שגיאה בהעלאה:", response.text)

# ▶️ הרצה עיקרית
async def main():
    refresh_token_if_needed()

    with open("stock_items.json", encoding="utf-8") as f:
        items = json.load(f)

    for item in items:
        print(f"🔄 מטפל ב־{item['name']} ({item['symbol']})")
        text = get_yahoo_text(item['symbol'], item['name'], item['type'])

        mp3_file = "temp.mp3"
        wav_file = "temp.wav"

        await create_mp3(text, mp3_file)
        convert_to_wav(mp3_file, wav_file)
        upload_to_yemot(wav_file, item['target_path'])

asyncio.run(main())
