import os
import time
from datetime import datetime
import notifier

try:
    import libcamera
    from picamera2 import Picamera2
    _cam_ok = True
except Exception:
    _cam_ok = False
    print("PiCamera2 ikke tilgængelig - kamera deaktiveret")

try:
    from ultralytics import YOLO
    _model = YOLO("/home/gruppe5/best_ncnn_model", task="classify")
    _yolo_ok = True
except Exception as e:
    _yolo_ok = False
    print(f"YOLOv8 ikke tilgængelig: {e}")

try:
    from rpi_hardware_pwm import HardwarePWM
    _servo = HardwarePWM(pwm_channel=0, hz=50, chip=0)
    _servo.start(0)
    _servo_ok = True
except Exception:
    _servo_ok = False
    print("Servo (HardwarePWM) ikke tilgængelig - kamera-bevægelse deaktiveret")

SERVO_MIN_DUTY = 2.5
SERVO_MAX_DUTY = 12.0

SERVO_GRADER_PLANTE1 = 60
SERVO_GRADER_PLANTE2 = 90

SERVO_FLYT_VENTETID = 3


def _grader_til_duty(grader):
    return SERVO_MIN_DUTY + (grader / 180) * (SERVO_MAX_DUTY - SERVO_MIN_DUTY)


IMG_MAPPE = "static/img"
os.makedirs(IMG_MAPPE, exist_ok=True)

seneste_resultat = {
    "billede":    None,
    "sundhed":    None,
    "labels":     [],
    "timestamp":  None,
    "plante2":    {"billede": None, "sundhed": None, "timestamp": None},
}


def _tag_billede(praefiks: str) -> dict:
    nu = datetime.now()
    filnavn = f"{praefiks}_{nu.strftime('%d-%m-%Y_%H-%M-%S')}.jpg"
    sti = f"{IMG_MAPPE}/{filnavn}"

    if _cam_ok:
        picam = Picamera2()
        config = picam.create_still_configuration(main={"size": (640, 480)})
        config["transform"] = libcamera.Transform(hflip=1, vflip=1)
        picam.configure(config)
        picam.start()
        picam.capture_file(sti)
        picam.close()
    else:
        filnavn = None

    sundhed = "Ukendt"
    if _yolo_ok and filnavn:
        results = _model(sti, verbose=False)
        probs = results[0].probs
        names = results[0].names
        healthy_idx = list(names.values()).index("healthy")
        sick_idx    = list(names.values()).index("sick")
        healthy_pct = round(probs.data[healthy_idx].item() * 100, 1)
        sick_pct    = round(probs.data[sick_idx].item() * 100, 1)
        sundhed = "Sund" if healthy_pct > sick_pct else "Syg"

    return {
        "billede":   filnavn,
        "sundhed":   sundhed,
        "timestamp": nu.strftime("%d-%m-%Y %H:%M:%S"),
    }


def tag_billede_og_analyser() -> dict:
    if _servo_ok:
        _servo.change_duty_cycle(_grader_til_duty(SERVO_GRADER_PLANTE1))
        time.sleep(SERVO_FLYT_VENTETID)
    resultat1 = _tag_billede("plante1")

    if _servo_ok:
        _servo.change_duty_cycle(_grader_til_duty(SERVO_GRADER_PLANTE2))
        time.sleep(SERVO_FLYT_VENTETID)
    resultat2 = _tag_billede("plante2")

    if resultat1["billede"]:
        notifier.send_billede(
            f"{IMG_MAPPE}/{resultat1['billede']}",
            f"Plante 1: {resultat1['sundhed']}",
            titel="GrowSense - Plante 1",
        )
    if resultat2["billede"]:
        notifier.send_billede(
            f"{IMG_MAPPE}/{resultat2['billede']}",
            f"Plante 2: {resultat2['sundhed']}",
            titel="GrowSense - Plante 2",
        )

    seneste_resultat["billede"]   = resultat1["billede"]
    seneste_resultat["sundhed"]   = resultat1["sundhed"]
    seneste_resultat["labels"]    = []
    seneste_resultat["timestamp"] = resultat1["timestamp"]

    seneste_resultat["plante2"] = resultat2

    return seneste_resultat.copy()


def get_galleri(antal: int = 12) -> list:
    if not os.path.exists(IMG_MAPPE):
        return []
    filer = sorted(
        [f for f in os.listdir(IMG_MAPPE) if f.endswith(".jpg")],
        reverse=True,
    )
    return filer[:antal]
