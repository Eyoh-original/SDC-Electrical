from smbus2 import SMBus


class INA219:
    # Default I2C address
    INA219_ADDRESS = 0x40

    # Register addresses
    REG_CONFIG = 0x00
    REG_SHUNT_VOLTAGE = 0x01
    REG_BUS_VOLTAGE = 0x02
    REG_POWER = 0x03
    REG_CURRENT = 0x04
    REG_CALIBRATION = 0x05

    # Configuration values
    CONFIG_RESET = 0x8000

    # Bus voltage range
    CONFIG_BVOLTAGERANGE_16V = 0x0000
    CONFIG_BVOLTAGERANGE_32V = 0x2000

    # Gain
    CONFIG_GAIN_1_40MV = 0x0000
    CONFIG_GAIN_2_80MV = 0x0800
    CONFIG_GAIN_4_160MV = 0x1000
    CONFIG_GAIN_8_320MV = 0x1800

    # ADC resolution
    CONFIG_BADCRES_12BIT = 0x0180
    CONFIG_SADCRES_12BIT_1S = 0x0018

    # Operating modes
    CONFIG_MODE_POWERDOWN = 0x00
    CONFIG_MODE_SVOLT_CONTINUOUS = 0x05
    CONFIG_MODE_BVOLT_CONTINUOUS = 0x06
    CONFIG_MODE_SANDBVOLT_CONTINUOUS = 0x07

    def __init__(self, address=INA219_ADDRESS, bus_number=1):
        self.address = address
        self.bus = SMBus(bus_number)

        self.cal_value = 0
        self.current_divider_mA = 1
        self.power_multiplier_mW = 1

        self._success = False

    # ---------------------------------------------------------
    # Low-level I2C functions
    # ---------------------------------------------------------

    def _write_register(self, register, value):
        """
        Write a 16-bit value to an INA219 register.
        INA219 uses big-endian register values.
        """
        high_byte = (value >> 8) & 0xFF
        low_byte = value & 0xFF

        self.bus.write_i2c_block_data(
            self.address,
            register,
            [high_byte, low_byte]
        )

    def _read_register(self, register):
        """
        Read a 16-bit value from an INA219 register.
        """
        data = self.bus.read_i2c_block_data(
            self.address,
            register,
            2
        )

        return (data[0] << 8) | data[1]

    # ---------------------------------------------------------
    # Initialization
    # ---------------------------------------------------------

    def begin(self):
        """
        Check whether the INA219 is connected.
        """
        try:
            self._read_register(self.REG_CONFIG)
            self._success = True
            return True

        except Exception as error:
            print("INA219 not found:", error)
            self._success = False
            return False

    def success(self):
        return self._success

    # ---------------------------------------------------------
    # Calibration
    # ---------------------------------------------------------

    def set_calibration_32V_2A(self):
        """
        Configure the INA219 for approximately:
        0-32 V
        0-2 A
        """

        self.cal_value = 4096

        # Current LSB = 100 uA per bit
        self.current_divider_mA = 10

        # Power LSB = 2 mW per bit
        self.power_multiplier_mW = 2.0

        self._write_register(
            self.REG_CALIBRATION,
            self.cal_value
        )

        config = (
            self.CONFIG_BVOLTAGERANGE_32V
            | self.CONFIG_GAIN_8_320MV
            | self.CONFIG_BADCRES_12BIT
            | self.CONFIG_SADCRES_12BIT_1S
            | self.CONFIG_MODE_SANDBVOLT_CONTINUOUS
        )

        self._write_register(
            self.REG_CONFIG,
            config
        )

    def set_calibration_32V_1A(self):
        """
        Configure the INA219 for approximately:
        0-32 V
        0-1 A
        """

        self.cal_value = 10240

        # Current LSB = 40 uA per bit
        self.current_divider_mA = 25

        # Power LSB = 800 uW per bit
        self.power_multiplier_mW = 0.8

        self._write_register(
            self.REG_CALIBRATION,
            self.cal_value
        )

        config = (
            self.CONFIG_BVOLTAGERANGE_32V
            | self.CONFIG_GAIN_8_320MV
            | self.CONFIG_BADCRES_12BIT
            | self.CONFIG_SADCRES_12BIT_1S
            | self.CONFIG_MODE_SANDBVOLT_CONTINUOUS
        )

        self._write_register(
            self.REG_CONFIG,
            config
        )

    def set_calibration_16V_400mA(self):
        """
        Configure the INA219 for approximately:
        0-16 V
        0-400 mA
        """

        self.cal_value = 8192

        # Current LSB = 100 uA per bit
        self.current_divider_mA = 10

        # Power LSB = 2 mW per bit
        self.power_multiplier_mW = 2.0

        self._write_register(
            self.REG_CALIBRATION,
            self.cal_value
        )

        config = (
            self.CONFIG_BVOLTAGERANGE_16V
            | self.CONFIG_GAIN_1_40MV
            | self.CONFIG_BADCRES_12BIT
            | self.CONFIG_SADCRES_12BIT_1S
            | self.CONFIG_MODE_SANDBVOLT_CONTINUOUS
        )

        self._write_register(
            self.REG_CONFIG,
            config
        )

    # ---------------------------------------------------------
    # Raw readings
    # ---------------------------------------------------------

    def get_bus_voltage_raw(self):
        """
        Read raw bus voltage value.
        """
        value = self._read_register(self.REG_BUS_VOLTAGE)

        # Bus voltage register:
        # Bits 15-3 contain voltage
        value >>= 3

        return value

    def get_shunt_voltage_raw(self):
        """
        Read raw shunt voltage value as signed 16-bit integer.
        """
        value = self._read_register(self.REG_SHUNT_VOLTAGE)

        if value & 0x8000:
            value -= 0x10000

        return value

    def get_current_raw(self):
        """
        Read raw current value as signed 16-bit integer.
        """
        value = self._read_register(self.REG_CURRENT)

        if value & 0x8000:
            value -= 0x10000

        return value

    def get_power_raw(self):
        """
        Read raw power value.
        """
        return self._read_register(self.REG_POWER)

    # ---------------------------------------------------------
    # Human-readable measurements
    # ---------------------------------------------------------

    def get_bus_voltage_V(self):
        """
        Return bus voltage in volts.
        """

        raw_value = self.get_bus_voltage_raw()

        # Each bit = 4 mV
        return raw_value * 0.004

    def get_shunt_voltage_mV(self):
        """
        Return shunt voltage in millivolts.

        Each bit = 10 uV = 0.01 mV
        """

        raw_value = self.get_shunt_voltage_raw()

        return raw_value * 0.01

    def get_current_mA(self):
        """
        Return current in milliamps.
        """

        raw_value = self.get_current_raw()

        return raw_value / self.current_divider_mA

    def get_power_mW(self):
        """
        Return power in milliwatts.
        """

        raw_value = self.get_power_raw()

        return raw_value * self.power_multiplier_mW

    # ---------------------------------------------------------
    # Power saving
    # ---------------------------------------------------------

    def power_save(self, on):
        """
        Enable or disable power-saving mode.
        """

        config = self._read_register(self.REG_CONFIG)

        if on:
            config &= 0xFFF8
            config |= self.CONFIG_MODE_POWERDOWN
        else:
            config &= 0xFFF8
            config |= self.CONFIG_MODE_SANDBVOLT_CONTINUOUS

        self._write_register(
            self.REG_CONFIG,
            config
        )

    # ---------------------------------------------------------
    # Close I2C bus
    # ---------------------------------------------------------

    def close(self):
        self.bus.close()
