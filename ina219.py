from smbus2 import SMBus


class INA219:

    INA219_ADDRESS = 0x40

    REG_CONFIG = 0x00
    REG_SHUNT_VOLTAGE = 0x01
    REG_BUS_VOLTAGE = 0x02
    REG_POWER = 0x03
    REG_CURRENT = 0x04
    REG_CALIBRATION = 0x05


    def __init__(
        self,
        address=INA219_ADDRESS,
        bus_number=1
    ):

        self.address = address

        self.bus = SMBus(
            bus_number
        )

        self.cal_value = 0

        self.current_divider_mA = 1

        self.power_multiplier_mW = 1


    def _write_register(
        self,
        register,
        value
    ):

        high_byte = (
            value >> 8
        ) & 0xFF

        low_byte = (
            value
        ) & 0xFF


        self.bus.write_i2c_block_data(

            self.address,

            register,

            [
                high_byte,
                low_byte
            ]

        )


    def _read_register(
        self,
        register
    ):

        data = (

            self.bus.read_i2c_block_data(

                self.address,

                register,

                2

            )

        )


        return (

            (data[0] << 8)

            |

            data[1]

        )


    def begin(self):

        try:

            self._read_register(

                self.REG_CONFIG

            )

            return True


        except Exception as error:

            print(

                "INA219 not found:",

                error

            )

            return False


    def set_calibration_32V_2A(self):

        self.cal_value = 4096

        self.current_divider_mA = 10

        self.power_multiplier_mW = 2.0


        self._write_register(

            self.REG_CALIBRATION,

            self.cal_value

        )


        config = (

            0x2000

            | 0x1800

            | 0x0180

            | 0x0018

            | 0x0007

        )


        self._write_register(

            self.REG_CONFIG,

            config

        )


    def get_current_mA(self):

        raw_value = (

            self._read_register(

                self.REG_CURRENT

            )

        )


        # Convert unsigned 16-bit
        # value to signed 16-bit

        if raw_value & 0x8000:

            raw_value -= 0x10000


        return (

            raw_value

            /

            self.current_divider_mA

        )


    def get_bus_voltage_V(self):

        raw_value = (

            self._read_register(

                self.REG_BUS_VOLTAGE

            )

        )


        raw_value >>= 3


        return (

            raw_value * 0.004

        )


    def close(self):

        self.bus.close()
