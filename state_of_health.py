import re
import subprocess
import time
import os
import math

from ina219 import INA219
from max31855 import AdafruitMAX31855


# ============================================================
# BATTERY SETTINGS
# ============================================================

BATTERY_CAPACITY_AH = 3.0
BATTERY_FULL_VOLTAGE = 7.4
BATTERY_MINIMUM_VOLTAGE = 6.4

BATTERY_STATE_FILE = "battery_state.txt"


# ============================================================
# INA219 SETUP
# ============================================================

ina219 = INA219(
    address=0x40,
    bus_number=1
)

ina219_available = False

if ina219.begin():

    ina219.set_calibration_32V_2A()

    ina219_available = True

else:

    print("WARNING: INA219 not found")


# ============================================================
# THERMOCOUPLE SETUP
# ============================================================

thermocouple = AdafruitMAX31855(
    bus=0,
    device=0
)

thermocouple_available = thermocouple.begin()

if not thermocouple_available:

    print("WARNING: Could not initialize thermocouple SPI")


# ============================================================
# BATTERY STATE
# ============================================================

remaining_capacity_Ah = None
last_battery_time = None


# ============================================================
# HELPER FUNCTION
# ============================================================

def calculate_percentage(
    value,
    minimum,
    maximum
):

    percentage = (

        (
            value
            -
            minimum
        )

        /

        (
            maximum
            -
            minimum
        )

    ) * 100

    return max(
        0,
        min(100, percentage)
    )


# ============================================================
# INITIALISE BATTERY STATE
# ============================================================

def initialise_battery():

    global remaining_capacity_Ah
    global last_battery_time

    if not ina219_available:

        return False


    starting_voltage = (
        ina219.get_bus_voltage_V()
    )


    print(
        f"Starting battery voltage: "
        f"{starting_voltage:.2f} V"
    )


    if starting_voltage <= BATTERY_MINIMUM_VOLTAGE:

        print("WARNING!")
        print(
            "Battery voltage is already at "
            "or below the minimum."
        )

        print(
            "Battery should be charged "
            "before use."
        )


    starting_voltage_percentage = calculate_percentage(

        starting_voltage,

        BATTERY_MINIMUM_VOLTAGE,

        BATTERY_FULL_VOLTAGE

    )


    print(
        f"Starting voltage estimate: "
        f"{starting_voltage_percentage:.1f}%"
    )


    # --------------------------------------------------------
    # Load saved battery capacity
    # --------------------------------------------------------

    if os.path.exists(BATTERY_STATE_FILE):

        try:

            with open(
                BATTERY_STATE_FILE,
                "r"
            ) as file:

                remaining_capacity_Ah = float(
                    file.read()
                )


            print(
                f"Previous capacity loaded: "
                f"{remaining_capacity_Ah:.3f} Ah"
            )


        except ValueError:

            print(
                "Invalid battery state file."
            )

            remaining_capacity_Ah = (

                starting_voltage_percentage
                /
                100

            ) * BATTERY_CAPACITY_AH


    else:

        remaining_capacity_Ah = (

            starting_voltage_percentage
            /
            100

        ) * BATTERY_CAPACITY_AH


        print(
            f"Initial capacity estimated "
            f"from voltage: "
            f"{remaining_capacity_Ah:.3f} Ah"
        )


    last_battery_time = time.monotonic()

    return True


# ============================================================
# BATTERY MONITOR
# ============================================================

def read_battery():

    global remaining_capacity_Ah
    global last_battery_time


    if not ina219_available:

        return {

            "available": False,

            "voltage": None,

            "current": None,

            "remaining_capacity_Ah": None,

            "capacity_percentage": None,

            "voltage_percentage": None,

            "low_voltage": None

        }


    # --------------------------------------------------------
    # Initialise battery state if required
    # --------------------------------------------------------

    if remaining_capacity_Ah is None:

        initialise_battery()


    # --------------------------------------------------------
    # Calculate elapsed time
    # --------------------------------------------------------

    current_time = time.monotonic()

    elapsed_seconds = (

        current_time
        -
        last_battery_time

    )

    elapsed_hours = (

        elapsed_seconds
        /
        3600

    )


    # --------------------------------------------------------
    # Read current
    # --------------------------------------------------------

    current_mA = (

        ina219.get_current_mA()
    )


    current_A = (

        current_mA
        /
        1000
    )


    # --------------------------------------------------------
    # Calculate charge consumed
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
    # Calculate capacity percentage
    # --------------------------------------------------------

    capacity_percentage = (

        remaining_capacity_Ah
        /
        BATTERY_CAPACITY_AH

    ) * 100


    capacity_percentage = max(

        0,
        min(100, capacity_percentage)

    )


    # --------------------------------------------------------
    # Read voltage
    # --------------------------------------------------------

    battery_voltage = (

        ina219.get_bus_voltage_V()
    )


    voltage_percentage = calculate_percentage(

        battery_voltage,

        BATTERY_MINIMUM_VOLTAGE,

        BATTERY_FULL_VOLTAGE

    )


    # --------------------------------------------------------
    # Save capacity state
    # --------------------------------------------------------

    with open(

        BATTERY_STATE_FILE,
        "w"

    ) as file:

        file.write(

            str(
                remaining_capacity_Ah
            )

        )


    # --------------------------------------------------------
    # Update time
    # --------------------------------------------------------

    last_battery_time = current_time


    return {

        "available": True,

        "voltage": battery_voltage,

        "current": current_A,

        "remaining_capacity_Ah":
            remaining_capacity_Ah,

        "capacity_percentage":
            capacity_percentage,

        "voltage_percentage":
            voltage_percentage,

        "low_voltage":
            battery_voltage <= BATTERY_MINIMUM_VOLTAGE

    }


