#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from UiBrowser import *
from UiAbout import *
from UiUrl import *
from Printer import Printer
from multiprocessing import Process, Queue
from OpenSSL import SSL
from configparser import SafeConfigParser
from PyQt4.QtCore import QObject, QThread, pyqtSignal, pyqtSlot
from PyQt4.QtNetwork import QNetworkAccessManager, QNetworkDiskCache
from PyQt4.QtWebKit import QWebPage
from PyQt4 import QtGui
from time import sleep
from ansistrm import ColorizingStreamHandler
from observer import ObservableSubject, Observer
from flsconfiguration import FLSConfiguration
import sys, os, socket, select, uuid, signal, queue, random, logging, abc

__author__  = 'Lukas Schreiner'
__copyright__ = 'Copyright (C) 2012 - 2013 Website-Team Friedrich-List-Schule-Wiesbaden'

FORMAT = '%(asctime)-15s %(message)s'
formatter = logging.Formatter(FORMAT, datefmt='%b %d %H:%M:%S')
log = logging.getLogger()
log.setLevel(logging.INFO)
hdlr = ColorizingStreamHandler()
hdlr.setFormatter(formatter)
log.addHandler(hdlr)

workDir = os.path.dirname(os.path.realpath(__file__))
# global config
globConfig = FLSConfiguration(os.path.join(workDir,'config.ini'))

try:
	_fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
	_fromUtf8 = lambda s: s

def verify_cb(conn, cert, errnum, depth, ok):
	# This obviously has to be updated
	log.debug('Got certificate: %s' % cert.get_subject())

	certIssuer = cert.get_issuer()
	certSubject = cert.get_subject()

	if depth == 0 and certIssuer is not None and certIssuer.commonName == 'CAcert Class 3 Root' \
		and certSubject.OU == 'Website-Team' \
		and certSubject.CN == 'pytools.fls-wiesbaden.de':
		return ok
	elif depth > 0 and depth < 3:
		return ok
	else:
		return 0

