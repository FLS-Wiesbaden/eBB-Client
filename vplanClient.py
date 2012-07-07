#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from UiBrowser import *
from UiAbout import *
from UiUrl import *
from Printer import Printer
from configparser import SafeConfigParser
from PyQt4.QtCore import QObject, QThread, pyqtSignal, pyqtSlot
from PyQt4.QtNetwork import QNetworkAccessManager, QNetworkDiskCache
from PyQt4.QtWebKit import QWebPage
from time import sleep
import sys, os

workDir = os.path.dirname(os.path.realpath(__file__))

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    _fromUtf8 = lambda s: s

class VPlanAbout(QtGui.QDialog):
    def __init__(self, parentMain):
        QtGui.QDialog.__init__(self, parent=parentMain)
        self.config = None
        self.loadConfig()

        self.ui = Ui_About()
        self.ui.setupUi(self)

        self.autostart()

    def loadConfig(self, conffile = os.path.join(workDir,'config.ini')):
        self.config = SafeConfigParser()
        self.config.read([conffile])

    def autostart(self):
        # wait - what should i do?
        # set version!
        self.ui.textVersion.setText(_fromUtf8(self.config.get('app', 'version')))
        self.ui.textVersionQt.setText(
                'PyQt-Version: %s / Qt-Version: %s' % (QtCore.PYQT_VERSION_STR, QtCore.QT_VERSION_STR)
        )

        self.show()

class VPlanURL(QtGui.QDialog):
    def __init__(self, parentMain):
        QtGui.QDialog.__init__(self, parent=parentMain)
        self.state = False
        self.config = None
        self.loadConfig()

        self.ui = Ui_VPlanURL()
        self.ui.setupUi(self)

        self.autostart()

    def loadConfig(self, conffile = os.path.join(workDir,'config.ini')):
        self.config = SafeConfigParser()
        self.config.read([conffile])

    def accept(self):
        self.state = True
        super().accept()

    def autostart(self):
        self.show()

class VPlanReloader(QThread):
    def __init__(self, widget, reloadTime, parent = None):
        QThread.__init__(self, parent)
        self.exiting = False
        self.reloadTime = reloadTime
        self.widget = widget

        self.start()

    def run(self):
        while not self.exiting:
            sleep(self.reloadTime)
            self.emit(QtCore.SIGNAL('reloader(QString)'), self.widget)

    def __del__(self):
        self.exiting = True
        self.wait()

