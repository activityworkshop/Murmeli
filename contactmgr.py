from dbclient import DbClient
from cryptoclient import CryptoClient


class ContactMaker:
	'''Class responsible for updating the database and crypto keyring
	according to changes in contact information, like establishing
	or deleting contacts'''

	@staticmethod
	def handleInitiate(torId, displayName):
		'''We have requested contact with another id, so we can set up
		this new contact's name with a status of "requested"'''
		# TODO: If row already exists then get status (and name/displayname) and error with it
		# Add new row in db with id, name and "requested"
		if torId and torId != DbClient.getOwnTorId():
			DbClient.updateContact(torId, {'displayName':displayName, 'status':'requested'})


	@staticmethod
	def handleDeleteContact(torId):
		'''For whatever reason, we don't trust this contact any more, so status is set to "deleted"'''
		if torId and torId != DbClient.getOwnTorId():
			DbClient.updateContact(torId, {"status" : "deleted"})
		#       If torId isn't found in profiles table then do nothing

	@staticmethod
	def getSharedAndPossibleContacts(torid):
		'''Check which contacts we share with the given torid and which ones we could recommend to them'''
		sharedContactIds = set()
		possibleContactIds = set()
		ourContacts = {}
		trustedContactIds = set()
		# Firstly, build information about our contacts
		for c in DbClient.getMessageableContacts():
			ourContacts[c['torid']] = c['displayName']
			if c['status'] == 'trusted':
				trustedContactIds.add(c['torid'])
		# Now our id so we can exclude it
		myTorId = DbClient.getOwnTorId()
		if torid == myTorId:
			return (None, None, None)
		# Now loop through selected person's contacts
		selectedProfile = DbClient.getProfile(torid, False)
		selectedContacts = selectedProfile.get('contactlist', None) if selectedProfile else None
		if selectedContacts:
			for s in selectedContacts.split(","):
				if s and len(s) >= 16:
					foundid = s[0:16]
					if foundid != myTorId:
						name = ourContacts.get(foundid, None)
						if name:
							sharedContactIds.add(foundid)
		else:
			# Maybe our other friends can tell us whether they're friends with torid
			for c in DbClient.getTrustedContacts():
				foundContacts = c.get('contactlist', None)
				if foundContacts:
					for s in foundContacts.split(","):
						if s and len(s) >= 16 and s[0:16] == torid:
							sharedContactIds.add(c['torid'])
		# Go through trusted contacts and see which ones aren't in the shared list
		for c in trustedContactIds:
			if c not in sharedContactIds and c != torid:
				possibleContactIds.add(c)
		# Either or both of these sets may be empty, but we still return the map so we can look up names
		return (sharedContactIds, possibleContactIds, ourContacts)
