'''Module to deal with the in-memory storage of the status of our contacts'''

class Contacts:
	'''Class to manage the set of which of our contacts are currently online'''
	_online_list = set()

	@staticmethod
	def comeOnline(torId):
		'''The given tor id has announced it is online'''
		Contacts._online_list.add(torId)
		#print("Contacts just informed that", torId, "is online.  Set is now", Contacts._online_list)

	@staticmethod
	def goneOffline(torId):
		'''The given tor id has announced it is offline (or we failed to send to it)'''
		if torId in Contacts._online_list:
			Contacts._online_list.remove(torId)
		#print("Contacts just informed that", torId, "is offline.  Set is now", Contacts._online_list)

	@staticmethod
	def isOnline(torId):
		'''Check whether the given tor id is currently online (as far as we know)'''
		#print("Contact list asked about", torId, ", answer is", (torId in Contacts._online_list))
		return torId in Contacts._online_list
