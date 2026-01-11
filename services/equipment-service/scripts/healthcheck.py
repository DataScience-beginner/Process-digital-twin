#!/usr/bin/env python3
import socket
import sys
import time
import urllib.request
import urllib.error

MQTT_HOST = "localhost"
MQTT_PORT = 1883
INFLUX_URL = "http://localhost:8086"
INFLUX_TOKEN = "influx-token"
INFLUX_ORG = "dcs"
INFLUX_BUCKET = "refinery"


def check_tcp(host, port, timeout=3):
    try:
        s = socket.create_connection((host, port), timeout)
        s.close()
        return True, None
    except Exception as e:
        return False, str(e)


def influx_write_test(token, org, bucket, url):
    ts = int(time.time())
    data = f"health_check,host=health value=1 {ts}\n"
    write_url = f"{url}/api/v2/write?org={org}&bucket={bucket}&precision=s"
    req = urllib.request.Request(write_url, data=data.encode("utf-8"), method="POST")
    req.add_header("Authorization", f"Token {token}")
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.getcode() == 204, f"write_status={resp.getcode()}"
    except urllib.error.HTTPError as he:
        return False, f"HTTPError:{he.code}:{he.reason}"
    except Exception as e:
        return False, str(e)


def influx_query_test(token, org, url):
    flux = "from(bucket:\"refinery\") |> range(start: -5m) |> filter(fn: (r) => r._measurement == \"health_check\") |> last()"
    query_url = f"{url}/api/v2/query?org={org}"
    req = urllib.request.Request(query_url, data=flux.encode("utf-8"), method="POST")
    req.add_header("Authorization", f"Token {token}")
    req.add_header("Content-Type", "application/vnd.flux")
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            body = resp.read().decode("utf-8")
            return ("health_check" in body) or ("_measurement" in body), body
    except urllib.error.HTTPError as he:
        return False, f"HTTPError:{he.code}:{he.reason}"
    except Exception as e:
        return False, str(e)


def main():
    ok, msg = check_tcp(MQTT_HOST, MQTT_PORT)
    if ok:
        print(f"MQTT TCP connect: OK ({MQTT_HOST}:{MQTT_PORT})")
    else:
        print(f"MQTT TCP connect: FAIL -> {msg}")

    ok_w, msg_w = influx_write_test(INFLUX_TOKEN, INFLUX_ORG, INFLUX_BUCKET, INFLUX_URL)
    if ok_w:
        print("Influx write: OK")
    else:
        print(f"Influx write: FAIL -> {msg_w}")

    ok_q, msg_q = influx_query_test(INFLUX_TOKEN, INFLUX_ORG, INFLUX_URL)
    if ok_q:
        print("Influx query: OK")
    else:
        print(f"Influx query: FAIL -> {msg_q}")

    if ok and ok_w and ok_q:
        print("HEALTHCHECK: OK")
        sys.exit(0)
    else:
        print("HEALTHCHECK: FAIL")
        sys.exit(2)


if __name__ == '__main__':
    main()
