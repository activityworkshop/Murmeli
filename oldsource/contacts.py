'''Module to deal with the in-memory storage of the status of our contacts'''
import datetime

class Contacts:
	'''Class to manage the set of which of our contacts are currently online'''
	_instance = None

	def __init__(self):
		'''Constructor'''
		self._online_list = set()
		self._last_times = {}

	@staticmethod
	def instance():
		if not Contacts._instance:
			Contacts._instance = Contacts()
		return Contacts._instance

	def comeOnline(self, torId):
		'''The given tor id has announced it is online'''
		if not self.isOnline(torId):
			self._last_times[torId] = datetime.datetime.now()
		self._online_list.add(torId)
		#print("Contacts just informed that", torId, "is online.  Set is now", self._online_list)

	def goneOffline(self, torId):
		'''The given tor id has announced it is offline (or we failed to send to it)'''
		if self.isOnline(torId):
			self._online_list.remove(torId)
			self._last_times[torId] = datetime.datetime.now()
		#print("Contacts just informed that", torId, "is offline.  Set is now", self._online_list)

	def isOnline(self, torId):
		'''Check whether the given tor id is currently online (as far as we know)'''
		#print("Contact list asked about", torId, ", answer is", (torId in self._online_list))
		return torId in self._online_list

	def lastSeen(self, torId):
		'''Get the last time this contact went on- or offline'''
		return self._last_times.get(torId, None)

