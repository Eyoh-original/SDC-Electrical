from ina219 import INA219
import time


# Create the INA219 object
ina219 = INA219(
    address=0x40,
    bus_number=1
)


# Check that the sensor is connected
if not ina219.begin():
    print("INA219 not found")
    exit()


# Configure the sensor
ina219.set_calibration_32V_2A()


while True:

    # Read current
    current_mA = ina219.get_current_mA()

    # Convert milliamps to amps
    current_A = current_mA / 1000

    print(f"Current: {current_A:.3f} A")

    time.sleep(1)
