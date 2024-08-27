import random, json, time, logging, sys, getopt, os
import string
from paho.mqtt import client as mqtt_client
from functools import reduce

FORMAT = '%(asctime)s:%(levelname)s: %(message)s'
logging.basicConfig(stream=sys.stdout, level="INFO", format=FORMAT)
log = logging.getLogger("")
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("requests").setLevel(logging.WARNING)

sf_device_id = os.environ.get('SF_DEVICE_ID',None)
sf_product_id = os.environ.get('SF_PRODUCT_ID',"73bkTV")
mqtt_user = os.environ.get('MQTT_USER',None)
mqtt_pwd = os.environ.get('MQTT_PWD',None)
mqtt_host = os.environ.get('MQTT_HOST',None)
mqtt_port = os.environ.get('MQTT_PORT',1883)
report_topic = None
devices = set()

def on_message(client, userdata, msg):
    global devices
    global sf_product_id

    if sf_product_id in msg.topic:
        device_id = msg.topic.split('/')[2]
        devices.add(device_id)
        payload = json.loads(msg.payload.decode())
        if "properties" in payload:
            props = payload["properties"]
            for prop, val in props.items():
                client.publish(f'solarflow-hub/{device_id}/telemetry/{prop}',val)

        if "packData" in payload:
            packdata = payload["packData"]
            if len(packdata) > 0:
                for pack in packdata:
                    sn = pack.pop('sn')
                    for prop, val in pack.items():
                        client.publish(f'solarflow-hub/{device_id}/telemetry/batteries/{sn}/{prop}',val)

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        log.info("Connected to MQTT Broker!")
        subscribe(client)
    else:
        log.error("Failed to connect, return code %d\n", rc)

def connect_mqtt() -> mqtt_client:
    id = ''.join(random.choices(string.ascii_lowercase, k=5))
    client = mqtt_client.Client(mqtt_client.CallbackAPIVersion.VERSION1,f'zen-topic-remap-{id}')
    if mqtt_user is not None and mqtt_pwd is not None:
        client.username_pw_set(mqtt_user, mqtt_pwd)
    client.on_connect = on_connect
    client.connect(mqtt_host, mqtt_port)
    return client

def subscribe(client: mqtt_client):
    client.subscribe(report_topic)
    client.on_message = on_message
    #client.publish(f'iot/{sf_product_id}/{sf_device_id}/properties/read','{"properties": ["getAll"]}')

def run():
    global devices
    global sf_product_id
    client = connect_mqtt()
    client.loop_start()

    while True:
        for device in devices:
            client.publish(f'iot/{sf_product_id}/{device}/properties/read','{"properties": ["getAll"]}')
        time.sleep(60)


def main(argv):
    global mqtt_host, mqtt_port, mqtt_user, mqtt_pwd
    global sf_device_id
    global sf_product_id
    global report_topic
    opts, args = getopt.getopt(argv,"hb:p:u:s:d:s:",["broker=","port=","user=","password=","device=","smartmeter="])
    for opt, arg in opts:
        if opt == '-h':
            log.info('solarflow-control.py -b <MQTT Broker Host> -p <MQTT Broker Port>')
            sys.exit()
        elif opt in ("-b", "--broker"):
            mqtt_host = arg
        elif opt in ("-p", "--port"):
            mqtt_port = arg
        elif opt in ("-u", "--user"):
            mqtt_user = arg
        elif opt in ("-s", "--password"):
            mqtt_pwd = arg
        elif opt in ("-d", "--device"):
            sf_device_id = arg

    if mqtt_host is None:
        log.error("You need to provide a local MQTT broker (environment variable MQTT_HOST or option --broker)!")
        sys.exit(0)
    else:
        log.info(f'MQTT Host: {mqtt_host}:{mqtt_port}')

    if mqtt_user is None or mqtt_pwd is None:
        log.info(f'MQTT User is not set, assuming authentication not needed')
    else:
        log.info(f'MQTT User: {mqtt_user}/{mqtt_pwd}')

    if sf_device_id is None:
        log.error(f'You need to provide a SF_DEVICE_ID (environment variable SF_DEVICE_ID or option --device)!')
        sys.exit()
    else:
        log.info(f'Solarflow Hub: {sf_product_id}/{sf_device_id}')
        report_topic = f'/{sf_product_id}/+/properties/report'
        log.info(f'Reporting topic: {report_topic}')

    run()

if __name__ == '__main__':
    main(sys.argv[1:])
