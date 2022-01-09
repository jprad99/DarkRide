#   ___  ___          _       _
#   |  \/  |         | |     | |
#   | .  . | ___   __| |_   _| | __ _ _ __
#   | |\/| |/ _ \ / _` | | | | |/ _` | '__|
#   | |  | | (_) | (_| | |_| | | (_| | |
#   \_|  |_/\___/ \__,_|\__,_|_|\__,_|_|
#
#   ______           _     ______ _     _
#   |  _  \         | |    | ___ (_)   | |
#   | | | |__ _ _ __| | __ | |_/ /_  __| | ___
#   | | | / _` | '__| |/ / |    /| |/ _` |/ _ \
#   | |/ / (_| | |  |   <  | |\ \| | (_| |  __/
#   |___/ \__,_|_|  |_|\_\ \_| \_|_|\__,_|\___|
#
#   Created by James Radko
#   Version 1.0.0

################################################
###############Settings!!!!!!###################
################################################
# Choose the serial port name.
# Linux USB example:  "/dev/ttyACM0"  (see also: /dev/serial/by-id)
# macOS USB example:  "/dev/cu.usbmodem001234562"
# Windows example:    "COM6"
port_name = "/dev/ttyACM0"
baud_rate = 9600  # Standard for SMC G2
device_number = None  # Typically not used, here for future
db_address = "192.168.1.152" # Where the MariaDB is!


################################################
##################DEBUGGING#####################
################################################
runWithoutSMC = True  # True will run with virtualSMC

################################################
#################PACKAGES#######################
################################################
import netifaces  # to retrieve IP Address
import signal  # to process SIGTERM and other OS Signals for clean shutdown
import os  # prereq
import sys  # prereq
import pyfiglet  # create logo at beginning of terminal, purely cosmetic
import time  # for sleep
import mariadb  # database connector
import threading  # run background processes to check ESTOP and other
from multiprocessing import Process
from subprocess import PIPE, Popen
from threading import Thread
import re  # regular expression
import serial  # For comms with the SMC G2 via USB/Serial
from queue import Queue, Empty

################################################
###############Global Variables#################
################################################
global vehicle  # the vehicle ID to communicate with the server
global status  # current operational status
global enableMotor  # local version of the estop parameter, for holding
global stopped  # is the vehicle stopped, EXPERIMENT
global currentBlock  # current location in the blocking system of the vehicle
global speed

vehicle = 1

################################################
##################Pre-Startup###################
################################################
logo = pyfiglet.figlet_format("  Modular\nDark Ride", font="slant")


################################################
###################Database#####################
################################################
try:
    conn = mariadb.connect(
        user="python",
        password="python",
        host=db_address,
        port=5557,
        database="darkride",
    )
    print("Connection Successful")

except mariadb.Error as e:
    # if the system is unable to connect to the database
    print(f"Error connecting to MariaDB Platform: {e}")
    print()
    print("Terminating Process")
    exit()
cur = conn.cursor()  # create cursor object


