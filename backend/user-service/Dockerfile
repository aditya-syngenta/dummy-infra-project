# BUG: No specific base image tag - may get unexpected updates
FROM python:3.11-slim

# BUG: Still running as root
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# BUG: Exposes wrong port documentation (actual port is 5001 not 8001)
EXPOSE 8001

# BUG: No HEALTHCHECK defined
CMD ["python", "app.py"]
