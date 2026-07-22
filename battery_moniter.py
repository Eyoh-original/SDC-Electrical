from ina219 import INA219
import time


# ============================================================
# BATTERY SETTINGS
# ============================================================

BATTERY_CAPACITY_AH = 3.0

BATTERY_FULL_VOLTAGE = 7.4
BATTERY_MINIMUM_VOLTAGE = 6.4


# ============================================================
# CREATE INA219 SENSOR
# ============================================================

ina219 = INA219(
    address=0x40,
    bus_number=1
)


# ============================================================
# INITIALIZE SENSOR
# ============================================================

if not ina219.begin():
    print("INA219 not found")
    exit()


# Configure for your expected current range
ina219.set_calibration_32V_2A()


# ============================================================
# INITIAL BATTERY STATE
# ============================================================

remaining_capacity_Ah = BATTERY_CAPACITY_AH

last_time = time.monotonic()


# ============================================================
# MAIN MONITORING LOOP
# ============================================================

while True:

    # --------------------------------------------------------
    # 1. Get the current time
    # --------------------------------------------------------

    current_time = time.monotonic()


    # --------------------------------------------------------
    # 2. Calculate how much time has passed
    # --------------------------------------------------------

    elapsed_seconds = current_time - last_time

    elapsed_hours = elapsed_seconds / 3600


    # --------------------------------------------------------
    # 3. Read the current from the INA219
    # --------------------------------------------------------

    current_mA = ina219.get_current_mA()

    current_A = current_mA / 1000


    # --------------------------------------------------------
    # 4. Calculate charge consumed during this interval
    # --------------------------------------------------------

    charge_used_Ah = current_A * elapsed_hours


    # --------------------------------------------------------
    # 5. Subtract that charge from the battery capacity
    # --------------------------------------------------------

    remaining_capacity_Ah -= charge_used_Ah


    # Prevent the value becoming negative
    if remaining_capacity_Ah < 0:
        remaining_capacity_Ah = 0


    # --------------------------------------------------------
    # 6. Read the battery voltage
    # --------------------------------------------------------

    battery_voltage = ina219.get_bus_voltage_V()


    # --------------------------------------------------------
    # 7. Calculate percentage remaining
    # --------------------------------------------------------

    battery_percentage = (
        remaining_capacity_Ah / BATTERY_CAPACITY_AH
    ) * 100


    # Keep percentage between 0 and 100
    battery_percentage = max(
        0,
        min(100, battery_percentage)
    )


    # --------------------------------------------------------
    # 8. Display the information
    # --------------------------------------------------------

    print(f"Battery Voltage: {battery_voltage:.2f} V")
    print(f"Current:         {current_A:.3f} A")
    print(f"Remaining:       {remaining_capacity_Ah:.3f} Ah")
    print(f"Battery:         {battery_percentage:.1f}%")

    print("-----------------------------")


    # --------------------------------------------------------
    # 9. Check minimum voltage
    # --------------------------------------------------------

    if battery_voltage <= BATTERY_MINIMUM_VOLTAGE:

        print("WARNING: BATTERY VOLTAGE TOO LOW")


    # --------------------------------------------------------
    # 10. Save time for the next measurement
    # --------------------------------------------------------

    last_time = current_time


    # Wait one second
    time.sleep(1)
