import sqlite3
import os
import threading
from datetime import datetime
from time import sleep, time
import notifier

try:
    import serial
    _serial_ok = True
except ImportError:
    _serial_ok = False

SERIAL_PORT  = "/dev/serial0"
BAUD_RATE    = 115200

DB_FIL = "data/growsense.db"

sensor_data = {
    "soil1":     0.0,
    "soil2":     0.0,
    "light":     0,
    "vandstand": "Ukendt",
    "pumpe":     "FRA",
    "lysprofil": "standard",
    "led":       0,
    "timestamp": "Ingen data endnu",
}

_ser = None

_sidste_vandstand = None

def _gem_til_db(data: dict, notifikation_sendt: bool):
    if notifikation_sendt:
        notifikation_tal = 1
    else:
        notifikation_tal = 0

    conn = sqlite3.connect(DB_FIL)

    query = """INSERT INTO sensor_log
               (timestamp, soil1, soil2, light, vandstand, pumpe, notifikation_sendt)
               VALUES (?, ?, ?, ?, ?, ?, ?)"""
    values = (
        data["timestamp"],
        data["soil1"],
        data["soil2"],
        data["light"],
        data["vandstand"],
        data["pumpe"],
        notifikation_tal,
    )

    try:
        cur = conn.cursor()
        cur.execute(query, values)
        conn.commit()
    except sqlite3.Error as e:
        conn.rollback()
        print(f"Kunne ikke gemme måling i databasen! {e}")
    finally:
        conn.close()

def _tjek_og_send_notifikation(vandstand: str) -> bool:
    global _sidste_vandstand

    status_er_ikke_aendret = vandstand == _sidste_vandstand
    if status_er_ikke_aendret:
        return False

    _sidste_vandstand = vandstand

    if vandstand == "Dine planter mangler vand!":
        notifier.send_notifikation(vandstand)
        return True

    return False

def _laes_serial():
    global _ser
    try:
        _ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=2)
        print(f"Forbundet til ESP32 på {SERIAL_PORT}")
        while True:
            linje = _ser.readline().decode("utf-8", errors="ignore").strip()
            if not linje:
                continue
            try:
                for del_ in linje.split(","):
                    if ":" not in del_:
                        continue
                    key, val = del_.split(":", 1)
                    key = key.strip()
                    val = val.strip().rstrip("%")
                    if key == "soil1":       sensor_data["soil1"] = float(val)
                    elif key == "soil2":     sensor_data["soil2"] = float(val)
                    elif key == "light":     sensor_data["light"] = int(float(val))
                    elif key == "vandstand": sensor_data["vandstand"] = val
                    elif key == "pumpe":     sensor_data["pumpe"] = val
                    elif key == "lysprofil": sensor_data["lysprofil"] = val
                    elif key == "led":       sensor_data["led"] = int(float(val))
                sensor_data["timestamp"] = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
                notifikation_sendt = _tjek_og_send_notifikation(sensor_data["vandstand"])
                _gem_til_db(sensor_data.copy(), notifikation_sendt)
            except:
                pass
    except:
        print("Kan ikke oprette forbindelse til ESP32. - prøver igen om 2 sekunder")
        time.sleep(2)

def send(besked: str):
    if _ser is not None:
        try:
            _ser.write((besked.strip() + "\n").encode("utf-8"))
        except Exception:
            pass

def start():
    t = threading.Thread(target=_laes_serial, daemon=True)
    t.start()

def get_data() -> dict:
    return sensor_data.copy()

def get_historik(antal: int = 20) -> list:
    if not os.path.exists(DB_FIL):
        return []

    conn = sqlite3.connect(DB_FIL)
    conn.row_factory = sqlite3.Row

    raekker_nyeste_foerst = []
    try:
        cur = conn.cursor()
        query = "SELECT * FROM sensor_log ORDER BY id DESC LIMIT ?"
        cur.execute(query, (antal,))
        raekker_nyeste_foerst = cur.fetchall()
    except sqlite3.Error as e:
        print(f"Kunne ikke hente historik fra databasen! {e}")
    finally:
        conn.close()

    raekker_aeldste_foerst = list(reversed(raekker_nyeste_foerst))

    return [dict(raekke) for raekke in raekker_aeldste_foerst]
