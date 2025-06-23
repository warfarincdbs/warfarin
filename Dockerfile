# ✅ ใช้ Python 3.10
FROM python:3.10-slim

# ✅ ตั้ง working directory
WORKDIR /app

# ✅ คัดลอกไฟล์ทั้งหมดจาก repo เข้า container
COPY . /app

# ✅ ติดตั้ง package จาก requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# ✅ สั่งให้รัน Flask ด้วย app.py
CMD ["python", "app.py"]
