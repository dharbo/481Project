from flask import Flask, render_template, request, session, redirect, url_for
from flask_socketio import join_room, leave_room, send, SocketIO
import random
from string import ascii_uppercase
import os
import openai
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = "hjhjsdahhds"
socketio = SocketIO(app)

rooms = {}

API_KEY = os.getenv('API_KEY')
openai.api_key = API_KEY

# we can add more later
listenFor = {"hey chad", "hi chad", "hello chad", "chad can you help", "chad help"}

def useAPI(inputString):
    completion = openai.Completion.create(
        model="text-davinci-003",
        prompt=inputString,
        max_tokens=50, # change for longer responses
        temperature=0
    )
    return completion.choices[0].text

def generate_unique_code(length):
    while True:
        code = ""
        for _ in range(length):
            code += random.choice(ascii_uppercase)
        
        if code not in rooms:
            break
    
    return code

@app.route("/", methods=["POST", "GET"])
def home():
    session.clear()
    if request.method == "POST":
        name = request.form.get("name")
        code = request.form.get("code")
        join = request.form.get("join", False)
        create = request.form.get("create", False)

        if not name:
            return render_template("home.html", error="Please enter a name.", code=code, name=name)
        
        if name.lower() == "chad":
            return render_template("home.html", error="Please enter a different name. There is only one Chad.", code=code, name=name)

        if join != False and not code:
            return render_template("home.html", error="Please enter a room code.", code=code, name=name)
        
        room = code
        if create != False:
            room = generate_unique_code(4)
            rooms[room] = {"members": 0, "messages": []}
        elif code not in rooms:
            return render_template("home.html", error="Room does not exist.", code=code, name=name)
        
        session["room"] = room
        session["name"] = name
        return redirect(url_for("room"))

    return render_template("home.html")

@app.route("/room")
def room():
    room = session.get("room")
    if room is None or session.get("name") is None or room not in rooms:
        return redirect(url_for("home"))

    return render_template("room.html", code=room, messages=rooms[room]["messages"])

@socketio.on("message")
def message(data):
    room = session.get("room")
    if room not in rooms:
        return 
    
    content = {
        "name": session.get("name"),
        "message": data["data"]
    }
    send(content, to=room)
    rooms[room]["messages"].append(content)
    # check if Chad was called.
    # change to lowercase and remove additional spaces.
    inputMessage = content["message"].lower()
    inputMessage = " ".join(inputMessage.split())

    # set variables
    useChad = False
    lengthActivation = 0

    # loop through all strings to listen for and if
    # there is one, update variables.
    for activation in listenFor:
        if inputMessage.find(activation) != -1:
            useChad = True
            lengthActivation = len(activation)
            break

    # if Chad is being prompted, call API.
    if useChad:
        stringToProcess = inputMessage[lengthActivation+1::]
        if (stringToProcess[0] == ' '):
            stringToProcess = stringToProcess[1::] + " just list them out and keep it short"  # this is here to ensure results are listed

        result = useAPI(inputMessage)
        # print("Assistant: ", result, "\n")

        chadContent = {
            "name": "Chad",
            "message": result
        }
        send(chadContent, to=room)

    print(f"{session.get('name')} said: {data['data']}")

@socketio.on("connect")
def connect(auth):
    room = session.get("room")
    name = session.get("name")
    if not room or not name:
        return
    if room not in rooms:
        leave_room(room)
        return
    
    join_room(room)
    send({"name": name, "message": "has entered the room"}, to=room)
    rooms[room]["members"] += 1
    print(f"{name} joined room {room}")

@socketio.on("disconnect")
def disconnect():
    room = session.get("room")
    name = session.get("name")
    leave_room(room)

    if room in rooms:
        rooms[room]["members"] -= 1
        if rooms[room]["members"] <= 0:
            del rooms[room]
    
    send({"name": name, "message": "has left the room"}, to=room)
    print(f"{name} has left the room {room}")

if __name__ == "__main__":
    socketio.run(app, debug=True)