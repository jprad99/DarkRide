import sys


from PyQt5.QtCore import Qt

#import PyQt5.QtSql

from PyQt5.QtSql import QSqlDatabase, QSqlTableModel

from PyQt5.QtWidgets import (

    QApplication,

    QMainWindow,

    QMessageBox,

    QTableView,

)


class Contacts(QMainWindow):

    def __init__(self, parent=None):

        super().__init__(parent)

        self.setWindowTitle("QTableView Example")

        self.resize(415, 200)

        # Set up the model

        self.model = QSqlTableModel(self)

        self.model.setTable("contacts")

        self.model.setEditStrategy(QSqlTableModel.OnFieldChange)

        self.model.setHeaderData(0, Qt.Horizontal, "ID")

        self.model.setHeaderData(1, Qt.Horizontal, "Name")

        self.model.setHeaderData(2, Qt.Horizontal, "Job")

        self.model.setHeaderData(3, Qt.Horizontal, "Email")

        self.model.select()

        # Set up the view

        self.view = QTableView()

        self.view.setModel(self.model)

        self.view.resizeColumnsToContents()

        self.setCentralWidget(self.view)


def createConnection():

    db = QSqlDatabase.addDatabase("QMYSQL")
    db.setHostName("localhost")
    db.setDatabaseName("DarkRide")
    db.setPort(5575) # int
    db.setUserName("python")
    db.setPassword("python")


    if not db.open():

        QMessageBox.critical(

            None,

            "QTableView Example - Error!",

            "Database Error: %s" % db.lastError().databaseText(),

        )

        return False

    return True


app = QApplication(sys.argv)

if not createConnection():

    sys.exit(1)

win = Contacts()

win.show()

sys.exit(app.exec_())