################################################
##############Motor Controller##################
################################################
class SmcG2Serial(object):  # define functions of the Pololu SMC G2
    def __init__(self, port, device_number=None):
        self.port = port
        self.device_number = device_number
        global enableMotor
        enableMotor = False

    def send_command(self, cmd, *data_bytes):
        if self.device_number == None:
            header = [cmd]  # Compact protocol
        else:
            header = [0xAA, device_number, cmd & 0x7F]  # Pololu protocol
        self.port.write(bytes(header + list(data_bytes)))

    # Sends the Exit Safe Start command, which is required to drive the motor.
    def exit_safe_start(self):
        self.send_command(0x83)
        global enableMotor
        enableMotor = True

    # Sets the SMC's target speed (-3200 to 3200).
    def set_target_speed(self, speed):
        cmd = 0x85  # Motor forward
        if speed < 0:
            cmd = 0x86  # Motor reverse
            speed = -speed
        self.send_command(cmd, int(speed) & 0x1F, int(speed) >> 5 & 0x7F)

    # Gets the specified variable as an unsigned value.
    def get_variable(self, id):
        self.send_command(0xA1, id)
        result = self.port.read(2)
        if len(result) != 2:
            raise RuntimeError("Expected to read 2 bytes, got {}.".format(len(result)))
        b = bytearray(result)
        return b[0] + 256 * b[1]

    # Gets the specified variable as a signed value.
    def get_variable_signed(self, id):
        value = self.get_variable(id)
        if value >= 0x8000:
            value -= 0x10000
        return value

    # Gets the target speed (-3200 to 3200).
    def get_target_speed(self):
        return self.get_variable_signed(20)

    # Gets a number where each bit represents a different error, and the
    # bit is 1 if the error is currently active.
    # See the user's guide for definitions of the different error bits.
    def get_error_status(self):
        return self.get_variable(0)  ### THIS IS WORTH IMPLEMENTING DOWN THE ROAD

    #
    def stop_motor(self):
        self.send_command(0xE0)
        global enableMotor
        enableMotor = False


class virtualSMC(
    object
):  # Create a virtual version of the SMC for testing without motor control
    def __init__(self):
        print("virtualSMC initiated")
        global enableMotor
        enableMotor = False

    def send_command(self, cmd, *data_bytes):
        print("virtualSMC sending command: " + cmd)

    # Sends the Exit Safe Start command, which is required to drive the motor.
    def exit_safe_start(self):
        self.send_command("Enable Motor")
        global enableMotor
        enableMotor = True

    # Sets the SMC's target speed (-3200 to 3200).
    def set_target_speed(self, speed):
        cmd = "forward"  # Motor forward
        if speed < 0:
            cmd = "reverse"  # Motor reverse
            speed = -speed
        print(f"virtualSMC sending command: Speed {speed} {cmd}")

    def stop_motor(self):
        self.send_command("Stop Motor")
        global enableMotor
        enableMotor = False


class shutdownWatchdog:
    # basic watchdog to detect if the machine is shutting down, and ensure that
    # the code can send final pings to the database informing it that the vehicle
    # is going offline
    def __init__(self):
        signal.signal(signal.SIGINT, self.exit_gracefully)
        signal.signal(signal.SIGTERM, self.exit_gracefully)
        signal.signal(signal.SIGHUP, self.exit_gracefully)
        signal.signal(signal.SIGQUIT, self.exit_gracefully)

    def exit_gracefully(self, signum, frame):
        print("YAY")
        print(signum)
        print(frame)
        time.sleep(5)
        shutdown()


def rideStart():
    global status
    global vehicle
    global enableMotor
    global currentBlock
    global speed

    # Start the motor controller
    try:
        if runWithoutSMC == True:
            smc = virtualSMC()
        else:
            port = serial.Serial(port_name, baud_rate, timeout=0.1, write_timeout=0.1)
            smc = SmcG2Serial(port, device_number)
    except Exception as E:
        print(
            "SMC Controller Not Found on Port "
            + port_name
            + "\nPlease Check Connection"
        )
        print()
        print("System Error Message:")
        print(E)
        print()
        status = "SMC ERROR"
        updateStatus()
        quit()
    # enable the motor
    smc.exit_safe_start()

    status = "initializing"
    updateStatus()
    print(logo)
    print("Initializing")
    cur.execute("SELECT location FROM vehicles WHERE vehicleID = %s" % (vehicle))
    currentBlock = cur.fetchall()[0][0]
    conn.commit()
    cur.execute("SELECT speed FROM vehicles WHERE vehicleID = %s" % (vehicle))
    rawSpeed = cur.fetchall()[0][0]
    speed = rawSpeed // 32
    print(f"Speed is: {speed}")
    conn.commit()
    time.sleep(1)
    print("activating motor")
    eStop(False)
    time.sleep(1)
    print(f"resuming speed {speed}%")
    setSpeed(speed)
    getIP()
    print("Finished with startup")
    status = "READY"
    updateStatus()


