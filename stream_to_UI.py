from flask import Flask, jsonify, render_template
import time

from ina219 import INA219

import board
import digitalio
import adafruit_max6675


app = Flask(__name__)


# ============================================================
# SAFETY LIMITS
# ============================================================

MINIMUM_BATTERY_VOLTAGE = 6.4
MAXIMUM_BATTERY_TEMPERATURE = 60.0
MINIMUM_BATTERY_TEMPERATURE = 0.0


# ============================================================
# INA219
# ============================================================

ina219 = INA219(
    address=0x40,
    bus_number=1
)

ina219.begin()
ina219.set_calibration_32V_2A()


# ============================================================
# THERMOCOUPLE
# ============================================================

spi = board.SPI()

cs = digitalio.DigitalInOut(
    board.D5
)

thermocouple = adafruit_max6675.MAX6675(
    spi,
    cs
)


# ============================================================
# BATTERY DATA
# ============================================================

BATTERY_CAPACITY_AH = 3.0

remaining_capacity_Ah = 3.0

last_time = time.monotonic()


# ============================================================
# SENSOR DATA FUNCTION
# ============================================================

def get_sensor_data():

    global remaining_capacity_Ah
    global last_time


    # --------------------------------------------------------
    # Measure elapsed time
    # --------------------------------------------------------

    current_time = time.monotonic()

    elapsed_seconds = (
        current_time - last_time
    )

    elapsed_hours = (
        elapsed_seconds / 3600
    )


    # --------------------------------------------------------
    # Read current
    # --------------------------------------------------------

    current_mA = (
        ina219.get_current_mA()
    )

    current_A = (
        current_mA / 1000
    )


    # --------------------------------------------------------
    # Calculate charge used
    # --------------------------------------------------------

    charge_used_Ah = (
        current_A
        *
        elapsed_hours
    )


    remaining_capacity_Ah -= (
        charge_used_Ah
    )


    if remaining_capacity_Ah < 0:

        remaining_capacity_Ah = 0


    # --------------------------------------------------------
    # Read voltage
    # --------------------------------------------------------

    voltage = (
        ina219.get_bus_voltage_V()
    )


    # --------------------------------------------------------
    # Read temperature
    # --------------------------------------------------------

    temperature = (
        thermocouple.temperature
    )


    # --------------------------------------------------------
    # Calculate battery percentage
    # --------------------------------------------------------

    capacity_percentage = (

        remaining_capacity_Ah
        /
        BATTERY_CAPACITY_AH

    ) * 100


    # --------------------------------------------------------
    # Check safety limits
    # --------------------------------------------------------

    warnings = []


    if voltage <= MINIMUM_BATTERY_VOLTAGE:

        warnings.append(
            "BATTERY VOLTAGE TOO LOW"
        )


    if temperature > MAXIMUM_BATTERY_TEMPERATURE:

        warnings.append(
            "TEMPERATURE TOO HIGH"
        )


    if temperature < MINIMUM_BATTERY_TEMPERATURE:

        warnings.append(
            "TEMPERATURE TOO LOW"
        )


    # --------------------------------------------------------
    # Update timer
    # --------------------------------------------------------

    last_time = current_time


    # --------------------------------------------------------
    # Return all data
    # --------------------------------------------------------

    return {

        "voltage": round(
            voltage,
            2
        ),

        "current": round(
            current_A,
            3
        ),

        "temperature": round(
            temperature,
            2
        ),

        "capacity_ah": round(
            remaining_capacity_Ah,
            3
        ),

        "capacity_percent": round(
            capacity_percentage,
            1
        ),

        "warning": len(warnings) > 0,

        "warnings": warnings

    }


# ============================================================
# DATA API
# ============================================================

@app.route("/data")
def data():

    return jsonify(
        get_sensor_data()
    )


# ============================================================
# UI PAGE
# ============================================================

@app.route("/")
def index():

    return render_template(
        "index.html"
    )


# ============================================================
# START SERVER
# ============================================================

app.run(
    host="0.0.0.0",
    port=5000
)
