from picamera2 import Picamera2
from pprint import pprint
import cv2

picam2 = Picamera2(1)

# pprint(picam2.sensor_modes)

config =picam2.create_preview_configuration(
    main={"size": (2304, 1296)}
)

picam2.configure(config)
picam2.start()

while True:
    frame = picam2.capture_array()

    cv2.imshow("Camera", frame)

    if cv2.waitKey(1)==ord('q'):
        break

cv2.destroyAllWindows()

# [{'bit_depth': 10,
#   'crop_limits': (768, 432, 3072, 1728),
#   'exposure_limits': (9, 77208145, 20000),
#   'format': SRGGB10_CSI2P,
#   'fps': 120.13,
#   'size': (1536, 864),
#   'unpacked': 'SRGGB10'},
#  {'bit_depth': 10,
#   'crop_limits': (0, 0, 4608, 2592),
#   'exposure_limits': (13, 112015096, 20000),
#   'format': SRGGB10_CSI2P,
#   'fps': 56.03,
#   'size': (2304, 1296),
#   'unpacked': 'SRGGB10'},
#  {'bit_depth': 10,
#   'crop_limits': (0, 0, 4608, 2592),
#   'exposure_limits': (26, 220416802, 20000),
#   'format': SRGGB10_CSI2P,
#   'fps': 14.35,
#   'size': (4608, 2592),
#   'unpacked': 'SRGGB10'}]