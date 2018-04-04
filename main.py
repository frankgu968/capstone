from camera_detect import *
import cv2
import io
import time
import numpy as np
import tensorflow as tf
from flask import Flask, render_template, Response
from flask_socketio import SocketIO
from PIL import Image
from motion import *

app = Flask(__name__)
socketio = SocketIO(app)
serial = []
cap = []
devMode = False
state = {
    'runMode': 0,
    'status': -1,
    'log': '',
    'endpoint': 'http://192.168.3.1/',
    'cmdStr': '',
    'response': '',
    'cmdResponse': '',
    'aligned' : False,
    'engaged' : False,
    'disableReset' : False,
    'firstRun': True
}

# Calibrations
Z_OFFSET = -42.
X_OFFSET = 0.
MAX_DISTANCE = 350.

# Filter samples
FILTER_NUM = 1

def gen():
    """Video streaming generator function."""
    global cap
    while True:
        success, image = cap.read()
        cv2.line(image, (0, int(HEIGHT/2)), (int(WIDTH), int(HEIGHT/2)), (0,255,0), 2)
        cv2.line(image, (int(WIDTH/2), 0), (int(WIDTH/2), int(HEIGHT)), (0,255,0), 2)
        ret, jpeg = cv2.imencode('.jpg', image)
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n')

@app.route('/')
def view():
    """ View only page """
    return render_template('view.html')

@app.route('/controls')
def controls():
    """ Control Page"""
    return render_template('control.html')

@app.route('/test')
def test():
    print("hit!")
    return 'hit!'

@app.route('/charge_on')
def charge_on():
    global state
    retStr = 'Charging begins!'
    print(retStr)
    state['response'] += retStr
    socketio.emit('state', state)

@app.route('/charge_off')
def charge_off():
    global state
    retStr = 'Charging completed!'
    print(retStr)
    state['response'] += retStr
    socketio.emit('state', state)

    cmd = generate_reset()
    state['cmdStr'] = str(cmd)
    socketio.emit('state', state)
    state['cmdResponse'] = execute_cmd(cmd, serial, devMode)

    # State transition
    if(state['cmdResponse'] == 1):
        state['status'] = -1
        state['response'] = ''
        state['cmdResponse'] = 0
        state['disableReset'] = False
        state['runMode'] = 0
        state['aligned'] = False
        state['engaged'] = False
        state['firstRun'] = True
    else:
        state['status'] = 2
        state['disableReset'] = True
        state['response'] += 'ERROR: Reset failed!\n'

    socketio.emit('state', state)

