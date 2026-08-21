import cv2
import numpy as np
from libcamera import controls
from picamera2 import Picamera2
import time

import cameras


import board_detection

EMPTY = 0
RED = 2
YELLOW = 1
min_vote_thresh = 10

def get_vote_pattern(radius, n_votes):

    angles = np.linspace(0, 2*np.pi, n_votes,endpoint=False)
    rel_x = radius*np.cos(angles)
    rel_y= radius*np.sin(angles)
    z =np.zeros_like(rel_x) #cv2 needs the extra axis
    tot_pos = np.column_stack((rel_x,rel_y, z))

    return tot_pos

def get_voting_locs():
    circle_rads = 6, 3
    num_votes = 12, 6

    # tot_angles = [0,0]
    # for rad, n_votes in zip(circle_rads, num_votes):
    #     tot_angles.extend(space_votes(rad, n_votes))

    tot_rel_pos = np.vstack([[0,0,0] , get_vote_pattern(3,6) , get_vote_pattern(6,12)])
    # print(tot_rel_pos)

    voting_coords = []
    window_centres = board_detection.grid_coords
    # grid_coordsis (42,3)
    for (centre) in window_centres:
            voting_coords.append(centre + tot_rel_pos)

    return np.array(voting_coords)

def proj_voting_locs(vote_locs,rvec,tvec, f_cam_mat):
    #cv2 wants flat list
    vote_locs = vote_locs.reshape(-1,1,3)#reshape from 42,19,3 to 798,1,3

    dist_coeffs = np.zeros(5)
    proj_vote_locs, _ = cv2.projectPoints(vote_locs,rvec,tvec, f_cam_mat, dist_coeffs)#798,1,2, lost axis due to proj

    proj_vote_locs = proj_vote_locs.reshape(42,-1,2) #back to 42 windows, 19 samples, x,y coords

    return proj_vote_locs

def read_colours(img, proj_vote_locs):

    # #cv2 wants flat list
    # centre_coords = centre_coords.reshape(-1,1,3)#reshape from 42,19,3 to 798,1,3

    # dist_coeffs = np.zeros(5)
    # vote_locs, _ = cv2.projectPoints(centre_coords,rvec,tvec, f_cam_mat, dist_coeffs)#798,1,2, lost axis due to proj

    # vote_locs = vote_locs.reshape(42,19,2) #back to 42 windows, 19 samples, x,y coords
    
    img_x = proj_vote_locs[:,:,0]
    img_y = proj_vote_locs[:,:,1]

    #img indexing needs integers, round first so dont truncate
    y_rounded = np.round(img_y).astype(int)
    x_rounded = np.round(img_x).astype(int)
    
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    samples = hsv[y_rounded, x_rounded]#indexing needs integers, y before x

    return samples

def vote_pixel(hue, sat, val):
    sat_thresh = 190
    yel_h_low = 12   
    yel_h_high = 32  
    red_h_high = 165
    red_h_low = 5  

    # EMPTY
    # = 0
    # RED = 1
    # YELLOW = 2

    if sat < sat_thresh:
        return EMPTY

    elif yel_h_low <= hue <= yel_h_high:
        return YELLOW

    elif hue >= red_h_high or hue <= red_h_low:
        return RED     

    return EMPTY
 

def vote_window(samples):

    states = []
    
    #samples is (42,19,3 )  3 is HSV
    for window in samples:
        #votes in each window
        r_votes =0 
        y_votes = 0
        # print("window: ", window)

        for (h,s,v) in window:
            vote = vote_pixel(h,s,v)
            

            if vote == RED:
                r_votes +=1
            elif vote == YELLOW:
                y_votes +=1

        if r_votes >= min_vote_thresh:
            states.append(RED)
        elif y_votes >= min_vote_thresh:
            states.append(YELLOW)
        else:
            states.append(EMPTY
        )

    return states


def check_gravity(states):
    floating_list = [] #list discs above gap
    for col in range(7):
        floating = False

        for row in range (6):
            state = states[row*7+col]

            if state == EMPTY :
                floating = True

            if state !=  EMPTY and floating:
                floating_list.append((col,row))

    return floating_list 

def mean_colour(samples):
    #(42,19,3 )
    bgr = cv2.cvtColor(samples, cv2.COLOR_HSV2BGR)
    means = np.mean(bgr, axis=1)

    return means



def draw_vote_patterns(img, proj_vote_locs):
    #proj_vote_locs is 42,19,2
    points = proj_vote_locs.reshape(-1,2 )#now (42*19, 2)
    for x,y in points:
        cv2.circle(img, (int(x),int(y)), 1, (0,255,0), -1)


