FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# BUG: Port mismatch with actual app port (app runs on 8003)
EXPOSE 8003

CMD ["python", "app.py"]
