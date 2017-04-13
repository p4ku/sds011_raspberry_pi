import sys
import time
import json
import datetime
import logging
import subprocess
import traceback
import argparse
import paho.mqtt.client as paho
from lib.sds011 import SDS011 as Sensor

SAMPLES = 25
WAKEUP_TIME = 35
SLEEP_TIME = 9 * 60  # 9min

UNIT = '\xc2\xb5g/m3'  # ug/m3
SIGMA = '\xcf\x83'     # sigma
log_template = 'PM10:{:.2f} {} {}: {:.2f}, PM2.5: {:.2f} {} {}: {:.2f}'


def cacert_location():
    return subprocess.check_output('curl-config --ca', shell=True).strip()


def on_connect(client, userdata, flags, rc):
    print('MQTT connected')


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


def main(mqtt_broker, mqtt_port, mqtt_username, mqtt_password):
    sensor = Sensor('/dev/ttyS1')

    if mqtt_broker and mqtt_port and mqtt_username and mqtt_password:
        mqtt_channel = "devices/" + mqtt_username
        client = paho.Client()
        client.username_pw_set(mqtt_username,  mqtt_password)
        client.tls_set(cacert_location())
        client.on_connect = on_connect
        client.connect(mqtt_broker, mqtt_port)
        client.loop_start()
    else:
        client = None

    print('Start measurement')
    sensor.wake_up()

    while True:
        try:
            """
               Measurement steps:

               1. Wake up
               2. Wait 35s
               3. Sample data 25 slmples ~25s
               4. Sleep 9min 30s
            """
            PM10_samples = []
            PM25_samples = []

            # Wake up sensor, wait 35s
            sensor.wake_up()
            time.sleep(WAKEUP_TIME)

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
                "version": 1,
                "data": [
                    {
                        "kind": "pm25",
                        "value": round(mean(PM25_samples), 2),
                        "dev": round(stddev(PM25_samples), 2)
                    },
                    {
                        "kind": "pm10",
                        "value": round(mean(PM10_samples), 2),
                        "dev": round(stddev(PM10_samples), 2)
                    }
                ]
            }
            payload = json.dumps(data)
            if client:
                msg_info = client.publish(mqtt_channel, payload, qos=1)
                print('Publish to MQTT channel: {}'.format(mqtt_channel))

        except KeyboardInterrupt:
            if client:
                client.disconnect()
                client.loop_stop()
            sys.exit(0)
        except:
            print(traceback.format_exc())

        # Put sensor into sleep mode
        sensor.sleep()
        time.sleep(SLEEP_TIME)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--mqtt-broker', help='MQTT broker',
                        default='broker.less-smog.xyz')
    parser.add_argument('--mqtt-port', help='MQTT port', default=8883)
    parser.add_argument('--mqtt-username', help='MQTT username', default=None)
    parser.add_argument('--mqtt-password', help='MQTT password', default=None)
    args = parser.parse_args()
    main(args.mqtt_broker, args.mqtt_port,
         args.mqtt_username, args.mqtt_password)
