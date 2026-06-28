#!/usr/bin/env bash
set -e

# Genera un certificado autofirmado dentro del contenedor si no existe.
# Necesario para que la cámara web (getUserMedia) funcione por HTTPS en la LAN.
if [ ! -f /certs/cert.pem ] || [ ! -f /certs/key.pem ]; then
    HOST="${CERT_HOST:-localhost}"
    IP="${CERT_IP:-127.0.0.1}"
    echo "[entrypoint] Generando certificado para ${HOST} / ${IP}"
    openssl req -x509 -newkey rsa:2048 -nodes \
        -keyout /certs/key.pem -out /certs/cert.pem -days 825 \
        -subj "/CN=${HOST}" \
        -addext "subjectAltName=DNS:${HOST},DNS:localhost,IP:${IP},IP:127.0.0.1" \
        2>/dev/null
fi

echo "[entrypoint] Arrancando en HTTPS (puerto 8000)"
exec uvicorn main:app --host 0.0.0.0 --port 8000 \
    --ssl-certfile /certs/cert.pem --ssl-keyfile /certs/key.pem
