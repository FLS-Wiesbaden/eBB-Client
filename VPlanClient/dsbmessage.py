#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json

class DsbMessage:

	TARGET_DSB = 'dsb'
	TARGET_CLIENT = 'client'
	TARGET_WS = 'ws'
	TARGET_PYTOOLS = 'pyTools'

	EVENT_CHANGE = 'change'
	EVENT_CREATE = 'create'
	EVENT_DELETE = 'delete'
	EVENT_TRIGGER = 'trigger'

	ACTION_NEWS = 'news'
	ACTION_VPLAN = 'vplan'
	ACTION_ANNOUNCEMENT = 'announcement'
	ACTION_CONFIG = 'config'
	ACTION_STATE  = 'state'
	ACTION_REBOOT = 'reboot'
	ACTION_SUSPEND = 'suspend'
	ACTION_RESUME = 'resume'
	ACTION_SCREENSHOT = 'screenshot'
	ACTION_FIREALARM = 'firealarm'
	ACTION_INFOSCREEN = 'infoscreen'
	ACTION_RESET = 'reset'

	STATE_UNKNOWN = -10
	STATE_UNREGISTERED = -1
	STATE_ONLINE = 1
	STATE_OFFLINE = 0
	STATE_DISABLED = 2
	STATE_IDLE = 3
	STATE_PENDING = 5

	POSSIBLE_TARGETS = [TARGET_DSB, TARGET_CLIENT, TARGET_WS, TARGET_PYTOOLS]
	POSSIBLE_EVENTS = [EVENT_CHANGE, EVENT_CREATE, EVENT_DELETE, EVENT_TRIGGER]
	POSSIBLE_ACTIONS = [
		ACTION_NEWS, ACTION_VPLAN, ACTION_ANNOUNCEMENT, ACTION_CONFIG, 
		ACTION_REBOOT, ACTION_SUSPEND, ACTION_RESUME, ACTION_FIREALARM,
		ACTION_INFOSCREEN, ACTION_SCREENSHOT, ACTION_STATE, ACTION_RESET
	]

	def __init__(self):
		self.target = None
		self.event = None
		self.action = None
		self.id = None
		self.value = None

	def toJson(self):
		# create dict:
		data = {
			'target': self.target,
			'event': self.event,
			'action': self.action,
			'id': self.id,
			'value': self.value
		}
		return json.dumps(data)

	@classmethod
	def fromJsonString(sh, jsonStr):
		try:
			arr = json.loads(jsonStr)
		except ValueError as e:
			raise
		else:
			self = sh()
			self.target = arr['target'] if arr['target'] in DsbMessage.POSSIBLE_TARGETS else None
			self.event = arr['event'] if arr['event'] in DsbMessage.POSSIBLE_EVENTS else None
			self.action = arr['action'] if arr['action'] in DsbMessage.POSSIBLE_ACTIONS else None
			self.id = arr['id']
			self.value = arr['value']

			return self
