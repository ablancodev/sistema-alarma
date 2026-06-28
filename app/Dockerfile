FROM python:3.12-slim

# Dependencias de sistema para OpenCV (headless)
RUN apt-get update && apt-get install -y --no-install-recommends \
        libglib2.0-0 libgl1 openssl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod +x entrypoint.sh
EXPOSE 8000
ENTRYPOINT ["./entrypoint.sh"]
