#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from ui_browser import *
from ui_about import *
from ui_url import *
from Printer import Printer
from OpenSSL import SSL
from configparser import SafeConfigParser
from PyQt4.QtCore import QObject, QThread, pyqtSignal, pyqtSlot, pyqtProperty, QBuffer, QByteArray, QIODevice, QMutex, QMutexLocker, QTimer
from PyQt4.QtNetwork import QNetworkAccessManager, QNetworkDiskCache, QNetworkRequest, QNetworkProxy, QAuthenticator, QNetworkReply
from PyQt4.QtWebKit import QWebPage
from PyQt4 import QtGui, QtWebKit
from time import sleep
from ansistrm import ColorizingStreamHandler
from observer import ObservableSubject, Observer, NotifyReceiver
from flsconfiguration import FLSConfiguration
from threading import Lock, Thread
from io import BytesIO
from hashlib import sha512
from struct import Struct
from dsbmessage import DsbMessage
from logging.handlers import WatchedFileHandler
import sys, os, socket, select, uuid, signal, queue, random, logging, abc, json, atexit, shlex, subprocess, zlib, binascii, pickle
import traceback

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
flsConfig = FLSConfiguration()

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

class DsbServer(QThread):
	sigShowEBB = pyqtSignal()
	sigHideEBB = pyqtSignal()
	sigQuitEBB = pyqtSignal()
	sigNewMsg  = pyqtSignal(DsbMessage)
	sigCrtScrShot = pyqtSignal()

	# Commonly used flag setes
	READ_ONLY = select.POLLIN | select.POLLPRI | select.POLLHUP | select.POLLERR
	READ_WRITE = READ_ONLY | select.POLLOUT
	TIMEOUT = 1000

	def __init__(self, parent = None):
		QThread.__init__(self, parent)
		#Observer.__init__(self) HIDDEN dependency
		self._notifyReceiver = NotifyReceiver(self)
		
		# load config
		# WE NEED globConfig!
		self.config = globConfig
		self.config.addObserver(self)
		self.flsConfig = flsConfig
		self.flsConfig.addObserver(self)
		self.scrshotSend = True
		self.machineId = None

		# Initialize context
		self.ctx = SSL.Context(SSL.SSLv3_METHOD)
		self.ctx.set_options(SSL.OP_NO_SSLv2|SSL.OP_NO_TLSv1)
		self.ctx.set_verify(SSL.VERIFY_PEER|SSL.VERIFY_FAIL_IF_NO_PEER_CERT, verify_cb)
		self.ctx.use_privatekey_file(self.config.get('connection', 'privKey'))
		self.ctx.use_certificate_file(self.config.get('connection', 'pubKey'))
		self.ctx.load_verify_locations(self.config.get('connection', 'caCert'))
		self.ctx.set_verify_depth(self.config.getint('connection', 'verifyDepth'))

		self.poller = None
		self.sock = None
		self.runState = False
		self.data = queue.Queue()
		self.events = queue.Queue()

		# check name - use Hostname. Should be unique enough!
		self.checkName()

	@pyqtSlot(str)
	def notification(self, state):
		pass

	def getHostname(self):
		return socket.gethostname()

	def getMachineID(self):
		if self.machineId is None:
			machineId = uuid.getnode()
			try:
				with open(self.config.get('connection', 'pathMachine'), 'rb') as f:
					machineId = f.read().strip().decode('utf-8')
			except Exception as e:
				log.warning('Dbus-File with machine id does not exist at %s' % (self.config.get('connection', 'pathMachine'),))

			log.debug('Used machine id: %s' % (machineId,))
			self.config.set('connection', 'machineId', machineId)
			self.machineId = machineId

		return self.machineId

	def checkName(self):
		if self.config.get('connection', 'dsbName') is None or len(self.config.get('connection', 'dsbName')) <= 0:
			# uhh no name... thats bad.. generate something... hostname !?
			self.config.set('connection', 'dsbName', '%s' % (uuid.getnode(),))
			self.config.save()

	def addData(self, msg):
		self.data.put(msg)
		if self.poller is not None:
			self.poller.modify(self.sock, DsbServer.READ_WRITE)

	@pyqtSlot()
	def quitEBB(self):
		self.addData('goOffline;;')

	@pyqtSlot(object)
	def addEvent(self, evt):
		self.events.put(evt)

	@pyqtSlot(str)
	def changeMode(self, mode):
		self.addData('mode;%s;' % (mode,))

	@pyqtSlot(QtGui.QPixmap)
	def sendScreenshot(self, scrshot):
		if self.scrshotSend is True:
			self.scrshotSend = False
			# Save QPixmap to QByteArray via QBuffer.
			byte_array = QByteArray()
			iobuffer = QBuffer(byte_array)
			iobuffer.open(QIODevice.WriteOnly)
			scrshot.save(iobuffer, 'PNG')

			# Read QByteArray containing PNG into a StringIO.
			string_io = BytesIO(byte_array)
			string_io.seek(0)
			data = zlib.compress(string_io.getvalue(), 9)
			
			self.addData('screenshot;chksum;%i:%s' % (len(data),sha512(data).hexdigest()))

			data = Struct('%is'%(len(data),)).pack(data)
			data = binascii.hexlify(data).decode('utf-8')
			i = 0
			for pos in range(0, len(data), 2048):
				self.addData('screenshot;%i;%s' % (i, data[pos:pos+2048]))
				i += 1

			self.addData('screenshot;eof;')

	def connect(self):
		tryNr = 0
		wait = 1
		self.sock = SSL.Connection(self.ctx, socket.socket(socket.AF_INET, socket.SOCK_STREAM))
		while tryNr >= 0:
			try:
				self.sock.connect((self.config.get('connection', 'host'), self.config.getint('connection', 'port')))
				tryNr = -1
			except socket.error as e:
				log.warning('Connection try #%i not possible!' % (tryNr,))
				tryNr += 1
				wait = random.randint(1, 5 + tryNr * 2)
				log.info('Waiting %i seconds!' % (wait,))
				sleep(wait)

			if tryNr >= 99:
				log.critical('Connection impossible!')
				break

		if tryNr == -1:
			log.info(
				'Connected to %s:%i with success.' % (
					self.config.get('connection', 'host'), 
					self.config.getint('connection', 'port')
				)
			)

		return True if tryNr == -1 else False

	def parseCommand(self, cmd):
		code, msg, *args = cmd.decode('utf-8').rstrip().split(' - ')
		log.debug('%s: %s' % (code, msg))

		# TODO: make constants for the codes similiar as in dsb.py!
		if code == '201':
			log.info('OK... our request is in processing but we have to wait for communication with the cms.')
		elif code == '202' or code == '205':
			log.info('We got a new message... analysing the target.')
			# because the msg could contain " - " we have to recreate the data.
			if len(args) > 0:
				pMsg = ' - '.join([msg, ' - '.join([args])])
			else:
				pMsg = msg

			self.processMessage(pMsg)
		elif code == '203':
			log.info('Ok. Version is up to date.')
			# now register!
			self.addData('register;%s;%s' % (self.getMachineID(), self.getHostname()))
		elif code == '204':
			self.config.set('connection', 'dsbName', msg)
			self.addData('getConfig;;')
		elif code == '303':
			log.info('Ok. Version is sufficient but there is a new version?')
			# FIXME update the vplan client?
			pass
		elif code == '402':
			# uhhh we have a version mismatch!
			log.critical('Version mismatch - you need at least "%s"' % (msg,))
			self.interrupt(None, None)
		elif code == '621':
			log.info('Can\'t go offline. Ignore events.')
		elif code == '623':
			# we are now in idle mode. So we will wait for commands.
			self.sigHideEBB.emit()
		elif code == '622':
			log.info('Marked as offline. Accept close events.')
			# i'm offline. Stop application!
			# we should have a specific things in events..
			self.sigHideEBB.emit()
			self.addData('exit;;')
			self.addData('exit')
			self.sigQuitEBB.emit()
		elif code == '625':
			self.sigShowEBB.emit()
		elif code == '626':
			# connection will be closed! Don't observe anymore!
			self.sigQuitEBB.emit()

	def processMessage(self, msg):
		# let us read the json string.
		try:
			data = DsbMessage.fromJsonString(msg)
		except ValueError as e:
			log.critical('We got a json string which is not really json...: %s' % (msg,))
		else:
			# is it something we have to do or something that has to be interpreted by ebb itself?
			if data.target == DsbMessage.TARGET_CLIENT:
				log.debug('Message is for the client. We will proceed.')
				try:
					func = getattr(self, 'evt%s%s' % (data.event.title(), data.action.title()))
					func(data)
				except AttributeError as e:
					log.critical(
						'We got an event without a possibility to execute it: evt%s%s\nError: %s' %
						(data.event.title(), data.action.title(), e)
					)
			elif data.target == DsbMessage.TARGET_DSB:
				log.debug('Message is for the ebb. We will redirect the request.')
				#import rpdb2; rpdb2.start_embedded_debugger('test')
				try:
					self.sigNewMsg.emit(data)
				except Exception as e:
					log.critical('There is an exception by emitting signal: %s!' % (e,))
			else:
				log.warning('Target of message is unknown.')

	def evtChangeState(self, msg):
		if msg.value == DsbMessage.STATE_DISABLED:
			log.info('eBB was disabled. Close eBB.')
			self.sigHideEBB.emit()
			self.addData('exit;;')
			self.addData('exit')
			self.sigQuitEBB.emit()
		elif msg.value == DsbMessage.STATE_IDLE:
			self.evtTriggerSuspend(msg)
		elif msg.value == DsbMessage.STATE_ONLINE:
			self.evtTriggerResume(msg)

	def evtTriggerSuspend(self, msg):
		log.info('Suspend eBB')
		log.debug('Hide main frame.')
		self.sigHideEBB.emit()
		log.debug('Disable display.')
		exitCode = subprocess.call(shlex.split('xset dpms force off'))
		log.debug('Displayed turned off %s' % ('successful' if exitCode == 0 else 'with errors',))
		log.info('Now we are suspended, we will inform the cms.')
		self.addData('goIdle;;')

	def evtTriggerResume(self, msg):
		log.info('Resume eBB')
		log.debug('Show main frame.')
		self.sigShowEBB.emit()
		log.debug('Enable display.')
		exitCode = subprocess.call(shlex.split('xset dpms force on'))
		log.debug('Displayed turned on %s' % ('successful' if exitCode == 0 else 'with errors',))
		self.addData('goOnline;;')

	def evtTriggerReboot(self, msg):
		log.info('Reboot requested.')
		log.debug('Hide main frame.')
		self.sigHideEBB.emit()
		log.debug('Send quit (offline) message to dsb server')
		self.quitEBB()
		log.debug('Save configuration.')
		self.config.save()
		log.debug('Send reboot request NOW!')
		subprocess.call(shlex.split('sudo shutdown -r now'))

	def evtTriggerShutdown(self, msg):
		log.info('Shutdown requested.')
		log.debug('Hide main frame.')
		self.sigHideEBB.emit()
		log.debug('Send quit (offline) message to dsb server')
		self.quitEBB()
		log.debug('Save configuration.')
		self.config.save()
		log.debug('Send shutdown request NOW!')
		subprocess.call(shlex.split('sudo shutdown -h now'))

	def evtCreateScreenshot(self, msg):
		log.info('Create screenshot requested.')
		self.sigCrtScrShot.emit()

	def evtTriggerConfig(self, msg):
		try:
			if msg.id == 'ebb':
				self.config.loadJson(msg.value)
				self.config.set('connection', 'machineId', self.getMachineID())
				self.config.save()
				log.info('New ebb configuration set.')
			elif msg.id == 'fls':
				self.flsConfig.loadJson(msg.value)
				self.flsConfig.save()
				log.info('New fls configuration set.')
		except ValueError as e:
			log.error('Got wrong configuration string!')

	def run(self):
		error = True

		while error:
			error = False
			self.poller = None
			if not self.connect():
				break

			# clear queue
			with self.data.mutex:
				self.data.queue.clear()
			# start module dsb on connect
			self.addData('dsb')
			# send client version
			self.addData('version;%s;' % (self.config.get('app', 'version'),))

			self.runState = True
			self.sendNextRequest()
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
						except SSL.SysCallError as e:
							log.error('error occurred while reading (SysCallError): %s' % (e,))
							newData = None
							error = True
							self.runState = False
							continue
						except SSL.ZeroReturnError as e:
							log.info('Connection closed (ZeroReturnError): %s!' % (e,))
							newData = None
						except SSL.WantReadError as e:
							log.error('error occurred while reading (WantReadError): %s' % (e,))
						except SSL.WantWriteError as e:
							log.error('error occurred while reading (WantWriteError): %s' % (e,))
						except SSL.WantX509LookupError as e:
							log.error('error occurred while reading (WantX509LookupError): %s' % (e,))
						except SSL.Error as e:
							# maybe client does not use ssl
							log.error('error occurred while reading (ssl error): %s' % (e,))

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
							self.poller.modify(s, DsbServer.READ_ONLY)
						else: 
							if not nextMsg.startswith('screenshot'):
								log.debug('sending msg %s' % (nextMsg,))
							elif nextMsg == 'screenshot;eof;':
								self.scrshotSend = True
								log.debug('sending a screenshot.')
							s.sendall(nextMsg)
					elif flag & select.POLLERR:
						log.error('Handling exceptional condition.')
						log.info('Will stop listening!')
						self.runState = False
						self.poller.unregister(s)
						s.shutdown(socket.SHUT_WR)
						s.close()
						self.sock = None

	def sendNextRequest(self):
		try:
			nextMsg = self.data.get_nowait()
		except queue.Empty:
			log.debug('output queue is empty.')
		else:
			log.debug('sending data')
			self.sock.send(nextMsg)

	def shutdown(self):
		try:
			if self.sock is not None:
				self.runState = False
				# delete queue.
				log.debug('waiting for queue clearing...')
				with self.data.mutex:
					self.data.queue.clear()
				# first exit dsb
				log.debug('added exit no. 1')
				self.addData('exit;;')
				self.sendNextRequest()
				# next exit pyTools
				log.debug('added exit no. 2')
				self.addData('exit')
				self.sendNextRequest()
				# shutdown
				#self.sock.shutdown(socket.SHUT_WR)
				#self.sock.close(self.sock.fileno())
		except Exception as e:
			log.error('Could not close connection: %s' % (e,))

