# Protocollo RS485 BMS Tianpower (HY-CW007-B200LT55-V1.0.6T_0) — appunti

3 batterie con ADR diverso: **00 Carlotta, 01 Barbotta, 02 Oscar**. Seriale: **9600 baud, 8N1**.

## Frame
`7E | ADR | CMD | LEN | DATA(LEN) | CHK | 0D`
- Risposte spezzate in pacchetti USB da 64 byte: riassemblare con LEN (0x0D può comparire nei dati).
- **CHK** (dall'exe Windows, metodo `Form1.check`): `CHK = (XOR di tutti i byte ^ SOMMA di tutti i byte) & 0xFF`, su tutti i byte da `7E` incluso fino all'ultimo byte di DATA (CHK e `0D` esclusi). La somma non è troncata a 8 bit prima dello XOR finale. Verificato su 19/19 frame noti. Implementato in `bms.py` (`checksum()`, `build(adr, cmd, data)`).
- **Il BMS valida il checksum.** Checksum sbagliato → nessuna esecuzione e risposta di errore `7e <adr> <cmd> 01 02 <chk> 0d` (dato 02 = checksum errato). Risposta OK a E3: `7e<adr>e30100<chk>0d`.

## Frame di riferimento
| CMD | ADR 00 | ADR 01 | ADR 02 |
|---|---|---|---|
| 01 poll | `7e000100000d` | `7e010100fe0d` | `7e020100fc0d` |
| 33 ident | `7e003300fc0d` | `7e013300fe0d` | `7e023300fc0d` |
| 42 stringa | `7e004200fc0d` | `7e014200fc0d` | `7e024200fc0d` |
| DC blocco | `7e00dc03060000c40d` | `7e01dc03060000c20d` | `7e02dc03060000c00d` |
| E3 ON | `7e00e30101fe0d` | `7e01e30101f80d` | `7e02e30101fa0d` |
| E3 OFF | `7e00e30102fa0d` | `7e01e30102fa0d` | `7e02e30102fa0d` |

## E3 = riscaldamento FORZATO
Corrisponde al tasto "Enable_Heat" nella tab Config del software Windows. I pad scaldano anche sopra "heat off temp" (Param1): E3 scavalca le soglie automatiche e i pad restano accesi finché non si invia OFF. Il servizio ha limiti di sicurezza (vedi README).

## Risposta CMD 01 (130 byte, LEN=0x7c, TLV [id][n][valori])
- 16 celle mV da offset 6; pack voltage in 10 mV a offset 82–83.
- **Flag riscaldatori: byte 71 bit 4 (0x10).**
- **Temperature (id05, 6 word da offset 52): byte basso − 50 = °C.** Ordine: T1–T4 celle, MOSFET, ambiente. Solo su Carlotta T4 è vicino ai pad.
- CMD 42: stringa seriale. CMD DC: nome batteria.

## Catalogo comandi dell'exe Windows
Vedi `tools/comandi_exe.csv` (170 frame, estratti dall'IL dell'exe con `tools/extract_frames.py`; etichette inglesi dal cambio lingua dell'exe). **Non ancora testati su BMS reale**, salvo E3.
- **MOSFET** (CMD `d3`, 1 byte): `01` connetti MOS carica, `02` disconnetti carica, `03` connetti MOS scarica, `04` disconnetti scarica.
- Ventola `e2 01 01/02`; buzzer `d1 02 01 01/00`; allarme sonoro/luminoso `63 02 00 01/00`.
- Soglie riscaldamento: `Heat_On_Temp` lettura `f1`, scrittura `f2`; Heat_Off_Temp `f3`/`f4` (da verificare).
- Protezione alta temperatura MOS: `e6`/`e7` Frequency, `e8`/`eb` Open °C, `e9`/`ec` Stop °C, `ea`/`ed` Delay ms.
- **Pericolosi:** `cd` (sleep forzato), `60` (Zero_Calib), `d6` (calibrazione celle), `fe 05` (parametri, IP server), `fb` (unlock), aggiornamento firmware, ripristino parametri di fabbrica.

## Allarmi, protezioni, riscaldamento
Nell'exe allarmi e protezioni di bassa temperatura sono solo flag di abilitazione (`DSG_UT_Alarm`, `CHG_LT_Prot`, ...); nessun collegamento col riscaldamento (`Heat_On_Temp`/`Heat_Off_Temp`). La logica reale è nel firmware: da verificare in pratica (soglia di accensione sopra la temperatura delle celle, senza E3, e osservare il flag).
