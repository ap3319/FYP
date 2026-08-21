# %%
import matplotlib.pyplot as plt

# plt.plot([1,2,3], [4,5,6])
# plt.show()

# Import EEZYbotARM library
from easyEEZYbotARM.kinematic_model import EEZYbotARM_Mk2

# Initialise robot arm with initial joint angles
myRobotArm = EEZYbotARM_Mk2(initial_q1=0, initial_q2=90, initial_q3=90)
# myRobotArm.plot()  # plot it

# Assign cartesian position where we want the robot arm end effector to move to
# (x,y,z in mm from centre of robot base)
x = 200  # mm
y = 0  # mm
z = 115  # mm add 52mm to account for changed end effector design 

# Compute inverse kinematics
a1, a2, a3 = myRobotArm.inverseKinematics(x, y, z)

# Print the result
print('To move the end effector to the cartesian position (mm) x={}, y={}, z={}, the robot arm joint angles (degrees)  are q1 = {}, q2= {}, q3 = {}'.format(x, y, z, a1, a2, a3))

# Visualise the new joint angles
myRobotArm.updateJointAngles(q1=a1, q2=a2, q3=a3)
myRobotArm.plot()


servoAngle_q1, servoAngle_q2, servoAngle_q3 = myRobotArm.map_kinematicsToServoAngles()

print('The robot arm joint angles (degrees) are q1 = {}, q2= {}, q3 = {}'.format(myRobotArm.q1, myRobotArm.q2, myRobotArm.q3))
print('The corresponding servo angles (degrees) are servoAngle_q1 = {}, servoAngle_q2= {}, servoAngle_q3 = {}'.format(servoAngle_q1, servoAngle_q2, servoAngle_q3))

# %%
