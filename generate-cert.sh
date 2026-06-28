#!/usr/bin/env bash
# Detecta el nombre .local y la IP local del Mac y los escribe en .env.
# El contenedor usa esos valores para generar su certificado HTTPS al arrancar.
set -e

[ -f .env ] || cp .env.example .env

HOST_NAME="$(scutil --get LocalHostName 2>/dev/null || hostname -s).local"
IP="$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || echo 127.0.0.1)"

# Reemplaza o añade LAN_HOST / LAN_IP en .env
set_var() {
  local key="$1" val="$2"
  if grep -q "^${key}=" .env; then
    sed -i '' "s|^${key}=.*|${key}=${val}|" .env
  else
    printf '%s=%s\n' "$key" "$val" >> .env
  fi
}

set_var LAN_HOST "$HOST_NAME"
set_var LAN_IP "$IP"

echo "Detectado: LAN_HOST=${HOST_NAME}  LAN_IP=${IP}"
echo "En el móvil abre:  https://${HOST_NAME}:8000/   (o https://${IP}:8000/)"
echo "La primera vez tendrás que aceptar el certificado en Safari."
