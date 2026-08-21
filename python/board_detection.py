import numpy as np

import cv2 #using >>> print(cv2.__version__) 5.0.0 opencv-contrib-python
from libcamera import controls
from picamera2 import Picamera2

# funnel_ids = [46, 6, 36, 42, 32, 12, 2] 
little_marker_size = 18
big_marker_size = 34
# leg_border = 45

#offsets from PIVOT to forward camera
f_cam_offset_x = 9.4825   
f_cam_offset_z = 17.5 + 14.1075 #32.3 

#offsets from PIVOT to vertical camera
d_cam_offset_z = 29.04497# 
d_cam_offset_x = 49.495#51.818  


board_height = 249.268  # origin down to the desk surface the board's feet stand on (the mdf
                        # playarea board is separate, see PLAYAREA_Y)

#robot playarea (mdf board robot is mounted on)

##### ARUCO COORDS ######
#written by hand as was having many issues with measuring where they were
#these are the masurements from CAD whic is why there are so many dp
# 46 is the top leftmost marker and its top left point is the origin of the whole "board space"
# funnel_aruco = {
#                 46:( 0, 0,0,little_marker_size),
#                 6:(34.833, 0,0, little_marker_size),
#                 36: (69.667, 0,0,little_marker_size),
#                 42: (104.5, 0,0, little_marker_size),
#                 32: (139.333, 0,0, little_marker_size),
#                 12: (174.167, 0, 0, little_marker_size),
#                 2:  (209,0,0 , little_marker_size),
# }
funnel_aruco = np.array([[ 0, 0,0,little_marker_size],
                [34.833, 0,0, little_marker_size],
                [69.667, 0,0,little_marker_size],
                [104.5, 0,0, little_marker_size],
                [139.333, 0,0, little_marker_size],
                [174.167, 0, 0, little_marker_size],
                [209,0,0 , little_marker_size]])

funnel_aruco_ids = [46,6,36,42,32,12,2]


l_leg_aruco =  np.array([[-50, 69.018, 0, big_marker_size],
                [-50, 117.018, 0, big_marker_size],
                [-50, 165.018, 0, big_marker_size]])

l_leg_ids = [28,23,24]

r_leg_aruco =  np.array([
                [243.5, 69.018, 0, big_marker_size],
                [243.5, 117.018, 0, big_marker_size],
                [243.5, 165.018, 0, big_marker_size]
])

r_leg_ids = [18,22,27]

all_aruco_coords = np.vstack([funnel_aruco, l_leg_aruco,r_leg_aruco])
all_ids = np.concatenate([funnel_aruco_ids, l_leg_ids, r_leg_ids])



#aruco markers defined by each corner 
def calc_aruco_array (x,y,z,size): #board flat so z always same
    coords = np.array([
        [x, y, z,],
        [x + size, y, z],
        [x+size, y+size, z],
        [x, y+size, z]

    ], dtype=np.float32) #solvepnp needs floats
    return coords

#TODO: is there a compute before compile thing like used in ES?
#proably makes v little difference
aruco_corner_coords = []
for x,y,z,size in all_aruco_coords: 
    aruco_corner_coords.append(calc_aruco_array(x,y,z,size))


board =cv2.aruco.Board(
    aruco_corner_coords,
    cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50),
    all_ids
)

#### CONNECT 4 GRID #######

# centre of windows in connect 4 grid, 
col_x = [8, 42.833, 77.667, 112.5, 147.333, 182.167, 217]
row_y = [36.25, 67.25, 98.25, 129.25, 160.25, 191.25]
z_offset = 5.25   #mid funnel depth

#(6,7,3) idx 0 = bottom of board
grid_coords = np.array([[[x, y, z_offset] for x in col_x] for y in reversed(row_y)])
grid_coords = grid_coords.reshape(-1,3) #(6,7,3) to flat

funnel_y = -18.5#16 #height above origin of funnel opening
board_depth =11.0 

#Column drop coords
col_drop = np.array([[x, funnel_y , board_depth/2] for x in col_x ])



### POSE DETECTION ###

def calc_board_pose(img, cam_mat):
    #IPPE SQUARE removed as not useful at close distances
    # couldnt reproduce error with the current marker setup
    aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    parameters = cv2.aruco.DetectorParameters()
    detector = cv2.aruco.ArucoDetector(aruco_dict, parameters)
    
    dist_coeffs = np.zeros(5) #TODO remap first so no distortion atm, chage this everywhere
    grey = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    corners,ids,_ = detector.detectMarkers(grey)
    
    if ids is not None:
        obj_p, img_p = board.matchImagePoints(corners, ids)
    #     obj_p = []
    #     img_p = []
    #     for aruco_id, coords in zip(ids.flatten(), corners):
    #         if aruco_id in id_to_coords:
    #             obj_p.append(id_to_coords[aruco_id])#real coords in mm
    #             img_p.append(coords.reshape(4,2)) #img coords

        
        yay, rvec, tvec = cv2.solvePnP(obj_p, img_p, cam_mat,dist_coeffs,flags=cv2.SOLVEPNP_SQPNP)

        return corners, ids,rvec,tvec
    else:
        return None,None,None,None

### TRANSFORMATIONS ###

def frontcam_to_pivot(front_cam_x,front_cam_y,front_cam_z):
    # the camera's z is forward and x is right and y is down. 
    # the robot's x is forward
    # z is up 
    # y is left or right.
    ee_dx = front_cam_z - f_cam_offset_x
    ee_dy = -front_cam_x
    ee_dz = -front_cam_y + f_cam_offset_z
    return ee_dx, ee_dy, ee_dz

