import json
import time
import pathlib
import os #lol

import cv2
import numpy as np

import board_detection



############# MARKER WHITE BALANCE CONSTANTS ###################

CONVERGE_TOLERANCE = 0.01  #stop when within 1 percent
#what to adjust green to, max 255 but dont wann clip
WHITE_TARGET = 140


PYTHON_FOLDER = pathlib.Path(__file__).parent.resolve()
CALIB_FOLDER = PYTHON_FOLDER  / "calibration"

front_map_x = np.load(CALIB_FOLDER /"forward"/ "map_x.npy")
front_map_y = np.load(CALIB_FOLDER/"forward"/ "map_y.npy")

down_map_x = np.load(CALIB_FOLDER/"down"/"opencv"/"map_x.npy")
down_map_y = np.load(CALIB_FOLDER/"down"/"opencv"/"map_y.npy")

##### LOADING CALIBRATIONS + INITIALISING CAMERAS #########

def load_d_calib():
    calib = json.loads((CALIB_FOLDER/"down"/"down_opencv.json").read_text())

    camera_matrix = np.array([

    [calib['fx'], 0, calib['cx']],
    [0, calib['fy'], calib['cy']],
    [0, 0, 1]
    ])

    dist_coeffs=np.array(calib['distortion_coeffs'])
    return camera_matrix, dist_coeffs


def load_f_calib():
    #reads the calibration exported by lensboy
    #lensboy not for pi
   
    calib = json.loads((CALIB_FOLDER / "forward"/"model.json").read_text())
    # map_x = np.load(calibration_dir / "map_x.npy")
    # map_y = np.load(calibration_dir / "map_y.npy")

    camera_matrix = np.array([

        [calib['fx'], 0,  calib['cx']],
        [0, calib['fy'],  calib['cy']],
        [0, 0, 1],
    ])

    return camera_matrix


def undistort_front(img): 

    undistorted = cv2.remap(img, front_map_x, front_map_y,interpolation=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    return  undistorted


def undistort_down(img):

    undistorted = cv2.remap(img, down_map_x, down_map_y,interpolation=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    return undistorted

######WRITE IMAGES FROM SEPERATE PBVS' TO UI - here because it needed to be somewhere both imported #############################

def write_ui_img(name, img):
    path = "/dev/shm/" + name +  ".jpg"
    temp = path +".temp.jpg"

    cv2.imwrite(temp, img, [cv2.IMWRITE_JPEG_QUALITY,60])#default 95 made things slow
    os.replace(temp, path)
    

#############EXPOSURE AND WB #################################


def lock_exposure(cam):
    #run auto exposure and AWB and then freeze

    time.sleep(2)
    md = cam.capture_metadata()
    cam.set_controls({
        "AeEnable": False,
        "ExposureTime": md["ExposureTime"],
        "AnalogueGain": md["AnalogueGain"],
        "AwbEnable": False,
        "ColourGains": md["ColourGains"],
    })
    return md


   ################## MARKER LOCK ################# 


def get_square(coords,offset):
    x, y,z, size = coords
    x -= offset
    y -= offset
    size = size +2*offset

    aruco_corner_coords = board_detection.calc_aruco_array(x,y,z,size)
    return aruco_corner_coords


def get_square_coords(coords, offset, rvec,tvec, f_cam_mat):
    f_dist_coeffs = np.zeros(5) # undistorted from maps b4 detection

    big_square = get_square(coords,offset)
    proj_square, _ = cv2.projectPoints(big_square, rvec,tvec, f_cam_mat,f_dist_coeffs)

    proj_square = proj_square.reshape(-1,2) #cv2 extra axis again
    proj_square =  np.round(proj_square).astype(np.int32) #need int coords

    return proj_square

    
def  get_mean_white(f_img, rvec,tvec, f_cam_mat):

    if rvec is None:
       return 0,0,0,0

    inner_square =1 #'radius' of square to sample from
    outer_square =3

    img_h,img_w, = f_img.shape[:2] #(h,w,3)
    shape = (img_h,img_w)

    mask = np.zeros(shape, np.uint8)

    leg_aruco = np.vstack([board_detection.l_leg_aruco, board_detection.r_leg_aruco])    

    for coords in leg_aruco:
        inner = get_square_coords(coords, inner_square, rvec,tvec, f_cam_mat)    
        outer =  get_square_coords(coords, outer_square, rvec,tvec, f_cam_mat) 

        cv2.fillConvexPoly(mask, outer, 255) #fill outer square
        cv2.fillConvexPoly(mask, inner, 0) #unfill inner square to get ring

        total = cv2.countNonZero(mask) # divide by numbner of pixels in mask when avg
        b,g,r,a = cv2.mean(f_img, mask=mask)

    return b,g,r,total


def apply_correction(f_cam, r_gain_change, b_gain_change, exp_change):
    fcam_set = f_cam.capture_metadata()

    #can only set r and b, g is referecnce
    cur_r_gain, cur_b_gain = fcam_set["ColourGains"]
    cur_exp = fcam_set["ExposureTime"]

    new_r_gain = cur_r_gain * r_gain_change
    new_b_gain =cur_b_gain * b_gain_change

    new_exp= int(cur_exp * exp_change) # ExposureTime needs int

    f_cam.set_controls({
        "ColourGains": (new_r_gain, new_b_gain),
        "ExposureTime": new_exp

        })

    return new_r_gain,new_b_gain,new_exp


def set_exposure_markers(f_cam,f_cam_mat):
    #another proportional controller but this one multiplieeees
    skip_frames = 10
    max_loops = 10
    

    lock_exposure(f_cam)

    for loop_no in range(1, max_loops+1):

        for skip in range(skip_frames):
            f_cam.capture_array()

        f_img = f_cam.capture_array()
        f_img = cv2.cvtColor(f_img, cv2.COLOR_RGB2BGR)
        f_img = undistort_front(f_img)

        corners,ids,rvec,tvec, = board_detection.calc_board_pose(f_img,f_cam_mat)

        avg_b,avg_g,avg_r,total = get_mean_white(f_img, rvec,tvec, f_cam_mat)

        if total != 0:

            r_gain_change = avg_g/ avg_r
            b_gain_change = avg_g/ avg_b
            exp_change = WHITE_TARGET/ avg_g
        else:
                return False
        
        print("loop: ",  str(loop_no), "R: ",  str(avg_r), "G: ",  str(avg_g), "B: ",  str(avg_b))
        print("changes r: ", str(r_gain_change), " b: ", str( b_gain_change))

        col_converged = (abs(r_gain_change - 1) < CONVERGE_TOLERANCE and abs(b_gain_change - 1) < CONVERGE_TOLERANCE  ) 
        brigtness_coverged = (abs(exp_change - 1)) < CONVERGE_TOLERANCE

        if col_converged and brigtness_coverged:
            print("converged after loops: ", str(loop_no))
            return True

        apply_correction(f_cam, r_gain_change, b_gain_change, exp_change)
    

    print("didnt converge, loops: ", str(loop_no))
    return False
















    


        







