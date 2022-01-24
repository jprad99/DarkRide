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
engine = sqlalchemy.create_engine("mariadb+mariadbconnector://remote:remote@darkrideserver:3306/DarkRide")

app = Flask(__name__)
turbo = Turbo(app)


@app.context_processor
def inject_load():
    data = pd.read_sql_table('vehicles', engine)
    data = data.to_dict()
    color = f'{random.randint(0,255)}, {random.randint(0,255)}, {random.randint(0,255)}'
    return {'SQLData':data, 'COLOR':color}


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/submit/', methods = ['POST', 'GET'])
def data():
    if request.method == 'GET':
        return f"The URL /data is only used to post data"
    if request.method == 'POST':
        form_data = request.form
        print(form_data)
        return redirect(url_for('index'))

@app.before_first_request
def before_first_request():
    threading.Thread(target=update_load).start()


def update_load():
    with app.app_context():
        while True:
            time.sleep(1)
            turbo.push(turbo.replace(render_template('ridetable.html'),'load'))
            turbo.push(turbo.replace(render_template('estop.html'),'estop'))

if __name__ == "__main__":
    app.run(host='0.0.0.0',debug=True,port=5000)