# def frontcam_heights(rvec,tvec):#height above mdf board/playarea
#     R,_ = cv2.Rodrigues(rvec)#vector to matrix
#     playarea_surface = np.array([0,PLAYAREA_Y,0])#playarea directly under origin
#     rotation = np.dot(R,playarea_surface)
#     front_cam_x, front_cam_y, front_cam_z = rotation + tvec.flatten()

#     pivot_height = front_cam_y - FORWARD_CAM_OFFSET_Z
#     down_cam_height = pivot_height -DOWN_CAMERA_OFFSET_Z
#     return pivot_height, front_cam_y, down_cam_height

def target_to_cam(rvec,tvec,target):
    rot_mat, _ = cv2.Rodrigues(rvec)#cv2 gives a vector, need a matrix
    target= np.dot(rot_mat, target)#rotation
    cam_x,cam_y,cam_z = target + tvec.flatten() #translation

    return cam_x, cam_y, cam_z


def frontcam_heights(rvec,tvec):
    mdf_height = 6
    playarea_y = board_height - mdf_height
    playarea_surface = np.array([0,playarea_y,0])#playarea directly under origin

    f_cam_x,f_cam_y,f_cam_z = target_to_cam(rvec,tvec,playarea_surface)
    pivot_height = f_cam_y - f_cam_offset_z
    d_cam_height = pivot_height - d_cam_offset_z
    return pivot_height, f_cam_y, d_cam_height


    #robot x axis = cam z
    #robot y = cam u
    #robot z = cam v
def frontcam_col_dists(col_idx,rvec,tvec, extra_height):
    
    world_x,world_y,world_z = col_drop[col_idx] #board detection has col coords
    drop_coords = np.array([world_x, world_y - extra_height, world_z])#drop point with extra height, above board is -y
    
    cam_x,cam_y,cam_z = target_to_cam(rvec,tvec,drop_coords)

    ee_dx, ee_dy, ee_dz = frontcam_to_pivot(cam_x,cam_y,cam_z)
    ee_dx = ee_dx - 122 #girpper horizontal so length further forward than pivot thinks
    return ee_dx, ee_dy, ee_dz
    

### DRAWING ####

def overlay(img, corners, ids, rvec, tvec, cam_mat, dist_coeffs):
    # grid = grid_coords.reshape(-1,3) #(6,7,3) to flat

    cell_centres, _ = cv2.projectPoints(grid_coords, rvec, tvec, cam_mat, dist_coeffs) 
    cell_centres = cell_centres.astype(np.float32)#drawCHessboard needs float 32
    cv2.drawChessboardCorners(img,(7,6),cell_centres, True )# (7,6) shape of c4board

    funnel_centres, _ = cv2.projectPoints(col_drop,rvec,tvec,cam_mat,dist_coeffs)
    funnel_centres= funnel_centres.astype(np.float32)
    cv2.drawChessboardCorners(img,(7,1),funnel_centres, False )#False draws without the lines

    col_label = funnel_centres.reshape(-1,2)#(7,1,2) to (7,2)
    for col_indx, (x,y) in enumerate(col_label):
        label = "col"+str(col_indx)
        pos = int(x)+8, int(y)-8
        cv2.putText(img,label,pos, cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        

    cv2.aruco.drawDetectedMarkers(img, corners, ids)
    cv2.drawFrameAxes(img,cam_mat,dist_coeffs, rvec, tvec, 40)


def draw_heights(img,pivot_height, front_cam_y, down_cam_height):
    pos_x = 40
    pos_y = 40 
    font_size = 0.6
    font_weight = 2
    cv2.putText(img,"pivot height: "+str(round(pivot_height,1)),(pos_x,pos_y),cv2.FONT_HERSHEY_SIMPLEX,font_size, (255, 0, 0), font_weight)
    cv2.putText(img, "front_cam height: "+str(round(front_cam_y,1)),(pos_x+200, pos_y),cv2.FONT_HERSHEY_SIMPLEX, font_size, (255, 0, 0), font_weight)
    cv2.putText(img, "down_cam height: "+str(round(down_cam_height,1)),(pos_x+600, pos_y),cv2.FONT_HERSHEY_SIMPLEX, font_size, (255, 0, 0), font_weight)
    



if __name__== "__main__":
    import cameras

    front_cam = Picamera2(1)
    config = front_cam.create_preview_configuration({"size": (1152,648)},raw={"size": (2304,1296)})
    front_cam.configure(config)
    front_cam.start()
    front_cam.set_controls({"AfMode": controls.AfModeEnum.Manual, "LensPosition": 6.415897846221924})#set raw otherwise get centre crop
    
    front_cam_mat= cameras.load_f_calib()
    dist_coeffs = np.zeros(5)

    while True:
        img = front_cam.capture_array()
        img=cv2.cvtColor(img,cv2.COLOR_RGB2BGR)#cv2 needs bgr
        img = cameras.undistort_front(img)

        clean_img =img.copy()  
        corners,ids,rvec,tvec = calc_board_pose(clean_img, front_cam_mat)

        if rvec is not None: #if pose
            pivot_height, front_cam_y, down_cam_height = frontcam_heights(rvec,tvec) 
            overlay(img,corners,ids,rvec,tvec,front_cam_mat,dist_coeffs)
            draw_heights(img, pivot_height, front_cam_y, down_cam_height)

        cv2.imshow("pose detection", img)
        if cv2.waitKey(25) & 0xFF == ord('q'):
            break
    
    cv2.destroyAllWindows()
    front_cam.stop()
    