class DsbServer(Process, Observer):
	# Commonly used flag setes
	READ_ONLY = select.POLLIN | select.POLLPRI | select.POLLHUP | select.POLLERR
	READ_WRITE = READ_ONLY | select.POLLOUT
	TIMEOUT = 1000

	def __init__(self):
		Process.__init__(self, name='DsbServer')
		Observer.__init__(self)

		# load config
		# WE NEED globConfig!
		self.config = globConfig
		self.config.addObserver(self)

		# Initialize context
		self.ctx = SSL.Context(SSL.SSLv3_METHOD)
		self.ctx.set_options(SSL.OP_NO_SSLv2)
		self.ctx.set_verify(SSL.VERIFY_PEER|SSL.VERIFY_FAIL_IF_NO_PEER_CERT, verify_cb)
		self.ctx.use_privatekey_file(self.config.get('connection', 'privKey'))
		self.ctx.use_certificate_file(self.config.get('connection', 'pubKey'))
		self.ctx.load_verify_locations(self.config.get('connection', 'caCert'))
		self.ctx.set_verify_depth(self.config.getint('connection', 'verifyDepth'))

		self.exit = False
		self.poller = None
		self.sock = None
		self.runState = False
		self.data = queue.Queue()
		self.vplanQueue = Queue()
		self.vplanProcess = None

		# check name - use Hostname. Should be unique enough!
		self.checkName()

		# start module dsb on connect
		self.addData('dsb')
		# send client version
		self.addData('version;%s;' % (self.config.get('app', 'version'),))
		# register...
		self.addData('register;%s;%i' % (self.config.get('connection', 'dsbName'), uuid.getnode()))

	def notification(self, state):
		pass

	def checkName(self):
		if self.config.get('connection', 'dsbName') is None or len(self.config.get('connection', 'dsbName')) <= 0:
			# uhh no name... thats bad.. generate something... hostname !?
			self.config.set('connection', 'dsbName', socket.gethostname())
			self.config.save()
		else:
			# we can use the config
			pass

	def addData(self, msg):
		self.data.put(msg)
		if self.poller is not None:
			self.poller.modify(self.sock, DsbServer.READ_WRITE)

	def connect(self):
		tryNr = 0
		wait = 1
		self.sock = SSL.Connection(self.ctx, socket.socket(socket.AF_INET, socket.SOCK_STREAM))
		while tryNr >= 0:
			try:
				self.sock.connect(('localhost', 8080))
				tryNr = -1
			except socket.error as e:
				log.warning('Connection try #%i not possible!' % (tryNr,))
				tryNr += 1
				wait += random.randint(10, 10 + tryNr * 3)
				log.info('Waiting %i seconds!' % (wait,))
				sleep(wait)

			if tryNr >= 30:
				log.critical('Connection impossible!')
				break

		return True if tryNr == -1 else False

	def parseCommand(self, cmd):
		code, msg, *args = cmd.decode('utf-8').split(' - ')
		log.debug('%s: %s' % (code, msg))

		if code == '402':
			# uhhh we have a version mismatch!
			log.critical('Version mismatch - you need at least "%s"' % (msg,))
			self.interrupt(None, None)
		elif code == '999':
			self.vplanProcess = VPlanApplication(self.vplanQueue)
			self.vplanProcess.start()

	def waitAndClose(self):
		log.info('finished!')
		self.__del__()
		sys.exit(0)

	def interrupt(self, signal, frame):
		log.info('requested shutdown...')
		if self.runState:
			# delete queue.
			log.debug('waiting for queue clearing...')
			with self.data.mutex:
				self.data.queue.clear()
			# first exit dsb
			log.debug('added exit no. 1')
			self.addData('exit;;')
			# next exit pyTools
			log.debug('added exit no. 2')
			self.addData('exit')
			# wait until all exits are processed.
			log.debug('Wait for empty queue...')
			self.exit = True
		else:
			self.__del__()
			sys.exit(0)

	def run(self):
		if not self.connect():
			return
		else:
			log.info('Connected to DSB Server!')

		self.runState = True
		# sending the first request (to auth)
		self.sock.send(self.data.get_nowait())
		self.sock.setblocking(0)

		self.poller = select.poll()
		self.poller.register(self.sock, DsbServer.READ_ONLY)
		fd_to_socket = {self.sock.fileno(): self.sock}

		while self.runState:
			try:
				events = self.poller.poll(DsbServer.TIMEOUT)
			except select.error:
				break

			for fd, flag in events:
				s = fd_to_socket[fd]
				if flag & (select.POLLIN | select.POLLPRI):
					try:
						newData = s.recv(4096)
					except SSL.ZeroReturnError as e:
						log.info('Connection closed!')
						newData = None

					if newData:
						self.parseCommand(newData)
						self.poller.modify(s, DsbServer.READ_WRITE)
					else:
						log.info('Disconnect...')
						self.poller.unregister(s)
						self.runState = False
						s.shutdown(socket.SHUT_WR)
						s.close()
						self.sock = None
				elif flag & select.POLLHUP:
					log.info('Client hung up..')
					self.poller.unregister(s)
					s.shutdown(socket.SHUT_WR)
					s.close()
					self.sock = None
				elif flag & select.POLLOUT:
					try:
						nextMsg = self.data.get_nowait()
					except queue.Empty:
						log.debug('output queue is empty.')
						if self.exit:
							self.waitAndClose()
						else:
							self.poller.modify(s, DsbServer.READ_ONLY)
					else:
						log.debug('sending data')
						s.send(nextMsg)
				elif flag & select.POLLERR:
					log.error('Handling exceptional condition.')
					log.info('Will stop listening!')
					self.runState = False
					self.poller.unregister(s)
					s.shutdown(socket.SHUT_WR)
					s.close()
					self.sock = None

	def __del__(self):
		try:
			if self.sock is not None:
				self.sock.shutdown(socket.SHUT_WR)
				self.sock.close()
		except Exception as e:
			log.error('Could not close connection: %s' % (e,))

