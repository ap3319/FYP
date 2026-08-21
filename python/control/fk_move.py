# Import EEZYbotARM library
from easyEEZYbotARM.kinematic_model import EEZYbotARM_Mk2
from easyEEZYbotARM.serial_communication import arduinoController

# Initialise robot arm with initial joint angles
#myRobotArm = EEZYbotARM_Mk2(initial_q1=0, initial_q2=70, initial_q3=-100)
myRobotArm = EEZYbotARM_Mk2(initial_q1=0, initial_q2=90, initial_q3=-90)
# myRobotArm.plot()  # plot it

# Assign new joint angles
a1 = 0  # joint angle 1
a2 = 90  # joint angle 2
a3 = -90 # joint angle 3



# Compute forward kinematics
x, y, z = myRobotArm.forwardKinematics(q1=a1, q2=a2, q3=a3)

# Print the result
print('With joint angles(degrees) q1={}, q2={}, q3={}, the cartesian position of the end effector(mm) is x={}, y={}, z={}'.format(a1, a2, a3, x, y, z))


# update kinematic model with new joint angles
myRobotArm.updateJointAngles(q1=a1, q2=a2, q3=a3)

# Map the kinematic model joint angles to servo angles
servo = myRobotArm.map_kinematicsToServoAngles()
print('Servo angles to achieve these joint angles: ', servo)

# Plot model
# myRobotArm.plot()


# Insert your Arduino serial port here
myArduino = arduinoController(port="/dev/ttyACM0")

#send previously calculated servo angles by the forward kinematics
testData = []
testData.append(myArduino.composeMessage(servoAngle_q1=servo[0],
                                         servoAngle_q2=servo[1],
                                         servoAngle_q3=servo[2],
                                         servoAngle_EE=90,
                                        instruction="OFF"))

# The connection should be managed in this sequence (will be simplified in future)
# Open a serial port and connect to the Arduino
myArduino.openSerialPort()
# Send the data which is managed by the 'run test' function'
myArduino.communicate(data=testData, delay_between_commands=3)
myArduino.closeSerialPort()  # Close the serial port
