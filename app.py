# streamlit_app.py
import mariadb
import streamlit as st
import pandas as pd
import sqlalchemy
from sqlalchemy.ext.declarative import declarative_base
import time


# Initialize connection.
# Uses st.cache to only run once.
@st.cache(allow_output_mutation=True, hash_funcs={"_thread.RLock": lambda _: None})
def init_connection():
    return mariadb.connect(user="remote",
                password="remote",
                host="darkrideserver",
                port=3306,
                database="DarkRide",
            )

conn = init_connection()

# Perform query.
# Uses st.cache to only rerun when the query changes or after 10 min.
#@st.cache(ttl=600)

engine = sqlalchemy.create_engine("mariadb+mariadbconnector://remote:remote@darkrideserver:3306/DarkRide")
# Print results.

def commandHandler():
    print('Hello')


sqltable = st.empty()
df = pd.read_sql('vehicles', engine)
sqltable.table(df)
command = st.text_input('COMMAND INPUT',on_change=commandHandler())

while True:
    time.sleep(0.5)
    df = pd.read_sql_table('vehicles', engine)
    sqltable.table(df)