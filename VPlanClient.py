#!/usr/bin/env python3.2
# -*- coding: utf-8 -*-
import sys
from PyQt4 import QtCore, QtGui
from PyQt4.QtCore import QObject, pyqtSignal, pyqtSlot
from Ui_VPlanClient import *

class VPlanClient(QtGui.QMainWindow):
    def __init__(self, app):
        QtGui.QMainWindow.__init__(self)
        self.app = app
        self.ui = Ui_VPlanClient(self, app)
        
        # connect quit-slot
        self.connect(self.ui.actionQuit, QtCore.SIGNAL('triggered()'), self.slotQuit)

        #window.showFullScreen()
        self.show()

    def slotQuit(self):
        print('He wants to quit...')

app = QtGui.QApplication(sys.argv)
app.setApplicationName('FLS Vertretungsplaner')
app.setApplicationVersion('0.1 Alpha')
app.setOrganizationName('Friedrich-List-Schule Wiesbaden')
app.setOrganizationDomain('fls-wiesbaden.de') 
vp = VPlanClient(app)

# now we add something.
#ui.vplantable.setRowCount(ui.vplantable.rowCount()+1)
#item = QtGui.QTableWidgetItem()
#item.setText(QtGui.QApplication.translate("VPlanClient", "13/2-Data-1", None, QtGui.QApplication.UnicodeUTF8))
#ui.vplantable.setVerticalHeaderItem(ui.vplantable.rowCount(), item)
#
# DATA 13/2
#item = QtGui.QTableWidgetItem()
#item.setText(QtGui.QApplication.translate("VPlanClient", "8", None, QtGui.QApplication.UnicodeUTF8))
#item.setFlags(QtCore.Qt.ItemIsEnabled)
#ui.vplantable.setItem(ui.vplantable.rowCount(), 0, item)
#item = QtGui.QTableWidgetItem()
#item.setText(QtGui.QApplication.translate("VPlanClient", "TEST", None, QtGui.QApplication.UnicodeUTF8))
#item.setFlags(QtCore.Qt.ItemIsEnabled)
#ui.vplantable.setItem(ui.vplantable.rowCount(), 1, item)
#item = QtGui.QTableWidgetItem()
#item.setText(QtGui.QApplication.translate("VPlanClient", "A203", None, QtGui.QApplication.UnicodeUTF8))
#item.setFlags(QtCore.Qt.ItemIsEnabled)
#ui.vplantable.setItem(ui.vplantable.rowCount(), 2, item)
#item = QtGui.QTableWidgetItem()
#item.setFlags(QtCore.Qt.ItemIsEnabled)
#ui.vplantable.setItem(ui.vplantable.rowCount(), 3, item)
#item = QtGui.QTableWidgetItem()
#item.setFlags(QtCore.Qt.ItemIsEnabled)
#ui.vplantable.setItem(ui.vplantable.rowCount(), 4, item)
#item = QtGui.QTableWidgetItem()
#item.setText(QtGui.QApplication.translate("VPlanClient", "Frei", None, QtGui.QApplication.UnicodeUTF8))
#item.setFlags(QtCore.Qt.ItemIsEnabled)
#ui.vplantable.setItem(ui.vplantable.rowCount(), 5, item)
#item = QtGui.QTableWidgetItem()
#item.setText(QtGui.QApplication.translate("VPlanClient", "in die Betriebe", None, QtGui.QApplication.UnicodeUTF8))
#item.setFlags(QtCore.Qt.ItemIsEnabled)
#ui.vplantable.setItem(ui.vplantable.rowCount(), 6, item)
#
#ui.vplantable.update()
#
sys.exit(app.exec_())
