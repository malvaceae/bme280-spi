import spidev

class BME280(spidev.SpiDev):
    def __init__(self):
        super().__init__()
        self.__dig_t = []
        self.__dig_p = []
        self.__dig_h = []

    def read_bytes(self, addr, nums):
        return self.xfer2([
            addr | 0b10000000,
            *[0] * nums,
        ])[1:]

    def write_byte(self, addr, byte):
        self.xfer2([
            addr & 0b01111111,
            byte,
        ])

    def setup(self, osrs_t, osrs_p, osrs_h, mode, t_sb, filter, spi3w_en):
        # SPIモード CPOL=1, CPHA=1
        self.mode = 0b11

        # SPIクロックスピード 1MHz
        self.max_speed_hz = 1000000

        # 各種設定
        self.write_byte(0xF2, (osrs_h))
        self.write_byte(0xF4, (osrs_t << 5) | (osrs_p << 2) | mode)
        self.write_byte(0xF5, (t_sb   << 5) | (filter << 2) | spi3w_en)

        # キャリブレーション用のパラメータ
        self.__get_calib_params()

    def measure(self):
        # 気温・気圧・湿度
        raw_bytes = self.read_bytes(0xF7, 8)
        adc_t = int.from_bytes(raw_bytes[3:6]) >> 4
        adc_p = int.from_bytes(raw_bytes[0:3]) >> 4
        adc_h = int.from_bytes(raw_bytes[6:8])

        # 気温キャリブレーション
        t_fine, temperature = self.__compensate_temperature(adc_t)

        # 気圧キャリブレーション
        pressure = self.__compensate_pressure(adc_p, t_fine)

        # 湿度キャリブレーション
        humidity = self.__compensate_humidity(adc_h, t_fine)

        return temperature, pressure, humidity

    def __get_calib_params(self):
        raw_bytes = [
            *self.read_bytes(0x88, 24),
            *self.read_bytes(0xA1, 1),
            *self.read_bytes(0xE1, 7),
        ]

        self.__dig_t = [
            int.from_bytes(raw_bytes[0:2], byteorder="little", signed=False),
            int.from_bytes(raw_bytes[2:4], byteorder="little", signed=True),
            int.from_bytes(raw_bytes[4:6], byteorder="little", signed=True),
        ]

        self.__dig_p = [
            int.from_bytes(raw_bytes[6:8], byteorder="little", signed=False),
            int.from_bytes(raw_bytes[8:10], byteorder="little", signed=True),
            int.from_bytes(raw_bytes[10:12], byteorder="little", signed=True),
            int.from_bytes(raw_bytes[12:14], byteorder="little", signed=True),
            int.from_bytes(raw_bytes[14:16], byteorder="little", signed=True),
            int.from_bytes(raw_bytes[16:18], byteorder="little", signed=True),
            int.from_bytes(raw_bytes[18:20], byteorder="little", signed=True),
            int.from_bytes(raw_bytes[20:22], byteorder="little", signed=True),
            int.from_bytes(raw_bytes[22:24], byteorder="little", signed=True),
        ]

        self.__dig_h = [
            int.from_bytes(raw_bytes[24:25], byteorder="little", signed=False),
            int.from_bytes(raw_bytes[25:27], byteorder="little", signed=True),
            int.from_bytes(raw_bytes[27:28], byteorder="little", signed=False),
            raw_bytes[28] << 4 | (0b00001111 & (raw_bytes[29] >> 0)),
            raw_bytes[30] << 4 | (0b00001111 & (raw_bytes[29] >> 4)),
            int.from_bytes(raw_bytes[31:32], byteorder="little", signed=True),
        ]

    def __compensate_temperature(self, adc_t):
        var1 = (adc_t / 16384.0 - self.__dig_t[0] / 1024.0) * self.__dig_t[1]
        var2 = ((adc_t / 131072.0 - self.__dig_t[0] / 8192.0) *
            (adc_t / 131072.0 - self.__dig_t[0] / 8192.0)) * self.__dig_t[2]
        t_fine = int(var1 + var2)
        t = (var1 + var2) / 5120.0
        return t_fine, t

    def __compensate_pressure(self, adc_p, t_fine):
        var1 = (t_fine / 2.0) - 64000.0
        var2 = var1 * var1 * self.__dig_p[5] / 32768.0
        var2 = var2 + var1 * self.__dig_p[4] * 2.0
        var2 = (var2 / 4.0) + (self.__dig_p[3] * 65536.0)
        var1 = (self.__dig_p[2] * var1 * var1 / 524288.0 + self.__dig_p[1] * var1) / 524288.0
        var1 = (1.0 + var1 / 32768.0) * self.__dig_p[0]
        if var1 == 0.0:
            return 0 # avoid exception caused by division by zero
        p = 1048576.0 - adc_p
        p = (p - (var2 / 4096.0)) * 6250.0 / var1
        var1 = self.__dig_p[8] * p * p / 2147483648.0
        var2 = p * self.__dig_p[7] / 32768.0
        p = p + (var1 + var2 + self.__dig_p[6]) / 16.0
        return p / 100.0

    def __compensate_humidity(self, adc_h, t_fine):
        var_h = (t_fine - 76800.0)
        var_h = (adc_h - (self.__dig_h[3] * 64.0 + self.__dig_h[4] / 16384.0 *
            var_h)) * (self.__dig_h[1] / 65536.0 * (1.0 + self.__dig_h[5] /
            67108864.0 * var_h *
            (1.0 + self.__dig_h[2] / 67108864.0 * var_h)))
        var_h = var_h * (1.0 - self.__dig_h[0] * var_h / 524288.0)

        if var_h > 100.0:
            var_h = 100.0
        elif var_h < 0.0:
            var_h = 0.0
        return var_h
