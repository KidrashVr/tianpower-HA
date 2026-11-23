# tianpower-bms

Lettura stato e controllo riscaldatori di BMS Tianpower (HY-CW007) via RS485, con pubblicazione MQTT per Home Assistant (discovery automatica).

- `bms.py`: protocollo (frame fissi per ADR 0/1/2, 9600 8N1) e uso da riga di comando: `python3 bms.py <dev> <adr> status|on|off`
- `bms_mqtt.py`: servizio MQTT (switch riscaldatori + sensori tensione pack, cella min/max, delta)
- `tianpower-bms.service`: unit systemd
- `tianpower-bms.ini.example`: configurazione di esempio (il vero `.ini` non va nel repo)

Il checksum dei frame non è decodificato: per ogni ADR si usano i frame catturati dal software ufficiale (vedi `FRAMES` in `bms.py`).

## Installazione (su ogni server, come root)

    apt install -y git python3-paho-mqtt
    git clone https://github.com/UTENTE/tianpower-bms /opt/tianpower
    cp /opt/tianpower/tianpower-bms.ini.example /etc/tianpower-bms.ini
    chmod 600 /etc/tianpower-bms.ini
    nano /etc/tianpower-bms.ini        # password MQTT, name, adr, device
    systemctl enable --now /opt/tianpower/tianpower-bms.service

## Aggiornamento

    cd /opt/tianpower && git pull && systemctl restart tianpower-bms

## Config per batteria

| name | adr | note |
|---|---|---|
| Carlotta | 0 | |
| Barbotta | 1 | |
| Oscar | 2 | |

Usare per `device` un percorso stabile in `/dev/serial/by-id/`.
