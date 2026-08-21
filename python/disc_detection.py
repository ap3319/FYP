import cv2
import numpy as np
import math
from libcamera import controls
from picamera2 import Picamera2


disc_diameter = 31
disc_depth = 7

d_cam_offset_x = 49.495
#TODONE:Since changed boundaries. #Check in multiple different place, the lab, different times of day. seems mostly ok but might not be


# #hough parameters
#  		double 	dp,
# 		double 	minDist,
# 		double 	param1 = 100,
# 		double 	param2 = 100,
# 		int 	minRadius = 0,
# 		int 	maxRadius = 0 )

#### HOUGH + THRESHOLDING ###

def colour_thresh(img): #only run detection on red parts of image, ignore yellow discs
    hsv_img = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    lower_red1 = np.array([0, 90, 70])
    upper_red1 = np.array([10, 255, 255])
    lower_red2= np.array([155, 90, 70])
    upper_red2  = np.array([180, 255, 255])

    #red wraps round 0
    mask1 = cv2.inRange(hsv_img, lower_red1, upper_red1)
    mask2 = cv2.inRange(hsv_img,lower_red2,upper_red2)

    mask = mask1+mask2 #grey where red is
    # result = cv2.bitwise_and(img,img, mask)

    return  mask



def calc_img_radius(cam_to_disc, focal_length):
    # dist_to_disc = down_cam_height - disc_depth
    radius = disc_diameter/2
    img_radius = radius * focal_length/ cam_to_disc #pinhole cam eq x=f * (x/z)
    
    return img_radius


def detect_circles(mask,img_radius):

    # blur = cv2.medianBlur(mask, 5)
    blur = cv2.GaussianBlur(mask,(11,11),2)

    min_rad = int(img_radius * 0.85) #tolerance when constraining rad
    max_rad = int(img_radius *1.05) #0.08 originally

    min_dist = img_radius * 1.3 #convert 1.3 radii to pixels, <2 to avoid merging

    circles = cv2.HoughCircles(
    blur,
    cv2.HOUGH_GRADIENT,
    dp=1.5,
    minDist=min_dist,      
    param1=100,  #103,       
    param2=34,       
    minRadius=min_rad,       
    maxRadius=max_rad
    )

    
    centres = []
    radii = []

    if circles is not None:
        circles = circles.reshape(-1,3) #extra opencv axis again
        for x, y, r, in circles:
            centres.append((x,y))
            radii.append(r)
    
    return centres,radii


#### TRANSFORMATIONS ###


def img_to_world(u, v, z_to_disc,cam_mat): #u,v are img coords
    fx = cam_mat[0,0]
    fy=cam_mat[1,1]
    cx = cam_mat[0,2] #cx and cy are principal point
    cy =cam_mat[1,2]

    x = (u- cx) * z_to_disc/fx
    y = (v-cy) * z_to_disc/fy

    return x,y


def cam_to_ee(img_x, img_y):
    #downcam to ee offset

    robot_y = -img_x
    robot_x = -img_y - d_cam_offset_x
    return robot_x,robot_y


#### DETECTION ###

def main_disc_detect(img, cam_mat, downcam_height, target):
    fx = cam_mat[0,0]
    fy=cam_mat[1,1]
    cx = cam_mat[0,2] #cx and cy are principal points
    cy =cam_mat[1,2]

    mask = colour_thresh(img)
    cam_to_disc  = downcam_height - disc_depth
    img_radius = calc_img_radius(cam_to_disc, fx)
    centres, radii = detect_circles(mask,img_radius)

    if len(centres)>0:

        current_disc = (cx,cy) #default is img centre
        if target is not None:
            current_disc = target
        
        distances = []
        for x,y in centres:
            delta_x = x - current_disc[0]
            delta_y = y - current_disc[1]
            distances.append(math.hypot(delta_x,delta_y))

        current_idx = distances.index(min(distances))
        target_centre = centres[current_idx]

        img_x, img_y = img_to_world(target_centre[0], target_centre[1], cam_to_disc, cam_mat)
        dx, dy = cam_to_ee(img_x, img_y)
        return dx, dy, target_centre, centres, radii

    else:
        return None, None, None, [], []
        


    



