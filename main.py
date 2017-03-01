import sys
import time
import json
import datetime
import logging
import traceback
import paho.mqtt.client as paho
from sds011 import SDS011 as Sensor

SAMPLES = 25
UNIT = '\xc2\xb5g/m3'  # ug/m3
SIGMA = '\xcf\x83'     # sigma
log_template = 'PM10:{:.2f} {} {}: {:.2f}, PM2.5: {:.2f} {} {}: {:.2f}'

MQTT_BROKER = "broker.mqttdashboard.com"
MQTT_PORT = 1883
MQTT_USERNAME = ""
MQTT_PASSWORD = ""
MQTT_CHANNEL = "/sensor/123/data"


def on_publish(client, userdata, mid):
    print("mid: " + str(mid))

logger = logging.getLogger('air_quality')
hdlr = logging.FileHandler('./air_quality.log')
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
hdlr.setFormatter(formatter)
logger.addHandler(hdlr)
logger.setLevel(logging.INFO)

consoleHandler = logging.StreamHandler()
consoleHandler.setFormatter(formatter)
logger.addHandler(consoleHandler)


def mean(data):
    if len(data) == 0:
        return 0
    return sum(data) / float(len(data))


def stddev(data):
    ld = len(data)
    if ld < 2:
        return 0
    m = mean(data)
    ss = sum((x - m)**2 for x in data)
    return (ss / float(ld))**0.5


def main():
    sensor = Sensor('/dev/ttyS1')

    client = paho.Client()
    # client.tls_set("/path/to/ca.crt")
    client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    # client.on_publish = on_publish
    client.connect(MQTT_BROKER, MQTT_PORT)
    client.loop_start()

    while True:
        try:
            """
               Measurement procedure:

               1. Wake up
               2. Wait 35s
               3. Sample data 25 slmples ~25s
               4. Sleep 9min 30s
            """
            PM10_samples = []
            PM25_samples = []

            # Wake up sensor, wait 30s
            sensor.wake_up()
            time.sleep(35)

            # Sampling sensor
            for i in range(SAMPLES):
                PM10, PM25 = sensor.read()
                PM10_samples.append(PM10)
                PM25_samples.append(PM25)
                time.sleep(0.1)

            logger.info(log_template.format(mean(PM10_samples),
                                            UNIT,
                                            SIGMA,
                                            stddev(PM10_samples),
                                            mean(PM25_samples),
                                            UNIT,
                                            SIGMA,
                                            stddev(PM25_samples)))

            data = {
                # "timestamp": 1485778030,
                "protocol_version": 1,
                "data": [
                    {"type": "pm2.5", "value": mean(
                        PM25_samples), "dev": stddev(PM25_samples)},
                    {"type": "pm10", "value": mean(
                        PM10_samples), "dev": stddev(PM10_samples)}
                ]
            }
            msg_info = client.publish(MQTT_CHANNEL, json.dumps(data), qos=1)

        except KeyboardInterrupt:
            sys.exit(0)
        except:
            print(traceback.format_exc())

        # Put sensor into sleep mode
        sensor.sleep()
        time.sleep(9 * 60)


if __name__ == "__main__":
    main()
