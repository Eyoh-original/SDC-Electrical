from smbus2 import SMBus


class INA219:
    # Default I2C address
    INA219_ADDRESS = 0x40

    # INA219 registers
    REG_CONFIG = 0x00
    REG_SHUNTVOLTAGE = 0x01
    REG_BUSVOLTAGE = 0x02
    REG_POWER = 0x03
    REG_CURRENT = 0x04
    REG_CALIBRATION = 0x05

    # Configuration values
    CONFIG_BVOLTAGERANGE_16V = 0x0000
    CONFIG_BVOLTAGERANGE_32V = 0x2000

    CONFIG_GAIN_1_40MV = 0x0000
    CONFIG_GAIN_8_320MV = 0x1800

    CONFIG_BADCRES_12BIT = 0x0180

    CONFIG_SADCRES_12BIT_1S_532US = 0x0018

    CONFIG_MODE_POWERDOWN = 0x0000
    CONFIG_MODE_SANDBVOLT_CONTINUOUS = 0x0007

    def __init__(self, address=INA219_ADDRESS, bus_number=1):
        self.address = address
        self.bus = SMBus(bus_number)

        self.cal_value = 0
        self.current_divider_mA = 0
        self.power_multiplier_mW = 0.0

        self._success = False

    # ---------------------------------------------------------
    # Low-level I2C communication
    # ---------------------------------------------------------

    def _write_register(self, register, value):
        """
        Write a 16-bit value to an INA219 register.

        The INA219 uses big-endian register values.
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
    # Constructor / initialization
    # ---------------------------------------------------------

    def begin(self):
        """
        Initialize communication with the INA219.

        Returns:
            True  - success
            False - failure
        """

        try:
            # Test communication by reading the config register
            self._read_register(self.REG_CONFIG)

            # Equivalent to init()
            self.init()

            self._success = True
            return True

        except Exception as error:
            print(f"INA219 initialization failed: {error}")
            self._success = False
            return False

    def init(self):
        """
        Set the default calibration.

        The original C++ code defaults to 32 V / 2 A.
        """
        self.set_calibration_32V_2A()

    # ---------------------------------------------------------
    # Raw sensor readings
    # ---------------------------------------------------------

    def get_bus_voltage_raw(self):
        """
        Read the raw bus voltage.

        The INA219 bus voltage register stores the voltage
        in bits 15 through 3.

        Each resulting unit represents 4 mV.
        """

        value = self._read_register(
            self.REG_BUSVOLTAGE
        )

        # Shift right by 3 to remove CNVR and OVF bits
        return (value >> 3) * 4

    def get_shunt_voltage_raw(self):
        """
        Read raw shunt voltage.
        """

        value = self._read_register(
            self.REG_SHUNTVOLTAGE
        )

        # Convert unsigned 16-bit to signed 16-bit
        if value & 0x8000:
            value -= 0x10000

        return value

    def get_current_raw(self):
        """
        Read raw current.

        The calibration register is rewritten before reading
        the current register, just like the original C++ code.
        """

        # Restore calibration in case the INA219 reset it
        self._write_register(
            self.REG_CALIBRATION,
            self.cal_value
        )

        value = self._read_register(
            self.REG_CURRENT
        )

        if value & 0x8000:
            value -= 0x10000

        return value

    def get_power_raw(self):
        """
        Read raw power.
        """

        # Restore calibration in case the INA219 reset it
        self._write_register(
            self.REG_CALIBRATION,
            self.cal_value
        )

        value = self._read_register(
            self.REG_POWER
        )

        if value & 0x8000:
            value -= 0x10000

        return value

    # ---------------------------------------------------------
    # Converted measurements
    # ---------------------------------------------------------

    def get_shunt_voltage_mV(self):
        """
        Return shunt voltage in millivolts.

        Each raw bit = 10 microvolts = 0.01 millivolts.
        """

        value = self.get_shunt_voltage_raw()

        return value * 0.01

    def get_bus_voltage_V(self):
        """
        Return bus voltage in volts.

        Raw value is already in units of 4 mV.
        The original C++ code multiplies by 0.001
        after getBusVoltage_raw() has multiplied by 4.
        """

        value = self.get_bus_voltage_raw()

        return value * 0.001

    def get_current_mA(self):
        """
        Return current in milliamps.
        """

        value = self.get_current_raw()

        return value / self.current_divider_mA

    def get_power_mW(self):
        """
        Return power in milliwatts.
        """

        value = self.get_power_raw()

        return value * self.power_multiplier_mW

    # ---------------------------------------------------------
    # Calibration: 32 V / 2 A
    # ---------------------------------------------------------

    def set_calibration_32V_2A(self):
        """
        Configure INA219 for approximately:

            32 V maximum
            2 A expected current

        Assumes a 0.1 ohm shunt resistor.
        """

        # Calibration value
        self.cal_value = 4096

        # 100 uA per bit
        self.current_divider_mA = 10

        # 2 mW per bit
        self.power_multiplier_mW = 2.0

        # Write calibration register
        self._write_register(
            self.REG_CALIBRATION,
            self.cal_value
        )

        # Build configuration register
        config = (
            self.CONFIG_BVOLTAGERANGE_32V
            | self.CONFIG_GAIN_8_320MV
            | self.CONFIG_BADCRES_12BIT
            | self.CONFIG_SADCRES_12BIT_1S_532US
            | self.CONFIG_MODE_SANDBVOLT_CONTINUOUS
        )

        # Write configuration
        self._write_register(
            self.REG_CONFIG,
            config
        )

        self._success = True

    # ---------------------------------------------------------
    # Calibration: 32 V / 1 A
    # ---------------------------------------------------------

    def set_calibration_32V_1A(self):
        """
        Configure INA219 for approximately:

            32 V maximum
            1 A expected current

        Assumes a 0.1 ohm shunt resistor.
        """

        # Calibration value
        self.cal_value = 10240

        # 40 uA per bit
        self.current_divider_mA = 25

        # 0.8 mW per bit
        self.power_multiplier_mW = 0.8

        # Write calibration register
        self._write_register(
            self.REG_CALIBRATION,
            self.cal_value
        )

        config = (
            self.CONFIG_BVOLTAGERANGE_32V
            | self.CONFIG_GAIN_8_320MV
            | self.CONFIG_BADCRES_12BIT
            | self.CONFIG_SADCRES_12BIT_1S_532US
            | self.CONFIG_MODE_SANDBVOLT_CONTINUOUS
        )

        self._write_register(
            self.REG_CONFIG,
            config
        )

        self._success = True

    # ---------------------------------------------------------
    # Calibration: 16 V / 400 mA
    # ---------------------------------------------------------

    def set_calibration_16V_400mA(self):
        """
        Configure INA219 for approximately:

            16 V maximum
            400 mA maximum current

        Assumes a 0.1 ohm shunt resistor.
        """

        # Calibration value
        self.cal_value = 8192

        # 50 uA per bit
        self.current_divider_mA = 20

        # 1 mW per bit
        self.power_multiplier_mW = 1.0

        # Write calibration register
        self._write_register(
            self.REG_CALIBRATION,
            self.cal_value
        )

        config = (
            self.CONFIG_BVOLTAGERANGE_16V
            | self.CONFIG_GAIN_1_40MV
            | self.CONFIG_BADCRES_12BIT
            | self.CONFIG_SADCRES_12BIT_1S_532US
            | self.CONFIG_MODE_SANDBVOLT_CONTINUOUS
        )

        self._write_register(
            self.REG_CONFIG,
            config
        )

        self._success = True

    # ---------------------------------------------------------
    # Power saving
    # ---------------------------------------------------------

    def power_save(self, on):
        """
        Enable or disable power-saving mode.

        The INA219 operating mode is stored in bits 0-2
        of the configuration register.
        """

        config = self._read_register(
            self.REG_CONFIG
        )

        # Clear bits 0-2
        config &= 0xFFF8

        if on:
            # Power-down mode = 0
            config |= self.CONFIG_MODE_POWERDOWN
        else:
            # Continuous shunt + bus voltage mode = 7
            config |= self.CONFIG_MODE_SANDBVOLT_CONTINUOUS

        self._write_register(
            self.REG_CONFIG,
            config
        )

        self._success = True

    # ---------------------------------------------------------
    # Status
    # ---------------------------------------------------------

    def success(self):
        """
        Return the success status of the last operation.
        """
        return self._success

    # ---------------------------------------------------------
    # Cleanup
    # ---------------------------------------------------------

    def close(self):
        """
        Close the I2C bus.
        """
        self.bus.close()
