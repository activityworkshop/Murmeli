'''Module for the management of contacts within Murmeli'''

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
			DbClient.updateContact(torId, {'displayName':displayName, 'name':displayName,
			  'status':'requested'})


	@staticmethod
	def handleDeleteContact(torId):
		'''For whatever reason, we don't trust this contact any more, so status is set to "deleted"'''
		if torId and torId != DbClient.getOwnTorId():
			DbClient.updateContact(torId, {"status" : "deleted"})
		#       If torId isn't found in profiles table then do nothing

	@staticmethod
	def getSharedAndPossibleContacts(torid):
		'''Check which contacts we share with the given torid and which ones we could recommend to each other'''
		nameMap = {}
		ourContactIds = set()
		trustedContactIds = set()
		theirContactIds = set()
		# Get our id so we can exclude it from the sets
		myTorId = DbClient.getOwnTorId()
		if torid == myTorId:
			return (None, None, None, None)
		# Find the contacts of the specified person
		selectedProfile = DbClient.getProfile(torid, False)
		selectedContacts = selectedProfile.get('contactlist', None) if selectedProfile else None
		if selectedContacts:
			for s in selectedContacts.split(","):
				if s and len(s) >= 16:
					foundid = s[0:16]
					if foundid != myTorId:
						foundName = s[16:]
						theirContactIds.add(foundid)
						nameMap[foundid] = foundName
		foundTheirContacts = len(theirContactIds) > 0
		# Now get information about our contacts
		for c in DbClient.getMessageableContacts():
			foundid = c['torid']
			ourContactIds.add(foundid)
			if c['status'] == 'trusted' and foundid != torid:
				trustedContactIds.add(foundid)
			nameMap[foundid] = c['displayName']
			# Should we check the contact information too?
			if not foundTheirContacts:
				foundContacts = c.get('contactlist', None)
				if foundContacts:
					for s in foundContacts.split(","):
						if s[0:16] == torid:
							theirContactIds.add(foundid)
		# Now we have three sets of torids: our contacts, our trusted contacts, and their contacts.
		sharedContactIds = ourContactIds.intersection(theirContactIds) # might be empty
		suggestionsForThem = trustedContactIds.difference(theirContactIds)
		possibleForMe = theirContactIds.difference(ourContactIds)

		# Some or all of these sets may be empty, but we still return the map so we can look up names
		return (sharedContactIds, suggestionsForThem, possibleForMe, nameMap)

	@staticmethod
	def _getContactNameFromProfile(profile, torId):
		'''If the given profile has a contact list, use it to look up the torid'''
		contactList = profile.get("contactlist", None) if profile else None
		if contactList:
			for c in contactList.split(","):
				if c and len(c) > 16 and c[0:16] == torId:
					return c[16:]
		return torId # not found

	@staticmethod
	def checkAllContactsKeys():
		for c in DbClient.getMessageableContacts():
			torId = c.get("torid", None) if c else None
			if torId:
				keyId = c.get("keyid", None)
				if not keyId:
					print("No keyid found for torid", torId)
				elif not CryptoClient.getPublicKey(keyId):
					print("CryptoClient hasn't got a public key for torid", torId)
				if not keyId or not CryptoClient.getPublicKey(keyId):
					# We haven't got their key in our keyring!
					DbClient.updateContact(torId, {"status":"requested"})