def ping(IP):
    response = os.system('ping ' + str(IP))
    return response


def updateStatus():
    global status
    cur.execute("UPDATE vehicles SET Status = %s WHERE vehicleID=%d" %((status),int(vehicle)))
    conn.commit()
#Create a function for checking if the new block is free
#If it is, set prior block to '' and set new block to vehicle ID, return TRUE
#If it is NOT, return FALSE as advance
def nextBlockClear(newBlock):
    newBlock = int(newBlock)
    cur.execute("SELECT location FROM vehicles WHERE location = %s" %(newBlock))
    occupant = cur.fetchall() #strip down result to the desired value
    QtyInBlock = len(occupant)
    print(QtyInBlock)
    if QtyInBlock == 0:
        cur.execute("UPDATE vehicles SET location = %s WHERE vehicleID=%d" %(newBlock,int(vehicle)))
        advance = 1
    else:
        advance = 0
    conn.commit()
    return advance

def dispatch():
    cur.execute("SELECT dispatch FROM vehicles WHERE vehicleID = %s" %(int(vehicle)))
    dispatchStatus = cur.fetchall()[0][0] #strip down result to the desired value
    if dispatch == 'GO':
        cur.execute("UPDATE vehicles SET dispatch = 'In Motion' WHERE vehicleID=%d" %(int(vehicle)))
        dispatch = 1
    else:
        dispatch = 0
    conn.commit()
    return dispatch

def setSpeed(speedPercent):
    if 0<=speedPercent<=100:
        global speed
        speed = speedPercent*32
        smc.set_target_speed(speed)
        cur.execute("UPDATE vehicles SET speed = %s WHERE vehicleID=%d" %(speed,int(vehicle)))
        conn.commit()
    else:
        print(f'Improper Speed of {speedPercent}%')
        print('Activating ESTOP')
        eStop(True)


def activateProp(propID):
    cur.execute("UPDATE props SET propstate = %s WHERE propID = %d" %(1,propID))
    conn.commit()

def hold(hold):
    global enableMotor
    global status
    global speed
    global resumeSpeed
    if speed != 0:
        resumeSpeed = speed
    status = "'holding'"
    #print(f'Hold {hold}')
    if hold == True:
        if enableMotor == True:
            setSpeed(0)
            enableMotor = False
    elif hold == False:
        if enableMotor == False:
            setSpeed(resumeSpeed)
            status = "'running'"
            enableMotor = True
    conn.commit()


def eStop(hold):
    global enableMotor
    global status
    global stopped
    print(f'estop: {stopped} hold: {hold} enableMotor" {enableMotor}')
    if (hold == True) and (enableMotor == True):
        #cur.execute("UPDATE vehicles SET MotorEnable = %s WHERE vehicleID = %d" %(0,int(vehicle)))
        smc.stop_motor()
        status = "'GLOBAL ESTOP'"
        enableMotor = False
    elif (hold == False) and (enableMotor == False):
        #cur.execute("UPDATE vehicles SET MotorEnable = %s WHERE vehicleID = %d" %(1,int(vehicle)))
        smc.exit_safe_start()
        status = "'running'"
        enableMotor = True

def localeStop(hold):
    global enableMotor
    global status
    global stopped
    print(f'estop: {stopped} hold: {hold} enableMotor" {enableMotor}')
    if (hold == True) and (enableMotor == True):
        try:
            cur.execute("UPDATE vehicles SET MotorEnable = %s WHERE vehicleID = %d" %(0,int(vehicle)))
        except:
            print('An Error Occured')
            shutdown()
        smc.stop_motor()
        status = "'LOCAL ESTOP'"
        enableMotor = False
        stopped = True
    elif (hold == False) and (enableMotor == False):
        try:
            cur.execute("UPDATE vehicles SET MotorEnable = %s WHERE vehicleID = %d" %(1,int(vehicle)))
        except:
            print('An Error Occured')
            shutdown()
        smc.exit_safe_start()
        status = "'running'"
        enableMotor = True
        stopped = False