class FlsWebPage(QWebPage):
	
	def __init__(self, parent=None):
		super(FlsWebPage, self).__init__(parent)

	def javaScriptConsoleMessage(self, msg, lineNumber, sourceID):
		log.debug("JsConsole(%s:%d): %s" % (sourceID, lineNumber, msg))

	def javaScriptAlert(self, frame, msg):
		log.warning('JsAlert (%s): %s' % (frame.frameName(), msg))

class VPlanAbout(QtGui.QDialog):
	def __init__(self, parentMain):
		QtGui.QDialog.__init__(self, parent=parentMain)
		self.config = globConfig
		self.numTry = 0

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
		self.ui.textVersionPy.setText(sys.version)

		self.show()

class VPlanURL(QtGui.QDialog):
	def __init__(self, parentMain):
		QtGui.QDialog.__init__(self, parent=parentMain)
		self.state = False
		self.config = globConfig

		self.ui = Ui_VPlanURL()
		self.ui.setupUi(self)

		self.autostart()

	def accept(self):
		self.state = True
		super().accept()

	def autostart(self):
		self.show()

class VPlanReloader(QThread):
	"""it is an observer !!!"""
	def __init__(self, widget, reloadTime, parent = None):
		QThread.__init__(self, parent)
		self.lock = False
		self.exiting = False
		self.reloadTime = reloadTime
		self.widget = widget

		self.start()

	def run(self):
		while not self.exiting:
			sleep(self.reloadTime)
			if not self.lock:
				self.lock = True
				self.emit(QtCore.SIGNAL('reloader(QString)'), self.widget)

	@pyqtSlot(bool)
	def pageLoaded(self, state):
		self.lock = False

	@pyqtSlot(str)
	def notification(self, state):
		if state == 'configChanged':
			self.reloadTime = globConfig.get('browser', 'reloadEvery')
			if self.reloadTime <= 0:
				self.stop()

	def __del__(self):
		self.exiting = True
		self.wait() 

