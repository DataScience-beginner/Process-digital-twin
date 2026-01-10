#!/usr/bin/env bash
set -euo pipefail

# Script: set_influx_retention.sh
# Updates the `refinery` bucket retention to 90 days using the Influx CLI inside the running container.

DC_CMD="docker compose -f services/equipment-service/docker-compose.yml"

if ! $DC_CMD ps influxdb >/dev/null 2>&1; then
  echo "InfluxDB container not running. Start the stack first:"
  echo "  $DC_CMD up -d"
  exit 1
fi

echo "Updating InfluxDB bucket 'refinery' retention to 90d..."
$DC_CMD exec -T influxdb influx bucket update --name refinery --retention 90d --org dcs --token influx-token
echo "Done."
