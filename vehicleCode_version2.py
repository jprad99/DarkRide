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
#   Version 2.2.1

smc_port = "/dev/ttyACM0"
baud_rate = 9600  # Standard for SMC G2
device_number = None  # Typically not used, here for future
db_address = "darkrideserver" # Where the MariaDB is!
runWithoutSMC = True


# IMPORTS
import socket  # to retrieve IP Address
import signal  # to process SIGTERM and other OS Signals for clean shutdown
import os
from sqlite3 import InterfaceError  # prereq
import sys  # prereq
import pyfiglet  # create logo at beginning of terminal, purely cosmetic
import time  # for sleep
import mariadb  # database connector
import threading  # run background processes to check ESTOP and other
from multiprocessing import Process, set_forkserver_preload
import subprocess
from subprocess import PIPE, Popen
from threading import Thread
import re  # regular expression
import serial  # For comms with the SMC G2 via USB/Serial
from queue import Queue, Empty
import asyncio
import aioconsole
import platform
import time

# CREATE ASCII LOGO FOR TERMINAL
logo = pyfiglet.figlet_format("  Modular\nDark Ride", font="slant")

# GLOBAL VARIABLES
global status
global vehicle
global eStop
global enableMotor
global currentBlock
global speed

# MOTOR CONTROLLER
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
        self.send_command(cmd, int(abs(speed)) & 0x1F, int(speed) >> 5 & 0x7F)

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


class virtualSMC(object):  # Create a virtual version of the SMC for testing without motor control
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

