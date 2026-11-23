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
# sicurezza riscaldatori (forzati da E3, non seguono le soglie del BMS)
OFF_T = int(B.get("heater_off_temp", "20"))        # spegni quando la cella piu' fredda >= soglia
MAX_MIN = int(B.get("heater_max_minutes", "120"))  # durata massima
MOS_MAX = int(B.get("mos_max_temp", "60"))         # spegni subito se il MOSFET >= soglia
PAD = int(B.get("pad_sensor", "0"))                # 1-4 = sensore cella vicino ai pad, 0 = nessuno
PAD_MAX = int(B.get("pad_max_temp", "45"))         # spegni se il sensore vicino ai pad >= soglia
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
st = {"paused": False, "last": None}   # paused: seriale rilasciata; last: ultimo stato letto
heat = {"t0": None}      # istante in cui i riscaldatori sono stati visti accesi
stop = []


def split_temps(s):
    """(temperature celle senza il sensore dei pad, temp sensore pad o None, MOSFET, ambiente)"""
    t = s["temps"]
    cells, pad = t[:4], None
    if 1 <= PAD <= 4:
        pad = cells[PAD - 1]
        cells = cells[:PAD - 1] + cells[PAD:]
    return cells, pad, t[4], t[5]


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
    sensors = [("pack_v", "Tensione pack", "V", "voltage"),
               ("cell_min_mv", "Cella min", "mV", "voltage"),
               ("cell_max_mv", "Cella max", "mV", "voltage"),
               ("cell_delta_mv", "Delta celle", "mV", "voltage"),
               ("t_cell_min", "Temp celle min", "°C", "temperature"),
               ("t_cell_max", "Temp celle max", "°C", "temperature"),
               ("t_mos", "Temp MOSFET", "°C", "temperature"),
               ("t_amb", "Temp ambiente", "°C", "temperature")]
    if PAD:
        sensors.append(("t_pad", "Temp pad (T%d)" % PAD, "°C", "temperature"))
    for key, label, icon in (("prot", "Protezioni attive", "mdi:shield-alert"),
                             ("alarm", "Allarmi attivi", "mdi:alarm-light")):
        s = dict(common, name=label, unique_id="tianpower_%s_%s" % (SLUG, key),
                 state_topic=STATE, value_template="{{ value_json.%s }}" % key, icon=icon)
        client.publish("homeassistant/sensor/tianpower_%s/%s/config" % (SLUG, key),
                       json.dumps(s), retain=True)
    for key, label, icon in (("heater", "Pad riscaldanti", "mdi:radiator"),
                             ("chg_ut_prot", "Sotto-temperatura carica (protezione)", "mdi:snowflake-alert"),
                             ("chg_open_low", "Carica bloccata: temperatura bassa", "mdi:snowflake-thermometer")):
        s = dict(common, name=label, unique_id="tianpower_%s_bin_%s" % (SLUG, key),
                 state_topic=STATE, value_template="{{ value_json.%s }}" % key,
                 payload_on="ON", payload_off="OFF", icon=icon)
        client.publish("homeassistant/binary_sensor/tianpower_%s/%s/config" % (SLUG, key),
                       json.dumps(s), retain=True)
    # rimuove entita' di versioni precedenti
    client.publish("homeassistant/sensor/tianpower_%s/t_t4/config" % SLUG, "", retain=True)
    for key, label, unit, dclass in sensors:
        s = dict(common, name=label, unique_id="tianpower_%s_%s" % (SLUG, key),
                 state_topic=STATE, value_template="{{ value_json.%s }}" % key,
                 unit_of_measurement=unit, device_class=dclass, state_class="measurement")
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


def safety(fd, s):
    """Con i riscaldatori accesi: spegne per temperatura raggiunta, MOSFET caldo o durata massima."""
    if not s["heater"]:
        heat["t0"] = None
        return s
    if heat["t0"] is None:
        heat["t0"] = time.time()
    cells, pad, mos, _ = split_temps(s)
    reason = None
    if mos >= MOS_MAX:
        reason = "MOSFET a %d C (max %d)" % (mos, MOS_MAX)
    elif pad is not None and pad >= PAD_MAX:
        reason = "sensore pad T%d a %d C (max %d)" % (PAD, pad, PAD_MAX)
    elif min(cells) >= OFF_T:
        reason = "celle a %d C (soglia %d)" % (min(cells), OFF_T)
    elif time.time() - heat["t0"] > MAX_MIN * 60:
        reason = "durata massima %d min" % MAX_MIN
    if reason:
        print("spegnimento automatico riscaldatori:", reason, flush=True)
        heat["t0"] = None
        return apply_heater(fd, False) or s
    return s


def set_avail(client, value):
    if avail["v"] != value:
        client.publish(AVAIL, value, retain=True)
        avail["v"] = value


def publish_state(client, s):
    cells, pad, mos, amb = split_temps(s)
    payload = {"pack_v": s["pack_v"], "cell_min_mv": s["cell_min_mv"],
               "cell_max_mv": s["cell_max_mv"],
               "cell_delta_mv": s["cell_max_mv"] - s["cell_min_mv"],
               "t_cell_min": min(cells), "t_cell_max": max(cells),
               "t_mos": mos, "t_amb": amb,
               "heater": "ON" if s["heater"] else "OFF"}
    names = [n for n, _ in s["active"]]
    payload["prot"] = ", ".join(n for n, t in s["active"] if t == "protezione/guasto")[:250] or "Nessuna"
    payload["alarm"] = ", ".join(n for n, t in s["active"] if t == "allarme")[:250] or "Nessuno"
    payload["chg_ut_prot"] = "ON" if "CHG_UN_TEMP_Protection" in names else "OFF"
    payload["chg_open_low"] = "ON" if "CHG_Open_TEMP_Too_Low" in names else "OFF"
    if pad is not None:
        payload["t_pad"] = pad
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
                cur = bms.status(fd, POLL) or st["last"]   # temperature fresche
                if val and cur and min(split_temps(cur)[0]) >= OFF_T:
                    print("ON ignorato: celle gia' a %d C (soglia %d)"
                          % (min(split_temps(cur)[0]), OFF_T), flush=True)
                    s = cur
                else:
                    s = apply_heater(fd, val)
            elif time.time() >= nxt:
                s = bms.status(fd, POLL)
            else:
                time.sleep(0.2)
                continue
            nxt = time.time() + INTERVAL
            if s:
                fails = 0
                s = safety(fd, s)
                st["last"] = s
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
