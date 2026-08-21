import threading
import subprocess
import signal

import pathlib
import sys

#TODO: maybe cameras should be a class too???
PYTHON_FOLDER = pathlib.Path(__file__).parent.parent.resolve()
CUR_PYTHON = sys.executable

class RobotStateMachine:

    idle = "IDLE"
    running = "RUNNING"
    stopped = "STOPPED"

    def __init__(self):

        self.state = self.idle
        self.lock = threading.Lock()#get status and clicking buttons are different threads
        self.game_on = None

    def is_running(self):
            ever_ran = self.game_on is not None
            if ever_ran is False:
                return False

            ended = self.game_on.poll()
            if ended is None:
                return True
            else:
                return False


    def update_idle(self):
        #call WITH LOCK! flask and start use this
        #go to idle if game process ended without estop
        if not self.is_running() and self.state != self.stopped:
            self.state = self.idle

        return self.state


    def check_status(self):
        with self.lock:
            state = self.update_idle()

        return state


    def start(self):
        with self.lock:

            #should we be idle?
            self.update_idle()

            #only start from idle
            if self.state == self.idle:

                #Popen returns object with .poll unlike run which waits tll process ends
                self.game_on = subprocess.Popen([CUR_PYTHON, "game_loop.py"], cwd = PYTHON_FOLDER)
                self.state = self.running

        return self.state


    def estop(self):
        with self.lock:
            #only stop if running
            if  self.is_running():

                self.game_on.send_signal(signal.SIGINT)#kills process but lets finally run
                self.state = self.stopped
        
        return self.state



    def reset(self):
        with self.lock:
            #only reset from stopped
            if self.state == self.stopped:

                #check if precess has finished exiting, has to turn off pump etc.
                if not self.is_running():
                    self.state = self.idle

        return self.state



















#Notes:

#run waits for process to finish popen doesnt

#Popen
#https://docs.python.org/3/library/subprocess.html#popen-objects
#Execute a child program in a new process.
#If args is a string, the string specifies the command to execute through the shell. 
#This means that the string must be formatted exactly as it would be when typed at the shell prompt.

#running python script
#https://stackoverflow.com/questions/7152340
#use list like in terminal ['python', 'somescript.py']
#need venv python tho not regular one

#Popen.poll()
# Check if child process has terminated. Set and return returncode attribute.
#  Otherwise, returns None.
#NONE = RUNNING

#A negative value -N indicates that the child was terminated by signal N (POSIX only).
# returncode -2 when SIGINT 

#sigterm and sigkill dont let finally block run, sigint does







