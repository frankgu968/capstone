import serial
import time

def init_serial():
    return serial.Serial('/dev/coprocessor', 9600, timeout=1)

def generate_move(x,y,z):
    cmdStr = '{MOV,' + str(x) + ','+ str(y) + ',' + str(z)+'}\n'
    return bytes(cmdStr, "utf")

def generate_reset():
    cmdStr = '{RST}\n'
    return bytes(cmdStr, "utf")

def generate_stop():
    cmdStr = '{STP}\n'
    return bytes(cmdStr, "utf")

def generate_engage():
    cmdStr = '{ENG}\n'
    return bytes(cmdStr, "utf")

# def generate_disengage():
#     cmdStr = '{DNG}\n'
#     return bytes(cmdStr, "utf")

def generate_LED(on):
    if on:
        # Turn on the LED
        cmdStr = '{LON}\n'
        return bytes(cmdStr, "utf")
    else:
        # Turn off the LED
         cmdStr = '{LOF}\n'
         return bytes(cmdStr, "utf")

def execute_cmd(cmdStr, ser, devMode):
    if(devMode):
        return 1

    ser.write(cmdStr)

    for i in range(25):
        try:
            time.sleep(0.01)
            result = ser.readline()
            # print(result)
            if result == b'{CPT}\n':
                return 1
            elif result == b'{ERR}\n':
                return -1
        except:
            print('excepted')
            pass

    # nice timeout :)
    return 1
