# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'vplan.ui'
#
# Created: Sun Sep 11 17:16:19 2011
#      by: PyQt4 UI code generator 4.8.5
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui
from PyQt4.QtCore import QObject, pyqtSignal, pyqtSlot

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    _fromUtf8 = lambda s: s

class Ui_VPlanClient():
    def __init__(self, vplan, app):
        self.VPlanClient = vplan
        self.app = app
        self.stylesheetDesign = {
                'wb': _fromUtf8("color: rgb(255, 255, 255);\nbackground-color: rgb(91, 126, 166);"), # white on blue
                }
        self.setupUi(self.VPlanClient)

    def setupUi(self, VPlanClient):
        VPlanClient.setObjectName(_fromUtf8("VPlanClient"))
        #Fullsize
        desktop = QtGui.QApplication.desktop()
        desktop_size = desktop.availableGeometry()
        maxWidth = desktop_size.width()
        maxHeight = desktop_size.height()
        VPlanClient.resize(maxWidth, maxHeight)

        VPlanClient.setCursor(QtGui.QCursor(QtCore.Qt.CrossCursor))
        VPlanClient.setWindowTitle(QtGui.QApplication.translate("VPlanClient", "FLS Vertretungsplaner", None, QtGui.QApplication.UnicodeUTF8))
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(_fromUtf8("./fls_logo.ico")), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        VPlanClient.setWindowIcon(icon)
        VPlanClient.setStyleSheet(_fromUtf8(""))

        self.centralwidget = QtGui.QWidget(VPlanClient)
        self.centralwidget.setObjectName(_fromUtf8("centralwidget"))
        # now the table
        self.vplantable = QtGui.QTableWidget(self.centralwidget)
        self.vplantable.setGeometry(QtCore.QRect(0, 30, VPlanClient.size().width(), VPlanClient.size().height()))
        self.vplantable.setFrameShape(QtGui.QFrame.NoFrame)
        self.vplantable.setFrameShadow(QtGui.QFrame.Sunken)
        self.vplantable.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.vplantable.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.vplantable.setEditTriggers(QtGui.QAbstractItemView.NoEditTriggers)
        self.vplantable.setTabKeyNavigation(False)
        self.vplantable.setProperty("showDropIndicator", False)
        self.vplantable.setDragDropOverwriteMode(False)
        self.vplantable.setAlternatingRowColors(True)
        self.vplantable.setShowGrid(True)
        self.vplantable.setGridStyle(QtCore.Qt.DotLine)
        self.vplantable.setCornerButtonEnabled(False)
        self.vplantable.setObjectName(_fromUtf8("vplantable"))
        self.vplantable.setColumnCount(7)
        self.vplantable.setRowCount(7)
        #font = QtGui.QFont()
        #font.setPointSize(14)
        #self.vplantable.setFont(font)

        # COL Widths
        self.vplantable.setColumnWidth(0, 40)
        #self.vplantable.setColumnWidth(5, 150)
        #self.vplantable.setColumnWidth(6, 150)

        # DATA BEGIN
        # ROWS
        item = QtGui.QTableWidgetItem()
        item.setText(QtGui.QApplication.translate("VPlanClient", "12/1", None, QtGui.QApplication.UnicodeUTF8))
        self.vplantable.setVerticalHeaderItem(0, item)
        item = QtGui.QTableWidgetItem()
        item.setText(QtGui.QApplication.translate("VPlanClient", "12/1-Data", None, QtGui.QApplication.UnicodeUTF8))
        self.vplantable.setVerticalHeaderItem(1, item)
        item = QtGui.QTableWidgetItem()
        item.setText(QtGui.QApplication.translate("VPlanClient", "12/1-Data", None, QtGui.QApplication.UnicodeUTF8))
        self.vplantable.setVerticalHeaderItem(2, item)
        item = QtGui.QTableWidgetItem()
        item.setText(QtGui.QApplication.translate("VPlanClient", "13/1", None, QtGui.QApplication.UnicodeUTF8))
        self.vplantable.setVerticalHeaderItem(3, item)
        item = QtGui.QTableWidgetItem()
        item.setText(QtGui.QApplication.translate("VPlanClient", "13/1-Data", None, QtGui.QApplication.UnicodeUTF8))
        self.vplantable.setVerticalHeaderItem(4, item)
        item = QtGui.QTableWidgetItem()
        item.setText(QtGui.QApplication.translate("VPlanClient", "13/2", None, QtGui.QApplication.UnicodeUTF8))
        self.vplantable.setVerticalHeaderItem(5, item)
        item = QtGui.QTableWidgetItem()
        item.setText(QtGui.QApplication.translate("VPlanClient", "13/2-Data", None, QtGui.QApplication.UnicodeUTF8))
        self.vplantable.setVerticalHeaderItem(6, item)

        # COLS
        item = QtGui.QTableWidgetItem()
        item.setText(QtGui.QApplication.translate("VPlanClient", "Std", None, QtGui.QApplication.UnicodeUTF8))
        self.vplantable.setHorizontalHeaderItem(0, item)
        item = QtGui.QTableWidgetItem()
        item.setText(QtGui.QApplication.translate("VPlanClient", "Lehrer", None, QtGui.QApplication.UnicodeUTF8))
        self.vplantable.setHorizontalHeaderItem(1, item)
        item = QtGui.QTableWidgetItem()
        item.setText(QtGui.QApplication.translate("VPlanClient", "Raum", None, QtGui.QApplication.UnicodeUTF8))
        self.vplantable.setHorizontalHeaderItem(2, item)
        item = QtGui.QTableWidgetItem()
        item.setText(QtGui.QApplication.translate("VPlanClient", "VLehrer", None, QtGui.QApplication.UnicodeUTF8))
        self.vplantable.setHorizontalHeaderItem(3, item)
        item = QtGui.QTableWidgetItem()
        item.setText(QtGui.QApplication.translate("VPlanClient", "VRaum", None, QtGui.QApplication.UnicodeUTF8))
        self.vplantable.setHorizontalHeaderItem(4, item)
        item = QtGui.QTableWidgetItem()
        item.setText(QtGui.QApplication.translate("VPlanClient", "Merkmal", None, QtGui.QApplication.UnicodeUTF8))
        self.vplantable.setHorizontalHeaderItem(5, item)
        item = QtGui.QTableWidgetItem()
        item.setText(QtGui.QApplication.translate("VPlanClient", "Info", None, QtGui.QApplication.UnicodeUTF8))
        self.vplantable.setHorizontalHeaderItem(6, item)

        # DATA - HEADER
        item = QtGui.QTableWidgetItem()
        item.setText(QtGui.QApplication.translate("VPlanClient", "Klasse: 12/1", None, QtGui.QApplication.UnicodeUTF8))
        brush = QtGui.QBrush(QtGui.QColor(211, 211, 211))
        item.setBackground(brush)
        item.setFlags(QtCore.Qt.ItemIsEnabled)
        font = QtGui.QFont()
        font.setBold(True)
        item.setFont(font)
        #item.setStyleSheet(_fromUtf8("border: 1px solid #000000;"))
        self.vplantable.setItem(0, 0, item)
        # now set the colspan
        self.vplantable.setSpan(0, 0, 1, 7)

        # DATA 12/1
        item = QtGui.QTableWidgetItem()
        item.setText(QtGui.QApplication.translate("VPlanClient", "1", None, QtGui.QApplication.UnicodeUTF8))
        item.setFlags(QtCore.Qt.ItemIsEnabled)
        self.vplantable.setItem(1, 0, item)
        item = QtGui.QTableWidgetItem()
        item.setText(QtGui.QApplication.translate("VPlanClient", "MÜCK", None, QtGui.QApplication.UnicodeUTF8))
        item.setFlags(QtCore.Qt.ItemIsEnabled)
        self.vplantable.setItem(1, 1, item)
        item = QtGui.QTableWidgetItem()
        item.setText(QtGui.QApplication.translate("VPlanClient", "A102", None, QtGui.QApplication.UnicodeUTF8))
        item.setFlags(QtCore.Qt.ItemIsEnabled)
        self.vplantable.setItem(1, 2, item)
        item = QtGui.QTableWidgetItem()
        item.setText(QtGui.QApplication.translate("VPlanClient", "SCLO", None, QtGui.QApplication.UnicodeUTF8))
        item.setFlags(QtCore.Qt.ItemIsEnabled)
        self.vplantable.setItem(1, 3, item)
        item = QtGui.QTableWidgetItem()
        item.setText(QtGui.QApplication.translate("VPlanClient", "110", None, QtGui.QApplication.UnicodeUTF8))
        item.setFlags(QtCore.Qt.ItemIsEnabled)
        self.vplantable.setItem(1, 4, item)
        item = QtGui.QTableWidgetItem()
        item.setFlags(QtCore.Qt.ItemIsEnabled)
        self.vplantable.setItem(1, 5, item)
        item = QtGui.QTableWidgetItem()
        item.setFlags(QtCore.Qt.ItemIsEnabled)
        self.vplantable.setItem(1, 6, item)

        #    NEXT ITEM for 12/1
        item = QtGui.QTableWidgetItem()
        item.setText(QtGui.QApplication.translate("VPlanClient", "3", None, QtGui.QApplication.UnicodeUTF8))
        item.setFlags(QtCore.Qt.ItemIsEnabled)
        self.vplantable.setItem(2, 0, item)
        item = QtGui.QTableWidgetItem()
        item.setText(QtGui.QApplication.translate("VPlanClient", "JACO", None, QtGui.QApplication.UnicodeUTF8))
        item.setFlags(QtCore.Qt.ItemIsEnabled)
        self.vplantable.setItem(2, 1, item)
        item = QtGui.QTableWidgetItem()
        item.setText(QtGui.QApplication.translate("VPlanClient", "310", None, QtGui.QApplication.UnicodeUTF8))
        item.setFlags(QtCore.Qt.ItemIsEnabled)
        self.vplantable.setItem(2, 2, item)
        item = QtGui.QTableWidgetItem()
        item.setText(QtGui.QApplication.translate("VPlanClient", "TEST", None, QtGui.QApplication.UnicodeUTF8))
        item.setFlags(QtCore.Qt.ItemIsEnabled)
        self.vplantable.setItem(2, 3, item)
        item = QtGui.QTableWidgetItem()
        item.setText(QtGui.QApplication.translate("VPlanClient", "A102", None, QtGui.QApplication.UnicodeUTF8))
        item.setFlags(QtCore.Qt.ItemIsEnabled)
        self.vplantable.setItem(2, 4, item)
        item = QtGui.QTableWidgetItem()
        item.setFlags(QtCore.Qt.ItemIsEnabled)
        self.vplantable.setItem(2, 5, item)
        item = QtGui.QTableWidgetItem()
        item.setFlags(QtCore.Qt.ItemIsEnabled)
        self.vplantable.setItem(2, 6, item)
        
        # DATA HEADER
        item = QtGui.QTableWidgetItem()
        item.setText(QtGui.QApplication.translate("VPlanClient", "Klasse: 13/1", None, QtGui.QApplication.UnicodeUTF8))
        brush = QtGui.QBrush(QtGui.QColor(211, 211, 211))
        item.setBackground(brush)
        item.setFlags(QtCore.Qt.ItemIsEnabled)
        font = QtGui.QFont()
        font.setBold(True)
        item.setFont(font)
        self.vplantable.setItem(3, 0, item)
        self.vplantable.setSpan(3, 0, 1, 7)

        # DATA 13/1
        item = QtGui.QTableWidgetItem()
        item.setText(QtGui.QApplication.translate("VPlanClient", "2", None, QtGui.QApplication.UnicodeUTF8))
        item.setFlags(QtCore.Qt.ItemIsEnabled)
        self.vplantable.setItem(4, 0, item)
        item = QtGui.QTableWidgetItem()
        item.setText(QtGui.QApplication.translate("VPlanClient", "SCLO", None, QtGui.QApplication.UnicodeUTF8))
        item.setFlags(QtCore.Qt.ItemIsEnabled)
        self.vplantable.setItem(4, 1, item)
        item = QtGui.QTableWidgetItem()
        item.setText(QtGui.QApplication.translate("VPlanClient", "110", None, QtGui.QApplication.UnicodeUTF8))
        item.setFlags(QtCore.Qt.ItemIsEnabled)
        self.vplantable.setItem(4, 2, item)
        item = QtGui.QTableWidgetItem()
        item.setFlags(QtCore.Qt.ItemIsEnabled)
        self.vplantable.setItem(4, 3, item)
        item = QtGui.QTableWidgetItem()
        item.setFlags(QtCore.Qt.ItemIsEnabled)
        self.vplantable.setItem(4, 4, item)
        item = QtGui.QTableWidgetItem()
        item.setText(QtGui.QApplication.translate("VPlanClient", "Frei", None, QtGui.QApplication.UnicodeUTF8))
        item.setFlags(QtCore.Qt.ItemIsEnabled)
        self.vplantable.setItem(4, 5, item)
        item = QtGui.QTableWidgetItem()
        item.setFlags(QtCore.Qt.ItemIsEnabled)
        self.vplantable.setItem(4, 6, item)

        # DATA HEADER
        item = QtGui.QTableWidgetItem()
        item.setText(QtGui.QApplication.translate("VPlanClient", "Klasse: 13/2", None, QtGui.QApplication.UnicodeUTF8))
        brush = QtGui.QBrush(QtGui.QColor(211, 211, 211))
        item.setBackground(brush)
        item.setFlags(QtCore.Qt.ItemIsEnabled)
        font = QtGui.QFont()
        font.setBold(True)
        item.setFont(font)
        self.vplantable.setItem(5, 0, item)
        self.vplantable.setSpan(5, 0, 1, 7)

        # DATA 13/2
        item = QtGui.QTableWidgetItem()
        item.setText(QtGui.QApplication.translate("VPlanClient", "7", None, QtGui.QApplication.UnicodeUTF8))
        item.setFlags(QtCore.Qt.ItemIsEnabled)
        self.vplantable.setItem(6, 0, item)
        item = QtGui.QTableWidgetItem()
        item.setText(QtGui.QApplication.translate("VPlanClient", "TEST", None, QtGui.QApplication.UnicodeUTF8))
        item.setFlags(QtCore.Qt.ItemIsEnabled)
        self.vplantable.setItem(6, 1, item)
        item = QtGui.QTableWidgetItem()
        item.setText(QtGui.QApplication.translate("VPlanClient", "A203", None, QtGui.QApplication.UnicodeUTF8))
        item.setFlags(QtCore.Qt.ItemIsEnabled)
        self.vplantable.setItem(6, 2, item)
        item = QtGui.QTableWidgetItem()
        item.setFlags(QtCore.Qt.ItemIsEnabled)
        self.vplantable.setItem(6, 3, item)
        item = QtGui.QTableWidgetItem()
        item.setFlags(QtCore.Qt.ItemIsEnabled)
        self.vplantable.setItem(6, 4, item)
        item = QtGui.QTableWidgetItem()
        item.setText(QtGui.QApplication.translate("VPlanClient", "Frei", None, QtGui.QApplication.UnicodeUTF8))
        item.setFlags(QtCore.Qt.ItemIsEnabled)
        self.vplantable.setItem(6, 5, item)
        item = QtGui.QTableWidgetItem()
        item.setFlags(QtCore.Qt.ItemIsEnabled)
        self.vplantable.setItem(6, 6, item)

        # DATA END

        self.vplantable.horizontalHeader().setVisible(True)
        self.vplantable.horizontalHeader().setHighlightSections(False)
        self.vplantable.verticalHeader().setVisible(False)
        self.vplantable.verticalHeader().setHighlightSections(False)

        # TITLE BAR START ######
        self.horizontalLayoutWidget = QtGui.QWidget(self.centralwidget)
        self.horizontalLayoutWidget.setGeometry(QtCore.QRect(0, 0, VPlanClient.size().width(), 32))
        self.horizontalLayoutWidget.setObjectName(_fromUtf8("horizontalLayoutWidget"))
        self.horizontalLayoutWidget.setStyleSheet(self.stylesheetDesign['wb'])
        self.horizontalLayout = QtGui.QHBoxLayout(self.horizontalLayoutWidget)
        self.horizontalLayout.setSizeConstraint(QtGui.QLayout.SetMaximumSize)
        self.horizontalLayout.setMargin(0)
        self.horizontalLayout.setObjectName(_fromUtf8("horizontalLayout"))

        # Title
        self.title = QtGui.QLabel(self.horizontalLayoutWidget)
        self.title.setGeometry(QtCore.QRect(0, 0, 241, 31))
        font = QtGui.QFont()
        font.setPointSize(19)
        font.setBold(True)
        font.setItalic(True)
        font.setUnderline(True)
        font.setWeight(75)
        font.setStrikeOut(False)
        font.setKerning(False)
        self.title.setFont(font)
        self.title.setAutoFillBackground(False)
        self.title.setStyleSheet(self.stylesheetDesign['wb'])
        self.title.setText(QtGui.QApplication.translate("VPlanClient", "Vertretungsplan", None, QtGui.QApplication.UnicodeUTF8))
        self.title.setTextFormat(QtCore.Qt.AutoText)
        self.title.setObjectName(_fromUtf8("title"))
        self.horizontalLayout.addWidget(self.title)

        # now we want an spacer
        tspacerSize = VPlanClient.size().width()*0.223
        self.horizontalLayout.addSpacing(tspacerSize)


        # Datetime
        self.datetime = QtGui.QLabel(self.horizontalLayoutWidget)
        self.datetime.setGeometry(QtCore.QRect(0, 0, 350, 31))
        font = QtGui.QFont()
        font.setPointSize(17)
        font.setBold(True)
        font.setWeight(75)
        self.datetime.setFont(font)
        self.datetime.setStyleSheet(self.stylesheetDesign['wb'])
        self.datetime.setText(QtGui.QApplication.translate("VPlanClient", "15.11.2011", None, QtGui.QApplication.UnicodeUTF8))
        self.datetime.setAlignment(QtCore.Qt.AlignCenter)
        self.datetime.setObjectName(_fromUtf8("datetime"))
        self.horizontalLayout.addWidget(self.datetime)
        
        # now we want an spacer
        tspacerSize = VPlanClient.size().width()*0.27
        self.horizontalLayout.addSpacing(tspacerSize)

        # Label LastUpdate
        self.label_lastupdate = QtGui.QLabel(self.horizontalLayoutWidget)
        self.label_lastupdate.setGeometry(QtCore.QRect(0, 0, 141, 31))
        font = QtGui.QFont()
        font.setUnderline(True)
        self.label_lastupdate.setFont(font)
        self.label_lastupdate.setStyleSheet(self.stylesheetDesign['wb'])
        self.label_lastupdate.setText(QtGui.QApplication.translate("VPlanClient", "Letzte Aktualisierung:", None, QtGui.QApplication.UnicodeUTF8))
        self.label_lastupdate.setObjectName(_fromUtf8("label_lastupdate"))
        self.horizontalLayout.addWidget(self.label_lastupdate)

        # LastUpdate
        self.lastupdate = QtGui.QLabel(self.horizontalLayoutWidget)
        self.lastupdate.setGeometry(QtCore.QRect(0, 0, 121, 31))
        self.lastupdate.setStyleSheet(self.stylesheetDesign['wb'])
        self.lastupdate.setText(QtGui.QApplication.translate("VPlanClient", "09.06.2011 12:13", None, QtGui.QApplication.UnicodeUTF8))
        self.lastupdate.setObjectName(_fromUtf8("lastupdate"))
        self.horizontalLayout.addWidget(self.lastupdate)

        # quit ???
        self.actionQuit = QtGui.QAction(VPlanClient)
        self.actionQuit.setText(QtGui.QApplication.translate("VPlanClient", "quit", None, QtGui.QApplication.UnicodeUTF8))
        self.actionQuit.setShortcut(QtGui.QApplication.translate("VPlanClient", "Ctrl+Q", None, QtGui.QApplication.UnicodeUTF8))
        self.actionQuit.setObjectName(_fromUtf8("actionQuit")) 

        VPlanClient.setCentralWidget(self.centralwidget)
        #self.retranslateUi(VPlanClient)
        QtCore.QObject.connect(self.actionQuit, QtCore.SIGNAL(_fromUtf8('triggered()')), VPlanClient.close)
        QtCore.QMetaObject.connectSlotsByName(VPlanClient)

    def retranslateUi(self, VPlanClient):
        self.vplantable.setSortingEnabled(False)
        item = self.vplantable.verticalHeaderItem(0)
        item = self.vplantable.verticalHeaderItem(1)
        item = self.vplantable.verticalHeaderItem(2)
        item = self.vplantable.verticalHeaderItem(3)
        item = self.vplantable.verticalHeaderItem(4)
        item = self.vplantable.verticalHeaderItem(5)
        item = self.vplantable.verticalHeaderItem(6)
        item = self.vplantable.horizontalHeaderItem(0)
        item = self.vplantable.horizontalHeaderItem(1)
        item = self.vplantable.horizontalHeaderItem(2)
        item = self.vplantable.horizontalHeaderItem(3)
        item = self.vplantable.horizontalHeaderItem(4)
        item = self.vplantable.horizontalHeaderItem(5)
        item = self.vplantable.horizontalHeaderItem(6)
        item = self.vplantable.item(0, 0)
        item = self.vplantable.item(1, 0)
        item = self.vplantable.item(1, 1)
        item = self.vplantable.item(1, 2)
        item = self.vplantable.item(1, 3)
        item = self.vplantable.item(1, 4)
        item = self.vplantable.item(2, 0)
        item = self.vplantable.item(2, 1)
        item = self.vplantable.item(2, 2)
        item = self.vplantable.item(2, 3)
        item = self.vplantable.item(2, 4)
        item = self.vplantable.item(3, 0)
        item = self.vplantable.item(4, 0)
        item = self.vplantable.item(4, 1)
        item = self.vplantable.item(4, 2)
        item = self.vplantable.item(4, 5)
        item = self.vplantable.item(5, 0)
        item = self.vplantable.item(6, 0)
        item = self.vplantable.item(6, 1)
        item = self.vplantable.item(6, 2)
        item = self.vplantable.item(6, 5)

        
