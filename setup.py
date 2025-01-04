from setuptools import setup

setup(
    name="bme280-spi",
    version="0.1.0",
    install_requires=[
        "spidev==3.6",
    ],
    py_modules=[
        "bme280",
    ],
)
