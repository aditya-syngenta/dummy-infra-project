FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8002

# BUG: No HEALTHCHECK
# BUG: No non-root user
CMD ["python", "app.py"]
