#!/usr/bin/env python3
# Uso: python3 bms.py <dispositivo> <adr> [status|on|off|chg_on|chg_off|dis_on|dis_off]
# Esempio: sudo python3 bms.py /dev/ttyUSB1 1 status
import os, sys, time, select, termios
import flags

def checksum(b):
    """Algoritmo del software Windows (Form1.check): (XOR ^ SOMMA) & 0xFF
    su tutti i byte da 0x7e incluso fino alla fine dei dati."""
    x = s = 0
    for v in b:
        x ^= v
        s += v
    return (x ^ s) & 0xFF


def build(adr, cmd, data=b""):
    f = bytes([0x7E, adr, cmd, len(data)]) + bytes(data)
    return (f + bytes([checksum(f), 0x0D])).hex()


class _Frames(dict):
    def __missing__(self, adr):
        if not 0 <= adr <= 255:
            raise KeyError(adr)
        self[adr] = {"poll": build(adr, 0x01), "on": build(adr, 0xE3, b"\x01"),
                     "off": build(adr, 0xE3, b"\x02")}
        return self[adr]


# CMD d3: 1 connetti MOS carica, 2 disconnetti MOS carica, 3 connetti MOS scarica, 4 disconnetti MOS scarica
MOS = {"chg_on": 1, "chg_off": 2, "dis_on": 3, "dis_off": 4}


# Frame generati per qualsiasi ADR (0 Carlotta, 1 Barbotta, 2 Oscar)
FRAMES = _Frames()


def open_port(dev):
    fd = os.open(dev, os.O_RDWR | os.O_NOCTTY)
    a = termios.tcgetattr(fd)
    a[0] = a[1] = a[3] = 0
    a[2] = termios.CS8 | termios.CREAD | termios.CLOCAL
    a[4] = a[5] = termios.B9600
    a[6][termios.VMIN] = 0
    a[6][termios.VTIME] = 0
    termios.tcsetattr(fd, termios.TCSANOW, a)
    termios.tcflush(fd, termios.TCIOFLUSH)
    return fd


def read_frame(fd, timeout):
    buf, end = b"", time.time() + timeout
    while time.time() < end:
        if select.select([fd], [], [], 0.05)[0]:
            buf += os.read(fd, 256)
        i = buf.find(b"\x7e")
        if i > 0:
            buf = buf[i:]
        if len(buf) >= 4 and buf[0] == 0x7E and len(buf) >= 6 + buf[3]:
            return buf[:6 + buf[3]]
    return None


def txrx(fd, cmd, timeout):
    termios.tcflush(fd, termios.TCIFLUSH)
    os.write(fd, cmd)
    return read_frame(fd, timeout)


def status(fd, poll):
    for _ in range(2):
        f = txrx(fd, poll, 1.5)
        if f and len(f) == 130 and f[2] == 1:
            cells = [int.from_bytes(f[6 + 2 * i:8 + 2 * i], "big") for i in range(16)]
            return {
                "pack_v": int.from_bytes(f[82:84], "big") / 100,
                "cell_min_mv": min(cells),
                "cell_max_mv": max(cells),
                "heater": bool(f[71] & 0x10),
                # 6 temperature (id05): celle 1-4, MOSFET, ambiente = byte basso - 50
                "temps": [f[53 + 2 * i] - 50 for i in range(6)],
                "id06": f[66:76].hex(),
                # bit di stato attivi (mappa dall'exe Windows, vedi flags.py)
                "active": flags.active(f),
            }
    return None


def set_heater(fd, fr, on):
    cmd = bytes.fromhex(fr["on" if on else "off"])
    for _ in range(3):
        ack = txrx(fd, cmd, 0.5)
        print("tx", cmd.hex(), "ack", ack.hex() if ack else None)
        for _ in range(4):
            time.sleep(1)
            s = status(fd, bytes.fromhex(fr["poll"]))
            if s and s["heater"] == on:
                print("OK", s)
                return
    print("FALLITO: flag riscaldatori non cambiato. Ultimo stato:",
          status(fd, bytes.fromhex(fr["poll"])))


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    dev, adr = sys.argv[1], int(sys.argv[2])
    cmd = sys.argv[3] if len(sys.argv) > 3 else "status"
    fr = FRAMES[adr]
    fd = open_port(dev)
    if cmd == "status":
        print(status(fd, bytes.fromhex(fr["poll"])))
    elif cmd in ("on", "off"):
        set_heater(fd, fr, cmd == "on")
    elif cmd in MOS:
        # MOSFET carica/scarica (CMD d3, dall'exe Windows). NON ancora verificati su BMS reale.
        r = txrx(fd, bytes.fromhex(build(adr, 0xD3, bytes([MOS[cmd]]))), 1.5)
        print("risposta:", r.hex() if r else None)
        print(status(fd, bytes.fromhex(fr["poll"])))
    else:
        sys.exit("comando sconosciuto: " + cmd)
