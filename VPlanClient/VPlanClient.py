#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: fenc=utf-8:ts=4:sw=4:si:sta:noet
from Printer import Printer
from OpenSSL import SSL
from configparser import SafeConfigParser
from html.parser import HTMLParser
from PyQt5.QtCore import QObject, QThread, pyqtSignal, pyqtSlot, pyqtProperty, QBuffer, QByteArray, QIODevice, QMutex
from PyQt5.QtCore import QMutexLocker, QTimer, QUrl, QVariant, QFile, QFileInfo, QUuid
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkDiskCache, QNetworkRequest, QNetworkProxy, QAuthenticator, QNetworkReply
from PyQt5.QtWebKitWidgets import QWebPage
from PyQt5.QtQuick import QQuickView
from PyQt5.QtQml import qmlRegisterType
from PyQt5.QtGui import QScreen
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
from urllib.parse import urlencode, urljoin
import sys, os, socket, select, uuid, signal, queue, random, logging, abc, json, atexit, shlex
import binascii, pickle, base64, traceback, urllib, urllib.request, subprocess, zlib, datetime
import popplerqt5, shutil

__author__  = 'Lukas Schreiner'
__copyright__ = 'Copyright (C) 2012 - 2015 Website-Team Friedrich-List-Schule-Wiesbaden'
__version__ = 0.9

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
flsConfig = FLSConfiguration(os.path.join(workDir,'fls_config.ini'))
ds = None

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
	urlLoaded = pyqtSignal()
	connected = pyqtSignal()
	disconnected = pyqtSignal()

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

		# obtain them from pyTools.
		self.baseUrl = None
		self.scrShotUrl = None
		self.loadPlanUrl = None
		self.loadNewsUrl = None
		self.loadAnnouncementUrl = None
		self.loadContentUrl = None

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
					key_file=self.config.get('connection', 'privKey'),
					cert_file=self.config.get('connection', 'pubKey'),
					cafile=self.config.get('connection', 'caCert')
				)

				# Do we have basic auth?
				if len(self.config.get('connection', 'username').strip()) > 0:
					authEncoded = base64.b64encode(
						('%s:%s' % (self.config.get('connection', 'username'), 
							self.config.get('connection', 'password'))).encode('utf-8')
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

		self.connected.emit()

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
			self.addData('getUrls;;')
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
			urls = json.loads(msg)
			self.baseUrl = urls['base']
			self.scrShotUrl = urls['screenshot']
			self.loadPlanUrl = urls['plan'] + '?raw=1&clientId=' + self.getMachineID()
			self.loadNewsUrl = urls['news'] + '?raw=1&clientId=' + self.getMachineID()
			self.loadAnnouncementUrl = urls['announcement'] + '?raw=1&clientId=' + self.getMachineID()
			self.loadContentUrl = urls['content'] + '?raw=1&clientId=' + self.getMachineID()
			self.urlLoaded.emit()

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

			self.disconnected.emit()

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

class EbbPlanHandler(QObject):
	siteReload = pyqtSignal()
	flsConfigLoaded = pyqtSignal()
	ebbConfigLoaded = pyqtSignal()
	connected = pyqtSignal()
	suspendTv = pyqtSignal()
	resumeTv = pyqtSignal()
	loadDesignPictures = pyqtSignal([QUrl, QUrl], arguments=['headerCenterUrl', 'headerRptUrl'])
	# timer signals
	timerChange = pyqtSignal([QVariant, QVariant, QVariant], arguments=['vplanInterval', 'newsInterval', 'annoInterval'])
	 
	# model signals
	newsAdded = pyqtSignal([QVariant], arguments=['news'])
	newsUpdate = pyqtSignal([QVariant], arguments=['news'])
	newsDeleted = pyqtSignal([QVariant], arguments=['newsId'])
	announcementAdded = pyqtSignal([QVariant], arguments=['anno'])
	announcementUpdate = pyqtSignal([QVariant], arguments=['anno'])
	announcementDelete = pyqtSignal([QVariant], arguments=['annoId'])
	planAvailable = pyqtSignal([QVariant, QVariant, str], arguments=['newDayList', 'newPlanList', 'newStand'])
	planColSizeChanged = pyqtSignal([QVariant], arguments=['planSizes'])
	cycleTimesChanged = pyqtSignal([QVariant, QVariant, QVariant, QVariant], arguments=['newsTime', 'annoTime', 'planTime', 'contentTime'])

	def __init__(self, parent=None):
		QObject.__init__(self, parent)
		# workaround to set these things from the beginning!
		global globConfig
		global flsConfig
		self.ebbConfig = globConfig
		self.flsConfig = flsConfig
		self.ready = False
		self.maxEntries = 0
		self.vplanInterval = 4
		self.newsInterval = 7
		self.annoInterval = 4
		self.uuidGenerator = QUuid()

	def setEbbConfig(self, config):
		self.ebbConfig = config
		self.ebbConfigLoaded.emit()
		if self.ebbConfig.getint('appearance', 'plan_cycle_time') != self.vplanInterval \
		 or self.ebbConfig.getint('appearance', 'news_cycle_time') != self.newsInterval \
		 or self.ebbConfig.getint('appearance', 'announcement_cycle_time') != self.annoInterval:
		 	self.vplanInterval = self.ebbConfig.getint('appearance', 'plan_cycle_time')
		 	self.newsInterval = self.ebbConfig.getint('appearance', 'news_cycle_time')
		 	self.annoInterval = self.ebbConfig.getint('appearance', 'announcement_cycle_time')
		 	self.timerChange.emit(
		 		QVariant(self.vplanInterval*1000), 
		 		QVariant(self.newsInterval*1000), 
		 		QVariant(self.annoInterval*1000)
	 		)

	def setFlsConfig(self, config):
		self.flsConfig = config
		self.flsConfigLoaded.emit()

	@pyqtSlot(int)
	def setMaxEntries(self, no):
		self.maxEntries = no

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
		self.siteReload.emit()
		log.info('js wants me to reload!')

	def _config(self):
		return self.ebbConfig.toJson()

	def _flsConfig(self):
		return self.flsConfig.toJson()

	def _machineId(self):
		return self.ebbConfig.get('connection', 'machineId')

	def _showFutureDays(self):
		# school start
		if self.ebbConfig.getboolean('appearance', 'filter_tomorrow'):
			now = datetime.datetime.now()
			after  = self.flsConfig.getint('vplan', 'school_start')
			after += self.ebbConfig.getint('appearance', 'filter_tomorrow_time')
			base  = datetime.datetime.now().replace(hour=0, minute=0, second=0)
			base += datetime.timedelta(minutes=after)
			return now >= base
		else: 
			return True

	def _generateUuid(self):
		return str(self.uuidGenerator.createUuid().toString())

	def _leftColumnTitle(self):
		return self.flsConfig.get('vplan_tv', 'leftDescription')


	def _rightColumnTitle(self):
		return self.flsConfig.get('vplan_tv', 'rightDescription')

	@pyqtSlot()
	def onConnected(self):
		self.connected.emit()

	config = pyqtProperty(str, fget=_config)
	flscfg = pyqtProperty(str, fget=_flsConfig)
	machineId = pyqtProperty(str, fget=_machineId)
	showFutureDays = pyqtProperty(bool, fget=_showFutureDays)
	generateUuid = pyqtProperty(str, fget=_generateUuid)
	leftTitle = pyqtProperty(str, fget=_leftColumnTitle)
	rightTitle = pyqtProperty(str, fget=_rightColumnTitle)

class EbbContentHandler(QObject):
	modeChanged = pyqtSignal(QVariant, arguments=['toMode'])
	flsConfigLoaded = pyqtSignal()
	ebbConfigLoaded = pyqtSignal()
	connected = pyqtSignal()
	suspendTv = pyqtSignal()
	resumeTv = pyqtSignal()
	# presenter
	contentAssigned = pyqtSignal()
	contentDeassigned = pyqtSignal()
	pageAdded = pyqtSignal([QVariant], arguments=['pdfPagePath'])
	# content page
	contentBodyChanged = pyqtSignal()
	contentArrowChanged = pyqtSignal([float], arguments=['newDirection'])
	# firealarm page
	fireArrowChanged = pyqtSignal([float], arguments=['newDirection'])

	def __init__(self, parent=None):
		QObject.__init__(self, parent)
		# workaround to set these things from the beginning!
		global globConfig
		global flsConfig
		self.ebbConfig = globConfig
		self.flsConfig = flsConfig
		self.prevContentArrow = 0
		self.prevFireArrow = 0
		self.currentMode = 'default'
		self.contentBody = ''

	def setEbbConfig(self, config):
		self.ebbConfig = config
		self.ebbConfigLoaded.emit()
		if self.prevContentArrow != self.ebbConfig.getfloat('appearance', 'content_direction'):
			self.contentArrowChanged.emit(self._contentArrow())
			self.prevContentArrow = self.ebbConfig.getfloat('appearance', 'content_direction')
		if self.prevFireArrow != self.ebbConfig.getfloat('appearance', 'escape_route_direction'):
			self.fireArrowChanged.emit(self._fireArrow())
			self.prevFireArrow = self.ebbConfig.getfloat('appearance', 'escape_route_direction')
		if self.currentMode != self.ebbConfig.get('app', 'mode'):
			self.currentMode = self.ebbConfig.get('app', 'mode')
			self.modeChanged.emit(self.currentMode)

	def setFlsConfig(self, config):
		self.flsConfig = config
		self.flsConfigLoaded.emit()

	def _config(self):
		return self.ebbConfig.toJson()

	def _flsConfig(self):
		return self.flsConfig.toJson()

	def _machineId(self):
		return self.ebbConfig.get('connection', 'machineId')

	def _contentArrow(self):
		return self.ebbConfig.getfloat('appearance', 'content_direction')

	def _contentBody(self):
		return QVariant(self.contentBody)

	def _fireArrow(self):
		return self.ebbConfig.getfloat('appearance', 'escape_route_direction')

	def _cycleTime(self):
		return self.ebbConfig.getint('appearance', 'content_cycle_time')*1000

	config = pyqtProperty(str, fget=_config)
	flscfg = pyqtProperty(str, fget=_flsConfig)
	machineId = pyqtProperty(str, fget=_machineId)
	contentArrow = pyqtProperty(float, fget=_contentArrow)
	contentText = pyqtProperty(QVariant, fget=_contentBody)
	fireArrow = pyqtProperty(float, fget=_fireArrow)
	cycleTime = pyqtProperty(float, fget=_cycleTime)

	@pyqtSlot()
	def onConnected(self):
		self.connected.emit()

class VPlanMainWindow(QQuickView):
	sigQuitEBB = pyqtSignal()
	sigSndScrShot = pyqtSignal(QtGui.QPixmap)
	sigSendState = pyqtSignal(QVariant)
	sysTermSignal = pyqtSignal()

	def __init__(self, app):
		QtWidgets.QMainWindow.__init__(self)
		global flsConfig
		global globConfig
		self._notifyReceiver = NotifyReceiver(self)
		self.config = globConfig
		self.config.addObserver(self)
		self.flsConfig = flsConfig
		self.flsConfig.addObserver(self)
		self.server = None
		self.quitTimer = None
		self.dayChangeTimer = QTimer()
		self.dayChangeTimer.setSingleShot(True)
		self.elapsedHourTimer = QTimer()
		self.elapsedHourTimer.setSingleShot(True)
		self.loaded = False
		self.app = app

		# our screenshot timer.
		self.scrShotTimer = QTimer()
		self.scrShotTimer.setSingleShot(False)
		self.scrShotTimer.setInterval(self.config.getint('options', 'scrShotInterval')*1000)
		self.scrShotTimer.timeout.connect(self.createScreenshot)

		self.setTitle(self.config.get('app', 'title'))
		self.setSource(QUrl(os.path.join(workDir, 'ui', 'main.qml')))
		self.setResizeMode(QQuickView.SizeRootObjectToView)

		rootContext = self.rootContext()
		rootObject = self.rootObject()
		self.ebbPlanHandler = rootObject.findChild(EbbPlanHandler, 'ebbPlanHandler')
		self.ebbPlanHandler.setEbbConfig(self.config)
		self.ebbPlanHandler.setFlsConfig(self.flsConfig)
		self.ebbContentHandler = rootObject.findChild(EbbContentHandler, 'ebbContentHandler')
		self.ebbContentHandler.setEbbConfig(self.config)
		self.ebbContentHandler.setFlsConfig(self.flsConfig)

		self.manager = QNetworkAccessManager()
		self.manager.finished.connect(self.dataLoadFinished)

		self.enableCache()
		self.enableProxy()
		
		self.setActions()
		self.calculateNextDayTimer()
		self.calculateNextHourTimer()

	def start(self):
		self.server = DsbServer(self)
		self.server.sigShowEBB.connect(self.showEBB)
		self.server.sigHideEBB.connect(self.hideEBB)
		self.server.sigQuitEBB.connect(self.quitEBB)
		self.server.sigNewMsg.connect(self.dsbMessage)
		self.server.sigCrtScrShot.connect(self.createScreenshot)
		self.server.sigGetState.connect(self.sendEbbState)
		self.server.urlLoaded.connect(self.loadPlanData)
		self.sigQuitEBB.connect(self.server.quitEBB)
		self.sigSendState.connect(self.server.sendState)
		self.sigSndScrShot.connect(self.server.sendScreenshot)
		self.ebbContentHandler.modeChanged.connect(self.server.changeMode)
		self.server.connected.connect(self.ebbPlanHandler.onConnected)
		self.server.connected.connect(self.ebbContentHandler.onConnected)

		self.server.start()

	def closeEvent(self, e):
		# first we try to send an offline signal to server!
		log.info('"Quit EBB" -> sending signal!')
		self.sigQuitEBB.emit()

		# we have to ignore it...
		e.ignore()

	@pyqtSlot()
	def handleTermSignal(self):
		log.info('Got a term signal (SIGTERM). Quitting.')
		self.sigQuitEBB.emit()

	@pyqtSlot()
	def quitEBB(self):
		self.scrShotTimer.stop()
		log.info('Quitting eBB. Wait 5 sec. for communication with pyTools.')
		self.hide()
		# wait 5 sec!
		self.quitTimer = QTimer()
		self.quitTimer.setInterval(5000)
		self.quitTimer.setSingleShot(True)
		self.quitTimer.timeout.connect(self.quitHard)
		self.quitTimer.start()

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
			if self.config.getint('options', 'scrShotInterval') > 0:
				self.scrShotTimer.start()
			del timerActive
			if self.config.getboolean('appearance', 'filter_elapsed_hour'):
				self.elapsedHourTimer.stop()
				self.calculateNextHourTimer()

			# inform the two js handlers.
			self.ebbPlanHandler.setFlsConfig(self.flsConfig)
			self.ebbPlanHandler.setEbbConfig(self.config)
			self.ebbContentHandler.setFlsConfig(self.flsConfig)
			self.ebbContentHandler.setEbbConfig(self.config)

	@pyqtSlot()
	def dayChangeTimerHook(self):
		log.info('Day changed...')

		# request for plan:
		req = QNetworkRequest(QUrl(self.server.loadPlanUrl))
		req.setPriority(QNetworkRequest.HighPriority)
		self.manager.get(req)

		self.calculateNextDayTimer()

	@pyqtSlot()
	def elapsedHourTimerHook(self):
		log.info('Hour changed -- reload plan...')

		# request for plan:
		req = QNetworkRequest(QUrl(self.server.loadPlanUrl))
		req.setPriority(QNetworkRequest.HighPriority)
		self.manager.get(req)

		self.calculateNextHourTimer()

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

	def setActions(self):
		# handler
		self.sysTermSignal.connect(self.handleTermSignal)
		# if page requires username / password
		self.manager.authenticationRequired.connect(self.setBasicAuth)
		# day change timer
		self.dayChangeTimer.timeout.connect(self.dayChangeTimerHook)
		# remove elapsed hour hook...
		self.elapsedHourTimer.timeout.connect(self.elapsedHourTimerHook)
	
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

	def calculateNextDayTimer(self):
		now = datetime.datetime.now()
		# in the night, 1-5 minutes are no problems.
		destination = (now + datetime.timedelta(days=1)).replace(hour=0, minute=3, second=0)
		self.dayChangeTimer.setInterval(round((destination-now).total_seconds()*1000))
		# and now start...
		self.dayChangeTimer.start()
		log.info('Next event of nextDayTimer: %s milliseconds' % (str(self.dayChangeTimer.interval()),))

	def calculateNextHourTimer(self):
		if not self.config.getboolean('appearance', 'filter_elapsed_hour'):
			return

		now = datetime.datetime.now()
		# in the night, 1-5 minutes are no problems.
		destination = (now + datetime.timedelta(hours=1)).replace(minute=self.config.getint('appearance', 'filter_elapsed_hour_buffer'), second=5)
		self.elapsedHourTimer.setInterval(round((destination-now).total_seconds()*1000))
		# and now start...
		self.elapsedHourTimer.start()
		log.info('Next event of nextHourTimer: %s milliseconds' % (str(self.elapsedHourTimer.interval()),))

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

		if self.config.getint('options', 'scrShotInterval') > 0:
			self.scrShotTimer.start()

		self.ebbPlanHandler.resumeTv.emit()
		self.ebbContentHandler.resumeTv.emit()

	@pyqtSlot()
	def hideEBB(self):
		# stop scrshot!
		self.scrShotTimer.stop()
		self.ebbPlanHandler.suspendTv.emit()
		self.ebbContentHandler.suspendTv.emit()
		self.hide()

		exitCode  = subprocess.call(shlex.split('xset +dpms'))
		exitCode += subprocess.call(shlex.split('xset s blank'))
		exitCode += subprocess.call(shlex.split('xset s expose'))
		exitCode += subprocess.call(shlex.split('xset s on'))
		log.info('Screensaver turned on %s' % ('successful' if exitCode == 0 else 'with errors',))
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
			screen = self.screen()
			if screen:
				scrShot = screen.grabWindow(self.winId())
				if self.config.getint('options', 'scrShotSize') > 0:
					scrShot = scrShot.scaledToWidth(self.config.getint('options', 'scrShotSize'))
				self.sigSndScrShot.emit(scrShot)
		else:
			log.debug('Screenshot canceled (runState: %s ; Visible: %s).' % (self.server.runState, self.isVisible()))

	@pyqtSlot(DsbMessage)
	def dsbMessage(self, msg):
		log.info('We got a message for the ebb: %s.' % (msg.toJson(),))
		# FIXME: we need to handle it by ourself!
		if msg.action == DsbMessage.ACTION_NEWS:
			news = msg.value
			if msg.event == DsbMessage.EVENT_CREATE:
				# extract image if there is an image.
				parser = ContentImageFinder()
				parser.feed(news['text'])
				# did we found an image?
				if len(parser.image) > 0:
					imgUrl = urljoin(self.server.baseUrl, parser.image)
				else:
					imgUrl = ''
				news['imgUrl'] = imgUrl
				self.ebbPlanHandler.newsAdded.emit(QVariant(news))
			elif msg.event == DsbMessage.EVENT_CHANGE:
				# extract image if there is an image.
				parser = ContentImageFinder()
				parser.feed(news['text'])
				# did we found an image?
				if len(parser.image) > 0:
					imgUrl = urljoin(self.server.baseUrl, parser.image)
				else:
					imgUrl = ''
				news['imgUrl'] = imgUrl
				self.ebbPlanHandler.newsUpdate.emit(QVariant(news))
			elif msg.event == DsbMessage.EVENT_DELETE:
				self.ebbPlanHandler.newsDeleted.emit(QVariant(msg.id))
		elif msg.action == DsbMessage.ACTION_ANNOUNCEMENT:
			anno = msg.value
			if msg.event == DsbMessage.EVENT_CREATE:
				self.ebbPlanHandler.announcementAdded.emit(QVariant(anno))
			elif msg.event == DsbMessage.EVENT_CHANGE:
				if anno['release'] != '1':
					self.ebbPlanHandler.announcementDelete.emit(QVariant(msg.id))
				else:
					self.ebbPlanHandler.announcementUpdate.emit(QVariant(anno))
			elif msg.event == DsbMessage.EVENT_DELETE:
				self.ebbPlanHandler.announcementDelete.emit(QVariant(msg.id))
		elif msg.action == DsbMessage.ACTION_VPLAN:
			# request for plan again. 
			req = QNetworkRequest(QUrl(self.server.loadPlanUrl))
			req.setPriority(QNetworkRequest.HighPriority)
			self.manager.get(req)
		elif msg.action == DsbMessage.ACTION_INFOSCREEN:
			if msg.event == DsbMessage.EVENT_DELETE:
				# by default nothing here.
				self.ebbContentHandler.contentDeassigned.emit()
			else:
				dataContent = msg.value
				# by default nothing here.
				self.ebbContentHandler.contentDeassigned.emit()
				if dataContent is not None and type(dataContent).__name__ == 'dict' \
					and len(dataContent['pdfUrl']) > 0:
					# yes there is something defined.
					# but the converting is done by another thread - so that nothing is blocked.
					self.checkRequestContentPdf(dataContent['pdfUrl'])
				else:
					self.ebbContentHandler.contentDeassigned.emit()
					if dataContent is not None \
						and type(dataContent).__name__ == 'dict' \
						and self.ebbContentHandler.contentBody != dataContent['content']:
						self.ebbContentHandler.contentBody = dataContent['content']
						self.ebbContentHandler.contentBodyChanged.emit()
		elif msg.action == DsbMessage.ACTION_MODE:
			if msg.event == DsbMessage.EVENT_CHANGE:
				toMode = msg.value
				if toMode in ['content', 'default', 'firealarm']:
					self.ebbContentHandler.modeChanged.emit(QVariant(toMode))
					self.flsConfig.set('app', 'mode', toMode)
					self.flsConfig.save(False)
					self.server.changeMode(toMode)
				else:
					log.error('Invalid destination mode given: %s' % (toMode,))

	@pyqtSlot()
	def sendEbbState(self):
		if self.isVisible():
			self.sigSendState.emit('online')
		else:
			self.sigSendState.emit('idle')

	@pyqtSlot()
	def loadPlanData(self):
		if self.server.baseUrl is None:
			self.loaded = False
		elif self.loaded:
			return None
		else:
			self.loaded = True

		# request for plan:
		req = QNetworkRequest(QUrl(self.server.loadPlanUrl))
		req.setPriority(QNetworkRequest.HighPriority)
		self.manager.get(req)

		# request for news:
		newsCount = self.config.get('appearance', 'news_count')
		req = QNetworkRequest(QUrl(self.server.loadNewsUrl + '&count=' + newsCount))
		req.setPriority(QNetworkRequest.LowPriority)
		self.manager.get(req)

		# request for announcement:
		req = QNetworkRequest(QUrl(self.server.loadAnnouncementUrl))
		req.setPriority(QNetworkRequest.NormalPriority)
		self.manager.get(req)

		# request for content:
		req = QNetworkRequest(QUrl(self.server.loadContentUrl))
		req.setPriority(QNetworkRequest.NormalPriority)
		self.manager.get(req)

		# so... we need some graphics data for the design!
		headerCenterUrl = self.server.baseUrl + 'res/ebb/header_center.png'
		headerRptUrl = self.server.baseUrl + 'res/ebb/header_wdh.png'
		self.ebbPlanHandler.loadDesignPictures.emit(QUrl(headerCenterUrl), QUrl(headerRptUrl))

	@pyqtSlot(QNetworkReply)
	def dataLoadFinished(self, reply):
		# first retrieve the ebb content type (X-eBB-Type).
		if not reply.hasRawHeader('X-eBB-Type'.encode('utf-8')):
			dataType = 'binary'
		else:
			dataType = reply.rawHeader('X-eBB-Type'.encode('utf-8')).data().decode('utf-8')

		# are there any errors?
		if reply.error():
			# FIXME: give correct url / error.
			url = reply.url().toString()
			log.error('Could not download %s because of %s.' % (url, reply.errorString()))
			return False

		if dataType not in ['Plan', 'News', 'Announcement', 'Content']:
			# must be a PDF....
			self.finishedDownloadingPdf(reply)
			return False

		try:
			dataContent = json.loads(reply.readAll().data().decode('utf-8'))
		except ValueError:
			# no valid data returned.
			dataContent = None

		if dataType == 'Plan' and dataContent is not None:
			self.parseNewPlanData(dataContent)
		elif dataType == 'News' and dataContent is not None:
			for news in dataContent:
				# extract image if there is an image.
				parser = ContentImageFinder()
				parser.feed(news['text'])
				# did we found an image?
				if len(parser.image) > 0:
					imgUrl = urljoin(self.server.baseUrl, parser.image)
				else:
					imgUrl = ''
				news['imgUrl'] = imgUrl
				self.ebbPlanHandler.newsAdded.emit(QVariant(news))
		elif dataType == 'Announcement' and dataContent is not None:
			for anno in dataContent:
				if anno['release'] == '1':
					self.ebbPlanHandler.announcementAdded.emit(QVariant(anno))
		elif dataType == 'Content':
			""" 
			Example:
			{
				'pdfUrl': 'http://fls.local/files/ebbPdf/553cd6320fcddreceipt_quadre_du_net.pdf', 
				'cid': '14', 
				'arrow': True, 
				'modifyTime': '26.04.15 14:14', 'creator': 'Lukas Schreiner', 
				'pdf': 'ebbPdf/553cd6320fcddreceipt_quadre_du_net.pdf', 
				'modifier': 'Lukas Schreiner', 
				'createTime': '26.04.15 14:14', 
				'title': 'PPPPL', 
				'content': ''
			}
			"""
			# by default nothing here.
			self.ebbContentHandler.contentDeassigned.emit()
			if type(dataContent).__name__ != 'dict':
				dataContent = None
			if dataContent is not None and len(dataContent['pdfUrl']) > 0:
				# yes there is something defined.
				# but the converting is done by another thread - so that nothing is blocked.
				self.checkRequestContentPdf(dataContent['pdfUrl'])
			else:
				self.ebbContentHandler.contentDeassigned.emit()
				if dataContent is not None and self.ebbContentHandler.contentBody != dataContent['content']:
					self.ebbContentHandler.contentBody = dataContent['content']
					self.ebbContentHandler.contentBodyChanged.emit()

	def checkRequestContentPdf(self, pdfUrl):
		baseName = QFileInfo(pdfUrl).fileName()
		baseDir = os.path.join('ebbPdfs/', baseName)

		req = QNetworkRequest(QUrl(pdfUrl))
		req.setPriority(QNetworkRequest.LowPriority)
		if os.path.exists(os.path.join(baseDir, baseName)):
			# the pdf does already exist. So get the modified information.
			sta = os.stat(os.path.join(baseDir, baseName)).st_mtime
			dt = datetime.datetime.fromtimestamp(sta)
			modified = dt.strftime('%a, %d %b %Y %T GMT')
			req.setRawHeader('If-Modified-Since', modified)
		self.manager.get(req)

	def finishedDownloadingPdf(self, reply):
		downloadPath = reply.url().path()
		baseName = QFileInfo(downloadPath).fileName()
		sts = reply.attribute(QNetworkRequest.HttpStatusCodeAttribute)

		# print the header list
		date = reply.rawHeader('Date').data().decode('utf-8')
		# process only if it is a PDF / PS!
		contentType = reply.rawHeader('Content-Type').data().decode('utf-8')
		contentType = (contentType.split(';')[0]).strip().lower()
		if contentType not in ['application/pdf', 'application/ps']:
			log.info('File %s not a valid presentation file.' % (baseName,))
			return False

		baseDir = os.path.join('ebbPdfs/', baseName)
		if sts == '304':
			self.loadContentPages(baseDir)
			return True

		if os.path.exists(baseDir):
			# delete all in it.
			shutil.rmtree(baseDir)
		os.makedirs(baseDir)

		# now we can save the pdf.
		f = QFile(os.path.join(baseDir, baseName))
		f.open(QIODevice.WriteOnly)
		f.write(reply.readAll())
		f.close()

		# which resolution do we have?
		xDpi = 100
		yDpi = 100
		screen = self.screen()
		xDpi = round(screen.physicalDotsPerInchX(), 0) * 3
		yDpi = round(screen.physicalDotsPerInchY(), 0) * 3

		# now we can convert.
		doc = popplerqt5.Poppler.Document.load(os.path.join(baseDir, baseName))
		if doc is None:
			log.error('Could not convert the pdf document %s' % (os.path.join(baseDir, baseName),))
		else:
			self.ebbContentHandler.contentDeassigned.emit()
			pageCounter = 0
			p = 0
			while p < len(doc):
				pageName = 'page' + str(pageCounter) + '.jpg'
				if os.path.exists(os.path.join(baseDir, pageName)):
					os.unlink(os.path.join(baseDir, pageName))
				pag1 = QtGui.QPixmap.fromImage(doc.page(pageCounter).renderToImage(xDpi, yDpi))
				pag1.save(os.path.join(baseDir, pageName))

				self.ebbContentHandler.pageAdded.emit(QVariant(os.path.abspath(os.path.join(baseDir, pageName))))
				pageCounter += 1
				p += 1

			self.ebbContentHandler.contentAssigned.emit()

	def loadContentPages(self, baseDir):
		# retrieve all files of that folder.
		relevantFiles = [ f for f in os.listdir(baseDir) if f.endswith('.jpg') ]

		self.ebbContentHandler.contentDeassigned.emit()
		for f in relevantFiles:
			self.ebbContentHandler.pageAdded.emit(QVariant(os.path.abspath(os.path.join(baseDir, f))))

		if len(relevantFiles) > 0:
			self.ebbContentHandler.contentAssigned.emit()

	def parseNewPlanData(self, data):
		"""
		The dayList contains a list of days/dicts we show. It must fit more or less the structure in qml:
		1. day => contains the date in format dd.mm.yyyy
		2. abbr => contains the abbreviation of the weekday
		3. name => contains the full weekday name.
		4. txt => human readable formatted name -- e.g. Montag, 04.05.2015
		5. index => contains the start index in the planList.
		6. pages => tells us, how many pages are possible.
		"""
		dayList = []
		"""
		The planList is a list which contains number of dicts with the following structure:
		1. classn => class name
		2. hour => hour
		3. original => contains the original data.
		4. change => contains the change information

		The handling is different to the javascript solution. We minimize the effort, this software is there to run in
		fullscreen on a window so we ignore resizing operations, etc. We have a couple number of entries which we
		can show and based on this we pre-generate the pages. 
		"""
		planList = []

		"""
		To update the columns width accordingly, we determine here the factors later for updating.
		"""
		maxFieldLengths = {
			'classn': 0,
			'hour': 0,
			'original': 0,
			'change': 0
		}

		didx = 0
		pidx = 0
		for day in data['times']:
			pageCounter = 0
			newDay = {'day': '', 'abbr': '', 'name': '', 'txt': '', 'index': 0, 'pages': 0}
			dt = datetime.datetime.fromtimestamp(day)
			newDay['day'] = dt.strftime('%d.%m.%Y')
			newDay['abbr'] = dt.strftime('%a')
			newDay['name'] = dt.strftime('%A')
			newDay['txt'] = dt.strftime('%A, %d.%m.%Y')
			newDay['index'] = didx

			entriesInPage = 0
			for entry in data['changes'][str(day)]:
				if len(planList) <= pidx:
					planList.append([])

				newEntry = {'classn': '', 'hour': '', 'original': '', 'change': ''}
				newEntry['classn'] = entry['raw']['class']
				newEntry['hour'] = entry['raw']['hour']
				newEntry['original'] = entry['raw']['what']
				newEntry['change'] = entry['raw']['change']
				tmpLen = len(entry['raw']['class'])
				if tmpLen > maxFieldLengths['classn']: 
					maxFieldLengths['classn'] = tmpLen
				tmpLen = len(entry['raw']['hour'])
				if tmpLen > maxFieldLengths['hour']: 
					maxFieldLengths['hour'] = tmpLen
				tmpLen = len(entry['raw']['what'])
				if tmpLen > maxFieldLengths['original']: 
					maxFieldLengths['original'] = tmpLen
				tmpLen = len(entry['raw']['change'])
				if tmpLen > maxFieldLengths['change']: 
					maxFieldLengths['change'] = tmpLen

				planList[pidx].append(newEntry)
				entriesInPage += 1

				if entriesInPage >= self.ebbPlanHandler.maxEntries:
					entriesInPage = 0
					pidx += 1
					pageCounter += 1
			
			if entriesInPage > 0:
				pageCounter += 1

			newDay['pages'] = pageCounter
			dayList.append(newDay)
			didx += 1
			# and we really need new page for new date!
			pidx += 1

		# calculate field factors...
		maxFieldLengths['classn'] += 3
		comLength = 0
		for k, v in maxFieldLengths.items():
			comLength += v

		fieldFactor = {
			'classn': 0,
			'hour': 0,
			'original': 0,
			'change': 0
		}
		for k, v in maxFieldLengths.items():
			fieldFactor[k] = round(v/comLength, 2)

		self.ebbPlanHandler.planColSizeChanged.emit(QVariant(fieldFactor))

		# now populate the data.
		stand = datetime.datetime.fromtimestamp(data['stand']).strftime('%d.%m. %H:%M')
		self.ebbPlanHandler.planAvailable.emit(QVariant(dayList), QVariant(planList), stand)

class ContentImageFinder(HTMLParser):

	def __init__(self):
		super().__init__()
		self.image = ''

	def handle_starttag(self, tag, attrs):
		if len(self.image) > 0:
			pass
			return

		if tag == 'img':
			for attr in attrs:
				if attr[0] == 'src':
					self.image = attr[1]
					break

def processTermSignal(signum, frame):
	log.debug('yes, the SIGTERM signal reached me.')
	global ds
	ds.sysTermSignal.emit()

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
	qmlRegisterType(EbbPlanHandler, 'EbbPlanHandler', 1, 0, 'EbbPlanHandler')
	qmlRegisterType(EbbContentHandler, 'EbbContentHandler', 1, 0, 'EbbContentHandler')
	ds = VPlanMainWindow(app)

	# register TERM signal.
	signal.signal(signal.SIGTERM, processTermSignal)
	# this does only work, when we let the python thing running...
	signalTimer = QTimer()
	signalTimer.start(500)
	signalTimer.timeout.connect(lambda: None)

	# start application.
	ds.start()
	sys.exit(app.exec_())
