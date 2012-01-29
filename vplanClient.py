#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from browser import *
import sys

class VPlanMainWindow(QtGui.QMainWindow):
    def __init__(self):
        QtGui.QMainWindow.__init__(self)

        self.exit = QtGui.QAction(QtGui.QIcon(''), 'Verlassen', self)
        self.exit.setShortcut('Ctrl+Q')
        self.exit.setStatusTip('Vertretungsplan Client verlassen')
        self.connect(self.exit, QtCore.SIGNAL('triggered()'), QtCore.SLOT('close()')) 

        self.addAction(self.exit)

app = QtGui.QApplication(sys.argv)
MainWindow = VPlanMainWindow()
ui = Ui_MainWindow()
ui.setupUi(MainWindow)
#MainWindow.show()
MainWindow.showFullScreen()
sys.exit(app.exec_())
