import math
import cv2
from libcamera import controls
from picamera2 import Picamera2
import numpy as np
import time
import cameras

import board_detection
import disc_detection


from easyEEZYbotARM.kinematic_model import EEZYbotARM_Mk2
from easyEEZYbotARM.serial_communication import arduinoController


disc_depth = 7
ee_length =  122#126

tolerance_x = 4
tolerance_y = 4
tolerance_z = 5#8
hover_xy_tol = 10#3
hover_height = 10

min_step = 3#2
gripper_vertical = 0

extra_down = 8 #dist to move further when gripping

gain = 0.5 #0.3

def get_height(front_cam, front_cam_mat):
    front_img = front_cam.capture_array()
    front_img = cv2.cvtColor(front_img,cv2.COLOR_RGB2BGR)
    front_img = cameras.undistort_front(front_img)

    # clean_img =img.copy()  
    # dist_coeffs = np.zeros(5) #after remap so 0 
    corners,ids,rvec,tvec = board_detection.calc_board_pose(front_img, front_cam_mat)

    pivot_height = None
    downcam_height = None
    if rvec is not None: #if pose
        pivot_height, _, downcam_height = board_detection.frontcam_heights(rvec,tvec) 

    return front_img, pivot_height, downcam_height#return img for overlay
       
# def get_target(centres, radii):
#     down_img = down_cam.capture_array()
#     down_img = cv2.cvtColor(down_img,cv2.COLOR_RGB2BGR)
#     down_img = cameras.undistort_down(down_img)

#hobby servos dont have incremental movements
#must convert to absolute coords
def error_to_world(q1,dx,dy):
    q1= math.radians(q1)
    x = dx*math.cos(q1) - dy*math.sin(q1)
    y = dx*math.sin(q1) + dy*math.cos(q1)

    return x,y

def adjust_servo_time(dz,arduino):
    if dz > 30:
        max_step_down = 25
        servo_time = 400#above 30mm faster
    else:               
        max_step_down = 10 
        servo_time = 800#below 30mm slower

    arduino.servoTime1 = servo_time
    arduino.servoTime2 = servo_time
    arduino.servoTime3 = servo_time

    return max_step_down

def limit_step(step,max_pos,max_neg):

    if step > max_pos:
        step = max_pos
    elif step < max_neg:
        step = max_neg

    return step

def scale_step(move, world,tolerance):#move_x,move_y,move_z,world_x,world_y,dz):

    if (0 < abs(move) < min_step):
        if abs(world)>tolerance:
            move = math.copysign(min_step, move) #min_step*sign of move
        else:
            move = 0
    
    return move
    # if (0 < abs(move_y) < min_step) and abs(world_y)>tolerance_y:
    #     move_y = math.copysign(min_step, move_y)
    # else:
    #     move_y = 0

    # if (0 < abs(move_z) < move_z) and dz >tolerance_z:
    #     step_z = math.copysign(min_step, move_z)
    # else:
    #     step_z = 0

def print_log(loop, ee_height, step_x, step_y):
    print("loop number: ", loop)
    print("ee pivot height: ",ee_height )
    print("ee dx: ",step_x )
    print("ee dy: ",step_y)

def display(d_disp_img, f_disp_img):
    cv2.imshow("pbvs down",d_disp_img)
    cv2.imshow("pbvs forward", f_disp_img)
    cv2.waitKey(1)#needed to actually how img



