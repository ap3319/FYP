import cv2
import time
import random
import json
import os

from libcamera import controls
from picamera2 import Picamera2


import bitbully as bb
from easyEEZYbotARM.kinematic_model import EEZYbotARM_Mk2
from easyEEZYbotARM.serial_communication import arduinoController

import board_detection
import game_state
import pick_and_place

import cameras



EMPTY = 0
RED = 2
YELLOW = 1



def setup_cams():

 ###### DOWN CAM #####
    d_cam = Picamera2(0)
    config = d_cam.create_preview_configuration({"size": (1152,648)},raw={"size": (2304,1296)})
    d_cam.configure(config)
    d_cam.start()
    d_cam.set_controls({"AfMode": controls.AfModeEnum.Manual, "LensPosition": 3.4398})#set raw otherwise get centre crop
    
    d_cam_mat, down_dist_coeffs = cameras.load_d_calib()

 ##### FRONT CAM #####
    f_cam = Picamera2(1)
    config = f_cam.create_preview_configuration({"size": (1152,648)},raw={"size": (2304,1296)})
    f_cam.configure(config)
    f_cam.start()
    f_cam.set_controls({"AfMode": controls.AfModeEnum.Manual, "LensPosition": 6.415897846221924})#set raw otherwise get centre crop
    
    f_cam_mat= cameras.load_f_calib()

    return d_cam,f_cam,d_cam_mat,f_cam_mat

def setup_arm():
    # init
    arduino = arduinoController(port="/dev/ttyACM0")
    arduino.openSerialPort()
    arm = EEZYbotARM_Mk2(initial_q1=0, initial_q2=90, initial_q3=-90)

    init_x=206 
    init_y=0.0 
    init_z=227
    arm.moveEEZYbotARM(init_x, init_y, init_z, "OFF", 0, arduino)
    time.sleep(0.3)

    return arm,arduino




def is_board_trusted(last_states):

    if len(last_states)>10:
        last_states.pop(0)#remove oldest

    if len(last_states)< 10:#dont have 10 yet so cant be trusted
        print("less than 10 frames")
        return False

    trusted = True
    for state in last_states:
        if state != last_states[0]:
            trusted = False
            break
    return trusted 


def is_board_change_ok(last_trusted, cur_states):

    dif = []
    dif_idx = None
    for i in range(len(last_trusted)):
        if last_trusted[i] != cur_states[i]:
            dif.append(i)
            dif_idx = i

    ok = True
    #is there only 1 new disc
    if len(dif) >1:
        ok = False


    #has disc colour changed
    elif last_trusted[dif_idx] != EMPTY:
        ok = False

    dif_colour = None
    dif_col = None
    if ok:
        dif_colour = cur_states[dif_idx]
        dif_col = dif_idx % 7 #42 windows, 7 per row 

    return  dif_col, ok



#bitbully also accepts row major so swapped to that
def array_to_solver(current_state):

    solver_array = []
    for row in range(6):#6 
        bottom = row*7
        board_row = current_state [bottom:bottom + 7]
        solver_array.append(board_row)
    solver_array.reverse() #bitbully wants top row first
    
    return solver_array



def choose_move(board,solver,difficulty):

    #dict keys =column, val = score for column
    scores = solver.score_all_moves(board )
    choices = []

    if difficulty == "perfect":
        return solver.best_move(board), scores

    
    #change moves to randomly choose from based on difficulty
    if difficulty == "very_hard":
        depth = 10000 #effectively max depth
        mistakes = 0.3
    elif difficulty == "hard":
        depth = 3#16
        mistakes = 0.6
    elif difficulty == "medium":
        depth = 2#8
        mistakes =0.75

    if difficulty == "easy" or random.random() < mistakes:
        easy_choices = list(scores.keys()) #any legal move
        return random.choice(easy_choices), scores
    
    for col in scores:
        moves_to_end = solver.score_to_moves_left(scores[col], board)

        if scores[col]>=0: #anything positive is non losing
            choices.append(col)

        elif moves_to_end > depth:
            choices.append(col)

    #all moves lead to loss, take from leas bad and any legal move
    if len(choices) == 0:
        # choices = list(scores.keys()) #any legal move
        return solver.best_move(board ), scores


    return random.choice(choices), scores