def watchdog():
    watchdog = shutdownWatchdog()
    while True:
        if watchdog.shutdown_now == True:
            shutdown()

def getIP():
    interfaces = netifaces.interfaces()
    interface = interfaces[1]
    local_ip = netifaces.ifaddresses(interface)[netifaces.AF_INET][0]['addr']
    local_ip = "'"+local_ip+"'"
    print(local_ip)
    cur.execute("UPDATE vehicles SET IP = %s WHERE vehicleID=%d" %((local_ip),int(vehicle)))
    conn.commit()

def advanceBlock(block):
    while True:
        advance = nextBlockClear(block)
        if advance == 0: # the next block is not clear
            print('waiting')
            hold(True)
            time.sleep(1)
        else:
            hold(False)
            break

def serverComms():
    while True:
        global vehicle
        global enableMotor
        global status
        global stopped
        try:
            updateStatus()
            cur.execute("SELECT MotorEnable FROM vehicles WHERE location <> 'M' and MotorEnable = 0")
            motorDB = cur.fetchall()
            qtyStops = len(motorDB)
            conn.commit()
        except mariadb.Error as e:
            print(f'Unable to access MariaDB: {e}')
            print()
            print('Terminating')
            shutdown()
        if qtyStops != 0 and stopped == False:
            stopped = True
        elif qtyStops == 0 and stopped == True:
            stopped = False
        time.sleep(1)

def shutdown():
    global status
    eStop(True)
    status = "'offline'"
    updateStatus()
    print('Shutting down')
    conn.close()
    exit()  


def scanner(command):
    global status
    global speed
    global enableMotor
    command = re.split('(\d+)',command)
    command = list(filter(None, command))
    if command[0] == 'shutdown':
        shutdown()
    elif len(command) == 2:
        cmdType = command[0]
        cmdVal = int(command[1])
        if cmdType.lower() == 'block': # command to check if the next block is available
            '''
            while True:
                advance = nextBlockClear(cmdVal)
                if advance == 0: # the next block is not clear
                    print('waiting')
                    hold(True)
                    time.sleep(1)
                else:
                    hold(False)
                    break
            '''
            advanceBlock(cmdVal) # replaces above code with a function that can be utilized elsewhere!
        elif cmdType.lower() == 'speed': # command to change speed
            print('Setting Speed')
            setSpeed(cmdVal)

        elif cmdType.lower() == 'prop': # change a prop state from 0 (off) to 1 (on) in the database
            print('Prop')
            activateProp(cmdVal)
        elif cmdType.lower() == 'resume':
            print('Resuming')
            hold(False)
            setSpeed(cmdVal)
        else:
            print("Unrecognized command")
    else:
        print('Improper command format')
        shutdown()

ON_POSIX = 'posix' in sys.builtin_module_names
def enqueue_output(out, queue):
    for line in iter(out.readline, b''):
        queue.put(line)
    out.close()
p = Popen(stdout=PIPE, bufsize=1, close_fds=ON_POSIX)
q = Queue()
t = Thread(target=enqueue_output, args=(p.stdout, q))
t.daemon = True # thread dies with the program
t.start()



def loop():
    server_state = ping(db_address)
    if server_state == 0:
        # good, server is up!
        try:
            line = q.get_nowait() # or q.get(timeout=.1)
        except Empty:
            pass

        else:
            try:
                scanner(line)
            except mariadb.Error as e:
                print(f'Unable to access MariaDB: {e}')
                print()
                print('Terminating')
                shutdown()
            except Exception as e:
                print(f'Exception encountered: {e}')
    else:
        print('SERVER IS NOT REACHABLE')
        localeStop(True)



if __name__ == "__main__":
    rideStart()
    while True:
        loop()