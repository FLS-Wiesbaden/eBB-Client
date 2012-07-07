#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from browser import *
from Printer import Printer
from PyQt4.QtCore import QObject, pyqtSignal, pyqtSlot
import sys

class VPlanMainWindow(QtGui.QMainWindow):
    def __init__(self):
        QtGui.QMainWindow.__init__(self)

        self.exit = QtGui.QAction(QtGui.QIcon(''), 'Verlassen', self)
        self.exit.setShortcut('Ctrl+Q')
        self.exit.setStatusTip('Vertretungsplan Client verlassen')
        self.connect(self.exit, QtCore.SIGNAL('triggered()'), QtCore.SLOT('close()')) 

        self.addAction(self.exit)

        self.fullScreen = QtGui.QAction(QtGui.QIcon(''), 'Vollbild an/aus', self)
        self.fullScreen.setShortcut('F11')
        self.fullScreen.setStatusTip('Vollbildmodus an/aus')
        self.connect(self.fullScreen, QtCore.SIGNAL('triggered()'), QtCore.SLOT('toggleScreen()'))

        self.addAction(self.fullScreen)

    def setActions(self):
        self.actReload = QtGui.QAction(QtGui.QIcon(''), 'Neuladen', self)
        self.actReload.setAutoRepeat(False)
        self.actReload.setShortcut('F5')
        self.actReload.setStatusTip('Neuladen')
        self.connect(self.actReload, QtCore.SIGNAL('triggered()'), self.ui.webView.reload)

        self.addAction(self.actReload)

    @pyqtSlot()
    def toggleScreen(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def setUi(self, ui):
        self.ui = ui

app = QtGui.QApplication(sys.argv)
MainWindow = VPlanMainWindow()
ui = Ui_MainWindow()
ui.setupUi(MainWindow)
MainWindow.setUi(ui)
MainWindow.setActions()
MainWindow.showFullScreen()
sys.exit(app.exec_())
