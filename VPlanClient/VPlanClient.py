#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: fenc=utf-8:ts=4:sw=4:si:sta:noet
from ui_browser import *
from ui_about import *
from ui_url import *
from Printer import Printer
from OpenSSL import SSL
from configparser import SafeConfigParser
from PyQt5.QtCore import QObject, QThread, pyqtSignal, pyqtSlot, pyqtProperty, QBuffer, QByteArray, QIODevice, QMutex, QMutexLocker, QTimer
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkDiskCache, QNetworkRequest, QNetworkProxy, QAuthenticator, QNetworkReply
from PyQt5.QtWebKitWidgets import QWebPage
from PyQt5 import QtGui, QtWebKit, QtCore, QtWidgets
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
from urllib.request import urlopen, URLopener
from urllib.parse import urlencode
import sys, os, socket, select, uuid, signal, queue, random, logging, abc, json, atexit, shlex, subprocess, zlib
import binascii, pickle, base64, traceback, urllib, urllib.request

__author__  = 'Lukas Schreiner'
__copyright__ = 'Copyright (C) 2012 - 2015 Website-Team Friedrich-List-Schule-Wiesbaden'
__version__ = 0.8

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

	# FIXME: make it configurable and not fix! (Like a string...)
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
	sigGetState = pyqtSignal()

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
		self.scrShotUrl = None

		# Initialize context
		self.ctx = SSL.Context(SSL.TLSv1_2_METHOD)
		self.ctx.set_options(SSL.OP_NO_SSLv2|SSL.OP_NO_TLSv1|SSL.OP_NO_SSLv3)
		self.ctx.set_verify(SSL.VERIFY_PEER|SSL.VERIFY_FAIL_IF_NO_PEER_CERT, verify_cb)
		self.ctx.use_privatekey_file(self.config.get('connection', 'privKey'))
		self.ctx.use_certificate_file(self.config.get('connection', 'pubKey'))
		self.ctx.load_verify_locations(os.path.abspath(self.config.get('connection', 'caCert')).encode('utf-8'))
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

	@pyqtSlot(str)
	def sendState(self, state):
		self.addData('go%s;;' % (state.capitalize(),))

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
			url = self.scrShotUrl
			if url is not None and len(url.strip()) > 0:
				log.debug('Try to open URL: %s' % (url,))
				img = string_io.getvalue()
				data = {'img': img}

				# Set the opener with private, public key.
				opener = URLopener(
					key_file=self.connection.get('connection', 'privKey'),
					cert_file=self.connection.get('connection', 'pubKey'),
					cafile=self.connection.get('connection', 'caCert')
				)

				# Do we have basic auth?
				if len(self.connection.get('connection', 'username').strip()) > 0:
					authEncoded = base64.b64encode(
						('%s:%s' % (self.connection.get('connection', 'username'), 
							self.connection.get('connection', 'password'))).encode('utf-8')
					).decode('utf-8')[:-1]
					opener.addheader("Authorization", 'Basic %s' % (authEncoded,))

				# We send data through POST.
				opener.addheader('Content-type', 'application/x-www-form-urlencoded')
				try:
					r = opener.open(url, None if data is None else urlencode(data))
					content = r.readline().decode('utf-8')
					log.debug('Got data: %s' % (content,))
					if r.code == 200:
						log.debug('Got data with success')
					else:
						log.error('Got wrong status code from cms...')
				except Exception as e:
					log.error('Could not open %s (%s)' % (url, str(e)))
			self.addData('screenshot;update;')
			self.scrshotSend = True

	def connect(self):
		tryNr = 0
		wait = 1
		if self.config.getboolean('connection', 'ssl'):
			self.sock = SSL.Connection(self.ctx, socket.socket(socket.AF_INET, socket.SOCK_STREAM))
		else:
			self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

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
		quit = False
		code, msg, *args = cmd.rstrip().split(' - ')
		log.debug('%s: %s' % (code, msg))

		# TODO: make constants for the codes similiar as in dsb.py!
		if code == '201':
			log.info('OK... our request is in processing but we have to wait for communication with the cms.')
		elif code == '202' or code == '205':
			log.info('We got a new message... analysing the target.')
			# because the msg could contain " - " we have to recreate the data.
			if len(args) > 0:
				pMsg = ' - '.join([msg, ' - '.join(args)])
			else:
				pMsg = msg

			self.processMessage(pMsg)
		elif code == '203':
			log.info('Ok. Version is up to date.')
			# now register!
			self.addData('register;%s;%s;%s' % (self.getMachineID(), self.getHostname(), __version__))
		elif code == '204':
			self.config.set('connection', 'dsbName', msg)
			self.addData('getConfig;;')
			self.addData('getScrShotUrl;;')
		elif code == '303':
			log.info('Ok. Version is sufficient but there is a new version?')
			# FIXME update the vplan client?
			pass
		elif code == '402':
			# uhhh we have a version mismatch!
			log.critical('Version mismatch - you need at least "%s"' % (msg,))
			quit = True
		elif code == '403':
			# uhhh we don't have permission to connect! Close!
			log.critical('No authorization ("%s") - will exit!' % (msg,))
			quit = True
		elif code == '621':
			log.info('Can\'t go offline. Ignore events.')
		elif code == '623':
			# we are now in idle mode. So we will wait for commands.
			self.sigHideEBB.emit()
		elif code == '622':
			log.info('Marked as offline. Accept close events.')
			# i'm offline. Stop application!
			# we should have a specific things in events..
			# bug 2014-07-27 LUS: only trigger this if we are not MDC (otherwise we would have a loop)
			if not self.config.getboolean('mdc', 'enable'):
				self.sigHideEBB.emit()
			self.addData('exit;;')
			self.addData('exit')
			# do not make a single quit. If we are offline. Than shutdown. 
			if self.config.getboolean('mdc', 'enable'):
				Thread(target=self.executeShutdown).start()
			else:
				self.sigQuitEBB.emit()
		elif code == '625':
			self.sigShowEBB.emit()
		elif code == '626':
			self.runState = False
			# connection will be closed! Don't observe anymore!
			self.sigQuitEBB.emit()
		elif code == '701':
			# now we got the url.
			self.scrShotUrl = msg

		return quit

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
		# we will go offline!!! do not sent him an goIdle, because in sigHideEBB he sent already an offline!
		if not self.config.getboolean('mdc', 'enable'):
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
		# use min. 3s !!!
		Thread(target=self.executeShutdown).start()

	def executeShutdown(self):
		log.info('Waiting 3sec before shutdown!')
		try:
			sleep(3)
		except:
			pass
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

	def evtGetState(self, msg):
		log.info('CMS / PyTools requests our state.')
		log.debug('[evtGetState] First funfact: we live.')
		self.sigGetState.emit()

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
			self.addData('version;%s;' % (__version__,))
			# reset screenshot
			self.scrshotSend = True

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
							quit = False
							for cmdData in newData.decode('utf-8').split('\n'):
								if len(cmdData.strip()) > 0:
									quit = self.parseCommand(cmdData)
									if quit:
										break
							if not quit:
								self.poller.modify(s, DsbServer.READ_WRITE)
							else:
								log.info('Disconnect...')
								self.poller.unregister(s)
								self.runState = False
								s.shutdown(socket.SHUT_WR)
								s.close()
								self.sock = None
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
							nextMsg += '\n'
							if not nextMsg.startswith('screenshot'):
								log.debug('sending msg %s' % (nextMsg,))
								s.sendall(nextMsg.encode('utf-8'))
							elif nextMsg.startswith('screenshot;eof;'):
								self.scrshotSend = True
								log.debug('sending a screenshot.')
								s.sendall(nextMsg.encode('utf-8'))
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
			nextMsg += '\n'
			log.debug('sending data')
			self.sock.send(nextMsg.encode('utf-8'))

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

