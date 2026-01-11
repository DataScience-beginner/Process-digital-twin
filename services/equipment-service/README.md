# Equipment Service - Local Demo

This folder contains the local demo for the Equipment Service stack used in the Process-digital-twin project.

Quick start

1. From repository root, start the stack:

```bash
docker compose -f services/equipment-service/docker-compose.yml up -d
```

2. Open Grafana: http://localhost:3000 (admin / refinery123)
3. Open InfluxDB UI: http://localhost:8086
4. MQTT broker: tcp://localhost:1883

Services (important)

- mosquitto (MQTT broker) — container: `dcs-mosquitto` — host ports: `1883` (MQTT), `9001` (websockets)
- telegraf — reads MQTT and writes to InfluxDB (config: `telegraf/telegraf.conf`)
- influxdb — container: `dcs-historian` — host port: `8086`, bucket `refinery`, org `dcs`
- grafana — container: `dcs-analytics` — host port: `3000` (provisioned datasource + dashboards)
- simulator — publishes telemetry to MQTT topic `factory/refinery/sensor` (1s interval)

Credentials / tokens (rotate these for production)

- Influx init token: `influx-token` (docker-compose env)
- Influx init user/password: admin / `historian123`
- Grafana admin: admin / `refinery123`
- Postgres: equipmentuser / `equipment123`

Set InfluxDB retention (recommended)

Raw telemetry retention goal: 90 days. Example CLI command to update bucket retention (requires stack running):

```bash
docker compose -f services/equipment-service/docker-compose.yml exec -T influxdb \
  influx bucket update --name refinery --retention 90d --org dcs --token influx-token
```

You can also create continuous aggregates or tasks in Influx to downsample to a long-term bucket.

Harden Mosquitto (summary)

1. Create Mosquitto password file (example uses the Mosquitto image's `mosquitto_passwd`):

```bash
docker run --rm -v "$PWD/services/equipment-service/mosquitto/config:/mosquitto/config" \
  eclipse-mosquitto mosquitto_passwd -c /mosquitto/config/passwordfile simulator
```

2. Update `services/equipment-service/mosquitto/config/mosquitto.conf`:

 - set `allow_anonymous false`
 - add a `password_file /mosquitto/config/passwordfile` line

3. Update services that publish/subscribe (simulator, telegraf) to supply `MQTT_USER` / `MQTT_PASS`.

Notes

- This README is a concise guide for local development. For production, move secrets to a secret manager (Vault/Keycloak/Secrets Manager), enable TLS/mTLS, and apply network policies.