class eBBJsHandler(QObject):
	sigModeChanged = pyqtSignal(str)
	sigReload = pyqtSignal()

	def __init__(self, config, flscfg):
		QObject.__init__(self)
		self.ebbConfig = config
		self.flsConfig = flscfg
		self.ready = False

	@pyqtSlot()
	def ready(self):
		log.info('js is ready now!')
		self.ready = True

	@pyqtSlot()
	def notReady(self):
		log.info('js is not ready anymore!')
		self.ready = False

	@pyqtSlot()
	def reload(self):
		self.sigReload.emit()
		log.info('js wants me to reload!')

	def _config(self):
		return self.ebbConfig.toJson()

	def _flsConfig(self):
		return self.flsConfig.toJson()

	def _machineId(self):
		return self.ebbConfig.get('connection', 'machineId')

	config = pyqtProperty(str, fget=_config)
	flscfg = pyqtProperty(str, fget=_flsConfig)
	machineId = pyqtProperty(str, fget=_machineId)

	@pyqtSlot(str)
	def modeChanged(self, mode):
		self.sigModeChanged.emit(mode)
		log.info('Mode changed: %s' % (mode,))

	@pyqtSlot(str)
	def logD(self, msg):
		log.debug(msg)

	@pyqtSlot(str)
	def logI(self, msg):
		log.info(msg)

	@pyqtSlot(str)
	def logW(self, msg):
		log.warning(msg)

	@pyqtSlot(str)
	def logE(self, msg):
		log.error(msg)