def draw_states(img,  proj_vote_locs, states):
    #proj_vote_locs is 42,19,2
    #centres is (42,2)
    centres = proj_vote_locs[:,0,:]#0 is centre point in pattern
    black = (0,0,0)

    for i,state in enumerate(states):
        if state == RED:
            letter = "R"
            colour  = (0,0,255)#red
        elif state == YELLOW:
            letter = "Y"
            colour=(0,215,255)#yellow in bgr
        else:
            letter = "E"
            colour = (200,200,200)#grey

        x , y= centres[i]
        round_x = round(x)#putText still needs ints 
        round_y = round(y)


        #+8 so doesnt cover sample pattern
        cv2.putText(img, letter, (round_x+8,round_y+8), cv2.FONT_HERSHEY_SIMPLEX, 0.7, black,4)#black outline
        cv2.putText(img, letter, (round_x+8,round_y+8), cv2.FONT_HERSHEY_SIMPLEX, 0.7, colour,2)



def draw_gravity(img, proj_vote_locs, floating_list):#,idx):
    #centres is (42,2)
    centres = proj_vote_locs[:,0,:]

    # print(centres[idx])
    # print(tuple(centres[idx].astype(int).tolist()))
    # cv2.circle(img, tuple(centres[idx].astype(int).tolist()) ,20,(203,192,255),2 )

    red = (0,0,255)

    for (col,row) in floating_list:

        x,y = centres[row*7 +col] #centres is 42 not 7x6 grid, TODO: anything better than this? 
        cv2.circle(img,(round(x),round(y)),20, red,2 )
    


def draw_means(img, proj_vote_locs, means):
    #show mean of all pattern points per window, just to give an idea
    centres = proj_vote_locs[:, 0,:]
    white = (255,255,255)

    for i,mean in enumerate(means): #we do this twice times maybe merge functions?
        x,y = centres[i]

        upper_l = round(x)-24, round(y)-24
        bottom_r = (upper_l[0] +12, upper_l[1] +12) 

        b = round(mean[0])
        g = round(mean[1])
        r = round(mean[2])
        colour = (b,g,r)

        cv2.rectangle(img, upper_l, bottom_r, colour, cv2.FILLED)#filled rec of mean colour
        cv2.rectangle(img, upper_l, bottom_r, white, 1)


def get_board(f_cam,f_cam_mat,vote_locs):#,idx):
    f_img = f_cam.capture_array()
    f_img=cv2.cvtColor(f_img,cv2.COLOR_RGB2BGR)#cv2 needs bgr
    f_img = cameras.undistort_front(f_img)
    disp_img = f_img.copy()

    
    corners, ids,rvec,tvec = board_detection.calc_board_pose(f_img, f_cam_mat)
    states= None

    if ids is not None:
    
        proj_locs = proj_voting_locs(vote_locs,rvec,tvec, f_cam_mat)

        samples = read_colours(f_img, proj_locs)
        states = vote_window(samples)
        floating_list = check_gravity(states)
        means = mean_colour(samples)

        
        #print(means[idx])
        # time.sleep(1.5)
        # print()
        
        

        draw_vote_patterns(disp_img, proj_locs)
        draw_states(disp_img,  proj_locs, states)
        draw_gravity(disp_img, proj_locs, floating_list)#,idx)
        draw_means(disp_img, proj_locs, means)
    return disp_img, states







if __name__== "__main__":

 ##### FRONT CAM #####
    f_cam = Picamera2(1)
    config = f_cam.create_preview_configuration({"size": (1152,648)},raw={"size": (2304,1296)})
    f_cam.configure(config)
    f_cam.start()
    f_cam.set_controls({"AfMode": controls.AfModeEnum.Manual, "LensPosition": 6.415897846221924})#set raw otherwise get centre crop
    
    f_cam_mat = cameras.load_f_calib()
    # f_dist_coeffs = np.zeros(5)

    cameras.set_exposure_markers(f_cam,f_cam_mat)
    # cameras.lock_exposure(f_cam, wait=5)
    f_cam_set = f_cam.capture_metadata() 
    print("exposure: ", f_cam_set['ExposureTime'])
    print("gain: ", f_cam_set['AnalogueGain'])
    print("colour gains: ", f_cam_set['ColourGains'])

    # print("enter index")
    # idx = int(input()) #flat 42 index

    vote_locs = get_voting_locs()
    while True:
        disp_img, states = get_board(f_cam,f_cam_mat,vote_locs)#,idx)
       
        # f_img = f_cam.capture_array()
        # f_img=cv2.cvtColor(f_img,cv2.COLOR_RGB2BGR)#cv2 needs bgr
        # f_img = cameras.undistort_front(f_img)
        # disp_img = f_img.copy()

        # corners, ids,rvec,tvec = board_detection.calc_board_pose(f_img, f_cam_mat)
        # if ids is not None:
        
        #     proj_locs = proj_voting_locs(vote_locs,rvec,tvec, f_cam_mat)

        #     samples = read_colours(f_img, proj_locs)
        #     states = vote_window(samples)
        #     floating_list = check_gravity(states)
        #     means = mean_colour(samples)

        #     draw_vote_patterns(disp_img, proj_locs)
        #     draw_states(disp_img,  proj_locs, states)
        #     draw_gravity(disp_img, proj_locs, floating_list)
        #     draw_means(disp_img, proj_locs, means)


        cv2.imshow("game state", disp_img)
        if cv2.waitKey(25) & 0xFF == ord('q'):
            break

    cv2.destroyAllWindows()
    f_cam.stop()