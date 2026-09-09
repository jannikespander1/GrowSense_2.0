from machine import Pin, ADC, UART
from neopixel import NeoPixel
from time import sleep
import time


SOIL1_PIN       = 34
SOIL2_PIN       = 35
LDR_PIN         = 39
WATER_LEVEL_PIN = 25
PUMP_PIN        = 27
LED_PIN         = 18
LED_COUNT       = 22
UART_TX         = 4
UART_RX         = 5
SOLENOID_PIN    = 32

SOLENOID_TIL_PLANTE1 = 1
SOLENOID_TIL_PLANTE2 = 0

SOIL_DRY   = 2600
SOIL_WET   = 870
ADC_DARK   = 0
ADC_BRIGHT = 1615

SOIL_MIN_P1 = 50
SOIL_MAX_P1 = 70
SOIL_MIN_P2 = 50
SOIL_MAX_P2 = 70

PROFILES = {
    "seedling": (25, 100, 25),
    "standard": (70, 100, 58),
}

PUMP_DURATION    = 4
PUMP_PAUSE       = 3
PUMP_LED_DELAY   = 3
LED_RESUME_DELAY = 3

SOIL_INTERVAL  = 5


def clamp(value, low=0, high=100):
    return max(low, min(high, value))


class WaterSystem:
    def __init__(self, soil1_pin, soil2_pin, pump_pin, solenoid_pin, dry, wet, light=None):
        self.soil1 = self._adc(soil1_pin)
        self.soil2 = self._adc(soil2_pin)
        self.pump = Pin(pump_pin, Pin.OUT)
        self.pump.value(0)

        self.solenoid = Pin(solenoid_pin, Pin.OUT)
        self.solenoid.value(SOLENOID_TIL_PLANTE2)

        self.dry = dry
        self.wet = wet
        self.light = light
        self.pumping = False
        self.start_time = None
        self.end_time = None
        self.last_soil = (0, 0)
        self.last_read_time = None

        self.waiting_for_pump = False
        self.light_off_time = None

    def _adc(self, pin):
        adc = ADC(Pin(pin))
        adc.atten(ADC.ATTN_11DB)
        return adc

    def _to_percent(self, raw):
        pct = (self.dry - raw) * 100 / (self.dry - self.wet)
        return clamp(int(round(pct)))

    def read(self):
        now = time.time()
        if self.last_read_time is None or now - self.last_read_time >= SOIL_INTERVAL:
            self.last_soil = (
                self._to_percent(self.soil1.read()),
                self._to_percent(self.soil2.read()),
            )
            self.last_read_time = now
        return self.last_soil

    def _set_pump(self, state):
        if state:
            if self.light:
                self.light.set_color(0, 0, 0)
                sleep(PUMP_LED_DELAY)
            self.pump.value(1)
        else:
            self.pump.value(0)
        self.pumping = state

    def _start_pump_sequence(self, solenoid_state):
        self.solenoid.value(solenoid_state)
        if self.light:
            self.light.set_color(0, 0, 0)
        self.light_off_time = time.time()
        self.waiting_for_pump = True

    def lights_should_be_off(self):
        if self.pumping or self.waiting_for_pump:
            return True
        if self.end_time and time.time() - self.end_time < LED_RESUME_DELAY:
            return True
        return False

    def pump_if_needed(self, soil1, soil2, soil_min_p1, soil_max_p1, soil_min_p2, soil_max_p2):
        now = time.time()

        if self.waiting_for_pump:
            led_forsinkelse_er_slut = now - self.light_off_time >= PUMP_LED_DELAY
            if led_forsinkelse_er_slut:
                self.pump.value(1)
                self.pumping = True
                self.waiting_for_pump = False
                self.start_time = now
            return self.pumping

        if self.pumping:
            pumpe_har_koert_laenge_nok = self.start_time and now - self.start_time >= PUMP_DURATION
            if pumpe_har_koert_laenge_nok:
                self._set_pump(False)
                self.end_time = now
            return self.pumping

        pause_er_ikke_slut = self.end_time and now - self.end_time < PUMP_PAUSE
        if pause_er_ikke_slut:
            return self.pumping

        plante1_er_toerst = soil1 < soil_min_p1
        plante2_er_toerst = soil2 < soil_min_p2

        if plante1_er_toerst:
            self._start_pump_sequence(SOLENOID_TIL_PLANTE1)
        elif plante2_er_toerst:
            self._start_pump_sequence(SOLENOID_TIL_PLANTE2)

        return self.pumping

    def set_pump_manuelt(self, state):
        self._set_pump(state)
        self.start_time = time.time() if state else None
        self.end_time = None if state else time.time()


