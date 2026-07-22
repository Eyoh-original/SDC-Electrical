from ina219 import INA219
import time
import os


# ============================================================
# BATTERY SETTINGS
# ============================================================

BATTERY_CAPACITY_AH = 3.0

BATTERY_FULL_VOLTAGE = 7.4
BATTERY_MINIMUM_VOLTAGE = 6.4


# ============================================================
# INA219 SETUP
# ============================================================

ina219 = INA219(
    address=0x40,
    bus_number=1
)


# Check that the INA219 is connected
if not ina219.begin():
    print("INA219 not found")
    exit()


# Configure the INA219
ina219.set_calibration_32V_2A()


# ============================================================
# READ INITIAL BATTERY VOLTAGE
# ============================================================

starting_voltage = ina219.get_bus_voltage_V()


print(f"Starting battery voltage: {starting_voltage:.2f} V")


# ============================================================
# CHECK WHETHER BATTERY VOLTAGE IS TOO LOW
# ============================================================

if starting_voltage <= BATTERY_MINIMUM_VOLTAGE:

    print("WARNING!")
    print("Battery voltage is already at or below the minimum.")
    print("Battery should be charged before use.")

    exit()


# ============================================================
# CALCULATE STARTING VOLTAGE PERCENTAGE
# ============================================================

starting_voltage_percentage = (
    (starting_voltage - BATTERY_MINIMUM_VOLTAGE)
    /
    (BATTERY_FULL_VOLTAGE - BATTERY_MINIMUM_VOLTAGE)
) * 100


# Keep percentage between 0 and 100
starting_voltage_percentage = max(
    0,
    min(100, starting_voltage_percentage)
)


print(
    f"Starting voltage estimate: "
    f"{starting_voltage_percentage:.1f}%"
)


# ============================================================
# LOAD PREVIOUS CAPACITY STATE
# ============================================================

STATE_FILE = "battery_state.txt"


if os.path.exists(STATE_FILE):

    with open(STATE_FILE, "r") as file:

        remaining_capacity_Ah = float(
            file.read()
        )

    print(
        f"Previous capacity loaded: "
        f"{remaining_capacity_Ah:.3f} Ah"
    )


else:

    # If there is no saved battery state,
    # use the starting voltage to estimate
    # the initial capacity.

    remaining_capacity_Ah = (
        starting_voltage_percentage
        / 100
    ) * BATTERY_CAPACITY_AH

    print(
        f"Initial capacity estimated from voltage: "
        f"{remaining_capacity_Ah:.3f} Ah"
    )


# ============================================================
# START TIMING
# ============================================================

last_time = time.monotonic()


# ============================================================
# MAIN MONITORING LOOP
# ============================================================

while True:


    # --------------------------------------------------------
    # 1. Get current time
    # --------------------------------------------------------

    current_time = time.monotonic()


    # --------------------------------------------------------
    # 2. Calculate elapsed time
    # --------------------------------------------------------

    elapsed_seconds = (
        current_time - last_time
    )


    elapsed_hours = (
        elapsed_seconds / 3600
    )


    # --------------------------------------------------------
    # 3. Measure current
    # --------------------------------------------------------

    current_mA = (
        ina219.get_current_mA()
    )


    current_A = (
        current_mA / 1000
    )


    # --------------------------------------------------------
    # 4. Calculate charge consumed
    # --------------------------------------------------------

    charge_used_Ah = (
        current_A * elapsed_hours
    )


    # --------------------------------------------------------
    # 5. Subtract consumed charge
    # --------------------------------------------------------

    remaining_capacity_Ah -= (
        charge_used_Ah
    )


    # Prevent negative capacity
    if remaining_capacity_Ah < 0:

        remaining_capacity_Ah = 0


    # --------------------------------------------------------
    # 6. Calculate capacity percentage
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
    # 7. Measure battery voltage
    # --------------------------------------------------------

    battery_voltage = (
        ina219.get_bus_voltage_V()
    )


    # --------------------------------------------------------
    # 8. Calculate voltage percentage
    # --------------------------------------------------------

    voltage_percentage = (

        (
            battery_voltage
            -
            BATTERY_MINIMUM_VOLTAGE
        )

        /

        (
            BATTERY_FULL_VOLTAGE
            -
            BATTERY_MINIMUM_VOLTAGE
        )

    ) * 100


    # Keep voltage percentage between 0 and 100
    voltage_percentage = max(
        0,
        min(100, voltage_percentage)
    )


    # --------------------------------------------------------
    # 9. Save the capacity state
    # --------------------------------------------------------

    with open(STATE_FILE, "w") as file:

        file.write(
            str(remaining_capacity_Ah)
        )


    # --------------------------------------------------------
    # 10. Display the readings
    # --------------------------------------------------------

    print()
    print("==============================")

    print(
        f"Battery Voltage: "
        f"{battery_voltage:.2f} V"
    )

    print(
        f"Current: "
        f"{current_A:.3f} A"
    )

    print(
        f"Remaining Capacity: "
        f"{remaining_capacity_Ah:.3f} Ah"
    )

    print(
        f"Capacity Percentage: "
        f"{capacity_percentage:.1f}%"
    )

    print(
        f"Voltage Percentage: "
        f"{voltage_percentage:.1f}%"
    )

    print("==============================")


    # --------------------------------------------------------
    # 11. Check for low voltage
    # --------------------------------------------------------

    if battery_voltage <= BATTERY_MINIMUM_VOLTAGE:

        print()
        print(
            "CRITICAL WARNING:"
        )

        print(
            "Battery voltage has reached "
            "the minimum allowed voltage."
        )

        print(
            "Consider shutting down the system."
        )


    # --------------------------------------------------------
    # 12. Update time
    # --------------------------------------------------------

    last_time = current_time


    # Wait one second
    time.sleep(1)
