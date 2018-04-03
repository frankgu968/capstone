from camera_detect import run_detect, load_graph
import cv2
import io
import numpy as np
import tensorflow as tf
from flask import Flask, render_template, Response
from flask_socketio import SocketIO
from PIL import Image
from motion import *

text = ''
auto = False
app = Flask(__name__)
socketio = SocketIO(app)
serial = []
aligned = False
engaged = False

def gen():
    """Video streaming generator function."""
    while True:
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + open('./img/current.jpg', 'rb').read() + b'\r\n')

@app.route('/')
def index():
    """Video streaming ."""
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    """Video streaming route. Put this in the src attribute of an img tag."""
    return Response(gen(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

def run_server():
    socketio.run(app, host='172.16.3.25', port=80)

@socketio.on('connect')
def on_connect():
    socketio.emit('serialData', text)
    print('Client connected!')

@socketio.on('disconnect')
def on_disconnect():
    print('Client disconnected!')

@socketio.on('reset')
def on_reset():
    print('Reset triggered!')
    global serial
    global auto
    global engaged
    global aligned
    global text
    cmdStr = generate_reset()
    socketio.emit('cmdData', str(cmdStr))
    result = execute_cmd(cmdStr, serial)
    socketio.emit('resetDone', result)
    auto = False
    aligned = False
    engaged = False
    text = ''

@socketio.on('mode')
def on_mode(data):
    global text
    global auto
    retStr = 'Set mode: '
    if data == 0:
        auto = True
        retStr += 'auto'

    elif data == 1:
        auto = False
        retStr += 'stepped'
    text += retStr  + '\n'
    print(retStr)
    socketio.emit('serialData', text)

@socketio.on('step')
def on_step():
    global text
    global imgByteArr
    global serial
    global aligned

    while not aligned:
        # Manual mode break condition
        if (not auto) and aligned:
            break

        # Turn on LED
        cmdStr = generate_LED(True)
        socketio.emit('cmdData', str(cmdStr))
        result = execute_cmd(cmdStr, serial)
        socketio.emit('stepDone', result)

        # Run detection algorithm
        result = run_detect(cap, sess, 5)   # 5 samples
        if result[0] < 0:
            retStr = 'ERROR: Execution failed [' + str(result) + ']'
            print(retStr)
            socketio.emit('serialData', retStr)
            socketio.emit('stepDone', -1)
            return

        # Save the current image
        # currentImage = Image.fromarray(result[3])
        # imgByteArr = io.BytesIO()
        # currentImage.save(imgByteArr, format='JPEG')

        # Append to log and send
        line = "Estimated Distance: " + str(result[0]) + " | X Correction: " + str(result[1]) + " | Z Correction: " + str(result[2]) + " | Y Correction: " + str(result[3])
        text += line  + '\n'
        socketio.emit('serialData', text)
        print('Sent: ' + line)

        if (result[1] == 0.) and (result[2] == 0.) and (result[3] == 0.):
            aligned = True
            retStr = 'Ready to engage'
            print(retStr)
            text += retStr  + '\n'
            socketio.emit('stepDone', 1)
            socketio.emit('serialData', text)
            if not auto:
                return

        else:
            cmdStr = generate_move(result[1], result[3], result[2])
            socketio.emit('cmdData', str(cmdStr))
            result = execute_cmd(cmdStr, serial)
            socketio.emit('stepDone', result)
            if not auto:
                break

    if(aligned):
        # Turn off the LED
        cmdStr = generate_LED(True)
        socketio.emit('cmdData', str(cmdStr))
        result = execute_cmd(cmdStr, serial)

        # Engage the charger
        retStr = 'Engaging charger...'
        text += retStr  + '\n'
        socketio.emit('serialData', text)
        cmdStr = generate_engage()
        socketio.emit('cmdData', str(cmdStr))
        result = execute_cmd(cmdStr, serial)
        socketio.emit('stepDone', result)

if __name__ == '__main__':
    # Create hardware peripheral objects
    cap = cv2.VideoCapture('/dev/camera')

    # Initialize the motion coprocessor
    serial = init_serial()

    # Load pre-trained models
    print("Loading pre-trained model...")
    detection_graph = load_graph()
    sess = tf.Session(graph=detection_graph)
    run_detect(cap, sess, 1)
    print("Detection model loaded!")

    # Start server
    socketio.start_background_task(run_server)
