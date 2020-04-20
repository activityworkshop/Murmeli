'''Module for the management of contacts within Murmeli'''

from dbinterface import DbI
from cryptoclient import CryptoClient
from message import StatusNotifyMessage, ContactReferralMessage,\
	ContactReferRequestMessage


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
		if torId and torId != DbI.getOwnTorid():
			DbI.updateProfile(torId, {'displayName':displayName, 'name':displayName,
			  'status':'requested'})

	@staticmethod
	def handleAccept(torId):
		'''We want to accept a contact request, so we need to find the request(s),
		and use it/them to update our keyring and our database entry'''

		# Get this person's current status from the db, if available
		profile = DbI.getProfile(torId)
		status = profile.get("status", None) if profile else None

		# Look for the contact request(s) in the inbox, and extract the name and publicKey
		senderName, senderKeystr, directRequest = ContactMaker.getContactRequestDetails(torId)
		keyValid = senderKeystr and len(senderKeystr) > 20

		if keyValid:
			if status in [None, "requested"]:
				# add key to keyring
				keyId = CryptoClient.importPublicKey(senderKeystr)
				# work out what name and status to stores
				storedSenderName = profile["name"] if profile else None
				nameToStore = storedSenderName if storedSenderName else senderName
				statusToStore = "untrusted" if directRequest else "pending"
				# add or update the profile
				DbI.updateProfile(torId, {"status" : statusToStore, "keyid" : keyId,
				  "name" : nameToStore, "displayName" : nameToStore})
				ContactMaker.processPendingContacts(torId)
			elif status == "pending":
				print("Request already pending, nothing to do")
			elif status in ["untrusted", "trusted"]:
				# set status to untrusted?  Send response?
				print("Trying to handle an accept but status is already", status)
			# Move all corresponding requests to be regular messages instead
			DbI.changeRequestMessagesToRegular(torId)
		else:
			print("Trying to handle an accept but key isn't valid")
			# TODO: Delete all requests?

	@staticmethod
	def processPendingContacts(torId):
		print("Process pending contact accept responses from:", torId)
		foundReq = False
		for resp in DbI.getPendingContactMessages(torId):
			name = resp.get("fromName", None)
			if not name:
				profile = DbI.getProfile(torId)
				name = profile["displayName"]
			print("Found pending contact accept request from: ", name)
			# Check signature using keyring
			_, signatureKey = CryptoClient.decryptAndCheckSignature(resp.get("encryptedMsg", None))
			if signatureKey:
				foundReq = True
				# Insert new message into inbox with message contents
				rowToStore = {"messageType":"contactresponse", "fromId":resp.get("fromId", None),
					"fromName":name, "accepted":True, "messageBody":resp.get("messageBody",""),
					"timestamp":resp.get("timestamp",None), "messageRead":True, "messageReplied":True,
					"recipients":DbI.getOwnTorid()}
				DbI.addToInbox(rowToStore)
		if foundReq:
			DbI.updateProfile(torId, {"status" : "untrusted"})
			# Delete all pending contact responses from this torId
			DbI.deletePendingContactMessages(torId)

	@staticmethod
	def handleDeny(torId):
		'''We want to deny a contact request - remember that this id is blocked'''
		DbI.updateProfile(torId, {"status" : "blocked"})
		# Delete request from Inbox
		message = ContactMaker._getInboxMessage(torId, "contactrequest")
		DbI.deleteFromInbox(message.get("_id"))
		# TODO: Delete all requests, not just this one

	@staticmethod
	def handleReceiveAccept(torId, name, keyStr):
		'''We have requested contact with another id, and this has now been accepted.
		So we can import their public key into our keyring and update their status
		from "requested" to "untrusted"'''
		# Use keyStr to update keyring and get the keyId
		keyId = CryptoClient.importPublicKey(keyStr)
		# Store the keyId and name in their existing row, and update status to "untrusted"
		DbI.updateProfile(torId, {"name" : name, "status" : "untrusted", "keyid" : keyId})
		# TODO: What to do if key import fails or status not what we expect?

	@staticmethod
	def handleReceiveDeny(torId):
		'''We have requested contact with another id, but this has been denied.
		So we need to update their status accordingly'''
		if torId and torId != DbI.getOwnTorid():
			DbI.updateProfile(torId, {"status" : "deleted"})
		# TODO: If profile not found, or status isn't requested then error

	@staticmethod
	def keyFingerprintChecked(torId):
		'''The fingerprint of this contact's public key has been checked (over a separate channel)'''
		# Check that userid exists and that status is currently "untrusted" (trusted also doesn't hurt)
		profile = DbI.getProfile(torId)
		if profile and profile["status"] in ["untrusted", "trusted"]:
			# Update the user's status to trusted
			DbI.updateProfile(torId, {"status" : "trusted"})
			# Trigger a StatusNotify to tell them we're online
			notify = StatusNotifyMessage(online=True, ping=True, profileHash=None)
			notify.recipients = [torId]
			DbI.addToOutbox(notify)

	@staticmethod
	def handleDeleteContact(torId):
		'''For whatever reason, we don't trust this contact any more, so status is set to "deleted"'''
		if torId and torId != DbI.getOwnTorid():
			DbI.updateProfile(torId, {"status" : "deleted"})
		#       If torId isn't found in profiles table then do nothing


	@staticmethod
	def _getInboxMessage(torId, messageType):
		for m in DbI.getInboxMessages():
			if m["fromId"] == torId and m["messageType"] == messageType:
				return m

	@staticmethod
	def getContactRequestDetails(torId):
		'''Use all the received contact requests for the given id, and summarize the name and public key'''
		# Set up empty name / publicKey
		nameList = set()
		keyList = set()
		directRequest = False
		# Loop through all contact requests and contact refers for the given torid
		for m in DbI.getInboxMessages():
			if m["messageType"] == "contactrequest" and m["fromId"] == torId:
				nameList.add(m.get("fromName", None))
				keyList.add(m.get("publicKey", None))
				directRequest = True
			elif m["messageType"] == "contactrefer" and m["friendId"] == torId:
				nameList.add(m.get("friendName", None))
				keyList.add(m.get("publicKey", None))
		if len(keyList) != 1:
			return (None, None, directRequest)	# no keys or more than one key!
		suppliedKey = keyList.pop()
		if suppliedKey is None or len(suppliedKey) < 80:
			return (None, None, directRequest)	# one key supplied but it's missing or too short
		suppliedName = nameList.pop() if len(nameList) == 1 else torId
		return (suppliedName, suppliedKey, directRequest)

	@staticmethod
	def getSharedAndPossibleContacts(torid):
		'''Check which contacts we share with the given torid and which ones we could recommend to each other'''
		nameMap = {}
		ourContactIds = set()
		trustedContactIds = set()
		theirContactIds = set()
		# Get our id so we can exclude it from the sets
		myTorId = DbI.getOwnTorid()
		if torid == myTorId:
			return (None, None, None, None)
		# Find the contacts of the specified person
		selectedProfile = DbI.getProfile(torid)
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
		for c in DbI.getMessageableProfiles():
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
		# TODO: Maybe subtract requested contacts from the "possibleForMe" set?

		# Some or all of these sets may be empty, but we still return the map so we can look up names
		return (sharedContactIds, suggestionsForThem, possibleForMe, nameMap)

	@staticmethod
	def sendReferralMessages(friendId1, friendId2, intro):
		'''Send messages to both friendId1 and friendId2, to recommend they become friends with each other'''
		friend1Profile = DbI.getProfile(friendId1)
		friend2Profile = DbI.getProfile(friendId2)
		if friend1Profile and friend1Profile.get("status", "nostatus") == "trusted" \
		  and friend2Profile and friend2Profile.get("status", "nostatus") == "trusted":
			print("Send message to", friendId1, "referring the details of", friendId2)
			notify = ContactReferralMessage(friendId=friendId2, friendName=None, introMessage=intro)
			notify.recipients = [friendId1]
			DbI.addToOutbox(notify)
			print("Send message to", friendId2, "referring the details of", friendId1)
			notify = ContactReferralMessage(friendId=friendId1, friendName=None, introMessage=intro)
			notify.recipients = [friendId2]
			DbI.addToOutbox(notify)

	@staticmethod
	def sendReferRequestMessage(sendToId, requestedId, intro):
		'''Send a message to sendToId, to ask that they recommend you to requestedId'''
		sendToProfile = DbI.getProfile(sendToId)
		if sendToProfile and sendToProfile.get("status", "nostatus") == "trusted" \
		  and requestedId != DbI.getOwnTorid():
			print("Send message to", sendToId, "requesting referral of", requestedId)
			notify = ContactReferRequestMessage(friendId=requestedId, introMessage=intro)
			notify.recipients = [sendToId]
			DbI.addToOutbox(notify)

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
		'''Return a list of names for which the key can't be found'''
		nameList = []
		for c in DbI.getMessageableProfiles():
			torId = c['torid'] if c else None
			if torId:
				keyId = c['keyid']
				if not keyId:
					print("No keyid found for torid", torId)
					nameList.append(c['displayName'])
				elif not CryptoClient.getPublicKey(keyId):
					print("CryptoClient hasn't got a public key for torid", torId)
					nameList.append(c['displayName'])
				if not keyId or not CryptoClient.getPublicKey(keyId):
					# We haven't got their key in our keyring!
					DbI.updateProfile(torId, {"status":"requested"})
		return nameList
