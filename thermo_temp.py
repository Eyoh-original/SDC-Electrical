from max31855 import AdafruitMAX31855
import math

sensor = AdafruitMAX31855(bus=0, device=0)

if sensor.begin():
    temperature_c = sensor.read_celsius()
    temperature_f = sensor.read_fahrenheit()
    internal_temp = sensor.read_internal()

    if math.isnan(temperature_c):
        error = sensor.read_error()

        print(f"Thermocouple fault: 0x{error:02X}")
    else:
        print(f"Thermocouple: {temperature_c:.2f} °C")
        print(f"Thermocouple: {temperature_f:.2f} °F")

    print(f"Internal temperature: {internal_temp:.2f} °C")

    sensor.close()
else:
    print("Could not initialize SPI")
