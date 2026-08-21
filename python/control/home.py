# Import EEZYbotARM library
from math import atan2, sin,cos
from time import sleep

from easyEEZYbotARM.kinematic_model import EEZYbotARM_Mk2
from easyEEZYbotARM.serial_communication import arduinoController

# Insert your Arduino serial port here to initialise the arduino controller
myArduino = arduinoController(port="/dev/ttyACM0")
myArduino.openSerialPort()

# Initialise kinematic model with initial joint angles (home position)
robotArm = EEZYbotARM_Mk2(initial_q1=0, initial_q2=90, initial_q3=-90)
# robotArm.plot()  # plot it

# init_x, init_y, init_z = robotArm.forwardKinematics(q1=0, q2=90, q3=-90)

# print("Initial position of wrist (x,y,z in mm from centre of robot base): ", init_x, init_y, init_z)
# ##(x=204.767, y=0.0, z=201.474)

#x=234, y=0.0, z=227 orignal ee
#for when gripoper points down
init_x=206 
init_y=0.0 
init_z=227

safe_rotation_spot_x = init_x-65
safe_rotation_spot_y = init_y
safe_rotation_spot_z = init_z

# Assign new cartesian position where we want the robot arm end effector to move to
# (x,y,z in mm from centre of robot base)
#y +ve is right of roboit as you face it


vacuum_gripper_length = 120 + 3 #3 foir offset bertween their pivot point and mine
base_to_midbase = 100 #80 # mm
grid_no_legs_height = 196 # mm
grid_legs_height = 245 #mm

drop_x =300#380#-base_to_midbase #380-vacuum_gripper_length-base_to_midbase # mm
drop_y = 0  # mm
drop_z = 235#50 + 52  # mm 


# pick_x = 200#270-98  # mm
# pick_y =  50# mm
# pick_z = 130#50 + 52  # mm 


pick_x = 231.0
pick_y = -16.8
pick_z = 262.6
# x = 280
# y = 0  # mm
# z = 102

pump = "OFF"

# robotArm.moveEEZYbotARM(init_x, init_y, init_z, pump, 120, myArduino)
robotArm.moveEEZYbotARM(init_x, init_y, init_z, pump, 0, myArduino)

# # #pick up disc
# robotArm.moveEEZYbotARM(pick_x, pick_y, pick_z, pump, 0, myArduino)
# robotArm.moveEEZYbotARM(pick_x, pick_y, 15+vacuum_gripper_length, pump, 0, myArduino)
sleep(1)
# # # # # #rotate ee
# robotArm.moveEEZYbotARM(safe_rotation_spot_x, safe_rotation_spot_y, safe_rotation_spot_z, pump, 0, myArduino)
# robotArm.moveEEZYbotARM(safe_rotation_spot_x+ vacuum_gripper_length, safe_rotation_spot_y, safe_rotation_spot_z+vacuum_gripper_length, pump, 94, myArduino)

# # # #drop
# robotArm.moveEEZYbotARM(drop_x, drop_y, drop_z+15, pump, 94, myArduino)
# robotArm.moveEEZYbotARM(drop_x, drop_y, drop_z, "OFF", 94, myArduino)
# robotArm.moveEEZYbotARM(safe_rotation_spot_x+vacuum_gripper_length, safe_rotation_spot_y, safe_rotation_spot_z+vacuum_gripper_length, "OFF", 94, myArduino)
robotArm.moveEEZYbotARM(arduinoInstance=myArduino) #back to home position

# Close the serial port
myArduino.closeSerialPort()

