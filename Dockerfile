FROM python:3.11

# התקנת ffmpeg
RUN apt-get update && apt-get install -y ffmpeg

WORKDIR /app

COPY . .

# התקנת כל התלויות
RUN pip install -r requirements.txt

CMD ["python", "bitcoin_update_upload.py"]