# ============================================================
# RASPBERRY PI CPU TEMPERATURE
# ============================================================

def read_cpu_temperature():

    temperature = None

    error_code, message = (

        subprocess.getstatusoutput(

            "vcgencmd measure_temp"

        )

    )


    if not error_code:

        match = re.search(

            r"-?\d\.?\d*",

            message

        )


        if match:

            try:

                temperature = float(
                    match.group()
                )

            except ValueError:

                temperature = None


    return {

        "temperature": temperature,

        "message": message,

        "available": temperature is not None

    }


# ============================================================
# THERMOCOUPLE TEMPERATURE
# ============================================================

def read_thermocouple():

    if not thermocouple_available:

        return {

            "available": False,

            "temperature_c": None,

            "temperature_f": None,

            "internal_temperature_c": None,

            "error": None

        }


    temperature_c = (

        thermocouple.read_celsius()
    )


    internal_temperature = (

        thermocouple.read_internal()
    )


    if math.isnan(temperature_c):

        error = (

            thermocouple.read_error()
        )


        return {

            "available": True,

            "temperature_c": None,

            "temperature_f": None,

            "internal_temperature_c":
                internal_temperature,

            "error": error

        }


    temperature_f = (

        thermocouple.read_fahrenheit()
    )


    return {

        "available": True,

        "temperature_c":
            temperature_c,

        "temperature_f":
            temperature_f,

        "internal_temperature_c":
            internal_temperature,

        "error": None

    }


# ============================================================
# COMPLETE STATE OF HEALTH READING
# ============================================================

def get_state_of_health():

    battery = read_battery()

    cpu = read_cpu_temperature()

    thermocouple_data = read_thermocouple()


    state_of_health = {

        "timestamp":
            time.time(),

        "battery":
            battery,

        "cpu":
            cpu,

        "thermocouple":
            thermocouple_data

    }


    return state_of_health


# ============================================================
# DISPLAY STATE OF HEALTH
# ============================================================

def print_state_of_health(
    state_of_health
):

    print()

    print(
        "================================"
    )

    print(
        "       SYSTEM STATE OF HEALTH"
    )

    print(
        "================================"
    )


    # --------------------------------------------------------
    # Battery
    # --------------------------------------------------------

    battery = (

        state_of_health[
            "battery"
        ]

    )


    print()

    print("BATTERY")

    print(
        f"Voltage: "
        f"{battery['voltage']:.2f} V"
        if battery["voltage"] is not None
        else "Voltage: unavailable"
    )


    print(
        f"Current: "
        f"{battery['current']:.3f} A"
        if battery["current"] is not None
        else "Current: unavailable"
    )


    print(
        f"Capacity: "
        f"{battery['remaining_capacity_Ah']:.3f} Ah"
        if battery[
            "remaining_capacity_Ah"
        ] is not None
        else "Capacity: unavailable"
    )


    print(
        f"Capacity Percentage: "
        f"{battery['capacity_percentage']:.1f}%"
        if battery[
            "capacity_percentage"
        ] is not None
        else "Capacity Percentage: unavailable"
    )


    print(
        f"Voltage Percentage: "
        f"{battery['voltage_percentage']:.1f}%"
        if battery[
            "voltage_percentage"
        ] is not None
        else "Voltage Percentage: unavailable"
    )


    if battery["low_voltage"]:

        print(
            "WARNING: Battery voltage is low!"
        )


    # --------------------------------------------------------
    # CPU
    # --------------------------------------------------------

    cpu = (

        state_of_health[
            "cpu"
        ]

    )


    print()

    print("RASPBERRY PI CPU")


    if cpu["available"]:

        print(
            f"Temperature: "
            f"{cpu['temperature']:.2f} °C"
        )

    else:

        print(
            "Temperature: unavailable"
        )


    # --------------------------------------------------------
    # Thermocouple
    # --------------------------------------------------------

    thermocouple_data = (

        state_of_health[
            "thermocouple"
        ]

    )


    print()

    print("THERMOCOUPLE")


    if thermocouple_data["error"] is not None:

        print(
            "Thermocouple fault: "
            f"0x"
            f"{thermocouple_data['error']:02X}"
        )


    elif thermocouple_data["temperature_c"] is not None:

        print(
            f"Temperature: "
            f"{thermocouple_data['temperature_c']:.2f} °C"
        )

        print(
            f"Temperature: "
            f"{thermocouple_data['temperature_f']:.2f} °F"
        )


    else:

        print(
            "Thermocouple temperature unavailable"
        )


    if thermocouple_data[
        "internal_temperature_c"
    ] is not None:

        print(
            f"Internal Temperature: "
            f"{thermocouple_data['internal_temperature_c']:.2f} °C"
        )


    print()

    print(
        "================================"
    )