class VPlanMainWindow(QtGui.QMainWindow):
    def __init__(self):
        QtGui.QMainWindow.__init__(self)
        self.reloader = []
        self.config = None;
        self.loadConfig()

        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.enableCache()

        self.autostart()

    def loadConfig(self, conffile = os.path.join(workDir,'config.ini')):
        self.config = SafeConfigParser()
        self.config.read([conffile])

    def reloadChild(self, widget):
        if widget == 'webView':
            self.ui.webView.reload()

    def enableCache(self):
        self.manager = QNetworkAccessManager()
        self.diskCache = QNetworkDiskCache()
        self.diskCache.setCacheDirectory(os.path.join(workDir, 'cache'))
        self.manager.setCache(self.diskCache)

        self.webpage = QWebPage()
        self.ui.webView.setPage(self.webpage)

        self.webpage.setNetworkAccessManager(self.manager)

    def enableProgressBar(self):
        self.ui.progressBar = QtGui.QProgressBar(self.ui.centralwidget)
        self.ui.progressBar.setMaximumSize(QtCore.QSize(16777215, self.config.getfloat('progress', 'maxHeight')))
        self.ui.progressBar.setContextMenuPolicy(QtCore.Qt.NoContextMenu)
        self.ui.progressBar.setProperty("value", 0)
        self.ui.progressBar.setTextVisible(self.config.getboolean('progress', 'showText'))
        self.ui.progressBar.setObjectName('progressBar')
        self.ui.verticalLayout.addWidget(self.ui.progressBar)
        self.connect(self.ui.webView, QtCore.SIGNAL('loadProgress(int)'), self.ui.progressBar.setValue)

    def disableProgressBar(self):
        self.disconnect(self.ui.webView, QtCore.SIGNAL('loadProgress(int)'), self.ui.progressBar.setValue)
        self.ui.progressBar.deleteLater()
        self.ui.verticalLayout.removeWidget(self.ui.progressBar)
        self.ui.progressBar = None

    def setActions(self):
        # Exit (Ctrl+Q)
        self.exit = QtGui.QAction(QtGui.QIcon(''), 'Verlassen', self)
        self.exit.setShortcut(self.config.get('shortcuts', 'quit'))
        self.connect(self.exit, QtCore.SIGNAL('triggered()'), QtCore.SLOT('close()'))
        self.addAction(self.exit)

        # Fullscreen (F11)
        self.fullScreen = QtGui.QAction(QtGui.QIcon(''), 'Vollbild an/aus', self)
        self.fullScreen.setShortcut(self.config.get('shortcuts', 'fullscreen'))
        self.connect(self.fullScreen, QtCore.SIGNAL('triggered()'), QtCore.SLOT('toggleScreen()'))
        self.addAction(self.fullScreen)

        # Toggle progressbar (F9)
        self.toggleProgress = QtGui.QAction(QtGui.QIcon(''), 'Progressbar an/aus', self)
        self.toggleProgress.setShortcut(self.config.get('shortcuts', 'toggleProgressBar'))
        self.connect(self.toggleProgress, QtCore.SIGNAL('triggered()'), QtCore.SLOT('toggleProgressBar()'))
        self.addAction(self.toggleProgress)

        # Reload planer (F5)
        self.actReload = QtGui.QAction(QtGui.QIcon(''), 'Neuladen', self)
        self.actReload.setAutoRepeat(self.config.getboolean('browser', 'autoRepeatReload'))
        self.actReload.setShortcut(self.config.get('shortcuts', 'reload'))
        self.connect(self.actReload, QtCore.SIGNAL('triggered()'), self.ui.webView.reload)
        self.addAction(self.actReload)

        # Browser: stop (Esc)
        self.actStop = QtGui.QAction(QtGui.QIcon(''), 'Stop', self)
        self.actStop.setShortcut(self.config.get('shortcuts', 'browserStop'))
        self.connect(self.actStop, QtCore.SIGNAL('triggered()'), self.ui.webView.stop)
        self.addAction(self.actStop)

        # Browser: forward (Alt+Right)
        self.actForward = QtGui.QAction(QtGui.QIcon(''), 'Forward', self)
        self.actForward.setShortcut(self.config.get('shortcuts', 'browserForward'))
        self.connect(self.actForward, QtCore.SIGNAL('triggered()'), self.ui.webView.forward)
        self.addAction(self.actForward)

        # Browser: Back (Alt+Left)
        self.actBack = QtGui.QAction(QtGui.QIcon(''), 'Back', self)
        self.actBack.setShortcut(self.config.get('shortcuts', 'browserBack'))
        self.connect(self.actBack, QtCore.SIGNAL('triggered()'), self.ui.webView.back)
        self.addAction(self.actBack)

        # About window (F1)
        self.actAbout = QtGui.QAction(QtGui.QIcon(''), 'Über', self)
        self.actAbout.setShortcut(self.config.get('shortcuts', 'about'))
        self.connect(self.actAbout, QtCore.SIGNAL('triggered()'), QtCore.SLOT('showAbout()'))
        self.addAction(self.actAbout)

        # Go to url... (F2)
        self.actURL = QtGui.QAction(QtGui.QIcon(''), 'Neue URL', self)
        self.actURL.setAutoRepeat(False)
        self.actURL.setShortcut(self.config.get('shortcuts', 'newURL'))
        self.connect(self.actURL, QtCore.SIGNAL('triggered()'), QtCore.SLOT('newURL()'))
        self.addAction(self.actURL)

        # we will set zoom factor ;)
        # increase Zoom factor of planer
        self.actIncZoom = QtGui.QAction(QtGui.QIcon(''), 'Plan vergrößern', self)
        self.actIncZoom.setShortcut(self.config.get('shortcuts', 'incZoom'))
        self.connect(self.actIncZoom, QtCore.SIGNAL('triggered()'), QtCore.SLOT('incZoom()'))
        self.addAction(self.actIncZoom)

        # decrease Zoom factor of planer
        self.actDecZoom = QtGui.QAction(QtGui.QIcon(''), 'Plan verkleinern', self)
        self.actDecZoom.setShortcut(self.config.get('shortcuts', 'decZoom'))
        self.connect(self.actDecZoom, QtCore.SIGNAL('triggered()'), QtCore.SLOT('decZoom()'))
        self.addAction(self.actDecZoom)

        # reset Zoom factor of planer
        self.actResetZoom = QtGui.QAction(QtGui.QIcon(''), 'Planzoom zurücksetzen', self)
        self.actResetZoom.setShortcut(self.config.get('shortcuts', 'resetZoom'))
        self.connect(self.actResetZoom, QtCore.SIGNAL('triggered()'), QtCore.SLOT('resetZoom()'))
        self.addAction(self.actResetZoom)

    @pyqtSlot()
    def showAbout(self):
        aboutWin = VPlanAbout(self)

    @pyqtSlot()
    def newURL(self):
        newURLWin = VPlanURL(self)
        if newURLWin.exec_() and newURLWin.state:
            # rejected or not?
            url = newURLWin.ui.url.text()
            self.loadUrl(url)

    @pyqtSlot()
    def toggleScreen(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    @pyqtSlot()
    def toggleProgressBar(self):
        try:
            getattr(self.ui, 'progressBar') is None
        except AttributeError:
            self.ui.progressBar = None

        if self.ui.progressBar is None:
            self.enableProgressBar()
        else:
            self.disableProgressBar()

    @pyqtSlot()
    def incZoom(self):
        zoomFact = self.ui.webView.zoomFactor()
        steps = self.config.getfloat('browser', 'zoomSteps')
        self.setBrowserZoom(zoomFact + steps)

    @pyqtSlot()
    def decZoom(self):
        zoomFact = self.ui.webView.zoomFactor()
        steps = self.config.getfloat('browser', 'zoomSteps')
        self.setBrowserZoom(zoomFact - steps)

    @pyqtSlot()
    def resetZoom(self):
        self.setBrowserZoom()

    def setBrowserZoom(self, zoom = None):
        if zoom is None:
            zoom = self.config.getfloat('browser', 'zoomFactor')

        self.ui.webView.setZoomFactor(zoom)

    def loadUrl(self, url=None):
        if url is None:
            url = self.config.get('app', 'url')

        self.ui.webView.setUrl(QtCore.QUrl(_fromUtf8(url)))

    def autostart(self):
        title = self.config.get('app', 'title')
        self.setWindowTitle(QtGui.QApplication.translate("MainWindow", title, None, QtGui.QApplication.UnicodeUTF8))

        self.setActions()
        # enable progressbar ?
        if self.config.getboolean('progress', 'enableBar'):
            self.enableProgressBar()

        if self.config.getboolean('app', 'fullScreenAtStartup'):
            self.showFullScreen()
        else:
            self.show()

        self.setBrowserZoom()
        self.loadUrl()

        # reload regulary?
        if self.config.getint('browser', 'reloadEvery') > 0:
            reloader = VPlanReloader('webView', self.config.getint('browser', 'reloadEvery'))
            self.reloader.append(reloader)
            self.connect(reloader, QtCore.SIGNAL('reloader(QString)'), self.reloadChild)


if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)
    MainWindow = VPlanMainWindow()
    sys.exit(app.exec_())
