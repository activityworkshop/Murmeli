'''Module to deal with the in-memory storage of the status of our contacts'''
import datetime

class Contacts:
	'''Class to manage the set of which of our contacts are currently online'''
	_online_list = set()
	_last_times = {}

	@staticmethod
	def comeOnline(torId):
		'''The given tor id has announced it is online'''
		if not Contacts.isOnline(torId):
			Contacts._last_times[torId] = datetime.datetime.now()
		Contacts._online_list.add(torId)
		#print("Contacts just informed that", torId, "is online.  Set is now", Contacts._online_list)

	@staticmethod
	def goneOffline(torId):
		'''The given tor id has announced it is offline (or we failed to send to it)'''
		if Contacts.isOnline(torId):
			Contacts._online_list.remove(torId)
			Contacts._last_times[torId] = datetime.datetime.now()
		#print("Contacts just informed that", torId, "is offline.  Set is now", Contacts._online_list)

	@staticmethod
	def isOnline(torId):
		'''Check whether the given tor id is currently online (as far as we know)'''
		#print("Contact list asked about", torId, ", answer is", (torId in Contacts._online_list))
		return torId in Contacts._online_list

	@staticmethod
	def lastSeen(torId):
		'''Get the last time this contact went on- or offline'''
		return Contacts._last_times.get(torId, None)