class VPlanApplication(Process):

	def __init__(self, q):
		Process.__init__(self, name='VPlanApplication')
		self.app = QtGui.QApplication(sys.argv)
		self.vplan = None
		self.queue = q

	def run(self):
		self.vplan = VPlanMainWindow()
		self.app.exec_()

class VPlanAbout(QtGui.QDialog):
	def __init__(self, parentMain):
		QtGui.QDialog.__init__(self, parent=parentMain)
		self.config = globConfig

		self.ui = Ui_About()
		self.ui.setupUi(self)

		self.autostart()

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
		self.config = globConfig
		self.loadConfig()

		self.ui = Ui_VPlanURL()
		self.ui.setupUi(self)

		self.autostart()

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
		self.config = globConfig

		self.ui = Ui_MainWindow()
		self.ui.setupUi(self)

		self.enableCache()

		self.autostart()

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

		# Loading finished (bool) 
		self.connect(self.ui.webView, QtCore.SIGNAL('loadFinished(bool)'), QtCore.SLOT('handleLoadReturn(bool)'))

	@pyqtSlot(bool)
	def handleLoadReturn(self, success):
		if not success:
			print('Selected Page could not be loaded.')
			errorPage = """
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"    "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
	<head>
		<title>Vertretungsplaner: Ladefehler</title>
		<style type="text/css">
			html{background:#A0A0A0}body{margin:0;padding:0 1em;color:#000;font:message-box}h1{margin:0 0 .6em 0;border-bottom:1px solid ThreeDLightShadow;font-size:160%}ul,ol{margin:0;padding:0}ul>li,ol>li{margin-bottom:.5em}ul{list-style:square}#errorPageContainer{position:relative;min-width:13em;max-width:52em;margin:4em auto;border:1px solid ThreeDShadow;border-radius:10px;padding:3em;background-color:#ffffff;background-origin:content-box}#errorShortDesc>p{overflow:auto;border-bottom:1px solid ThreeDLightShadow;padding-bottom:1em;font-size:130%;white-space:pre-wrap}#errorLongDesc{font-size:110%}#errorTryAgain{margin-top:2em;}#brand{position:absolute;right:0;bottom:-1.5em;opacity:.4}
		</style>
	</head>
	<body dir="ltr">
		<div id="errorPageContainer">
			<div id="errorTitle">
				<h1 id="errorTitleText">Fehler: Netzwerk-Zeitüberschreitung oder Nicht gefunden</h1>
			</div>
			<div id="errorLongContent">
				<div id="errorShortDesc">
					<p id="errorShortDescText">Der Zentralrechner zum Aufruf der Seite braucht zu lange, um eine Antwort zu senden oder die Datei konnte nicht gefunden werden.</p>
				</div>

				<div id="errorLongDesc">
					<ul xmlns="http://www.w3.org/1999/xhtml">
						<li>Die Seite könnte vorübergehend nicht erreichbar sein, versuchen Sie es bitte 
						später nochmals.</li>
						<li>Wenn Sie auch keine andere Seite aufrufen können, überprüfen Sie bitte die 
						Netzwerk-/Internetverbindung.</li>
						<li>Wenn Ihr Rechner oder Netzwerk von einem Schutzschild oder einem Proxy geschützt wird, 
						stellen Sie bitte sicher, dass Firefox auf das Internet zugreifen darf.</li>
					</ul>
				</div>
			</div>
		</div>
	</body>
</html>
			"""
			self.ui.webView.setHtml(errorPage)


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
	hdlr = logging.FileHandler('vclient.log')
	hdlr.setFormatter(formatter)
	log.addHandler(hdlr)
	log.setLevel(logging.DEBUG)

	ds = DsbServer()
	signal.signal(signal.SIGINT, ds.interrupt)
	ds.start()
	ds.join()

	