class vehicle(object):
    global cur
    global conn
    global smc
    def __init__(self, vehicleID):
        self.vehicleID = vehicleID
        # CONNECT TO THE DATABASE
        try:
            global conn
            conn = mariadb.connect(
                user="remote",
                password="remote",
                host=db_address,
                port=3306,
                database="DarkRide",
            )
            print("Connection Successful")
        except mariadb.Error as e:
            # if the system is unable to connect to the database
            print(f"Error connecting to MariaDB Platform: {e}")
            print()
            print("Terminating Process")
            exit()
        global cur
        cur = conn.cursor()  # create cursor object

        # CREATE MOTOR CONTROLLER OBJECT
        try:
            global smc
            if runWithoutSMC == True:
                smc = virtualSMC()
            else:
                port = serial.Serial(smc_port, baud_rate, timeout=0.1, write_timeout=0.1)
                smc = SmcG2Serial(port, device_number)
        except Exception as E:
            print(
                "SMC Controller Not Found on Port "
                + smc_port
                + "\nPlease Check Connection"
            )
            print()
            print("System Error Message:")
            print(E)
            print()
            self.updateStatus("SMC Error")
            quit()
        # TELL DATABASE OUR IP
        import socket
        hostname = socket.getfqdn()
        ipAddress = socket.gethostbyname_ex(hostname)[2][0]
        print(ipAddress)
        cur.execute("UPDATE vehicles SET IP = %s WHERE vehicleID=%d" %(("'"+ipAddress+"'"),int(self.vehicleID)))
        conn.commit()
        
        # UPDATE STATUS ON DATABASE
        self.updateStatus("Initializing")
        print(logo)

        # LEARN WHERE THE VEHICLE WAS AT POWER DOWN
        cur.execute("SELECT block FROM vehicles WHERE vehicleID = %s" % (self.vehicleID))
        self.currentBlock = cur.fetchall()[0][0]
        conn.commit()
        # SPEED PRIOR TO POWER LOSS
        cur.execute("SELECT speed FROM vehicles WHERE vehicleID = %s" % (self.vehicleID))
        rawSpeed = cur.fetchall()[0][0]
        self.speed = rawSpeed // 32
        conn.commit()

        # Put vehicle into an ESTOP to wait for the all clear
        self.estop(True,"Waiting For Start!")
        self.checkStops()

    # HANDLE ESTOP COMMANDS
    def estop(self, estop, cause="ESTOP"):
        self.localStop = estop
        if estop == True:
            smc.stop_motor()
            try:
                self.updateStatus(cause)
            except:
                pass
        elif estop == False:
            smc.exit_safe_start()
            try:
                self.updateStatus("Resume From ESTOP")
            except:
                pass
        try:
            cur.execute("UPDATE vehicles SET estop = %s WHERE vehicleID = %d" %(estop,int(self.vehicleID)))
            conn.commit()
        except:
            print('Unable to reach the server! Vehicle will be in safe stop violation!')
            smc.stop_motor()

    # HOLD POSITION (BUT NOT ESTOP)
    def hold(self, hold, dur = None, resumeSpeed = 10):
        if hold == True:
            resumeSpeed = self.speed
            self.setSpeed(0)
            self.updateStatus("Holding")
        elif hold == False:
            self.setSpeed(resumeSpeed)
            self.updateStatus("Resumed From Hold")
        if dur is not None:
            time.sleep(dur)
            self.setSpeed(resumeSpeed)
            self.updateStatus(f'Resumed From Timed {dur}s Hold')

    def updateStatus(self, status):
        cur.execute("UPDATE vehicles SET Status = %s WHERE vehicleID=%d" %(("'"+str(status)+"'"),int(self.vehicleID)))
        conn.commit()

    # SPEED CONTROL
    def setSpeed(self,speedPercent):
        if -100<=speedPercent<=100:
            self.speed = speedPercent*32
            smc.set_target_speed(self.speed)
            cur.execute("UPDATE vehicles SET speed = %s WHERE vehicleID=%d" %(self.speed,int(self.vehicleID)))
            conn.commit()
        else:
            print(f'Improper Speed of {speedPercent}%')
            print('Activating ESTOP')
            self.estop(True,'Speed Input Error')
    
    # CHECK NEXT BLOCK
    def nextBlockClear(self, newBlock):
        newBlock = int(newBlock)
        cur.execute("SELECT Block FROM vehicles WHERE Block = %s" %(newBlock))
        occupant = cur.fetchall() #strip down result to the desired value
        QtyInBlock = len(occupant)
        #print(QtyInBlock)
        if QtyInBlock == 0:
            cur.execute("UPDATE vehicles SET Block = %s WHERE vehicleID=%d" %(newBlock,int(self.vehicleID)))
            advance = 1
        else:
            advance = 0
        conn.commit()
        return advance

    # MOVE TO THE NEXT BLOCK
    def advanceBlock(self, block):
        blockHeld = False
        advance = self.nextBlockClear(block)
        if advance == 0:
            self.hold(True)
            blockHeld = True
        while advance == 0: # the next block is not clear
            advance = self.nextBlockClear(block)
            #wait for the all clear
            #print("Waiting For Block")
            time.sleep(1)
        if blockHeld == True:
            self.hold(False)
    # RECEIVE INPUT AND PROCESS IT
    def checkStops(self):
        cur.execute("SELECT estop FROM vehicles WHERE NOT (vehicleID =%d)" %(int(self.vehicleID)))
        res = cur.fetchall()
        remoteStops = []
        for i in range(len(res)):
            remoteStops.append(res[i][0])
        conn.commit()
        #print(remoteStops)
        if 1 in remoteStops:
            self.networkStop = True
        else:
            self.networkStop = False
        return self.networkStop


    def updateTime(self):
        cur_time = time.strftime("%H:%M:%S", time.localtime())
        cur.execute("UPDATE vehicles SET Time = %s WHERE vehicleID=%d" %(("'"+str(cur_time)+"'"),int(self.vehicleID)))
        conn.commit()
    def handleCommand(self, cmd):
        cmd = cmd.split()
        cmd = list(filter(None,cmd))
        if not cmd:
            pass
        elif cmd[0] == 'shutdown':
            self.shutdown()
        elif cmd[0] == 'c':
            self.checkStops()
        elif len(cmd) == 2:
            cmdType = cmd[0]
            cmdVal = int(cmd[1])
            if cmdType.lower() == 'block': # command to check if the next block is available
                self.advanceBlock(cmdVal) # replaces above code with a function that can be utilized elsewhere!
            elif cmdType.lower() == 'speed': # command to change speed
                print('Setting Speed')
                self.setSpeed(cmdVal)
            elif cmdType.lower() == 'hold':
                self.hold(True,cmdVal)
            elif cmdType.lower() == 'estop':
                if cmdVal == 1:
                    self.estop(True, 'Scan')
                if cmdVal == 0:
                    self.estop(False)
            elif cmdType.lower() == 'resume':
                print('Resuming From Scan')
                self.estop(False, 'Scanned Out of ESTOP')
                self.setSpeed(cmdVal)
            else:
                print("Unrecognized command")
        else:
            print('Improper command format')
            self.estop(True,'Scan Format Error')

    # SHUTDOWN PROCEDURE
    def shutdown(self):
        smc.stop_motor()
        self.updateStatus("OFFLINE")
        os._exit(1)

def vehicleLoop():
    global ride
    global cur
    networkStop = False
    while True:
        try:
            try:
                conn.ping()
            except mariadb.DatabaseError:
                conn.reconnect()
            if ride.checkStops(): # Should be estopped
                smc.stop_motor()
                ride.updateStatus('Network ESTOP')
                networkStop = True
            else: # can exit estop if local estop is clear
                if (networkStop == True) and (ride.localStop == False):
                    networkStop = False
                    smc.exit_safe_start()
                    ride.updateStatus('Resume from Network ESTOP')
            try:
                cmd = q.get_nowait()
                ride.handleCommand(cmd)
                q.task_done()
            except Empty:
                try:
                    time.sleep(0.5)
                    ride.updateTime()
                except mariadb.Error as e:
                    print(f'encountered error with database: {e}')
                    ride.estop(True, 'Database Error')
        except mariadb.Error as e: # Catches almost all mariadb errors
            print(f'encountered error with database: {e}')
            print('For safety, activating estop')
            ride.estop(True, 'Database Error')
            time.sleep(10)
        #print('LOOPED')


def main():
    global ride
    ride = vehicle(1)
    print(ride.speed)
    time.sleep(3)
    global q
    global t
    q = Queue()
    t = Thread(target=vehicleLoop)
    t.daemon = True # thread dies with the program
    t.start()

    while True:
        lineIn = input("Enter Command: ")
        q.put(lineIn)

main()