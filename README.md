# tianpower-bms

Lettura stato e controllo di BMS Tianpower (HY-CW007) via RS485, con pubblicazione MQTT per Home Assistant (discovery automatica).

- `bms.py`: protocollo (9600 8N1), checksum e generazione dei frame per qualsiasi ADR, uso da riga di comando
- `bms_mqtt.py`: servizio MQTT (switch riscaldatori e lettura BMS, sensori tensione, celle, temperature) con limiti di sicurezza
- `tianpower-bms.service`: unit systemd
- `tianpower-bms.ini.example`: configurazione di esempio (il vero `.ini` non va nel repo)
- `docs/protocollo-bms.md`: appunti sul protocollo
- `tools/`: `comandi_exe.csv` (catalogo dei comandi del software Windows), `extract_frames.py` (estrazione dall'exe), `find_chk.py` (oracolo checksum, ormai solo di verifica)

## Checksum

`CHK = (XOR di tutti i byte ^ SOMMA di tutti i byte) & 0xFF`, su tutti i byte da `7E` incluso fino alla fine dei DATA (CHK e `0D` esclusi). Frame: `7E ADR CMD LEN DATA.. CHK 0D`.

## Riga di comando

    python3 bms.py <dev> <adr> status|on|off
    python3 bms.py <dev> <adr> chg_on|chg_off|dis_on|dis_off   # MOSFET: NON ancora verificati su BMS reale

`on` forza il riscaldamento e i pad restano accesi finche' non si invia `off`: il servizio MQTT spegne in automatico (vedi sicurezza).

## Sicurezza riscaldatori (servizio MQTT)

Spegne se: cella piu' fredda (escluso il sensore vicino ai pad) >= `heater_off_temp`, sensore pad >= `pad_max_temp`, MOSFET >= `mos_max_temp`, durata > `heater_max_minutes`. L'accensione e' rifiutata se le celle sono gia' sopra soglia.

## Installazione (su ogni server, come root)

    apt install -y git python3-paho-mqtt
    git clone https://github.com/KidrashVr/tianpower-HA /opt/tianpower
    cp /opt/tianpower/tianpower-bms.ini.example /etc/tianpower-bms.ini
    chmod 600 /etc/tianpower-bms.ini
    nano /etc/tianpower-bms.ini        # password MQTT, name, adr, device, pad_sensor
    cp /opt/tianpower/tianpower-bms.service /etc/systemd/system/
    systemctl daemon-reload && systemctl enable --now tianpower-bms

## Aggiornamento

    cd /opt/tianpower && git pull && systemctl restart tianpower-bms

## Config per batteria

| name | adr | pad_sensor |
|---|---|---|
| Carlotta | 0 | 4 |
| Barbotta | 1 | 0 |
| Oscar | 2 | 0 |

Usare per `device` un percorso stabile in `/dev/serial/by-id/` (o by-path).