class VPlanAbout(QtWidgets.QDialog):
	def __init__(self, parentMain):
		QtWidgets.QDialog.__init__(self, parent=parentMain)
		self.config = globConfig
		self.numTry = 0

		self.ui = Ui_About()
		self.ui.setupUi(self)

		self.autostart()

	def autostart(self):
		# wait - what should i do?
		# set version!
		self.ui.textVersion.setText(str(__version__))
		self.ui.textVersionQt.setText(
				'PyQt-Version: %s / Qt-Version: %s' % (QtCore.PYQT_VERSION_STR, QtCore.QT_VERSION_STR)
		)
		self.ui.textVersionPy.setText(sys.version)

		self.show()

class VPlanURL(QtWidgets.QDialog):
	def __init__(self, parentMain):
		QtWidgets.QDialog.__init__(self, parent=parentMain)
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
		self.flsConfig.set('app', 'mode', mode)
		self.flsConfig.save(False)
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

class VPlanMainWindow(QtWidgets.QMainWindow):
	sigQuitEBB = pyqtSignal()
	sigSndScrShot = pyqtSignal(QtGui.QPixmap)
	sigSendState = pyqtSignal(QObject)

	NOTIFY_PAGE = "TvVplan.processMessage('{MSG}')"
	NOTIFY_CONFIG = "TvVplan.configChanged()"
	NOTIFY_SUSPEND = 'TvVplan.suspendTv()'
	NOTIFY_RESUME = 'TvVplan.resumeTv()'

	def __init__(self):
		QtWidgets.QMainWindow.__init__(self)
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
		self.server.sigGetState.connect(self.sendEbbState)
		self.sigQuitEBB.connect(self.server.quitEBB)
		self.sigSendState.connect(self.server.sendState)
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
		log.info('Quitting eBB. Wait 5 sec. for communication with pyTools.')
		# wait 2 sec!
		self.timer = QTimer()
		self.timer.setInterval(5000)
		self.timer.setSingleShot(True)
		self.timer.timeout.connect(self.quitHard)
		self.timer.start()

	def quitHard(self):
		log.info('Quit hard now!')
		self.server.runState = False
		self.server = None
		QtWidgets.QApplication.quit()

	@pyqtSlot(str)
	def notification(self, state):
		if state == 'configChanged':
			timerActive = self.scrShotTimer.isActive()
			if timerActive:
				self.scrShotTimer.stop()
			self.scrShotTimer.setInterval(self.config.getint('options', 'scrShotInterval')*1000)
			if timerActive:
				self.scrShotTimer.start()
			del timerActive
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
		self.ui.webView.loadProgress.connect(self.ui.progressBar.setValue)

	def disableProgressBar(self):
		self.ui.webView.loadProgress.disconnect(self.ui.progressBar.setValue)
		self.ui.progressBar.deleteLater()
		self.ui.verticalLayout.removeWidget(self.ui.progressBar)
		self.ui.progressBar = None

	def setActions(self):
		# Exit (Ctrl+Q)
		self.exit = QtWidgets.QAction(QtGui.QIcon(''), 'Verlassen', self)
		self.exit.setShortcut(self.config.get('shortcuts', 'quit'))
		self.exit.triggered.connect(self.close)
		self.addAction(self.exit)

		# Fullscreen (F11)
		self.fullScreen = QtWidgets.QAction(QtGui.QIcon(''), 'Vollbild an/aus', self)
		self.fullScreen.setShortcut(self.config.get('shortcuts', 'fullscreen'))
		self.fullScreen.triggered.connect(self.toggleScreen)
		self.addAction(self.fullScreen)

		# Toggle progressbar (F9)
		self.toggleProgress = QtWidgets.QAction(QtGui.QIcon(''), 'Progressbar an/aus', self)
		self.toggleProgress.setShortcut(self.config.get('shortcuts', 'toggleProgressBar'))
		self.toggleProgress.triggered.connect(self.toggleProgressBar)
		self.addAction(self.toggleProgress)

		# Reload planer (F5)
		self.actReload = QtWidgets.QAction(QtGui.QIcon(''), 'Neuladen', self)
		self.actReload.setAutoRepeat(self.config.getboolean('browser', 'autoRepeatReload'))
		self.actReload.setShortcut(self.config.get('shortcuts', 'reload'))
		self.actReload.triggered.connect(self.reload)
		self.addAction(self.actReload)

		# Browser: stop (Esc)
		self.actStop = QtWidgets.QAction(QtGui.QIcon(''), 'Stop', self)
		self.actStop.setShortcut(self.config.get('shortcuts', 'browserStop'))
		self.actStop.triggered.connect(self.ui.webView.stop)
		self.addAction(self.actStop)

		# Browser: forward (Alt+Right)
		self.actForward = QtWidgets.QAction(QtGui.QIcon(''), 'Forward', self)
		self.actForward.setShortcut(self.config.get('shortcuts', 'browserForward'))
		self.actForward.triggered.connect(self.ui.webView.forward)
		self.addAction(self.actForward)

		# Browser: Back (Alt+Left)
		self.actBack = QtWidgets.QAction(QtGui.QIcon(''), 'Back', self)
		self.actBack.setShortcut(self.config.get('shortcuts', 'browserBack'))
		self.actBack.triggered.connect(self.ui.webView.back)
		self.addAction(self.actBack)

		# About window (F1)
		self.actAbout = QtWidgets.QAction(QtGui.QIcon(''), 'Über', self)
		self.actAbout.setShortcut(self.config.get('shortcuts', 'about'))
		self.actAbout.triggered.connect(self.showAbout)
		self.addAction(self.actAbout)

		# Go to url... (F2)
		self.actURL = QtWidgets.QAction(QtGui.QIcon(''), 'Neue URL', self)
		self.actURL.setAutoRepeat(False)
		self.actURL.setShortcut(self.config.get('shortcuts', 'newURL'))
		self.actURL.triggered.connect(self.newURL)
		self.addAction(self.actURL)

		# we will set zoom factor ;)
		# increase Zoom factor of planer
		self.actIncZoom = QtWidgets.QAction(QtGui.QIcon(''), 'Plan vergrößern', self)
		self.actIncZoom.setShortcut(self.config.get('shortcuts', 'incZoom'))
		self.actIncZoom.triggered.connect(self.incZoom)
		self.addAction(self.actIncZoom)

		# decrease Zoom factor of planer
		self.actDecZoom = QtWidgets.QAction(QtGui.QIcon(''), 'Plan verkleinern', self)
		self.actDecZoom.setShortcut(self.config.get('shortcuts', 'decZoom'))
		self.actDecZoom.triggered.connect(self.decZoom)
		self.addAction(self.actDecZoom)

		# reset Zoom factor of planer
		self.actResetZoom = QtWidgets.QAction(QtGui.QIcon(''), 'Planzoom zurücksetzen', self)
		self.actResetZoom.setShortcut(self.config.get('shortcuts', 'resetZoom'))
		self.actResetZoom.triggered.connect(self.resetZoom)
		self.addAction(self.actResetZoom)

		# start debugger
		self.actStartDebug = QtWidgets.QAction(QtGui.QIcon(''), 'Debugger starten', self)
		self.actStartDebug.setShortcut(self.config.get('shortcuts', 'debugConsole'))
		self.actStartDebug.triggered.connect(self.startDebug)
		self.addAction(self.actStartDebug)

		# Loading finished (bool) 
		self.ui.webView.loadFinished.connect(self.handleLoadReturn)

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
		exitCode  = subprocess.call(shlex.split('xset -dpms'))
		exitCode += subprocess.call(shlex.split('xset s noblank'))
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
		else:
			self.ui.webView.page().mainFrame().evaluateJavaScript(VPlanMainWindow.NOTIFY_RESUME)

	@pyqtSlot()
	def hideEBB(self):
		# stop scrshot!
		self.scrShotTimer.stop()
		self.hide()

		exitCode  = subprocess.call(shlex.split('xset +dpms'))
		exitCode += subprocess.call(shlex.split('xset s blank'))
		exitCode += subprocess.call(shlex.split('xset s expose'))
		exitCode += subprocess.call(shlex.split('xset s on'))
		log.info('Screensaver turned on %s' % ('successful' if exitCode == 0 else 'with errors',))
		self.ui.webView.page().mainFrame().evaluateJavaScript(VPlanMainWindow.NOTIFY_SUSPEND)
		# if we are connected with MDC, shutdown directly. That's the best.
		if self.config.getboolean('mdc', 'enable'):
			# first send "go offline event"
			self.server.quitEBB()
			log.info('We are running with MDC. Lets shutdown because of hidding the eBB.')
			# wait min. 3s !!!
			Thread(target=self.server.executeShutdown).start()

	@pyqtSlot()
	def createScreenshot(self):
		if self.server.runState and self.isVisible():
			log.debug('Create screenshot')
			win = QtGui.QGuiApplication.topLevelWindows()
			if len(win) > 0:
				win = win[0]
				screen = QtGui.QGuiApplication.primaryScreen()
				if screen:
					scrShot = screen.grabWindow(win.winId())
					if self.config.getint('options', 'scrShotSize') > 0:
						scrShot = scrShot.scaledToWidth(self.config.getint('options', 'scrShotSize'))
					self.sigSndScrShot.emit(scrShot)
		else:
			log.debug('Screenshot canceled (runState: %s ; Visible: %s).' % (self.server.runState, self.isVisible()))

	@pyqtSlot(DsbMessage)
	def dsbMessage(self, msg):
		log.info('We got a message for the ebb: %s.' % (msg.toJson(),))
		self.ui.webView.page().mainFrame().evaluateJavaScript(VPlanMainWindow.NOTIFY_PAGE.format(MSG=msg.toJson()))

	@pyqtSlot()
	def sendEbbState(self):
		if self.isVisible():
			self.sigSendState.emit('online')
		else:
			self.sigSendState.emit('idle')

	def autostart(self):
		title = self.config.get('app', 'title')
		self.setWindowTitle(QtWidgets.QApplication.translate("MainWindow", title, None))

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
			self.reloader.reloader.connect(self.reloadChild)
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
	app = QtWidgets.QApplication(sys.argv)
	ds = VPlanMainWindow()
	ds.start()
	app.exec_()
