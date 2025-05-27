import requests
import subprocess
import asyncio
from gtts import gTTS

# === הגדרות קבועות ===
TEXT_TO_SPEAK = """
הָבִּיטְקוֹיְן עומד כעת על 110 אלף ו494 דולר. מתחילת היום נרשמה עלייה של 0 נקודה 96 אחוז.
מתחילת השבוע נרשמה עלייה של 0 נקודה 96 אחוז. בשלושת החודשים האחרונים נרשמה עלייה של 17 נקודה 02 אחוז.
המחיר הנוכחי רחוק מהשיא ב1 נקודה 32 אחוז.
"""

MP3_FILENAME = "btc_temp.mp3"
WAV_FILENAME = "M0000.wav"
YEMOT_PATH = f"8/{WAV_FILENAME}"  # שלוחה 8 לדוגמה
YEMOT_TOKEN = "yS6TJRLU8TyNRGgO"  # ← כאן תכניס תמיד את הטוקן התקף

# === פונקציה: יצירת MP3 ===
def generate_mp3():
    print("🎙️ מייצר MP3...")
    tts = gTTS(text=TEXT_TO_SPEAK, lang="he")
    tts.save(MP3_FILENAME)
    print("✅ נוצר קובץ MP3")

# === פונקציה: המרה ל-WAV עם ffmpeg ===
def convert_to_wav():
    print("🔁 ממיר ל-WAV...")
    subprocess.run([
        "ffmpeg",
        "-y",
        "-i", MP3_FILENAME,
        "-ar", "8000",
        "-ac", "1",
        WAV_FILENAME
    ])
    print(f"✅ מוכן: {WAV_FILENAME}")

# === פונקציה: מחיקת הקובץ הקודם בימות ===
def delete_old_file():
    print("🧹 מוחק קובץ קודם (אם קיים)...")
    response = requests.post("https://www.call2all.co.il/ym/api/DelFile", data={
        "token": YEMOT_TOKEN,
        "path": YEMOT_PATH
    })
    print("🔽 תגובת מחיקה:", response.text)

# === פונקציה: העלאה לימות המשיח ===
def upload_to_yemot():
    print("📤 מעלה לימות...")
    with open(WAV_FILENAME, 'rb') as f:
        files = {'file': (WAV_FILENAME, f)}
        data = {'token': YEMOT_TOKEN, 'path': YEMOT_PATH}
        response = requests.post('https://www.call2all.co.il/ym/api/UploadFile', data=data, files=files)
        print("🔼 תגובת העלאה:", response.text)

# === הפונקציה הראשית ===
async def main():
    generate_mp3()
    convert_to_wav()
    delete_old_file()
    upload_to_yemot()

# === הפעלת התוכנית ===
if __name__ == "__main__":
    asyncio.run(main())
