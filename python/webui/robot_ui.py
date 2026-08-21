import flask

import json
import os
import time

from robot_state import RobotStateMachine


app = flask.Flask(__name__)
robot = RobotStateMachine()

settings = {
    "difficulty": "easy",
    "start_number": 0 #so can abandon and then start a new game
}



#to game loop
def atomic_write_settings():
    #write first then replace so whole file updated at once
    with open("/dev/shm/c4_settings.json.temp","w") as f:
        json.dump(settings,f)

    os.replace("/dev/shm/c4_settings.json.temp", "/dev/shm/c4_settings.json")


@app.route("/") #called when / 
def index():
    return flask.render_template("index.html")

@app.route("/status", methods = ["GET"]) #only reads so only accept get
def status():
    return robot.check_status()

@app.route("/start", methods = ["POST"]) 
def start():
    return robot.start()

@app.route("/estop", methods=["POST"])
def estop():
    return robot.estop()

@app.route("/reset", methods = ["POST"])
def reset() :
    return robot.reset()


@app.route("/abandon_game", methods=["POST"])
def abandon_game():
    settings["start_number"] += 1
    atomic_write_settings()
    
    #return status so can use postUrlUpdateState like other buttons
    return robot.check_status() 




@app.route("/set_difficulty/<name>",methods=["POST"])
def set_difficulty(name):

    settings["difficulty"] = name
    atomic_write_settings()

    return robot.check_status() 


@app.route("/game_data")
def get_game_data():
    game_data_pth = "/dev/shm/c4_game_data.json"

    try:
        with open(game_data_pth) as f:
            game_data = json.load(f)
    except FileNotFoundError:
        print("game loop hasn't written game data yet")

        game_data = {
                "game_on": "",
                "error": ""
            }
        
    return game_data


def gen(name):
    while True:
        path = "/dev/shm/"+name+".jpg" 

        try:
            with open(path, "rb") as f:#read as binary
                frame = f.read()
        except FileNotFoundError:
                print("game loop hasn't written img yet")
                time.sleep(0.2)#dont spam open()
                continue #skip generator loop until  img

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        time.sleep(0.1)#otherwise as fast as possible


@app.route("/board.mjpg")
def get_board_image():

    board_img = flask.Response(gen("board"),
            mimetype='multipart/x-mixed-replace; boundary=frame')
    return board_img


@app.route("/pick.mjpg")
def get_pick_image():

    board_img = flask.Response(gen("pick"),
            mimetype='multipart/x-mixed-replace; boundary=frame')
    return board_img

@app.route("/place.mjpg")
def get_place_image():

    board_img = flask.Response(gen("place"),
            mimetype='multipart/x-mixed-replace; boundary=frame')
    return board_img


if __name__ == "__main__":
    atomic_write_settings()#now settings exists!

    #remove old file so last games messages dont show
    if os.path.exists("/dev/shm/c4_game_data.json"):
        os.remove("/dev/shm/c4_game_data.json")

    app.run(host="0.0.0.0", port=5000, debug=True)
























#notes:
# route() decorator 
# func defined, then aplied on other func with @decorator_name above the func
#https://www.w3schools.com/python/python_decorators.asp

#https://flask.palletsprojects.com/en/stable/quickstart

#https://www.geeksforgeeks.org/python/generators-in-python/
#" Instead of using return to send back a single value, 
#generator functions use yield to produce a series of results 
#over time. The function pauses its execution after yield,
#  maintaining its state between iterations."

#https://blog.miguelgrinberg.com/post/video-streaming-with-flask

#app.run(host="0.0.0.0", port=5000, debug=True)
# starts built in dev server
# debug = True allows auto reload when file is saved and gives in browser errors
# also auto reloads templates!