from tkinter import *
import pandas as pd
import sqlalchemy
engine = sqlalchemy.create_engine("mariadb+mariadbconnector://remote:remote@darkrideserver:3306/DarkRide")
class Table:
      
    def __init__(self,root):
          
        # code for creating table
        for i in range(total_rows):
            for j in range(total_columns):
                  
                self.e = Entry(root, width=10, fg='blue',
                               font=('Arial',16,'bold'))
                  
                self.e.grid(row=i, column=j)
                self.e.insert(END, df[i][j])
  

# take the data

df = pd.read_sql_table('vehicles', engine)
df = df.values.tolist()

def updateTable():
    df = pd.read_sql_table('vehicles', engine)
    df = df.values.tolist()
    root.pack()
    root.update()
    root.after(500, updateTable)
   
# find total number of rows and
# columns in list
total_rows = len(df)
total_columns = len(df[0])
   
# create root window
root = Tk()
t = Table(root)
root.after(500, updateTable)
root.mainloop()