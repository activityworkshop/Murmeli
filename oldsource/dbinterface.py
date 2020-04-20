import os
import shutil	# for copying files
import dbutils
import imageutils
from config import Config
from dbnotify import DbResourceNotifier, DbMessageNotifier
from cryptoclient import CryptoError


class DbI:
	'''Interface to the database.
	   The database isn't created here, but an instance is stored and
	   can be easily retrieved.  This avoids the need to pass the current
	   database around everywhere it's needed.'''

	db_instance = None
	own_torid = None
	own_keyid = None


	@staticmethod
	def setDb(db):
		DbI.db_instance = db

	@staticmethod
	def hasDbSet():
		return DbI.db_instance is not None

	@staticmethod
	def releaseDb():
		if DbI.db_instance:
			DbI.db_instance.stop()
		DbI.db_instance = None

	#### Getting (cached) information about oneself ####

	@staticmethod
	def getOwnTorid():
		if not DbI.own_torid and DbI.db_instance:
			ownProfile = DbI.db_instance.getProfile()
			if ownProfile:
				DbI.own_torid = ownProfile['torid']
		return DbI.own_torid

	@staticmethod
	def getOwnKeyid():
		if not DbI.own_keyid and DbI.db_instance:
			ownProfile = DbI.db_instance.getProfile()
			if ownProfile:
				DbI.own_keyid = ownProfile['keyid']
		return DbI.own_keyid

	#### Getting one or more profiles ####

	@staticmethod
	def getProfiles():
		'''Get all the profiles in the database, whatever their status'''
		return DbI.db_instance.getProfiles()

	@staticmethod
	def getProfile(torid=None):
		return DbI.db_instance.getProfile(torid)

	@staticmethod
	def findUserIdFromKeyId(keyid):
		for p in DbI.getProfiles():
			if p['keyid'] == keyid:
				return p['torid']

	@staticmethod
	def getMessageableProfiles():
		'''Get a list of contacts we can send messages to, ie trusted or untrusted'''
		return DbI.db_instance.getProfilesWithStatus(["trusted", "untrusted"])

	@staticmethod
	def getTrustedProfiles():
		'''Get a list of trusted contacts'''
		return DbI.db_instance.getProfilesWithStatus("trusted")

	@staticmethod
	def hasFriends():
		for c in DbI.getProfiles():
			if c['status'] in ["trusted", "untrusted"]:
				return True
		return False

	@staticmethod
	def exportAllAvatars(outputdir):
		for p in DbI.getProfiles():
			# Note that we handle all statuses, including requested, pending and blocked
			outpath = os.path.join(outputdir, "avatar-" + p['torid'] + ".jpg")
			if not os.path.exists(outpath):
				# File doesn't exist, so get profilepic data
				picstr = p["profilepic"]
				if picstr:
					# Convert string to bytes and write to file
					picBytes = imageutils.stringToBytes(picstr)
					with open(outpath, "wb") as f:
						f.write(picBytes)
				else:
					shutil.copy(os.path.join(outputdir, "avatar-none.jpg"), outpath)

	#### Adding and updating profiles ####

	@staticmethod
	def updateProfile(torid, inProfile, picOutputPath=None):
		'''Updates the profile with the given torid,
		   or adds a new profile if it's not found.
		   Also exports the avatar to the picOutputPath
		   if the profile picture has changed'''
		# If the profile pic path has changed, then we need to load the file
		givenprofilepicpath = inProfile.get('profilepicpath', None)
		pic_changed = False
		if givenprofilepicpath and os.path.exists(givenprofilepicpath):
			pic_changed = True
			# check if it's the same path as already stored
			storedProfile = DbI.getProfile(torid)
			if not storedProfile or storedProfile['profilepicpath'] != givenprofilepicpath:
				# file path has been given, so need to make a string from the bytes
				picBytes = imageutils.makeThumbnailBinary(givenprofilepicpath)
				inProfile['profilepic'] = imageutils.bytesToString(picBytes)
		elif inProfile.get('profilepic', None):
			pic_changed = True

		inProfile['torid'] = torid
		if not DbI.db_instance.addOrUpdateProfile(inProfile):
			print("FAILED to update profile!")
		if pic_changed and picOutputPath:
			DbI._updateAvatar(torid, picOutputPath)
		if inProfile.get("status", None) in ["blocked", "deleted", "trusted"]:
			DbI.updateContactList(Config.getProperty(Config.KEY_ALLOW_FRIENDS_TO_SEE_FRIENDS))
			# TODO: Could this flag come as input instead of from Config?

	@staticmethod
	def _updateAvatar(userid, outputdir):
		picname = "avatar-" + userid + ".jpg"
		outpath = os.path.join(outputdir, picname)
		# print("outpath = ", outpath)
		try: os.remove(outpath)
		except: pass # it wasn't there anyway
		# We export pics for all the contacts but only the ones whose jpg doesn't exist already
		DbI.exportAllAvatars(outputdir)
		# Inform all interested listeners that there's been some change with the given url
		DbResourceNotifier.getInstance().notify(picname)


	@staticmethod
	def updateContactList(showList):
		'''Depending on the setting, either clears the contact list from our own profile,
		   or populates it based on the list of contacts in the database'''
		contactlist = []
		if showList:
			# loop over trusted contacts
			for p in DbI.getTrustedProfiles():
				name = p['name']
				if name:
					contactlist.append(p['torid'] + name.replace(',', '.'))
		# Save this as comma-separated list in our own profile
		profile = {'torid':DbI.getOwnTorid(), 'contactlist':','.join(contactlist)}
		DbI.db_instance.addOrUpdateProfile(profile)

	#### Pending contacts table ####

	@staticmethod
	def addMessageToPendingContacts(message):
		'''Add the given message to the pending contacts table,
		   if a message with the same hash isn't there already'''
		thisHash = dbutils.calculateHash({"body":message['messageBody'],
			"timestamp":message['timestamp'], "senderId":message['fromId']})
		# Check id or hash of message to make sure we haven't got it already!
		for pc in DbI.db_instance.getPendingContactMessages():
			if pc and pc.get("messageHash") == thisHash:
				return
		message['messageHash'] = thisHash
		DbI.db_instance.addPendingContact(message)

	@staticmethod
	def getPendingContactMessages(torId):
		return [m for m in DbI.db_instance.getPendingContactMessages() if m.get('fromId', None) == torId]

	@staticmethod
	def deletePendingContactMessages(torId):
		return DbI.db_instance.deleteFromPendingContacts(torId)

	#### Inbox ####

	@staticmethod
	def getInboxMessages():
		# TODO: Other sorting/paging options?
		allMsgs = DbI.db_instance.getInbox()
		# Reverse to get newest first
		allMsgs.reverse()
		return allMsgs

	@staticmethod
	def addToInbox(message):
		'''A message has been received, need to add this to our inbox so it can be read'''
		# Calculate hash of message's body + timestamp + sender
		thisHash = dbutils.calculateHash({"body":message['messageBody'],
			"timestamp":message['timestamp'], "senderId":message['fromId']})
		# If hash is already in inbox, do nothing
		for m in DbI.getInboxMessages():
			if m and m.get("messageHash") == thisHash:
				return
		# This is a new message
		message['messageHash'] = thisHash
		# Either take its parent's conversation id, or generate a new one
		message['conversationid'] = DbI.getConversationId(message.get("parentHash", None))
		DbI.db_instance.addMessageToInbox(message)
		# Inform all interested listeners that there's been a change in the messages
		DbMessageNotifier.getInstance().notify()

	@staticmethod
	def deleteFromInbox(msgIndex):
		# TODO: Maybe don't delete it, just set deleted flag to true (for undelete)
		# also, that would prevent deleted messages being reinstated when received again
		# Then, getting (and searching) from Inbox would always have to check this flag
		return DbI.db_instance.deleteFromInbox(msgIndex)

	@staticmethod
	def changeRequestMessagesToRegular(torId):
		'''Change all contact requests from the given id to be regular messages instead'''
		for m in DbI.getInboxMessages():
			if (m['messageType'] == "contactrequest" and m['fromId'] == torId) or \
			(m['messageType'] == "contactrefer" and m['friendId'] == torId):
				DbI.db_instance.updateInboxMessage(m['_id'],
				  {"messageType":"normal", "recipients":DbI.getOwnTorid()})

	#### Searching the inbox ####

	@staticmethod
	def searchInboxMessages(searchString):
		# TODO: Make searching less primitive with case-insensitivity, word boundaries etc
		print("Searching for:", searchString)
		results = []
		for m in DbI.getInboxMessages():
			if m and not m.get("deleted", False):
				body = m.get("messageBody", "")
				if body and searchString in body:
					results.append(m)
		return results


	#### Outbox ####

	@staticmethod
	def getOutboxMessages():
		return DbI.db_instance.getOutbox()

	@staticmethod
	def addToOutbox(message):
		'''Note: this method takes a message object (with recipients and
		   a createOutput method), not just a dictionary of values.'''
		if message and message.recipients:
			relays = []
			if message.shouldBeRelayed:
				relays = [p['torid'] for p in DbI.getTrustedProfiles()]
			# TODO: Save (unencrypted) copy in inbox too as a sent message
			for r in message.recipients:
				prof = DbI.getProfile(torid=r)
				if prof:
					encryptKey = prof["keyid"]
					try:
						# message.output is a bytes() object, so we need to convert to string for storage
						messageToSend = imageutils.bytesToString(message.createOutput(encryptKey))
						if not messageToSend:
							print("How can the message to send be empty for type", message.getMessageTypeKey())
						DbI.db_instance.addMessageToOutbox({"recipient":r, "relays":relays,
							"message":messageToSend, "queue":message.shouldBeQueued,
							"msgType":message.getMessageTypeKey()})
						# Inform all interested listeners that there's been a change in the messages
						DbMessageNotifier.getInstance().notify()
					except CryptoError as e:
						print("Something has thrown a CryptoError :(  can't add message to Outbox!", e)

	@staticmethod
	def addRelayMessageToOutbox(messageBytes, dontSendTo):
		'''Note: this method takes a set of bytes resulting from the encryption.'''
		messageRecipients = [p['torid'] for p in DbI.getTrustedProfiles()]
		if dontSendTo:
			messageRecipients = [i for i in messageRecipients if i != dontSendTo]
		if messageRecipients:
			# message output is a bytes() object, so we need to convert to Binary for storage
			messageToSend = imageutils.bytesToString(messageBytes)
			DbI.db_instance.addMessageToOutbox({"recipientList":messageRecipients, "relays":None,
				"message":messageToSend, "queue":True, "msgType":"unknown"})
			# Inform all interested listeners that there's been a change in the messages
			DbMessageNotifier.getInstance().notify()
		else:
			print("After removing sender, there's noone left! - Throwing away message")

	@staticmethod
	def deleteFromOutbox(msgIndex):
		return DbI.db_instance.deleteFromOutbox(msgIndex)

	@staticmethod
	def updateOutboxMessage(messageId, props):
		return DbI.db_instance.updateOutboxMessage(messageId, props)

	#### Admin table ####

	@staticmethod
	def getConversationId(parentHash):
		'''Get the conversation id for the given parent hash'''
		if parentHash:
			for m in DbI.getInboxMessages():
				# There should be only one message with this hash (unless it's been deleted)
				if m.get("messageHash", None) == parentHash:
					cid = m.get("conversationid", None)
					if cid:
						return cid
		# No such parent message found, so generate a new conversation id
		return DbI.getNewConversationId()

	@staticmethod
	def getNewConversationId():
		# Get the next id from the db and increment it
		nextId = DbI.db_instance.getAdminValue("conversationId")
		nextId = nextId+1 if nextId else 1
		# store this value
		DbI.db_instance.setAdminValue("conversationId", nextId)
		return nextId
