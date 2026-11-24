# Mappa bit di stato (risposta CMD 01)

Dall'exe Windows (`flogbuff`, copia di 15 byte dei dati di stato). `flogbuff[k]` = byte `66+k` della risposta completa (7E ADR CMD LEN ...) con 16 celle e 6 temperature.

| flogbuff | byte risposta | bit | nome (EN) | tipo | cinese |
|---|---|---|---|---|---|
| 0 | 66 | 0x08 | Cell_VOL_Low_Fault | protezione/guasto | 单体电压过低故障 |
| 0 | 66 | 0x10 | VOL_Line_Break | protezione/guasto | 电压采样线断 |
| 0 | 66 | 0x20 | Charge_MOS_Fault | protezione/guasto | 充MOS损坏 |
| 0 | 66 | 0x40 | DISC_MOS_Fault | protezione/guasto | 放MOS损坏 |
| 0 | 66 | 0x80 | VOL_Sensor_Fault | protezione/guasto | 电压采样元件损坏 |
| 1 | 67 | 0x01 | NTC_Disconnection | protezione/guasto | NTC断路 |
| 1 | 67 | 0x02 | ADC_MOD_Fault | protezione/guasto | ADC模块损坏 |
| 1 | 67 | 0x04 | Reverse_Battery | protezione/guasto | 电池反接 |
| 1 | 67 | 0x08 | Hot_Failure | protezione/guasto | 加热故障 |
| 1 | 67 | 0x10 | Battery_Locked | protezione/guasto | 电池锁定 |
| 2 | 68 | 0x01 | DISC_OV_TEMP_Protection | protezione/guasto | 放电过温保护 |
| 2 | 68 | 0x02 | DISC_UN_TEMP_Protection | protezione/guasto | 放电欠温保护 |
| 2 | 68 | 0x08 | Startup_Failed | protezione/guasto | 启动失败 |
| 2 | 68 | 0x40 | 536_COM_Timeout | protezione/guasto | 536通信超时 |
| 3 | 69 | 0x01 | Charging Status | stato | 充电状态 |
| 3 | 69 | 0x02 | Discharge Status | stato | 放电状态 |
| 3 | 69 | 0x04 | Short_Circuit_Protection | protezione/guasto | 短路保护 |
| 3 | 69 | 0x08 | OV_CUR_Protection | protezione/guasto | 过流保护 |
| 3 | 69 | 0x40 | CHG_OV_TEMP_Protection | protezione/guasto | 充电过温保护 |
| 3 | 69 | 0x80 | CHG_UN_TEMP_Protection | protezione/guasto | 充电欠温保护 |
| 4 | 70 | 0x01 | Ambient_Low_TEMP_Protection | protezione/guasto | 环境低温保护 |
| 4 | 70 | 0x02 | ENV_High_TEMP_Protection | protezione/guasto | 环境高温保护 |
| 5 | 71 | 0x01 | Manual_CHG_MOS_Open | stato | 强制充电MOS开启 |
| 5 | 71 | 0x02 | Manual_CHG_MOS_Off | stato | 强制充电MOS关闭 |
| 5 | 71 | 0x04 | Manual_DISC_MOS_Open | stato | 强制放电MOS开启 |
| 5 | 71 | 0x08 | Manual_DISC_MOS_Off | stato | 强制放电MOS关闭 |
| 5 | 71 | 0x10 | Heating pad | stato | 加热垫开启 |
| 5 | 71 | 0x20 | MOSFET_OV_TEMP_Protection | protezione/guasto | MOSFET过温 |
| 5 | 71 | 0x40 | MOSFET_LO_TEMP_Protection | protezione/guasto | MOSFET低温 |
| 5 | 71 | 0x80 | CHG_Open_TEMP_Too_Low | protezione/guasto | 充电开启温度过低 |
| 7 | 73 | 0x01 | SOC_Low_Alarm2 | allarme | SOC过低告警2 |
| 7 | 73 | 0x02 | Vibration Alarm | allarme | 震动告警 |
| 7 | 73 | 0x04 | Gap power make-up waite | allarme | 间隙补电等待 |
| 7 | 73 | 0x08 | Fire fighting Alarm | allarme | 消防告警 |
| 7 | 73 | 0x20 | NTC short circuit | allarme | NTC短路 |
| 8 | 74 | 0x01 | AMB_Over_TEMP_Alarm | allarme | 环境过温告警 |
| 8 | 74 | 0x02 | AMB_Low_TEMP_Alarm | allarme | 环境欠温告警 |
| 8 | 74 | 0x04 | MOS_Over_TEMP_Alarm | allarme | MOS过温告警 |
| 8 | 74 | 0x08 | SOC_Low_Alarm | allarme | SOC过低告警 |
| 8 | 74 | 0x10 | Vol_DIF_Alarm | allarme | 压差过大告警 |
| 8 | 74 | 0x20 | BAT_DISC_Over_TEMP_Alarm | allarme | 电池放过温告警 |
| 8 | 74 | 0x40 | BAT_DISC_Low_TEMP_Alarm | allarme | 电池放欠温告警 |
| 9 | 75 | 0x01 | Cell_Over_VOL_Alarm | allarme | 单体过压告警 |
| 9 | 75 | 0x02 | Cell_Low_VOL_Alarm | allarme | 单体欠压告警 |
| 9 | 75 | 0x04 | Pack_Over_VOL_Alarm | allarme | 总体过压告警 |
| 9 | 75 | 0x08 | Pack_Low_VOL_Alarm | allarme | 总体欠压告警 |
| 9 | 75 | 0x10 | CHG_Over_CUR_Alarm | allarme | 过流告警 |
| 9 | 75 | 0x20 | DISC_Over_CURR_Alarm | allarme | 放过流告警 |
| 9 | 75 | 0x40 | BAT_CHG_Over_TEMP_Alarm | allarme | 电池充电过温告警 |
| 9 | 75 | 0x80 | BAT_CHG_Low_TEMP_Alarm | allarme | 电池充电欠温告警 |

Nota: nell'exe `flogbuff` viene riempito dalla risposta CMD 01 solo per gli indici 0-9 (byte 66-75). Le voci con indice 10-11 (Cell_Over_Prot, Pack_Over_Prot, Cell_Under_Prot, Pack_Under_Prot, Full_Cha_Prot) arrivano da un'altra fonte non ancora identificata e sono state tolte da `flags.py`: il byte 76 della risposta è l'intestazione del blocco id07, non un byte di stato.
