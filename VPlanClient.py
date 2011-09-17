#!/usr/bin/env python3.2
# -*- coding: utf-8 -*-
import sys, time, random, datetime
from PyQt4 import QtCore, QtGui
from PyQt4.QtCore import QObject, pyqtSignal, pyqtSlot
from Ui_VPlanClient import *
from Printer import Printer

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    _fromUtf8 = lambda s: s

class VPlanData(QtCore.QThread):
    actionData = pyqtSignal(bool, str, str, str, str, str, str, str, str, str, str) 

    def __init__(self, VPlanClient, parent = None):
        #QtCore.QThread.__init__(self, parent)
        super(VPlanData, self).__init__(parent)
        self.exiting = False
        self.client = VPlanClient
        
        self.actionData.connect(self.client.slotAddData)
        
    def __del__(self):
        self.exiting = True
        self.wait()

    def run(self):
        while not self.exiting:
            time.sleep(2)
            stufe = random.randint(11,13)
            classes = random.randint(1,12)
            withHeader = False

            if classes%2:
                withHeader = True

            self.actionData.emit(
                    withHeader,
                    '13/2',
                    '2',
                    'FUEL',
                    'GESC',
                    'A104',
                    'SCHM',
                    'DEUT',
                    'A310',
                    'Nothing',
                    'todo'
                    )


class VPlanClient(QtGui.QMainWindow):
    def __init__(self, app):
        QtGui.QMainWindow.__init__(self)
        self.app = app
        self.ui = Ui_VPlanClient(self, app)
        self.maxrows = 15
        self.calcMaximumRows()
        self.setTodayDate()
        
        #window.showFullScreen()
        self.thread = VPlanData(self)
        self.showFullScreen()
        self.thread.start()

    def setTodayDate(self):
        date = datetime.date.today()
        datef = date.strftime('%d.%m.%Y')
        self.ui.datetime.setText(datef)

    def calcMaximumRows(self):
        # header height: 
        rowHeight = self.ui.vplantable.rowHeight(0)
        tableHeight = self.ui.vplantable.height()

        self.maxrows = int(tableHeight/rowHeight)-2
    
    @pyqtSlot(bool, str,str,str,str,str,str,str,str,str,str)
    def slotAddData(self, withHeader, classes, std, teacher, subject, room, vteacher, vsubject, vroom, notice, info):
        # remove first
        if withHeader:
            newRows = 2
        else:
            newRows = 1

        while self.maxrows <= self.ui.vplantable.rowCount()+newRows and newRows > 0:
            print('Remove row: 0, %s :  %s ' % (self.maxrows, self.ui.vplantable.rowCount()+newRows))
            self.ui.vplantable.removeRow(0)
            newRows -= 1

        print('Adding data... %s Rows' % self.ui.vplantable.rowCount())

        # header ?
        if withHeader:
            self.ui.vplantable.insertRow(self.ui.vplantable.rowCount())
            # DATA - HEADER
            item = QtGui.QTableWidgetItem()
            item.setText("Klasse: %s" % classes)
            brush = QtGui.QBrush(QtGui.QColor(211, 211, 211))
            item.setBackground(brush)
            item.setFlags(QtCore.Qt.ItemIsEnabled)
            font = QtGui.QFont()
            font.setBold(True)
            item.setFont(font)
            self.ui.vplantable.setItem(self.ui.vplantable.rowCount(), 0, item)
            # now set the colspan
            self.ui.vplantable.setSpan(self.ui.vplantable.rowCount(), 0, 1, 9)


        # now we add something.
        self.ui.vplantable.insertRow(self.ui.vplantable.rowCount())
        print('Added row ... %s Rows' % self.ui.vplantable.rowCount())


        # DATA
        # std
        item = QtGui.QTableWidgetItem()
        item.setText(std)
        item.setFlags(QtCore.Qt.ItemIsEnabled)
        self.ui.vplantable.setItem(self.ui.vplantable.rowCount(), 0, item)

        # Teacher
        item = QtGui.QTableWidgetItem()
        item.setText(teacher)
        item.setFlags(QtCore.Qt.ItemIsEnabled)
        self.ui.vplantable.setItem(self.ui.vplantable.rowCount(), 1, item)

        # Subject
        item = QtGui.QTableWidgetItem()
        item.setText(subject)
        item.setFlags(QtCore.Qt.ItemIsEnabled)
        self.ui.vplantable.setItem(self.ui.vplantable.rowCount(), 2, item)

        # room
        item = QtGui.QTableWidgetItem()
        item.setText(room)
        item.setFlags(QtCore.Qt.ItemIsEnabled)
        self.ui.vplantable.setItem(self.ui.vplantable.rowCount(), 3, item)

        # vteacher
        item = QtGui.QTableWidgetItem()
        item.setText(vteacher)
        item.setFlags(QtCore.Qt.ItemIsEnabled)
        self.ui.vplantable.setItem(self.ui.vplantable.rowCount(), 4, item)

        # vsubject
        item = QtGui.QTableWidgetItem()
        item.setText(vsubject)
        item.setFlags(QtCore.Qt.ItemIsEnabled)
        self.ui.vplantable.setItem(self.ui.vplantable.rowCount(), 5, item)

        # vroom
        item = QtGui.QTableWidgetItem()
        item.setText(vroom)
        item.setFlags(QtCore.Qt.ItemIsEnabled)
        self.ui.vplantable.setItem(self.ui.vplantable.rowCount(), 6, item)

        # notice
        item = QtGui.QTableWidgetItem()
        item.setText(notice)
        item.setFlags(QtCore.Qt.ItemIsEnabled)
        self.ui.vplantable.setItem(self.ui.vplantable.rowCount(), 7, item)
 
        # info
        item = QtGui.QTableWidgetItem()
        item.setText(info)
        item.setFlags(QtCore.Qt.ItemIsEnabled)
        self.ui.vplantable.setItem(self.ui.vplantable.rowCount(), 8, item)

    @pyqtSlot()
    def slotQuit(self):
        print('He wants to quit...')

app = QtGui.QApplication(sys.argv)
app.setApplicationName('FLS Vertretungsplaner')
app.setApplicationVersion('0.1 Alpha')
app.setOrganizationName('Friedrich-List-Schule Wiesbaden')
app.setOrganizationDomain('fls-wiesbaden.de') 
vp = VPlanClient(app)

#
sys.exit(app.exec_())
