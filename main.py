import sys
import time
import datetime
import logging
import traceback
from sds011 import SDS011 as Sensor

SAMPLES = 20
UNIT = '\xc2\xb5g/m3'  # ug/m3
SIGMA = '\xcf\x83'     # sigma
log_template = 'PM10:{:.2f} {} {}: {:.2f}, PM2.5: {:.2f} {} {}: {:.2f}'


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

    while True:
        try:
            PM10_samples = []
            PM25_samples = []
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

        except KeyboardInterrupt:
            sys.exit(0)
        except:
            print(traceback.format_exc())

        time.sleep(60)


if __name__ == "__main__":
    main()
