# BUG: Using python:3.11 with no specific patch version (non-reproducible builds)
FROM python:3.11

# BUG: Running as root user - security risk
WORKDIR /app

# BUG: Copying everything before installing deps - poor layer caching
COPY . .

RUN pip install -r requirements.txt

# BUG: Exposing wrong port (should be 8000 but exposes 5000)
EXPOSE 5000

# BUG: No health check instruction
# BUG: Using development server instead of gunicorn
CMD ["python", "app.py"]
