#!/usr/bin/env python3
"""Trova il checksum valido di un frame usando il BMS come oracolo.
Un checksum sbagliato riceve un frame di errore (7e <adr> <cmd> 01 02 .. 0d) e NON esegue nulla;
quello giusto riceve la risposta normale (e il comando viene eseguito, se e' una scrittura).

Uso: python3 find_chk.py <dispositivo> <adr> <cmd_hex> [data_hex] [--write]
Esempi:
  python3 find_chk.py /dev/ttyUSB0 2 33            # lettura (sicuro)
  python3 find_chk.py /dev/ttyUSB0 2 e3 01 --write # scrittura: al checksum giusto il comando VIENE ESEGUITO
Fermare prima il servizio: systemctl stop tianpower-bms"""
import os, select, sys, time
sys.path.insert(0, "/opt/tianpower")
import bms

READ_ONLY = {0x01, 0x33, 0x42, 0x45, 0xDC}
write = "--write" in sys.argv
args = [a for a in sys.argv[1:] if a != "--write"]
if len(args) < 3:
    sys.exit(__doc__)
dev, adr, cmd = args[0], int(args[1]), int(args[2], 16)
data = bytes.fromhex(args[3]) if len(args) > 3 else b""
if cmd not in READ_ONLY and not write:
    sys.exit("CMD %02x non e' un comando di sola lettura noto: aggiungi --write se sei sicuro." % cmd)
fd = bms.open_port(dev)


def attempt(chk):
    frame = bytes([0x7E, adr, cmd, len(data)]) + data + bytes([chk, 0x0D])
    while select.select([fd], [], [], 0)[0]:
        os.read(fd, 4096)
    os.write(fd, frame)
    buf, end, quiet = b"", time.time() + 0.5, None
    while time.time() < end:
        if select.select([fd], [], [], 0.03)[0]:
            buf += os.read(fd, 4096)
            quiet = time.time() + 0.2
            end = max(end, quiet)
        elif quiet and time.time() > quiet:
            break
    return frame, buf


def is_chk_error(r):
    return len(r) == 7 and r[0] == 0x7E and r[3] == 1 and r[4] == 2


unknown = []
for chk in list(range(0, 256, 2)) + list(range(1, 256, 2)):   # i checksum visti sono tutti pari: prima quelli
    frame, r = attempt(chk)
    if not r:
        frame, r = attempt(chk)          # un secondo tentativo, le risposte possono perdersi
    if not r:
        unknown.append(chk)
        continue
    if is_chk_error(r):
        continue
    print("CHECKSUM TROVATO: %02x" % chk)
    print("frame:   ", frame.hex())
    print("risposta:", r[:40].hex() + (" ..." if len(r) > 40 else ""))
    sys.exit(0)
print("non trovato. Senza risposta:", " ".join("%02x" % c for c in unknown) or "nessuno")
