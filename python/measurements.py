#Measurements calibration paths, etc. In one place because I was getting very confused across files.
import pathlib


###################### ARUCO MARKERS + GRID ########################

############# CAMERA #################### 


# calibration paths:
#  from this file's location so they work whatever the working directory is
PYTHON_FOLDER = pathlib.Path(__file__).parent.resolve()

CALIB_FOLDER = PYTHON_FOLDER  / "calibration"# forward camera
DOWN_CALIB = CALIB_FOLDER / "down" / "down_opencv.json"# down camera
FORWARD_CALIB = CALIB_FOLDER/"forward"/ "model.json"