def cv2_select_diff(difficulty,disp_img,key):

    controls = "difficulties keys [1 - 5]"

    cv2.putText(disp_img, controls, (40, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)#this doesnt have to be in loop but updatesd diff so
    cv2.putText(disp_img, difficulty, (40, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)#this doesnt have to be in loop but updatesd diff so
    if key == ord('1'):
        difficulty = "easy"
        print("difficulty changed  to easy")

    elif key ==  ord('2'):
        difficulty = "medium"
        print("difficulty changed  to medium")   

    elif key ==  ord('3'):
        difficulty = "hard"
        print("difficulty changed  to hard")
    
    elif key ==  ord('4'):
        difficulty = "very_hard"
        print("difficulty changed  to very hard")

    elif key ==  ord('5'):
        difficulty = "perfect"
        print("difficulty changed  to perfect")

    # print("yay")
    return difficulty


# def get_img():
#     pass

def write_to_ui(game_data):
    game_json = "/dev/shm/c4_game_data.json"
    game_temp = "/dev/shm/c4_game_data.json.temp"

    with open(game_temp, "w") as f:
        json.dump(game_data, f)

    os.replace(game_temp,game_json)
        

def write_ui_img(name, img):
    path = "/dev/shm/" + name +  ".jpg"
    temp = path +".temp.jpg"

    cv2.imwrite(temp, img)
    os.replace(temp, path)
    


def read_ui_sett():
    setting_pth = "/dev/shm/c4_settings.json"
    with open(setting_pth) as f:
        settings = json.load(f)
    difficulty = settings["difficulty"]
    start_no = settings["start_number"]

    return difficulty, start_no





def main():
    # col_idx = 0
    # gripper_vertical = 0

    #initialise dict for transferring game data
    game_data = {
        "game_on": False,
        "turn": "",
        "col_idx": None,
        "difficulty": "easy",
        "little-message": "",
        "loading-message": "",
        "winner": None,
        "board": None,
        "error": "",
        "scores": None
    }

    game_data["loading-message"] = "Setting up arm."
    write_to_ui(game_data)
    #setup
    arm,arduino = setup_arm()
    

    game_data["loading-message"] = "Setting up cameras."  
    d_cam,f_cam,d_cam_mat,f_cam_mat = setup_cams()
    write_to_ui(game_data)
    solver = bb.BitBully()
    

    game_data["loading-message"] = "Going to board reading position."
    write_to_ui(game_data)
    #go to read board position
    arm.moveEEZYbotARM(135, 0.0, 119, "OFF", 0, arduino) 
    

    game_data["loading-message"] = "Setting white balance and exposure."
    write_to_ui(game_data)  
    cameras.set_exposure_markers(f_cam,f_cam_mat)
    


    #get locs ONCE
    vote_locs = game_state.get_voting_locs()

    # game_on = False
    # col_idx = None
    # difficulty = "easy"
    
    last_states = []
    last_trusted = None
    # frame =0
    key = None

    first_empty_message = True#so dont spam terminal
    first_trust_message = True

    game_data["difficulty"], last_start_no = read_ui_sett() #read start no so can compare in loop
    game_data["loading-message"] = ""  
    write_to_ui(game_data)  

    try:
        while True:

            game_data["difficulty"], start_no = read_ui_sett()
            write_to_ui(game_data)

            if start_no > last_start_no:
                last_start_no +=1
                game_data["game_on"] = False
                game_data["little-message"] = ""  #persists across turns but dont want it to be there if abandon game

                continue #clearing board starts new game 

    #########read board + write img to ui 3###########
            board_img,cur_states = game_state.get_board(f_cam,f_cam_mat,vote_locs)
            disp_img = board_img.copy()
      
            write_ui_img("board", board_img)
            # cv2.imshow("game state", board_img)
            # key = cv2.waitKey(1) & 0xFF
        
            # difficulty = select_diff(difficulty,disp_img,key)
            # cv2.waitKey(1)
            if key == ord('q'):
                        break

            
            # print("frame ", frame )
            # frame +=1

        ########## is game state changing ##############
            if cur_states is None:
                continue

            last_states.append(cur_states)
            trusted = is_board_trusted(last_states)

            if not trusted:
                game_data["error"] = "Game state unstable, please wait."
                # if first_trust_message:
                #     print("game state changing")
                #     first_trust_message = False#so dont spam
                continue
            first_trust_message = True

        ####### update board for drawing in ui #######
            solver_array = array_to_solver(cur_states) #bitbully wants top row first
            game_data["board"] = solver_array

        ############## is board empty #############
            empty = cur_states.count(EMPTY) == len(cur_states)
            if not game_data["game_on"] and not empty:
                game_data["error"] = "Please empty board."
                # if first_empty_message:
                #     # print("please empty board")
                #     first_empty_message = False
                continue#skip until empty

            elif not game_data["game_on"] and empty:
                game_data["game_on"] = True
                last_trusted = cur_states
            ######clear data from last game
                game_data["winner"] = None   
                game_data["error"] = ""    
                game_data["turn"] = YELLOW #human always plays first, so needs first message to be 'Your Turn"  
                game_data["little-message"] = ""         
                continue #game on for next loop
            # first_empty_message = True

       ######## do we think the board has changed? ##############
            if cur_states == last_trusted:
                game_data["error"] = ""   
                continue #skip if nothing happened 


           ###### is the last move allowed #######
            dif_col, ok = is_board_change_ok(last_trusted, cur_states)
                    
            if not ok: #me
                game_data["error"] = "Colour of a disc changed! Or two new discs at once? Please fix, if error continues, abandon game."  
                continue

            #now cur_states is trusted state
            


      ############# check if board legal, correct colour disc for player / gravity ###############
            try:
                board = bb.Board.from_array(solver_array) 
            except ValueError as illegal_board:
                # print("invalid board, check if disc in wrong place")
                game_data["error"] = "Invalid board, check if there's a disc in the wrong place."
                continue #skip until error resolved

            
     ####### is the game over? ###########
            game_data["winner"] = None
            if board.is_game_over():
                game_data["winner"] = board.winner()#number
                

                game_data["game_on"] = False
                game_data["turn"] = ""
                continue #clearing board starts new game


        #clear error
            game_data["error"] = ""  
                     

            
     ############ take turns THIS TAKES A LONG TIME SO MUST UPDATE MESSAGES BEFORE THIS ###############       
            game_data["turn"] = board.current_player()

        ##### ROBOT #####
            if game_data["turn"] == 2: #robot turn

                # print("robot's turn")

                game_data["col_idx"], scores = choose_move(board, solver,game_data["difficulty"]) #from robot's perpective

                ### get scores in right shape for UI###
                scores_list = []
                for col in range(7):
                    #make missing keys none, bitbully doesnt add full columns to scores dict
                    scores_list.append(scores.get(col))
                scores_list.reverse()# we face opposite side of board to robot

                game_data["scores"] = scores_list
                write_to_ui(game_data)#update ui so doesn't still say human turn, + update chart

                #home first so can see all discs
                arm.moveEEZYbotARM(arduinoInstance=arduino)

                placed = pick_and_place.pick_and_place(game_data["col_idx"], arm, arduino, 
                    d_cam,d_cam_mat,f_cam,f_cam_mat,show_image=False)

                #go to read board position
                arm.moveEEZYbotARM(135, 0.0, 119, "OFF", 0, arduino) 

                if placed:
                    # print("robot dropped disc in: ", game_data["col_idx"])
                    game_data["little-message"] = "Robot dropped disc in column " + str(game_data["col_idx"])

                else:
                    # print("robot failed, please place disc in ", game_data["col_idx"])
                    game_data["error"] = "Robot failed to play move. Please place a disc in " + str(game_data["col_idx"])
                last_trusted = cur_states

         #### HUMAN ###
            elif game_data["turn"] == 1: #human turn
                last_trusted = cur_states

                if dif_col!= game_data["col_idx"]:
                    # print("robot missed! disc landed in wrong column. it's still your turn again")
                    game_data["error"] = "Robot missed! Disc landed in wrong column. It's now your go."
                

            
            

    finally:
        cv2.destroyAllWindows()
        d_cam.stop()
        f_cam.stop()

        #turn off pump
        x,y, z= arm.forwardKinematics()
        arm.moveEEZYbotARM(x, y, z, "OFF", 0, arduino)


        #reset everything
        game_data = {
            "game_on": False,
            "turn": "",
            "col_idx": None,
            "difficulty": "easy",
            "little-message": "",
            "winner": None,
            "board": None,
            "error": "",
            "scores": None,
            "loading-message": ""
        }

        write_to_ui(game_data) 


        arduino.closeSerialPort()




if __name__== "__main__":
    main()



    


