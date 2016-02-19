#################################################################
# Classes to hold in memory the online/offline status of contacts
#################################################################

class Contacts:
	'''Class to manage the set of which of our contacts are currently online'''
	_online_list = set()

	@staticmethod
	def comeOnline(torId):
		Contacts._online_list.add(torId)
		#print("Contact list just informed that", torId, "has come online.  Set is now", Contacts._online_list)

	@staticmethod
	def goneOffline(torId):
		if torId in Contacts._online_list:
			Contacts._online_list.remove(torId)
		#print("Contact list just informed that", torId, "has gone offline.  Set is now", Contacts._online_list)

	@staticmethod
	def isOnline(torId):
		#print("Contact list asked about", torId, ", answer is", (torId in Contacts._online_list))
		return torId in Contacts._online_list