@app.route('/video_feed')
def video_feed():
    """Video streaming route. Put this in the src attribute of an img tag."""
    return Response(gen(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

def run_server():
    socketio.run(app, host='192.168.3.1', port=80)

@socketio.on('connect')
def on_connect():
    global state
    socketio.emit('state', state)
    print('Client connected!')

@socketio.on('disconnect')
def on_disconnect():
    print('Client disconnected!')

@socketio.on('reset')
def on_reset():
    print('Reset triggered!')
    global serial
    global state

    cmd = generate_LED(False)
    state['cmdStr'] = str(cmd)
    socketio.emit('state', state)
    state['cmdResponse'] = execute_cmd(cmd, serial, devMode)
    if(state['cmdResponse'] != 1):
        state['status'] = 2
        state['disableReset'] = True
        state['response'] += 'ERROR: LED Failed to turn OFF!\n'

    cmd = generate_reset()
    state['cmdStr'] = str(cmd)
    socketio.emit('state', state)
    state['cmdResponse'] = execute_cmd(cmd, serial, devMode)

    # State transition
    if(state['cmdResponse'] == 1):
        state['status'] = -1
        state['response'] = ''
        state['cmdResponse'] = 0
        state['disableReset'] = False
        state['runMode'] = 0
        state['aligned'] = False
        state['engaged'] = False
        state['firstRun'] = True
    else:
        state['status'] = 2
        state['disableReset'] = True
        state['response'] += 'ERROR: Reset failed!\n'

    socketio.emit('state', state)

@socketio.on('mode')
def on_mode(data):
    global state
    retStr = 'Set mode: '
    if data == 0:
        state['runMode'] = 0
        retStr += 'auto mode'

    elif data == 1:
        state['runMode'] = 1
        retStr += 'stepped mode'
    state['response'] += retStr  + '\n'
    print(retStr)
    socketio.emit('state', state)

@socketio.on('step')
def on_step():
    global state
    global serial

    while (not state['aligned']) and (state['status'] != 2):
        # Manual mode break condition
        if (state['runMode'] == 1) and state['aligned']:
            break

        # Turn on LED
        cmd = generate_LED(True)
        state['cmdStr'] = str(cmd)
        state['status'] = 1
        socketio.emit('state', state)
        state['cmdResponse'] = execute_cmd(cmd, serial, devMode)
        if state['cmdResponse'] != 1:
            state['status'] = 2
            state['response'] += 'ERROR: LED toggled failure!\n'
        socketio.emit('state', state)

        # Wait for camera to adjust
        if(state['firstRun']):
            time.sleep(0.5)
            state['firstRun'] = False

        # Run detection algorithm
        if not devMode:
            result = run_detect(cap, sess, FILTER_NUM)   # 7 samples
        else:
            result = [1, 1., -1.,1.]
        if result[0] < 0:
            retStr = 'ERROR: Execution failed [' + str(result) + ']\n'
            retStr += get_error_str(result[0])
            print(retStr)
            state['response'] += retStr
            state['cmdResponse'] = -1
            state['status'] = 2
            socketio.emit('state', state)
            return

        if result[0] > MAX_DISTANCE:
            retStr = 'ERROR: Charging port out of range'
            print(retStr)
            state['response'] += retStr
            state['status'] = 2
            socketio.emit('state', state)
            return

        # Append to log and send
        line = "Estimated Distance: " + "{:4.1f}".format(result[0]) + " (mm) | X Correction: " + "{:4.1f}".format(result[1]) + " (mm) | Z Correction: " +  "{:4.1f}".format(result[2]) + " (mm) | Y Correction: " + "{:4.1f}".format(result[3]) + ' (mm)\n'
        state['response'] += line
        socketio.emit('state', state)

        if (result[1] == 0.) and (result[2] == 0.) and (result[3] == 0.):
            state['aligned'] = True
            if not result[4]:
                retStr = 'ERROR: Exceeded allowable angular misalignment\n'
                print(retStr)
                state['status'] = 2
                state['response'] += retStr
                state['cmdResponse'] = 1
                socketio.emit('state', state)
                return

            retStr = 'Ready to engage\n'
            print(retStr)
            state['cmdResponse'] = 1
            state['status'] = 0
            state['response'] += retStr
            socketio.emit('state', state)
            if state['runMode'] == 1:
                return

        else:
            cmd = generate_move(result[1], result[3], result[2])
            state['cmdStr'] = str(cmd)
            socketio.emit('state', state)
            state['cmdResponse'] = execute_cmd(cmd, serial, devMode)
            if(state['cmdResponse'] == 1):
                state['status'] = 0
            else:
                state['status'] = 2
            socketio.emit('state', state)
            if state['runMode'] == 1:
                break

    if(state['aligned']):
        # Turn off the LED
        cmd = generate_LED(False)
        state['cmdStr'] = str(cmd)
        socketio.emit('state', state)
        state['cmdResponse'] = execute_cmd(cmd, serial, devMode)
        if(state['cmdResponse'] == 1):
            state['runMode'] = 0
        else:
            state['runMode'] = 2
        socketio.emit('state', state)

        # Final Correction
        cmd = generate_move(X_OFFSET, 50, Z_OFFSET)
        state['cmdStr'] = str(cmd)
        socketio.emit('state', state)
        state['cmdResponse'] = execute_cmd(cmd, serial, devMode)

        # Charger engagement
        retStr = 'Engaging charger...\n'
        state['response'] += retStr
        cmd = generate_move(0, 69, 0)
        state['cmdStr'] = str(cmd)
        socketio.emit('state', state)
        state['cmdResponse'] = execute_cmd(cmd, serial, devMode)

        retStr = 'Charger engaged!\n'
        state['response'] += retStr
        state['cmdStr'] = ''
        state['status'] = 3
        socketio.emit('state', state)
        # cmd = generate_engage()
        # state['cmdStr'] = str(cmd)
        # socketio.emit('state', state)
        # state['cmdResponse'] = execute_cmd(cmd, serial, devMode)
        # if(state['cmdResponse'] == 1):
        #     state['status'] = 0
        # else:
        #     state['status'] = 2
        # socketio.emit('state', state)

if __name__ == '__main__':
    if not devMode:
        # Create hardware peripheral objects
        cap = cv2.VideoCapture('/dev/camera')

        # Initialize the motion coprocessor
        serial = init_serial()

        # Load pre-trained models
        print("Loading pre-trained model...")
        detection_graph = load_graph()
        sess = tf.Session(graph=detection_graph)
        run_detect(cap, sess, 1)    # Run once to initialize graph
        print("Detection model loaded!")

    # Start server
    socketio.start_background_task(run_server)
