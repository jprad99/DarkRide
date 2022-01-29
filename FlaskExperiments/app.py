import random
import re
import sys
import threading
import time
from flask import Flask, render_template, request
from flask.helpers import url_for
from turbo_flask import Turbo
import sqlalchemy
import pandas as pd
from werkzeug.utils import redirect
from queue import Queue, Empty
from multiprocessing import Process, set_forkserver_preload
import subprocess
from subprocess import PIPE, Popen
from threading import Thread
import mariadb

db_address = 'darkrideserver'

engine = sqlalchemy.create_engine("mariadb+mariadbconnector://remote:remote@darkrideserver:3306/DarkRide")

app = Flask(__name__)
turbo = Turbo(app)

global estop
global remotestop
estop = False
remotestop = False

@app.context_processor
def inject_load():
    data = pd.read_sql_table('vehicles', engine)
    data = data.sort_values(by=['VehicleID'])

    data = data.to_dict()

    if estop == True:
        localColor = '255,0,0'
    else:
        localColor = '4,120,28'
    if remotestop == True:
        networkColor = '255,0,0'
    else:
        networkColor = '4,120,28'
    return {'SQLData':data, 'localestop':localColor, 'networkestop':networkColor, 'ESTOP' : estop}


@app.route('/')
def index():
    return render_template('index.html.j2')

@app.route('/submit/', methods = ['POST', 'GET'])
def data():
    if request.method == 'GET':
        return f"The URL /data is only used to post data"
    if request.method == 'POST':
        command = request.form['Command']
        loopQ.put(command)
        return redirect(url_for('index'))

@app.before_first_request
def before_first_request():
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
    
    global loopQ
    loopQ = Queue()
    t = Thread(target=stationLoop)
    t.daemon = True # thread dies with the program
    t.start()

'''
def update_load():
    with app.app_context():
        while True:
            time.sleep(1)
            turbo.push(turbo.replace(render_template('ridetable.html.j2'),'load'))
            turbo.push(turbo.replace(render_template('estop.html.j2'),'estop'))
'''


def cmdHandler(cmd):
    global estop
    cmd = cmd.split()
    if cmd[0].lower() == 'estop':
        if cmd[1].lower() == 'on':
            print('estop on')
            estop = True
        elif cmd[1].lower() == 'off':
            print('estop off')
            estop = False
        else:
            print(cmd[1])

def serverComms():
    global estop
    cur.execute("SELECT estop FROM vehicles WHERE NOT (vehicleID = Station)")
    res = cur.fetchall()
    remoteStops = []
    for i in range(len(res)):
        remoteStops.append(res[i][0])
    conn.commit()
    #print(remoteStops)
    if 1 in remoteStops:
        estop = True

def stationLoop():
    while True:
        time.sleep(0.5)
        try:
            cmd = loopQ.get_nowait()
            cmdHandler(cmd)
            loopQ.task_done()
        except Empty:
            time.sleep(0.5)
        finally:
            with app.app_context():
                turbo.push(turbo.replace(render_template('ridetable.html.j2'),'load'))
                turbo.push(turbo.replace(render_template('estop.html.j2'),'estop'))


if __name__ == "__main__":
    app.run(host='0.0.0.0',debug=True,port=5000)