def go_to_disc(arm, arduino, down_cam, front_cam, front_cam_mat, down_cam_mat, show_image=False):

    prev_target = None 

    for loop in range(40): #limit on iterations

 ####### measuring ######

        #take down img
        d_img = down_cam.capture_array()
        d_img = cv2.cvtColor(d_img,cv2.COLOR_RGB2BGR)
        d_img = cameras.undistort_down(d_img)
        
        #takes front img and gets height of ee pivot + downcam
        f_img, ee_height, downcam_height = get_height(front_cam, front_cam_mat)

        # if show_image:
        d_disp_img = d_img.copy()
        f_disp_img = f_img.copy()

        if ee_height is None:
            print("no markers")
            continue #skip if no markers

        dx, dy, target_centre, centres, radii = disc_detection.main_disc_detect(d_img, down_cam_mat, downcam_height, prev_target)
        if target_centre is not None:
            prev_target = target_centre #track last disc so dont swap


        #for Flask UI
        disc_detection.overlay(centres,radii,d_disp_img)
        cameras.write_ui_img("pick", d_disp_img)


        if show_image:
            disc_detection.overlay(centres,radii,d_disp_img)
            display(d_disp_img, f_disp_img)

        

        if dx is None: 
            print("no discs")
            continue #skip if no discs

        ee_target_height = disc_depth + ee_length
        dz = ee_height - ee_target_height

        #have we converged?
        if abs(dx) < tolerance_x and abs(dy) < tolerance_y and abs(dz) < tolerance_z:
            print("converged :D")
            return True #exit if converged

 ######### moving  ########

        q1 = arm.q1 #last commanded base angle
        world_x, world_y = error_to_world(q1,dx,dy)

        max_step_down = adjust_servo_time(dz,arduino)#limit "speed" based on height
        
        step_x = gain * world_x
        step_y = gain * world_y
        step_z = -gain * dz #moving downwards, could just subtract later...

        step_x = limit_step(step_x,30,-30)
        step_y = limit_step(step_y,30,-30)
        step_z = limit_step(step_z,30,-max_step_down)

        # print_log(loop, ee_height, step_x, step_y)

        #FIXED: by solving timing issue
        # #hover above disc, having issues gripping accurately
        # if abs(dz) < hover_height and (abs(dx) > hover_xy_tol or abs(dy) > hover_xy_tol):
        #     move_z = 0 #dont move until x and y under tolerance

        #servos have min movement 
        step_x = scale_step(step_x, world_x,tolerance_x)
        step_y = scale_step(step_y, world_y,tolerance_y)
        step_z = scale_step(step_z, dz,tolerance_z)

        #get estimated current pos from servos
        current_x, current_y, current_z = arm.forwardKinematics()

        move_x = current_x + step_x
        move_y = current_y + step_y
        move_z = current_z + step_z

        
        arm.moveEEZYbotARM(move_x, move_y, move_z,
            "OFF", gripper_vertical, arduino, delay_between_commands=0.15)#delay so def stop moving before next img

        #use what servos received instead of what we think we moved
        # current_x += move_x
        # current_y += move_y
        # current_z += move_z

        time.sleep(0.1)#timing margin #TODO: needed? esp given delay between moves?


    print("did not converge D:")
    return False



if __name__== "__main__":

      
 ###### DOWN CAM #####
    down_cam = Picamera2(0)
    config = down_cam.create_preview_configuration({"size": (1152,648)},raw={"size": (2304,1296)})
    down_cam.configure(config)
    down_cam.start()
    down_cam.set_controls({"AfMode": controls.AfModeEnum.Manual, "LensPosition": 3.4398})#set raw otherwise get centre crop
    
    down_cam_mat, down_dist_coeffs = cameras.load_d_calib()
    
    # map so can undistort images without recalculating
    # down_map_x, down_map_y =cv2.initUndistortRectifyMap(
    #     down_cam_mat, down_dist_coeffs, None, down_cam_mat,
    #     (1152,648), cv2.CV_32FC1
    #     )
    down_dist_coeffs = np.zeros(5)

 ##### FRONT CAM #####
    front_cam = Picamera2(1)
    config = front_cam.create_preview_configuration({"size": (1152,648)},raw={"size": (2304,1296)})
    front_cam.configure(config)
    front_cam.start()
    front_cam.set_controls({"AfMode": controls.AfModeEnum.Manual, "LensPosition": 6.415897846221924})#set raw otherwise get centre crop
    
    front_cam_mat= cameras.load_f_calib()
    front_dist_coeffs = np.zeros(5)

    # front_cam_vals = (front_cam_mat, front_dist_coeffs)
    cameras.lock_exposure(down_cam) 

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

    converged = go_to_disc(arm, arduino, down_cam, front_cam, front_cam_mat, down_cam_mat, True)
    if converged:
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

        #wait then drop disc at home for test
        time.sleep(0.3)
        arm.moveEEZYbotARM(init_x, init_y, init_z, "OFF", gripper_vertical, arduino)
    


    down_cam.stop()
    front_cam.stop()
    arduino.closeSerialPort()






