import math
import time
import cv2
import numpy as np

from libcamera import controls
from picamera2 import Picamera2


import cameras

import board_detection
import disc_detection

from easyEEZYbotARM.kinematic_model import EEZYbotARM_Mk2
from easyEEZYbotARM.serial_communication import arduinoController

extra_height = 5
tolerance = 5
max_loops = 15
gain = 0.6

move_angle = 120
drop_angle = 95
gripper_vertical = 0

col_idx = 0 # column to go to



#robot x axis = cam z
#robot y = cam u
#robot z = cam v
# def world_col_to_cam(col_idx,rvec,tvec, extra_height):
    
#     world_x,world_y,world_z = board_detection.col_drop[col_idx] #board detection has col coords
#     drop_coords = np.array([world_x, world_y - extra_height, world_z])#drop point with extra height, above board is -y
    
#     cam_x,cam_y,cam_z = target_to_cam(rvec,tvec,target)

#     ee_dx, ee_dy, ee_dz = board_detection.frontcam_to_pivot
#     ee_dx = ee_dx - EE_LENGTH 
#     return ee_dx, ee_dy, ee_dz



#same as pbvs down didnt want to import one into other
def error_to_world(q1,dx,dy):
    q1= math.radians(q1)
    x = dx*math.cos(q1) - dy*math.sin(q1)
    y = dx*math.sin(q1) + dy*math.cos(q1)

    return x,y 


def error_to_move(q1,cur_x,cur_y,cur_z, dx,dy,dz, gain):
    
    world_x,world_y = error_to_world(q1, dx, dy)
    world_z = dz #no disc depth this time

    step_x = gain * world_x
    step_y = gain * world_y
    step_z = gain * world_z

    
    if gain != 1:#blind uses gain 1
        step_x = limit_step(step_x,30,-30)
        step_y = limit_step(step_y,30,-30)
        step_z = limit_step(step_z,30, -30)

    mv_x = cur_x + step_x
    mv_y = cur_y + step_y
    mv_z = cur_z + step_z

    return mv_x,mv_y,mv_z

def limit_step(step,max_pos,max_neg):

    if step > max_pos:
        step = max_pos
    elif step < max_neg:
        step = max_neg

    return step

def blind_move(last_delta, arm, arduino):
    dx ,dy, dz = last_delta
    cur_x, cur_y, cur_z = arm.forwardKinematics()
    q1 = arm.q1
    move_x, move_y, move_z = error_to_move(q1,cur_x,cur_y,cur_z, dx,dy,dz, 1)

    arm.moveEEZYbotARM(move_x, move_y, move_z,
    "ON", move_angle, arduino, delay_between_commands=0.15)#delay so def stop moving before next img



def print_log(loop, ids,dx,dy,dz):
    print("iteration: ", loop)
    print("markers: ", len(ids))
    print("error: ", "dx: ", dx, "dy: ",dy, "dz: ",dz )
    

def display( f_disp_img):
    cv2.imshow("pbvs forward", f_disp_img)
    cv2.waitKey(1)#needed to actually show img

def go_to_column(arm, arduino, col_idx, cam_mat, f_cam, show_image=False):
    
    last_delta = None
    for loop in range(15):

        img = f_cam.capture_array()
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        img = cameras.undistort_front(img)
        
        #if show_image:
        f_disp_img = img.copy()
        

        #get board pose
        corners, ids, rvec,tvec = board_detection.calc_board_pose(img, cam_mat)

        
        if rvec is None or ids is None or len(ids)<2:
            
            # last_dx ,last_dy, last_dz = last_delta #TODO: there's gotta be a better way 
            # max_tol = max(abs(last_dz), abs(last_dx), abs(last_dy)) 

            if last_delta is not None and max(map(abs, last_delta)) <= 30:
                blind_move(last_delta, arm, arduino)
            
                print("blind move :/")
                return True #exit if converged
            else:
                time.sleep(0.2) #wait a bit to see if we can see markers again
                continue

        else:

            #get error to column
            dx,dy,dz = board_detection.frontcam_col_dists(col_idx,rvec,tvec, extra_height)
            # print_log(loop, ids,dx,dy,dz)

            #save prev error for blind move
            last_delta= dx,dy,dz 


            #for Flask UI
            board_detection.overlay(f_disp_img,corners,ids,rvec,tvec,cam_mat,np.zeros(5))
            cameras.write_ui_img("place", f_disp_img)

            if show_image:
                board_detection.overlay(f_disp_img,corners,ids,rvec,tvec,cam_mat,np.zeros(5))
                display( f_disp_img)

            #have we converged? only 1 tolerance for all 3 axis here
            if max(abs(dx), abs(dy), abs(dz)) < tolerance:
                print("converged :D")
                return True #exit if converged

            # q1 = arm.q1
            # world_x,world_y = error_to_world(q1, dx, dy)
            # world_z = dz #no disc depth this time

            # step_x = gain * world_x
            # step_y = gain * world_y
            # step_z = gain * world_z

            # step_x = limit_step(step_x,30,-30)
            # step_y = limit_step(step_y,30,-30)
            # step_z = limit_step(step_z,30, -20)

            # current_x, current_y, current_z = arm.forwardKinematics()

            # move_x = current_x + step_x
            # move_y = current_y + step_y
            # move_z = current_z + step_z

            cur_x, cur_y, cur_z = arm.forwardKinematics()
            q1 = arm.q1
            move_x, move_y, move_z = error_to_move(q1,cur_x,cur_y,cur_z, dx,dy,dz, gain)

            arm.moveEEZYbotARM(move_x, move_y, move_z,
                "ON", move_angle, arduino, delay_between_commands=0.15)#delay so def stop moving before next img

        time.sleep(0.1)#timing margin

    print("did not converge D:")
    return False
            


   

if __name__== "__main__":


 ##### FRONT CAM #####
    f_cam = Picamera2(1)
    config = f_cam.create_preview_configuration({"size": (1152,648)},raw={"size": (2304,1296)})
    f_cam.configure(config)
    f_cam.start()
    f_cam.set_controls({"AfMode": controls.AfModeEnum.Manual, "LensPosition": 6.415897846221924})#set raw otherwise get centre crop
    
    f_cam_mat= cameras.load_f_calib()
    f_dist_coeffs = np.zeros(5) 

    # init
    arduino = arduinoController(port="/dev/ttyACM0")
    arduino.openSerialPort()
    arm = EEZYbotARM_Mk2(initial_q1=0, initial_q2=90, initial_q3=-90)

    #home
    init_x=206 
    init_y=0.0 
    init_z=227

    arm.moveEEZYbotARM(init_x, init_y, init_z, "OFF", gripper_vertical, arduino)

    #pump on
    arm.moveEEZYbotARM(init_x, init_y, init_z, "ON", gripper_vertical, arduino)
    time.sleep(0.3) #time to give disc to robot

    #move at move angle    
    arm.moveEEZYbotARM(init_x, init_y, init_z, "ON", move_angle, arduino)

    converged =  go_to_column(arm, arduino, col_idx, f_cam_mat, f_cam)

    if converged:
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