class VPlanMainWindow(QtGui.QMainWindow):
	sigQuitEBB = pyqtSignal()
	sigEvtAdd = pyqtSignal()
	sigSndScrShot = pyqtSignal(QtGui.QPixmap)

	NOTIFY_PAGE = "TvVplan.processMessage('{MSG}')"
	NOTIFY_CONFIG = "TvVplan.configChanged()"

	def __init__(self):
		QtGui.QMainWindow.__init__(self)
		self._notifyReceiver = NotifyReceiver(self)
		self.reloader = []
		self.config = globConfig
		self.config.addObserver(self)
		self.flsConfig = globConfig
		#self.flsConfig.addObserver(self)
		self.server = None
		self.timer = None
		self.inspector = None
		self.loaded = False

		# our screenshot timer.
		self.scrShotTimer = QTimer()
		self.scrShotTimer.setSingleShot(False)
		self.scrShotTimer.setInterval(self.config.getint('options', 'scrShotInterval')*1000)
		self.scrShotTimer.timeout.connect(self.createScreenshot)

		self.ui = Ui_MainWindow()
		self.ui.setupUi(self)
		self.ebbJsHandler = eBBJsHandler(self.config, self.flsConfig)

		self.manager = QNetworkAccessManager()
		self.webpage = FlsWebPage()
		self.webpage.setNetworkAccessManager(self.manager)
		self.ui.webView.setPage(self.webpage)
		if self.config.get('debug', 'enabled'):
			self.ui.webView.settings().setAttribute(QtWebKit.QWebSettings.DeveloperExtrasEnabled, True)
		# enable js-object
		self.ui.webView.page().mainFrame().addToJavaScriptWindowObject('ebbClient', self.ebbJsHandler)

		self.enableCache()
		self.enableProxy()
		self.autostart()

	def start(self):
		self.server = DsbServer(self)
		self.server.sigShowEBB.connect(self.showEBB)
		self.server.sigHideEBB.connect(self.hideEBB)
		self.server.sigQuitEBB.connect(self.quitEBB)
		self.server.sigNewMsg.connect(self.dsbMessage)
		self.server.sigCrtScrShot.connect(self.createScreenshot)
		self.sigEvtAdd.connect(self.server.addEvent)
		self.sigQuitEBB.connect(self.server.quitEBB)
		self.sigSndScrShot.connect(self.server.sendScreenshot)
		self.ui.webView.page().mainFrame().javaScriptWindowObjectCleared.connect(self.attachJsObj)
		self.ebbJsHandler.sigModeChanged.connect(self.server.changeMode)
		self.ui.webView.page().mainFrame().loadStarted.connect(self.ebbJsHandler.notReady)
		self.ebbJsHandler.sigReload.connect(self.reload)

		self.server.start()

	def closeEvent(self, e):
		# first we try to send an offline signal to server!
		log.info('"Quit EBB" -> sending signal!')
		self.sigQuitEBB.emit()

		# we have to ignore it...
		e.ignore()

	@pyqtSlot()
	def reload(self):
		if self.diskCache is not None:
			log.info('Clear cache and reload page')
			self.diskCache.clear()

		self.ui.webView.reload()

	@pyqtSlot()
	def quitEBB(self):
		self.scrShotTimer.stop()
		log.info('Quitting eBB. Wait 2 sec. for communication with pyTools.')
		# wait 2 sec!
		self.timer = QTimer()
		self.timer.setInterval(2000)
		self.timer.setSingleShot(True)
		self.timer.timeout.connect(self.quitHard)
		self.timer.start()

	def quitHard(self):
		log.info('Quit hard now!')
		self.server.runState = False
		self.server = None
		QtGui.QApplication.quit()

	@pyqtSlot(str)
	def notification(self, state):
		if state == 'configChanged':
			# changed the url?
			if self.config.get('app', 'url') != self.ui.webView.page().mainFrame().url().toString() \
					and self.loaded:
				self.loadUrl()
			elif self.ebbJsHandler.ready:
				# now inform ebb
				log.info('Notifiy eBB (JS) about configuration change.')
				self.ui.webView.page().mainFrame().evaluateJavaScript(VPlanMainWindow.NOTIFY_CONFIG)

		if self.config.get('debug', 'enabled'):
			self.ui.webView.settings().setAttribute(QtWebKit.QWebSettings.DeveloperExtrasEnabled, True)
		else:
			self.ui.webView.settings().setAttribute(QtWebKit.QWebSettings.DeveloperExtrasEnabled, False)

	@pyqtSlot()
	def attachJsObj(self):
		self.ui.webView.page().mainFrame().addToJavaScriptWindowObject('ebbClient', self.ebbJsHandler)

	def reloadChild(self, widget):
		if widget == 'webView':
			self.ui.webView.reload()

	def enableCache(self):
		self.diskCache = QNetworkDiskCache()
		self.diskCache.setCacheDirectory(os.path.join(workDir, 'cache'))
		self.manager.setCache(self.diskCache)

	def enableProxy(self):
		if self.config.getboolean('proxy', 'enable'):
			log.info(
				'Enabled proxy with host %s and port %i' % (self.config.get('proxy', 'host'), self.config.getint('proxy', 'port'))
			)
			self.proxy = QNetworkProxy()
			self.proxy.setHostName(self.config.get('proxy', 'host'))
			self.proxy.setPort(self.config.getint('proxy', 'port'))
			self.proxy.setType(QNetworkProxy.HttpProxy)
			if self.config.get('proxy', 'username') is not None and len(self.config.get('proxy', 'username')) > 0:
				log.info('Proxy used with authentication!')
				self.proxy.setUser(self.config.get('proxy', 'username'))
				self.proxy.setPassword(self.config.get('proxy', 'password'))
			self.manager.setProxy(self.proxy)
			QNetworkProxy.setApplicationProxy(self.proxy)

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
		self.connect(self.actReload, QtCore.SIGNAL('triggered()'), self.reload)
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

		# start debugger
		self.actStartDebug = QtGui.QAction(QtGui.QIcon(''), 'Debugger starten', self)
		self.actStartDebug.setShortcut(self.config.get('shortcuts', 'debugConsole'))
		self.connect(self.actStartDebug, QtCore.SIGNAL('triggered()'), QtCore.SLOT('startDebug()'))
		self.addAction(self.actStartDebug)

		# Loading finished (bool) 
		self.connect(self.ui.webView, QtCore.SIGNAL('loadFinished(bool)'), QtCore.SLOT('handleLoadReturn(bool)'))

		# if page requires username / password
		self.manager.authenticationRequired.connect(self.setBasicAuth)

	@pyqtSlot(bool)
	def handleLoadReturn(self, success):
		if not success:
			log.error('Selected page could not be loaded.')
			errorPage = """
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"    "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
	<head>
		<title>eBlackboard: Ladefehler</title>
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
		else:
			log.debug('Selected page could be loaded.')
			self.numTry = 0
	
	@pyqtSlot(QNetworkReply, QAuthenticator)
	def setBasicAuth(self, reply, auth):
		self.numTry += 1

		if self.numTry > 2:
			log.warning('Authentication required but max number of tries are exceeded.')
			reply.abort()
		else:
			log.info('Authentication required (Try #%i). Use data from config.' % (self.numTry,))
			# on first
			auth.setUser(self.config.get('connection', 'username'))
			auth.setPassword(self.config.get('connection', 'password'))

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

	@pyqtSlot()
	def startDebug(self):
		if self.config.get('debug', 'enabled'):
			if self.inspector is None:
				self.inspector = QtWebKit.QWebInspector()
				self.inspector.setPage(self.ui.webView.page())
				self.inspector.show()
			elif self.inspector is not None:
				if self.inspector.close():
					self.inspector = None

	def setBrowserZoom(self, zoom = None):
		if zoom is None:
			zoom = self.config.getfloat('browser', 'zoomFactor')

		self.ui.webView.setZoomFactor(zoom)

	def loadUrl(self, url=None):
		if url is None:
			url = self.config.get('app', 'url')

		log.info('Call %s' % (url,))
		self.numTry = 0
		self.ui.webView.page().mainFrame().load(QNetworkRequest(QtCore.QUrl(_fromUtf8(url))))

	@pyqtSlot()
	def showEBB(self):
		exitCode  = subprocess.call(shlex.split('xset s noblank'))
		exitCode += subprocess.call(shlex.split('xset s noexpose'))
		exitCode += subprocess.call(shlex.split('xset s off'))
		log.info('Screensaver turned off %s' % ('successful' if exitCode == 0 else 'with errors',))

		# already shown?
		if self.isVisible():
			return

		if self.config.getboolean('app', 'fullScreenAtStartup'):
			self.showFullScreen()
		else:
			self.show()
		if self.config.getint('options', 'scrShotInterval'):
			self.scrShotTimer.start()

		if not self.loaded:
			self.loaded = True
			self.loadUrl()

	@pyqtSlot()
	def hideEBB(self):
		# stop scrshot!
		self.scrShotTimer.stop()
		self.hide()

		exitCode  = subprocess.call(shlex.split('xset s blank'))
		exitCode += subprocess.call(shlex.split('xset s expose'))
		exitCode += subprocess.call(shlex.split('xset s on'))
		log.info('Screensaver turned on %s' % ('successful' if exitCode == 0 else 'with errors',))

	@pyqtSlot()
	def createScreenshot(self):
		if self.server.runState and self.isVisible():
			log.debug('Create screenshot')
			scrShot = QtGui.QPixmap.grabWidget(self)
			if self.config.getint('options', 'scrShotSize') > 0:
				scrShot = scrShot.scaledToWidth(self.config.getint('options', 'scrShotSize'))
			self.sigSndScrShot.emit(scrShot)
		else:
			log.debug('Screenshot canceled (runState: %s ; Visible: %s).' % (self.server.runState, self.isVisible()))

	@pyqtSlot(DsbMessage)
	def dsbMessage(self, msg):
		log.info('We got a message for the ebb: %s.' % (msg.toJson(),))
		self.ui.webView.page().mainFrame().evaluateJavaScript(VPlanMainWindow.NOTIFY_PAGE.format(MSG=msg.toJson()))

	def autostart(self):
		title = self.config.get('app', 'title')
		self.setWindowTitle(QtGui.QApplication.translate("MainWindow", title, None, QtGui.QApplication.UnicodeUTF8))

		self.setActions()
		# enable progressbar ?
		if self.config.getboolean('progress', 'enableBar'):
			self.enableProgressBar()

		self.setBrowserZoom()
		#self.loadUrl()

		# reload regulary?
		if self.config.getint('browser', 'reloadEvery') > 0:
			reloader = VPlanReloader('webView', self.config.getint('browser', 'reloadEvery'))
			self.config.addObserver(reloader)
			self.reloader.append(reloader)
			self.connect(reloader, QtCore.SIGNAL('reloader(QString)'), self.reloadChild)
			self.ui.webView.loadFinished.connect(reloader.pageLoaded)

if __name__ == "__main__":
	hdlr = WatchedFileHandler('vclient.log')
	hdlr.setFormatter(formatter)
	log.addHandler(hdlr)
	log.setLevel(logging.DEBUG)

	log.debug('Main PID: %i' % (os.getpid(),))
	# save pid
	with open('vclient.pid', 'w') as f:
		f.write('%i' % (os.getpid(),))
	subprocess.call(shlex.split('xset dpms 0 0 0'))
	app = QtGui.QApplication(sys.argv)
	ds = VPlanMainWindow()
	ds.start()
	app.exec_()
