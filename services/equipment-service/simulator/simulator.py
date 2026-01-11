import os
import time
import json
import random
import socket
from paho.mqtt import client as mqtt_client

BROKER = os.getenv('MQTT_BROKER', 'mosquitto')
PORT = int(os.getenv('MQTT_PORT', '1883'))
CLIENT_ID = f"simulator-{socket.gethostname()}"
TOPIC = "factory/refinery/sensor"
INTERVAL = float(os.getenv('PUBLISH_INTERVAL', '1'))

mqtt_user = os.getenv('MQTT_USER', '')
mqtt_pass = os.getenv('MQTT_PASS', '')

client = mqtt_client.Client(CLIENT_ID)
if mqtt_user:
    client.username_pw_set(mqtt_user, mqtt_pass)


def connect():
    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            print("Connected to MQTT Broker")
        else:
            print("Failed to connect, return code %d\n", rc)

    client.on_connect = on_connect
    client.connect(BROKER, PORT)


def generate_message():
    timestamp = int(time.time() * 1000)
    device_id = "sensor-01"
    metrics = {
        "temperature": round(50 + random.uniform(-5, 5), 2),
        "pressure": round(10 + random.uniform(-1, 1), 3),
        "flow": round(100 + random.uniform(-10, 10), 2)
    }
    payload = {
        "timestamp": timestamp,
        "device_id": device_id,
        "metrics": metrics
    }
    return json.dumps(payload)


def run():
    connect()
    client.loop_start()
    try:
        while True:
            msg = generate_message()
            result = client.publish(TOPIC, msg)
            status = result[0]
            if status == 0:
                print(f"Sent `{msg}` to topic `{TOPIC}`")
            else:
                print(f"Failed to send message to topic {TOPIC}")
            time.sleep(INTERVAL)
    except KeyboardInterrupt:
        print("Simulator stopping...")
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == '__main__':
    run()
