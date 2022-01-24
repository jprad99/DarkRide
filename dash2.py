# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'main.ui'
#
# Created by: PyQt5 UI code generator 5.11.3
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QTableWidgetItem
import mariadb

try:
    conn = mariadb.connect(
        user="remote",
        password="remote",
        host="darkrideserver",
        port=3306,
        database="DarkRide"
    )
    print("Connection Successful")
except mariadb.Error as e:
    print(f"Error connecting to MariaDB Platform: {e}")
    print()
    print("Terminating Process")
    exit()
cur = conn.cursor()

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        self.checkThreadTimer = QtCore.QTimer()
        self.checkThreadTimer.setInterval(500) #.5 seconds
        self.checkThreadTimer.start()
        self.checkThreadTimer.timeout.connect(self.populateTable)

        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(1099, 600)
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.table = QtWidgets.QTableWidget(self.centralwidget)
        self.table.setGeometry(QtCore.QRect(0, 0, 921, 501))
        self.table.setMinimumSize(QtCore.QSize(0, 0))
        self.table.setLineWidth(1)
        self.table.setIconSize(QtCore.QSize(0, 0))
        self.table.setShowGrid(True)
        self.table.setCornerButtonEnabled(True)
        self.table.setRowCount(10)
        self.table.setColumnCount(7)
        self.table.setObjectName("table")
        self.table.horizontalHeader().setDefaultSectionSize(125)
        self.table.horizontalHeader().setMinimumSectionSize(30)
        self.table.verticalHeader().setCascadingSectionResizes(True)
        self.table.verticalHeader().setDefaultSectionSize(40)
        self.table.setHorizontalHeaderLabels(['Vehicle ID','Block','Speed','Enable','Status','IP Address','Dispatch'])
        self.command = QtWidgets.QLineEdit(self.centralwidget)
        self.command.setGeometry(QtCore.QRect(30, 520, 841, 41))
        self.command.setText("")
        self.command.setObjectName("command")
        self.execute = QtWidgets.QPushButton(self.centralwidget)
        self.execute.setGeometry(QtCore.QRect(880, 530, 93, 28))
        self.execute.setObjectName("execute")
        self.load = QtWidgets.QPushButton(self.centralwidget)
        self.load.setGeometry(QtCore.QRect(960, 170, 111, 101))
        self.load.setObjectName("load")
        self.unload = QtWidgets.QPushButton(self.centralwidget)
        self.unload.setGeometry(QtCore.QRect(960, 300, 111, 101))
        self.unload.setObjectName("unload")
        self.estop = QtWidgets.QPushButton(self.centralwidget)
        self.estop.setGeometry(QtCore.QRect(930, 10, 161, 81))
        self.estop.setObjectName("estop")
        self.estop.setCheckable(True)
        self.ErrorDisplay = QtWidgets.QTextBrowser(self.centralwidget)
        self.ErrorDisplay.setGeometry(QtCore.QRect(925, 410, 171, 51))
        self.ErrorDisplay.setObjectName("ErrorDisplay")
        self.estop_notice = QtWidgets.QTextBrowser(self.centralwidget)
        self.estop_notice.setGeometry(QtCore.QRect(940, 90, 141, 31))
        self.estop_notice.setObjectName("estop_notice")
        MainWindow.setCentralWidget(self.centralwidget)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

        self.estop.setStyleSheet("background-color: red")
        self.unload.setStyleSheet("background-color: orange")
        self.load.setStyleSheet("background-color: green")
        self.estop.clicked.connect(self.emgstop)
        self.load.clicked.connect(self.dispatchLoad)
        self.table.verticalHeader().setVisible(False)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "Dark Ride Controls Panel"))
        self.execute.setText(_translate("MainWindow", "Execute"))
        self.load.setText(_translate("MainWindow", "Dispatch Load"))
        self.unload.setText(_translate("MainWindow", "Dispatch Unload"))
        self.estop.setText(_translate("MainWindow", "EMERGENCY"))

    def populateTable(self):
        cur.execute("SELECT * FROM vehicles ORDER BY vehicleID")
        result = cur.fetchall()
        self.table.setRowCount(0)
        for row_number, row_data in enumerate(result):
            #print(row_number)
            self.table.insertRow(row_number)
            for column_number, data in enumerate(row_data):
                #print(column_number)
                self.table.setItem(row_number, column_number, QTableWidgetItem(str(data)))
        conn.commit()

    def emgstop(self):
        print('ESTOP')
        
        if self.estop.isChecked():
            cur.execute("UPDATE vehicles SET MotorEnable = 0 WHERE vehicleID = 0")
            self.estop_notice.setText("ESTOP ON")
        else:
            cur.execute("UPDATE vehicles SET MotorEnable = 1 WHERE vehicleID = 0")
            self.estop_notice.setText("ESTOP OFF")
        conn.commit()

    def dispatchLoad(self):
        cur.execute("SELECT vehicleID FROM vehicles WHERE location = '1'")
        result = cur.fetchall()
        print(result)
        if len(result) == 0:
            cur.execute("UPDATE vehicles SET dispatch = 'GO' WHERE location = 'Loading'")
        conn.commit()

if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    MainWindow = QtWidgets.QMainWindow()
    ui = Ui_MainWindow()
    ui.setupUi(MainWindow)
    MainWindow.show()
    sys.exit(app.exec_())

