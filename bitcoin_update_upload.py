import edge_tts
import asyncio
import subprocess
import requests
import json
import time
from requests_toolbelt.multipart.encoder import MultipartEncoder

# 🟡 פונקציה לשליפת טוקן עדכני מה-API של ימות
def get_token_from_yemot():
    try:
        url = "https://www.call2all.co.il/ym/api/Login?username=0733181201&password=6714453"
        response = requests.get(url)
        data = response.json()
        if data.get("responseStatus") == "OK":
            print("🔑 טוקן נטען בהצלחה")
            return data.get("token")
        else:
            print("❌ שגיאה בשליפת טוקן:", data)
            return None
    except Exception as e:
        print("❌ שגיאה כללית בשליפת טוקן:", e)
        return None

# 🔐 טוקן התחלתי
token = get_token_from_yemot()

# 📥 טוען את רשימת הסימבולים מהקובץ
with open("symbols.json", "r", encoding="utf-8") as f:
    SYMBOLS = json.load(f)

# 📢 התאמת פתיח לפי סוג הנייר
def get_intro_line(name, price_txt, data_type):
    if data_type == "crypto":
        return f"ה{name} נסחר בשער של {price_txt} דולר."
    elif data_type == "index":
        return f"מדד ה{name} עומד כעת על {price_txt} נקודות."
    elif data_type == "stock_us":
        return f"מניית {name} נסחרת כעת בשווי {price_txt} דולר."
    elif data_type == "stock_il":
        return f"מניית {name} נסחרת כעת בשווי {price_txt} שקלים חדשים."
    elif data_type == "energy":
        return f"מחיר ה{name} עומד כעת על {price_txt} דולר לחבית."
    elif data_type == "precious_metal":
        return f"מחיר ה{name} עומד כעת על {price_txt} דולר לאונקיה."
    elif data_type == "copper":
        return f"מחיר הנחושת עומד כעת על {price_txt} דולר לפאונד."
    elif data_type == "industrial_metal":
        return f"מחיר ה{name} עומד כעת על {price_txt} דולר לטון."
    elif data_type == "agriculture":
        return f"מחיר ה{name} עומד כעת על {price_txt} דולר."
    elif data_type == "futures":
        return f"החוזה של {name} עומד כעת על {price_txt} דולר."
    elif data_type == "forex":
        return f"אחד {name} שווה ל{price_txt} שקלים חדשים."
    else:
        return f"{name} עומד כעת על {price_txt}."

# 📊 בניית טקסט מלא להקראה
def get_text(symbol, name, data_type):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=6mo&interval=1d"
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
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
            return f"{sign} של {str(abs_change).replace('.', ' נקודה ')} אחוז"

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
        intro = get_intro_line(name, price_txt, data_type)
        change_day = format_change(current_price, price_day)
        change_week = format_change(current_price, price_week)
        change_year = format_change(current_price, price_year)

        dist_txt = ""
        if year_high:
            diff = ((current_price - year_high) / year_high) * 100
            dist_txt = str(abs(diff)).replace(".", " נקודה ") + " אחוז"

        return (
            f"{intro} "
            f"מאז תחילת היום נרשמה {change_day}. "
            f"מתחילת השבוע נרשמה {change_week}. "
            f"מתחילת השנה נרשמה {change_year}. "
            f"המחיר הנוכחי רחוק מהשיא ב{dist_txt}."
        )

    except Exception as e:
        print(f"❌ שגיאה בנתונים עבור {symbol}: {e}")
        return f"{name} - נתונים לא זמינים."

# 📤 העלאה לימות המשיח
def upload_to_yemot(branch, wav_file):
    global token
    path = f"ivr2:/{branch}/M0000.wav"

    def send(token_now):
        m = MultipartEncoder(
            fields={
                'token': token_now,
                'path': path,
                'upload': ('M0000.wav', open(wav_file, 'rb'), 'audio/wav')
            }
        )
        return requests.post(
            'https://www.call2all.co.il/ym/api/UploadFile',
            data=m,
            headers={'Content-Type': m.content_type}
        )

    r = send(token)
    if r.status_code == 200 and 'OK' in r.text:
        print(f"✅ הועלה בהצלחה לשלוחה {branch}")
    else:
        print("⚠️ טוקן לא תקף – מנסה לחדש...")
        token = get_token_from_yemot()
        r2 = send(token)
        if r2.status_code == 200 and 'OK' in r2.text:
            print(f"✅ הועלה בהצלחה לאחר ניסיון נוסף לשלוחה {branch}")
        else:
            print(f"❌ כישלון בהעלאה גם לאחר רענון טוקן: {r2.text}")

# ▶️ ביצוע מלא לנייר בודד
async def process_symbol(symbol, name, branch, data_type):
    text = get_text(symbol, name, data_type)
    print(f"📡 [{symbol}] {text}")
    mp3_file = f"{symbol}.mp3"
    wav_file = f"{symbol}.wav"
    tts = edge_tts.Communicate(text, "he-IL-AvriNeural")
    await tts.save(mp3_file)
    subprocess.run(["ffmpeg", "-y", "-i", mp3_file, "-ac", "1", "-ar", "8000", "-sample_fmt", "s16", wav_file])
    upload_to_yemot(branch, wav_file)

# ▶️ הרצת כל הסימבולים ברשימה
async def main():
    tasks = []
    for symbol, info in SYMBOLS.items():
        tasks.append(process_symbol(symbol, info['name'], info['branch'], info['type']))
    await asyncio.gather(*tasks)

asyncio.run(main())
