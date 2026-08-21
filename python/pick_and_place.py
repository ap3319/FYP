import time
import numpy as np
import cv2
from libcamera import controls
from picamera2 import Picamera2

from easyEEZYbotARM.kinematic_model import EEZYbotARM_Mk2
from easyEEZYbotARM.serial_communication import arduinoController

import pbvs_down
import pbvs_forward

import cameras



#TODO: literally the other two together, if have time change


def pick_and_place(col_idx, arm, arduino, d_cam, d_cam_mat, f_cam, f_cam_mat, show_image=False):
    extra_down = 8 
    move_angle = 120
    drop_angle = 95
    gripper_vertical = 0

    init_x=206 
    init_y=0.0 
    init_z=227


    pick_converged = pbvs_down.go_to_disc(arm, arduino, d_cam, f_cam, f_cam_mat, d_cam_mat, show_image)
    if pick_converged:
        x,y,z =  arm.forwardKinematics()
        #move down further 
        arm.moveEEZYbotARM(x,y,z - extra_down, "OFF", gripper_vertical, arduino)
        arm.moveEEZYbotARM(x,y,z - extra_down, "ON", gripper_vertical, arduino)
        time.sleep(0.3)#wait for seal TODO: needed? can shorten?

        #up first so dont drag disc
        arm.moveEEZYbotARM(x,y,z+10, "ON", gripper_vertical, arduino)

        #back to 800 for movement, could maybe be faster? but seems reliable
        #move to home is large movement so cant be too small
        arduino.servoTime1 = 800
        arduino.servoTime2 = 800
        arduino.servoTime3 = 800

        arm.moveEEZYbotARM(init_x, init_y, init_z, "ON", gripper_vertical, arduino)


    #move at move angle    
    arm.moveEEZYbotARM(init_x, init_y, init_z, "ON", move_angle, arduino)

    drop_converged =  pbvs_forward.go_to_column(arm, arduino, col_idx, f_cam_mat, f_cam,show_image)

    if drop_converged:
        cur_x, cur_y, cur_z = arm.forwardKinematics()

        #lift first to avoid funnel
        arm.moveEEZYbotARM(cur_x, cur_y, cur_z + 7, "ON", move_angle, arduino)

        #rotate to drop angle so error correct
        arm.moveEEZYbotARM(cur_x, cur_y, cur_z + 7, "ON", drop_angle, arduino)

        #drop
        arm.moveEEZYbotARM(cur_x, cur_y, cur_z + 7, "OFF", drop_angle, arduino)
        time.sleep(0.5)#let disc fall

        #rotate back
        arm.moveEEZYbotARM(cur_x, cur_y, cur_z + 7, "OFF", move_angle, arduino)

        #home with over rotated gripper
        arm.moveEEZYbotARM(init_x, init_y, init_z, "OFF", move_angle, arduino)

        #rotate gripper to vertical
        arm.moveEEZYbotARM(init_x, init_y, init_z, "OFF", gripper_vertical, arduino)

    if show_image:
        cv2.destroyAllWindows()
    return drop_converged and pick_converged


if __name__== "__main__":
    col_idx = 0
    gripper_vertical = 0

      
 ###### DOWN CAM #####
    d_cam = Picamera2(0)
    config = d_cam.create_preview_configuration({"size": (1152,648)},raw={"size": (2304,1296)})
    d_cam.configure(config)
    d_cam.start()
    d_cam.set_controls({"AfMode": controls.AfModeEnum.Manual, "LensPosition": 3.4398})#set raw otherwise get centre crop
    
    d_cam_mat, down_dist_coeffs = cameras.load_d_calib()
    
    down_dist_coeffs = np.zeros(5)

 ##### FRONT CAM #####
    f_cam = Picamera2(1)
    config = f_cam.create_preview_configuration({"size": (1152,648)},raw={"size": (2304,1296)})
    f_cam.configure(config)
    f_cam.start()
    f_cam.set_controls({"AfMode": controls.AfModeEnum.Manual, "LensPosition": 6.415897846221924})#set raw otherwise get centre crop
    
    f_cam_mat= cameras.load_f_calib()
    f_dist_coeffs = np.zeros(5)


    cameras.lock_exposure(d_cam) 

    # init
    arduino = arduinoController(port="/dev/ttyACM0")
    arduino.openSerialPort()
    arm = EEZYbotARM_Mk2(initial_q1=0, initial_q2=90, initial_q3=-90)

    #home
    init_x=206 
    init_y=0.0 
    init_z=227
    arm.moveEEZYbotARM(init_x, init_y, init_z, "OFF", gripper_vertical, arduino)
    time.sleep(0.3)
    
    placed = pick_and_place(col_idx, arm, arduino, d_cam, d_cam_mat, f_cam, f_cam_mat, show_image=True)#already back to home
    
    d_cam.stop()
    f_cam.stop()
    arduino.closeSerialPort()
