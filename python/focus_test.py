from picamera2 import Picamera2
from libcamera import controls
import cv2

cam = Picamera2()
cam.start()


cam.set_controls({"AfMode": controls.AfModeEnum.Continuous})

while True:

    img=cam.capture_array()
    img=cv2.cvtColor(img,cv2.COLOR_RGB2BGR)
    cv2.imshow("camera", img)

    key=cv2.waitKey(25) & 0xFF 

    data = cam.capture_metadata()
    print(data.get("LensPosition"))

    if key == ord("q"): #key to quit
        break

cv2.destroyAllWindows()



# 3.4398  = 200mm   using this for caliubration



#6.415897846221924 is roughly 300mm fromn wide camera
#https://wiki.amperka.ru/_media/articles:raspberry-pi-camera-guide:python-lib-picamera2-manual.pdf
#5.2.3. Setting the Lens Position Manually