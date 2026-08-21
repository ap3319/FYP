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


#x=234, y=0.0, z=227 orignal ee
#for when gripoper points down
init_x=206 
init_y=0.0 
init_z=227

pump = "OFF"

robotArm.moveEEZYbotARM(135,0,119, pump, 0, myArduino)#135,0,119 view board pose
# robotArm.moveEEZYbotARM(init_x, init_y, init_z, pump, 0, myArduino)
# robotArm.moveEEZYbotARM(init_x, init_y, init_z, pump, 0, myArduino)



# robotArm.moveEEZYbotARM(arduinoInstance=myArduino) #back to home position

# Close the serial port
myArduino.closeSerialPort()

