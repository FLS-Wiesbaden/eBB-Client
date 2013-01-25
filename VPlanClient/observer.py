import abc

class ObservableSubject:

	def __init__(self):
		self._observer = []

	def addObserver(self, observer):
		if hasattr(observer, 'notification'):
			if observer not in self._observer:
				self._observer.append(observer)
			else:
				raise ValueError('Observer is already observing the subject!')
		else:
			raise ValueError('Observer have to have special methods!')

	def removeObserver(self, observer):
		if observer in self._observer:
			self._observer.remove(observer)
		else:
			raise ValueError('Observer is not observing subject !?')

	def notify(self, state):
		for f in self._observer:
			f.notification(state)

class Observer(metaclass=abc.ABCMeta):

	def __init__(self):
		pass

	@abc.abstractmethod
	def notification(self, state):
		pass