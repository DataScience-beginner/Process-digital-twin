#!/usr/bin/env bash
set -euo pipefail

# Generates a Mosquitto password file and a .env containing MQTT_USER/MQTT_PASS.
# The passwordfile and .env are created under services/equipment-service/mosquitto/

WORKDIR="$(cd "$(dirname "$0")" && pwd)"
CONFIG_DIR="$WORKDIR/config"
ENV_FILE="$WORKDIR/.env"
PASSWORD_FILE="$CONFIG_DIR/passwordfile"

if [ -f "$PASSWORD_FILE" ]; then
  echo "Password file already exists at $PASSWORD_FILE"
  echo "If you want to recreate, remove it first."
  exit 0
fi

MQTT_USER="simulator"
MQTT_PASS=$(openssl rand -base64 16)

echo "Creating Mosquitto password file for user '$MQTT_USER'..."
docker run --rm -v "$CONFIG_DIR:/mosquitto/config" eclipse-mosquitto mosquitto_passwd -b -c /mosquitto/config/passwordfile $MQTT_USER "$MQTT_PASS"

echo "Writing env file to $ENV_FILE (gitignored)."
cat > "$ENV_FILE" <<EOF
MQTT_USER=$MQTT_USER
MQTT_PASS=$MQTT_PASS
EOF

echo "Done. Credentials:"
echo "  MQTT_USER=$MQTT_USER"
echo "  MQTT_PASS=$MQTT_PASS"
echo
echo "Next: restart the stack to apply changes:" 
echo "  docker compose -f services/equipment-service/docker-compose.yml up -d mosquitto telegraf simulator"
