#-*- coding:utf-8 -*-

import sys

# Pirate AudioのSPI液晶
from colorsys import hsv_to_rgb
from PIL import Image, ImageDraw, ImageFont
from ST7789 import ST7789

# SPI LCD
SPI_SPEED_MHZ = 80

st7789 = ST7789(
    rotation=90,  # Needed to display the right way up on Pirate Audio
    port=0,       # SPI port
    cs=1,         # SPI port Chip-select channel
    dc=9,         # BCM pin used for data/command
    backlight=13,
    spi_speed_hz=SPI_SPEED_MHZ * 1000 * 1000
)


# 画像表示
try:
    image_file_name = sys.argv[1]
    disp_image = Image.open(image_file_name)
    st7789.display(disp_image)
except:
    pass
