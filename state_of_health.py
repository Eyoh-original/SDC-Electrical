```python
# state_of_health.py

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
# FALLBACK BATTERY SETTINGS
# ============================================================

# Used when the INA219 current sensor is unavailable.

# Approximate average current consumption of the system.
# Change this value to match your actual system.
ESTIMATED_CURRENT_A = 0.5


# Approximate battery voltage drop per amp-hour consumed.
# This is an approximation and should be calibrated experimentally.
ESTIMATED_VOLTAGE_DROP_PER_AH = (

    BATTERY_FULL_VOLTAGE
    -
    BATTERY_MINIMUM_VOLTAGE

) / BATTERY_CAPACITY_AH


# ============================================================
# INA219 SETUP
# ============================================================

ina219 = INA219(

    address=0x40,

    bus_number=1

)


ina219_available = False


try:

    if ina219.begin():

        ina219.set_calibration_32V_2A()

        ina219_available = True

        print(
            "INA219 current sensor connected."
        )

    else:

        print(
            "WARNING: INA219 not found."
        )

        print(
            "Using estimated battery values."
        )


except Exception as error:

    print(
        "WARNING: INA219 failed to initialise."
    )

    print(
        f"Sensor error: {error}"
    )

    print(
        "Using estimated battery values."
    )


# ============================================================
# THERMOCOUPLE SETUP
# ============================================================

thermocouple = AdafruitMAX31855(

    bus=0,

    device=0

)


thermocouple_available = (

    thermocouple.begin()
)


if not thermocouple_available:

    print(
        "WARNING: Thermocouple unavailable."
    )


# ============================================================
# BATTERY STATE
# ============================================================

remaining_capacity_Ah = None

last_battery_time = None

last_known_voltage = None


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

    global last_known_voltage


    # --------------------------------------------------------
    # Try to obtain initial voltage from INA219
    # --------------------------------------------------------

    if ina219_available:

        try:

            starting_voltage = (

                ina219.get_bus_voltage_V()

            )


        except Exception as error:

            print(
                "WARNING: Could not read battery voltage."
            )

            print(
                f"Sensor error: {error}"
            )

            starting_voltage = (

                BATTERY_FULL_VOLTAGE
                +
                BATTERY_MINIMUM_VOLTAGE

            ) / 2


    else:

        # If there is no sensor, use the midpoint
        # between full and minimum voltage.

        starting_voltage = (

            BATTERY_FULL_VOLTAGE
            +
            BATTERY_MINIMUM_VOLTAGE

        ) / 2


    last_known_voltage = (

        starting_voltage

    )


    print(

        f"Starting battery voltage: "
        f"{starting_voltage:.2f} V"

    )


    # --------------------------------------------------------
    # Check for low voltage
    # --------------------------------------------------------

    if (

        starting_voltage
        <=
        BATTERY_MINIMUM_VOLTAGE

    ):

        print()

        print(
            "WARNING!"
        )

        print(

            "Battery voltage is at "
            "or below the minimum."

        )

        print(

            "Battery should be charged "
            "before use."

        )


    # --------------------------------------------------------
    # Estimate initial battery percentage
    # --------------------------------------------------------

    starting_voltage_percentage = (

        calculate_percentage(

            starting_voltage,

            BATTERY_MINIMUM_VOLTAGE,

            BATTERY_FULL_VOLTAGE

        )

    )


    print(

        f"Starting voltage estimate: "
        f"{starting_voltage_percentage:.1f}%"

    )


    # --------------------------------------------------------
    # Load previous capacity state
    # --------------------------------------------------------

    if os.path.exists(

        BATTERY_STATE_FILE

    ):

        try:

            with open(

                BATTERY_STATE_FILE,

                "r"

            ) as file:

                remaining_capacity_Ah = (

                    float(

                        file.read()

                    )

                )


            print(

                f"Previous capacity loaded: "
                f"{remaining_capacity_Ah:.3f} Ah"

            )


        except (

            ValueError,

            OSError

        ):

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


    last_battery_time = (

        time.monotonic()

    )


# ============================================================
# READ BATTERY USING INA219
# ============================================================

def read_battery_from_sensor():

    global last_known_voltage


    try:

        current_mA = (

            ina219.get_current_mA()

        )


        battery_voltage = (

            ina219.get_bus_voltage_V()

        )


        current_A = (

            current_mA
            /
            1000

        )


        last_known_voltage = (

            battery_voltage

        )


        return {

            "success": True,

            "voltage": battery_voltage,

            "current": current_A,

            "source": "INA219"

        }


    except Exception as error:

        print()

        print(

            "WARNING: INA219 reading failed."

        )

        print(

            f"Sensor error: {error}"

        )

        print(

            "Switching to estimated battery values."

        )


        return {

            "success": False,

            "voltage": None,

            "current": None,

            "source": "fallback"

        }


# ============================================================
# ESTIMATE BATTERY VALUES
# ============================================================

def estimate_battery_values(

    elapsed_hours

):

    global remaining_capacity_Ah

    global last_known_voltage


    # --------------------------------------------------------
    # Estimate current
    # --------------------------------------------------------

    estimated_current_A = (

        ESTIMATED_CURRENT_A

    )


    # --------------------------------------------------------
    # Estimate charge consumed
    # --------------------------------------------------------

    charge_used_Ah = (

        estimated_current_A
        *
        elapsed_hours

    )


    remaining_capacity_Ah -= (

        charge_used_Ah

    )


    if (

        remaining_capacity_Ah
        <
        0

    ):

        remaining_capacity_Ah = 0


    # --------------------------------------------------------
    # Estimate voltage
    # --------------------------------------------------------

    estimated_voltage = (

        BATTERY_MINIMUM_VOLTAGE

        +

        (

            remaining_capacity_Ah
            /
            BATTERY_CAPACITY_AH

        )

        *

        (

            BATTERY_FULL_VOLTAGE
            -
            BATTERY_MINIMUM_VOLTAGE

        )

    )


    last_known_voltage = (

        estimated_voltage

    )


    return {

        "voltage":

            estimated_voltage,

        "current":

            estimated_current_A,

        "source":

            "estimated"

    }


# ============================================================
# BATTERY MONITOR
# ============================================================

def read_battery():

    global remaining_capacity_Ah

    global last_battery_time


    # --------------------------------------------------------
    # Initialise battery state
    # --------------------------------------------------------

    if (

        remaining_capacity_Ah
        is
        None

    ):

        initialise_battery()


    # --------------------------------------------------------
    # Calculate elapsed time
    # --------------------------------------------------------

    current_time = (

        time.monotonic()

    )


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
    # Try to read the INA219
    # --------------------------------------------------------

    sensor_reading = (

        read_battery_from_sensor()

    )


    # --------------------------------------------------------
    # Sensor available
    # --------------------------------------------------------

    if (

        sensor_reading["success"]

    ):

        battery_voltage = (

            sensor_reading["voltage"]

        )


        current_A = (

            sensor_reading["current"]

        )


        source = (

            "INA219"

        )


        # Use the real measured current
        # to calculate charge consumed.

        charge_used_Ah = (

            current_A
            *
            elapsed_hours

        )


        remaining_capacity_Ah -= (

            charge_used_Ah

        )


    # --------------------------------------------------------
    # Sensor failed
    # --------------------------------------------------------

    else:

        estimated_values = (

            estimate_battery_values(

                elapsed_hours

            )

        )


        battery_voltage = (

            estimated_values["voltage"]

        )


        current_A = (

            estimated_values["current"]

        )


        source = (

            "ESTIMATED"

        )


    # --------------------------------------------------------
    # Prevent negative capacity
    # --------------------------------------------------------

    if (

        remaining_capacity_Ah
        <
        0

    ):

        remaining_capacity_Ah = 0


    # --------------------------------------------------------
    # Calculate battery percentages
    # --------------------------------------------------------

    capacity_percentage = (

        (

            remaining_capacity_Ah
            /
            BATTERY_CAPACITY_AH

        )

        *

        100

    )


    capacity_percentage = max(

        0,

        min(100, capacity_percentage)

    )


    voltage_percentage = (

        calculate_percentage(

            battery_voltage,

            BATTERY_MINIMUM_VOLTAGE,

            BATTERY_FULL_VOLTAGE

        )

    )


    # --------------------------------------------------------
    # Save battery capacity
    # --------------------------------------------------------

    try:

        with open(

            BATTERY_STATE_FILE,

            "w"

        ) as file:

            file.write(

                str(

                    remaining_capacity_Ah

                )

            )

    except OSError as error:

        print(

            f"WARNING: Could not save battery state: "
            f"{error}"

        )


    # --------------------------------------------------------
    # Update time
    # --------------------------------------------------------

    last_battery_time = (

        current_time

    )


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

            (

                battery_voltage
                <=
                BATTERY_MINIMUM_VOLTAGE

            ),

        "source":

            source

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

                temperature = (

                    float(

                        match.group()

                    )

                )

            except ValueError:

                temperature = None


    return {

        "temperature":

            temperature,

        "message":

            message,

        "available":

            temperature is not None

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


    try:

        temperature_c = (

            thermocouple.read_celsius()

        )


        internal_temperature = (

            thermocouple.read_internal()

        )


        if math.isnan(

            temperature_c

        ):

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


    except Exception as error:

        return {

            "available": False,

            "temperature_c": None,

            "temperature_f": None,

            "internal_temperature_c": None,

            "error": str(error)

        }


# ============================================================
# COMPLETE STATE OF HEALTH
# ============================================================

def get_state_of_health():

    return {

        "timestamp":

            time.time(),

        "battery":

            read_battery(),

        "cpu":

            read_cpu_temperature(),

        "thermocouple":

            read_thermocouple()

    }


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

        state_of_health["battery"]

    )


    print()

    print(

        "BATTERY"

    )


    print(

        f"Voltage: "
        f"{battery['voltage']:.2f} V"

    )


    print(

        f"Current: "
        f"{battery['current']:.3f} A"

    )


    print(

        f"Capacity: "
        f"{battery['remaining_capacity_Ah']:.3f} Ah"

    )


    print(

        f"Capacity Percentage: "
        f"{battery['capacity_percentage']:.1f}%"

    )


    print(

        f"Voltage Percentage: "
        f"{battery['voltage_percentage']:.1f}%"

    )


    print(

        f"Data Source: "
        f"{battery['source']}"

    )


    if (

        battery["low_voltage"]

    ):

        print()

        print(

            "WARNING: Battery voltage is low!"

        )


    # --------------------------------------------------------
    # CPU
    # --------------------------------------------------------

    cpu = (

        state_of_health["cpu"]

    )


    print()

    print(

        "RASPBERRY PI CPU"

    )


    if (

        cpu["available"]

    ):

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

        state_of_health["thermocouple"]

    )


    print()

    print(

        "THERMOCOUPLE"

    )


    if (

        thermocouple_data["error"]

        is not None

    ):

        print(

            "Thermocouple fault: "
            f"0x"
            f"{thermocouple_data['error']:02X}"

            if isinstance(

                thermocouple_data["error"],

                int

            )

            else

            f"Thermocouple error: "
            f"{thermocouple_data['error']}"

        )


    elif (

        thermocouple_data["temperature_c"]

        is not None

    ):

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

            "Temperature unavailable"

        )


    if (

        thermocouple_data[
            "internal_temperature_c"
        ]

        is not None

    ):

        print(

            f"Internal Temperature: "
            f"{thermocouple_data['internal_temperature_c']:.2f} °C"

        )


    print()

    print(

        "================================"

    )
```

Your `main.py` can remain:

```python
import time

from state_of_health import (

    get_state_of_health,

    print_state_of_health

)


while True:

    health = (

        get_state_of_health()

    )


    print_state_of_health(

        health

    )


    time.sleep(1)
```
