"""
Adafruit MAX31855 Thermocouple Driver

Python port of the Adafruit_MAX31855 C++ Arduino library.

The MAX31855 uses SPI to communicate and returns a 32-bit data value.
"""

import math
import spidev


class AdafruitMAX31855:
    # Fault masks
    MAX31855_FAULT_NONE = 0x00
    MAX31855_FAULT_OPEN = 0x01
    MAX31855_FAULT_SHORT_GND = 0x02
    MAX31855_FAULT_SHORT_VCC = 0x04
    MAX31855_FAULT_ALL = 0x07

    def __init__(self, bus=0, device=0, max_speed_hz=1_000_000):
        """
        Initialize the MAX31855 using hardware SPI.

        :param bus: SPI bus number
        :param device: SPI chip-select/device number
        :param max_speed_hz: SPI clock speed
        """
        self.bus = bus
        self.device = device
        self.max_speed_hz = max_speed_hz

        self.spi = spidev.SpiDev()
        self.initialized = False

        # By default, check all faults
        self.fault_mask = self.MAX31855_FAULT_ALL

    def begin(self):
        """
        Initialize the SPI interface.

        :return: True if initialized successfully.
        """
        try:
            self.spi.open(self.bus, self.device)

            self.spi.max_speed_hz = self.max_speed_hz
            self.spi.mode = 0b00
            self.spi.lsbfirst = False

            self.initialized = True
            return True

        except Exception:
            self.initialized = False
            return False

    def _spiread32(self):
        """
        Read 4 bytes (32 bits) from the MAX31855 over SPI.

        :return: Raw 32-bit integer value.
        """
        if not self.initialized:
            self.begin()

        data = self.spi.readbytes(4)

        # Equivalent to combining buf[0] through buf[3]
        value = (
            (data[0] << 24)
            | (data[1] << 16)
            | (data[2] << 8)
            | data[3]
        )

        return value

    def read_internal(self):
        """
        Read the MAX31855 internal temperature.

        :return: Internal temperature in degrees Celsius.
        """
        value = self._spiread32()

        # Ignore bottom 4 bits
        value >>= 4

        # Extract bottom 11 bits
        internal = value & 0x7FF

        # Check sign bit
        if value & 0x800:
            # Sign extend the 11-bit signed value
            internal = internal - 0x1000

        # LSB = 0.0625 degrees Celsius
        internal *= 0.0625

        return internal

    def read_celsius(self):
        """
        Read the thermocouple temperature.

        :return: Temperature in degrees Celsius.
        :return: NaN if a configured fault is detected.
        """
        value = self._spiread32()

        # Check fault bits
        if value & self.fault_mask:
            return math.nan

        # Extract signed 14-bit thermocouple temperature
        if value & 0x80000000:
            # Negative value
            temperature = (value >> 18) & 0x3FFF

            # Sign extend 14-bit signed value
            if temperature & 0x2000:
                temperature -= 0x4000
        else:
            # Positive value
            temperature = value >> 18

        # LSB = 0.25 degrees Celsius
        return temperature * 0.25

    def read_fahrenheit(self):
        """
        Read the thermocouple temperature.

        :return: Temperature in degrees Fahrenheit.
        """
        celsius = self.read_celsius()

        if math.isnan(celsius):
            return math.nan

        return (celsius * 9.0 / 5.0) + 32.0

    def read_error(self):
        """
        Read the MAX31855 error state.

        :return: Fault bit mask.
        """
        return self._spiread32() & 0x07

    def set_fault_checks(self, faults):
        """
        Set which faults should cause read_celsius() to return NaN.

        :param faults: Combination of fault masks.
        """
        self.fault_mask = faults & 0x07

    def close(self):
        """
        Close the SPI connection.
        """
        if self.initialized:
            self.spi.close()
            self.initialized = False