def overlay(centres, radii, img):

    #discs
    for (x,y), r in zip(centres,radii):
        #cv2 drawing needs integer points
        #circle outline
        cv2.circle(img, center=(int(x),int(y)), radius=int(r), color=(255, 255, 255), thickness=2)
        cv2.circle(img, center=(int(x),int(y)), radius=2, color=(0, 255, 0), thickness=-1)

    return img


if __name__== "__main__":
    import board_detection
    import cameras
    
 ###### DOWN CAM #####
    down_cam = Picamera2(0)
    config = down_cam.create_preview_configuration({"size": (1152,648)},raw={"size": (2304,1296)})
    down_cam.configure(config)
    down_cam.start()
    down_cam.set_controls({"AfMode": controls.AfModeEnum.Manual, "LensPosition": 3.4398})#set raw otherwise get centre crop
    
    down_cam_mat, down_dist_coeffs = cameras.load_d_calib()
    
    # # map so can undistort images without recalculating
    # down_map_x, down_map_y =cv2.initUndistortRectifyMap(
    #     down_cam_mat, down_dist_coeffs, None, down_cam_mat,
    #     (1152,648), cv2.CV_32FC1
    #     )
    # down_dist_coeffs = np.zeros(5)

 ##### FRONT CAM #####
    front_cam = Picamera2(1)
    config = front_cam.create_preview_configuration({"size": (1152,648)},raw={"size": (2304,1296)})
    front_cam.configure(config)
    front_cam.start()
    front_cam.set_controls({"AfMode": controls.AfModeEnum.Manual, "LensPosition": 6.415897846221924})#set raw otherwise get centre crop
    
    front_cam_mat = cameras.load_f_calib()
    # front_dist_coeffs = np.zeros(5)

    prev_target = None
    while True:
        front_img = front_cam.capture_array()
        front_img=cv2.cvtColor(front_img,cv2.COLOR_RGB2BGR)#cv2 needs bgr
        front_img = cameras.undistort_front(front_img)

        down_img = down_cam.capture_array()
        down_img=cv2.cvtColor(down_img,cv2.COLOR_RGB2BGR)#cv2 needs bgr
        down_img = cameras.undistort_down(down_img)

        disp_img = down_img.copy()

        #get height for hough
        corners,ids,rvec,tvec = board_detection.calc_board_pose(front_img, front_cam_mat)
        if rvec is not None: #if pose
            pivot_height, _, down_cam_height = board_detection.frontcam_heights(rvec,tvec) 

            dx, dy, current_centre, centres, radii = main_disc_detect(down_img, down_cam_mat, down_cam_height, prev_target)
            if current_centre is not None:
                prev_target = current_centre
            
            overlay(centres, radii, disp_img)


            font_size = 0.5
            font_weight = 2
            
            #heights
            if dx is not None:
                text = "disc dif_x: "+ str(round(dx,1)) +" dif y: "+ str(round(dy,1)) +  " pivot_height: "+ str(round(pivot_height,1)) +  " down camera height [from aruco]: " +str(round(down_cam_height,1))
                cv2.putText(disp_img, text, (40, 40), cv2.FONT_HERSHEY_SIMPLEX, font_size, (0, 255, 0), font_weight)
        else:
                
            cv2.putText(disp_img, "no aruco",(20, 20),cv2.FONT_HERSHEY_SIMPLEX, font_size, (0, 255, 0), font_weight)
                

        cv2.imshow("disc detection", disp_img)
        if cv2.waitKey(25) & 0xFF == ord('q'):
            break
    
    cv2.destroyAllWindows()
    down_cam.stop()
    front_cam.stop()


   