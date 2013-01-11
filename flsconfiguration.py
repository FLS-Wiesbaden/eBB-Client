from observer import ObservableSubject
from configparser import SafeConfigParser

class FLSConfiguration(SafeConfigParser, ObservableSubject):
	STATE_CHANGED = 'configChanged'
	STATE_LOADED  = 'configLoaded'

	def __init__(self, configFile):
		ObservableSubject.__init__(self)
		SafeConfigParser.__init__(self)
		self._configFile = configFile
		self.load()

	def load(self):
		self.read([self._configFile])
		self.notify(FLSConfiguration.STATE_LOADED)

	def save(self):
		with open(self._configFile, 'w') as f:
			self.write(f)

		# uhh we notify about changes!
		self.notify(FLSConfiguration.STATE_CHANGED)