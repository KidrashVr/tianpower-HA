#!/usr/bin/env python3
"""Tianpower BMS -> MQTT con discovery Home Assistant.
Uso: bms_mqtt.py <config.ini>   (richiede bms.py nella stessa cartella e paho-mqtt)"""
import configparser, json, os, queue, re, signal, sys, time
import paho.mqtt.client as mqtt
import bms

cfg = configparser.ConfigParser()
cfg.read(sys.argv[1] if len(sys.argv) > 1 else "/etc/tianpower-bms.ini")
M, B = cfg["mqtt"], cfg["bms"]
NAME, ADR, DEV = B["name"], int(B["adr"]), B["device"]
INTERVAL = int(B.get("interval", "15"))
SLUG = re.sub(r"[^a-z0-9]+", "_", NAME.lower()).strip("_")
BASE = "tianpower/" + SLUG
AVAIL, SVC, STATE = BASE + "/availability", BASE + "/service", BASE + "/state"
CMD = BASE + "/heater/set"
POLLCMD, POLLSTATE = BASE + "/polling/set", BASE + "/polling"
FR = bms.FRAMES[ADR]
POLL = bytes.fromhex(FR["poll"])
DEVICE = {"identifiers": ["tianpower_" + SLUG], "name": NAME,
          "manufacturer": "Tianpower", "model": "HY-CW007-B200LT55"}

cmds = queue.Queue()
avail = {"v": None}      # ultimo stato BMS pubblicato (None = da ripubblicare)
st = {"paused": False}   # True = seriale rilasciata
stop = []


def discovery(client):
    # le entita' sono disponibili solo se il servizio e' vivo (SVC) e il BMS risponde (AVAIL)
    common = {"availability": [{"topic": AVAIL}, {"topic": SVC}],
              "availability_mode": "all", "device": DEVICE}
    sw = dict(common, name="Riscaldatori", unique_id="tianpower_%s_heater" % SLUG,
              command_topic=CMD, state_topic=STATE,
              value_template="{{ value_json.heater }}",
              payload_on="ON", payload_off="OFF", icon="mdi:radiator")
    client.publish("homeassistant/switch/tianpower_%s/heater/config" % SLUG,
                   json.dumps(sw), retain=True)
    pl = {"availability_topic": SVC, "device": DEVICE, "name": "Lettura BMS",
          "unique_id": "tianpower_%s_polling" % SLUG, "command_topic": POLLCMD,
          "state_topic": POLLSTATE, "payload_on": "ON", "payload_off": "OFF",
          "icon": "mdi:serial-port"}
    client.publish("homeassistant/switch/tianpower_%s/polling/config" % SLUG,
                   json.dumps(pl), retain=True)
    sensors = [("pack_v", "Tensione pack", "V"), ("cell_min_mv", "Cella min", "mV"),
               ("cell_max_mv", "Cella max", "mV"), ("cell_delta_mv", "Delta celle", "mV")]
    for key, label, unit in sensors:
        s = dict(common, name=label, unique_id="tianpower_%s_%s" % (SLUG, key),
                 state_topic=STATE, value_template="{{ value_json.%s }}" % key,
                 unit_of_measurement=unit, device_class="voltage", state_class="measurement")
        client.publish("homeassistant/sensor/tianpower_%s/%s/config" % (SLUG, key),
                       json.dumps(s), retain=True)


def on_connect(client, userdata, flags, rc, properties=None):
    ok = (rc == 0) if isinstance(rc, int) else not rc.is_failure
    if not ok:
        print("connessione MQTT fallita:", rc, flush=True)
        return
    discovery(client)
    client.subscribe([(CMD, 0), (POLLCMD, 0)])
    client.publish(SVC, "online", retain=True)
    client.publish(POLLSTATE, "OFF" if st["paused"] else "ON", retain=True)
    avail["v"] = None


def on_message(client, userdata, msg):
    p = msg.payload.decode(errors="ignore").strip().upper()
    if p not in ("ON", "OFF"):
        return
    if msg.topic == CMD:
        cmds.put(("heater", p == "ON"))
    elif msg.topic == POLLCMD:
        cmds.put(("poll", p == "ON"))


def apply_heater(fd, on):
    cmd = bytes.fromhex(FR["on" if on else "off"])
    for _ in range(3):
        bms.txrx(fd, cmd, 0.5)
        for _ in range(4):
            time.sleep(1)
            s = bms.status(fd, POLL)
            if s and s["heater"] == on:
                return s
    return bms.status(fd, POLL)


def set_avail(client, value):
    if avail["v"] != value:
        client.publish(AVAIL, value, retain=True)
        avail["v"] = value


def publish_state(client, s):
    payload = {"pack_v": s["pack_v"], "cell_min_mv": s["cell_min_mv"],
               "cell_max_mv": s["cell_max_mv"],
               "cell_delta_mv": s["cell_max_mv"] - s["cell_min_mv"],
               "heater": "ON" if s["heater"] else "OFF"}
    client.publish(STATE, json.dumps(payload), retain=True)
    set_avail(client, "online")


def close_port(fd):
    if fd is not None:
        try:
            os.close(fd)
        except OSError:
            pass
    return None


def main():
    cid = "tianpower-" + SLUG
    try:
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=cid)
    except AttributeError:
        client = mqtt.Client(client_id=cid)
    client.username_pw_set(M["user"], M.get("password"))
    client.will_set(SVC, "offline", retain=True)
    client.on_connect, client.on_message = on_connect, on_message
    client.reconnect_delay_set(min_delay=2, max_delay=60)
    client.connect_async(M["host"], int(M.get("port", "1883")), 60)
    client.loop_start()
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda *a: stop.append(1))

    fd, fails, nxt = None, 0, 0.0
    while not stop:
        try:
            try:
                kind, val = cmds.get_nowait()
            except queue.Empty:
                kind = val = None
            if kind == "poll":
                st["paused"] = not val
                client.publish(POLLSTATE, "OFF" if st["paused"] else "ON", retain=True)
                if st["paused"]:
                    fd = close_port(fd)
                    set_avail(client, "offline")
                else:
                    nxt = 0.0
                continue
            if st["paused"]:
                if kind == "heater":
                    print("comando riscaldatori ignorato: lettura BMS in pausa", flush=True)
                time.sleep(0.2)
                continue
            if fd is None:
                fd = bms.open_port(DEV)
            if kind == "heater":
                s = apply_heater(fd, val)
            elif time.time() >= nxt:
                s = bms.status(fd, POLL)
            else:
                time.sleep(0.2)
                continue
            nxt = time.time() + INTERVAL
            if s:
                fails = 0
                publish_state(client, s)
            else:
                fails += 1
                print("nessuna risposta dal BMS (%d)" % fails, flush=True)
                if fails >= 3:
                    set_avail(client, "offline")
        except OSError as e:
            print("errore seriale:", e, flush=True)
            fd = close_port(fd)
            set_avail(client, "offline")
            time.sleep(5)
    fd = close_port(fd)
    client.publish(SVC, "offline", retain=True).wait_for_publish(2)
    client.loop_stop()
    client.disconnect()


if __name__ == "__main__":
    main()
