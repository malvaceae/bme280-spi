import time

from bme280 import BME280

if __name__ == "__main__":
    # BME280
    bme280 = BME280()
    bme280.open(0, 0)

    try:
        # 各種設定
        bme280.setup(
            0b010, # 気温 オーバーサンプリング x 2
            0b101, # 気圧 オーバーサンプリング x 16
            0b001, # 湿度 オーバーサンプリング x 1
            0b11,  # ノーマルモード
            0b000, # 測定待機時間 0.5ms
            0b100, # IIRフィルタ係数 16
            0b0,   # 4線式SPI
        )

        while True:
            # 気温・気圧・湿度
            temperature, pressure, humidity = bme280.measure()

            print(f"気温: {temperature:7.2f} ℃")
            print(f"気圧: {pressure:7.2f} hPa")
            print(f"湿度: {humidity:7.2f} ％")
            print()

            time.sleep(1)
    finally:
        bme280.close()
