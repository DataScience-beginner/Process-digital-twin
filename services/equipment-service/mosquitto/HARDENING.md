Mosquitto hardening notes
=========================

This document explains steps to harden the Mosquitto MQTT broker used by the local demo.

1) Create a Mosquitto password file

Use the `mosquitto_passwd` tool. Example (runs the tool from the docker image and writes a `passwordfile` into the config folder):

```bash
docker run --rm -v "$(pwd)/services/equipment-service/mosquitto/config:/mosquitto/config" \
  eclipse-mosquitto mosquitto_passwd -c /mosquitto/config/passwordfile simulator
```

You will be prompted for a password. The resulting `passwordfile` will be used by Mosquitto.

2) Update `mosquitto.conf`

In `services/equipment-service/mosquitto/config/mosquitto.conf` set:

```
allow_anonymous false
password_file /mosquitto/config/passwordfile
listener 1883 0.0.0.0
```

3) Update services to use credentials

- Simulator: set `MQTT_USER` and `MQTT_PASS` environment variables in `docker-compose.yml` for the `simulator` service.
- Telegraf: update `telegraf/telegraf.conf` `[[inputs.mqtt_consumer]]` section with `username = "simulator"` and `password = "<password>"`, or supply via environment variables and reference them in the config.

4) Optional: enable TLS

- Generate broker/server certs and configure `listener` with `cafile/certfile/keyfile` for TLS.
- Configure clients (simulator, telegraf) to use TLS + username/password or client certs.

5) Rotate credentials

- Keep the password file out of git; add an entry to `.gitignore` or mount from an external secret store.