class LightSystem:
    def __init__(self, ldr_pin, led_pin, led_count, adc_dark, adc_bright):
        self.ldr = ADC(Pin(ldr_pin))
        self.ldr.width(ADC.WIDTH_12BIT)
        self.ldr.atten(ADC.ATTN_11DB)
        self.led = NeoPixel(Pin(led_pin), led_count)
        self.count = led_count
        self.a = -100 / (adc_bright - adc_dark)
        self.b = 100 - self.a * adc_dark
        self.profile = PROFILES["standard"]
        self.profile_name = "standard"
        self.led_percent = 0
        self.light_allowed = True
        self.set_color(0, 0, 0)

    def set_color(self, r, g, b):
        color = (int(r / 100 * 255), int(g / 100 * 255), int(b / 100 * 255))
        for i in range(self.count):
            self.led[i] = color
        self.led.write()

    def select_profile(self, name):
        if name in PROFILES:
            self.profile = PROFILES[name]
            self.profile_name = name

    def set_light_allowed(self, state):
        self.light_allowed = state

    def update(self, keep_off=False):
        adc = self.ldr.read()
        ambient = clamp(adc * 100 // ADC_BRIGHT)

        if keep_off or not self.light_allowed:
            self.led_percent = 0
        else:
            self.led_percent = clamp(int(self.a * adc + self.b))

        scale = self.led_percent / 100
        r, g, b = self.profile
        self.set_color(r * scale, g * scale, b * scale)
        return ambient


class WaterLevel:
    def __init__(self, pin):
        try:
            self.sensor = Pin(pin, Pin.IN, Pin.PULL_UP)
        except ValueError:
            self.sensor = Pin(pin, Pin.IN)

    def read(self):
        if self.sensor.value() == 1:
            return "Dine planter mangler vand!"
        return "Dine planter er glade :)"


uart = UART(2, baudrate=115200, tx=UART_TX, rx=UART_RX, timeout=100)
light_system = LightSystem(LDR_PIN, LED_PIN, LED_COUNT, ADC_DARK, ADC_BRIGHT)
water_system = WaterSystem(SOIL1_PIN, SOIL2_PIN, PUMP_PIN, SOLENOID_PIN, SOIL_DRY, SOIL_WET, light_system)
water_level_sensor = WaterLevel(WATER_LEVEL_PIN)


def receive_settings():
    global SOIL_MIN_P1, SOIL_MAX_P1, SOIL_MIN_P2, SOIL_MAX_P2
    if not uart.any():
        return
    try:
        line = uart.readline().decode("utf-8", "ignore").strip()
        if not line.startswith("indstil:"):
            return
        for part in line.replace("indstil:", "").split(","):
            if "=" not in part:
                continue
            key, value = (s.strip() for s in part.split("=", 1))
            if key == "soil_min_p1":
                SOIL_MIN_P1 = int(value)
            elif key == "soil_max_p1":
                SOIL_MAX_P1 = int(value)
            elif key == "soil_min_p2":
                SOIL_MIN_P2 = int(value)
            elif key == "soil_max_p2":
                SOIL_MAX_P2 = int(value)
            elif key == "pumpe":
                water_system.set_pump_manuelt(value == "TIL")
            elif key == "lysprofil":
                light_system.select_profile(value)
            elif key == "lys":
                light_system.set_light_allowed(value == "TIL")
    except Exception:
        pass


try:
    while True:
        receive_settings()
        soil1, soil2 = water_system.read()

        pumping = water_system.pump_if_needed(
            soil1, soil2, SOIL_MIN_P1, SOIL_MAX_P1, SOIL_MIN_P2, SOIL_MAX_P2
        )
        light = light_system.update(water_system.lights_should_be_off())
        water_status = water_level_sensor.read()

        message = "vandstand:{},soil1:{},soil2:{},light:{},pumpe:{},lysprofil:{},led:{}\n".format(
            water_status, soil1, soil2, light,
            "TIL" if pumping else "FRA",
            light_system.profile_name,
            light_system.led_percent,
        )
        uart.write(message)
        print(message)
        sleep(1)
finally:
    water_system.pump.value(0)
    light_system.set_color(0, 0, 0)
    print("System slukket - pumpe og LED slaaet fra")
