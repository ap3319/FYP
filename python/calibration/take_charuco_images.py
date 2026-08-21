import cv2
from picamera2 import Picamera2
from libcamera import controls

cam = Picamera2()

config =cam.create_preview_configuration({"size":(1152,648)}, raw={"size":(2304,1296)})
cam.configure(config)
cam.start()
cam.set_controls({"AfMode": controls.AfModeEnum.Manual,"LensPosition": 6.4158978462219244})

img_idx = 78

while True:
    img = cam.capture_array()
    img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    window = cv2.flip(img,1)#flip preview becasue otherwise it breaks my brain and i want it to be like a mirror
    cv2.imshow("camera", window)

    key=cv2.waitKey(25) & 0xFF 

    if key == ord("s"):
        cv2.imwrite("charuco_images_wide/"+ idx+".jpg", img)
        print("image taken")
        idx  +=1

    elif key ==ord("q"):
        break

cv2.destroyAllWindows()
