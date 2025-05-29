import edge_tts
import asyncio
import subprocess
import requests
import os
from requests_toolbelt.multipart.encoder import MultipartEncoder
import time

# 🔄 שליפת טוקן מעודכן במידת הצורך
def get_token():
    try:
        res = requests.get("https://www.call2all.co.il/ym/api/Login?username=0733181201&password=6714453", timeout=10)
        token = res.json().get("token")
        if token:
            print("🔑 טוקן חדש נשלף בהצלחה")
            return token
        else:
            print("❌ לא הצליח לשאוב טוקן")
    except Exception as e:
        print("❌ שגיאה בשליפת טוקן:", e)
    return None

# 📤 העלאה לימות המשיח
def upload_to_yemot(wav_path, target_path, token):
    try:
        m = MultipartEncoder(
            fields={
                'token': token,
                'path': target_path + os.path.basename(wav_path),
                'upload': (os.path.basename(wav_path), open(wav_path, 'rb'), 'audio/wav')
            }
        )
        response = requests.post(
            'https://www.call2all.co.il/ym/api/UploadFile',
            data=m,
            headers={'Content-Type': m.content_type}
        )
        if 'token' in response.text and 'invalid' in response.text.lower():
            print("🔁 טוקן לא תקף – מנסה לשלוף חדש...")
            new_token = get_token()
            if new_token:
                upload_to_yemot(wav_path, target_path, new_token)
        elif 'OK' in response.text:
            print(f"✅ הקובץ הועלה בהצלחה ל־{target_path}")
        else:
            print(f"❌ שגיאה בהעלאה: {response.text}")
    except Exception as e:
        print("❌ שגיאה בהעלאה לימות:", e)

# 🔢 המרה של מספר למילים
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

# 🧠 חישוב שינויים
def format_change(current, previous):
    if previous is None or previous == 0:
        return "אין נתון זמין"
    change = ((current - previous) / previous) * 100
    sign = "עלייה" if change > 0 else "ירידה" if change < 0 else "שינוי אפסי"
    abs_change = abs(change)
    change_text = "אחוז" if round(abs_change, 2) == 1.00 else f"{abs_change:.2f}".replace(".", " נקודה ") + " אחוז"
    return f"{sign} של {change_text}"

# 🔄 שליפת נתונים מ-Yahoo לפי סמל
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

        price_txt = spell_price(current_price)
        change_day = format_change(current_price, price_day)
        change_week = format_change(current_price, price_week)
        change_year = format_change(current_price, price_year)

        dist_txt = ""
        if year_high:
            diff = ((current_price - year_high) / year_high) * 100
            abs_diff = abs(diff)
            dist_txt = f"{abs_diff:.2f}".replace(".", " נקודה ") + " אחוז"

        if type_ == "crypto":
            return f"ה{ name } עומד כעת על { price_txt } דולר. מאז תחילת היום נרשמה { change_day }. מתחילת השבוע נרשמה { change_week }. מתחילת השנה נרשמה { change_year }. המחיר הנוכחי רחוק מהשיא ב{ dist_txt }."
        elif type_ == "stock_us":
            return f"מניית { name } נסחרת כעת בשווי של { price_txt } דולר. מאז תחילת היום נרשמה { change_day }. מתחילת השבוע נרשמה { change_week }. מתחילת השנה נרשמה { change_year }. המחיר הנוכחי רחוק מהשיא ב{ dist_txt }."
        else:
            return "סוג לא נתמך כרגע."

    except Exception as e:
        print("❌ שגיאה בשליפת נתונים:", e)
        return f"{name} עומדת כעת על נתון לא זמין."

# 🎙 יצירת MP3
async def create_mp3(text, filename):
    print(f"🎙️ יוצר MP3 עבור {filename}...")
    tts = edge_tts.Communicate(text, "he-IL-AvriNeural")
    await tts.save(f"{filename}.mp3")

# 🎚 המרה ל־WAV
def convert_to_wav(mp3_path, wav_path):
    subprocess.run([
        "ffmpeg", "-y", "-i", mp3_path,
        "-ac", "1", "-ar", "8000", "-sample_fmt", "s16",
        wav_path
    ])

# ▶️ הפעלה
async def main():
    items = [
        {"name": "ביטקוין", "symbol": "BTC-USD", "type": "crypto", "target_path": "ivr2:/8/"},
        {"name": "אנבידיה", "symbol": "NVDA", "type": "stock_us", "target_path": "ivr2:/7/"}
    ]

    token = get_token()

    for item in items:
        text = get_text(item["name"], item["symbol"], item["type"])
        mp3_file = f"{item['symbol']}.mp3"
        wav_file = f"{item['symbol']}.wav"
        await create_mp3(text, item["symbol"])
        convert_to_wav(mp3_file, wav_file)
        upload_to_yemot(wav_file, item["target_path"], token)

asyncio.run(main())
