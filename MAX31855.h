import board
import digitalio
import adafruit_max31855


class MAX31855:

    def __init__(
        self,
        spi,
        cs_pin
    ):

        self.spi = spi

        self.cs = digitalio.DigitalInOut(
            cs_pin
        )

        self.sensor = adafruit_max31855.MAX31855(
            self.spi,
            self.cs
        )

    def read_celsius(self):

        return self.sensor.temperature

    def read_fahrenheit(self):

        celsius = self.read_celsius()

        return (
            celsius * 9 / 5
        ) + 32
