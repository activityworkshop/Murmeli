'''Module for shuffling messages around when received'''

from PyQt5.QtCore import QObject, pyqtSignal
from message import Message, StatusNotifyMessage, InfoRequestMessage,\
	InfoResponseMessage
from dbinterface import DbI
from contactmgr import ContactMaker
from contacts import Contacts
from config import Config


class MessageTannoy(QObject):
	'''Object to emit signals about incoming messages'''
	updateSignal = pyqtSignal(str)
	def __init__(self):
		QObject.__init__(self)
	def shout(self, msgText):
		# TODO: Pass these values with the signal as an object, not a string
		self.updateSignal.emit(msgText)


class MessageShuffler:
	'''This class is responsible for dealing with incoming messages, either
	   moving them to the inbox (if the message is for us) or to the outbox
	   (if we should relay it to a friend) or even just ignore it if it's not for us'''

	_tannoy = None

	@staticmethod
	def getTannoy():
		if not MessageShuffler._tannoy:
			MessageShuffler._tannoy = MessageTannoy()
		return MessageShuffler._tannoy

	@staticmethod
	def dealWithMessage(message):
		'''Examine the received message and decide what to do with it'''
		print("Hmm, the MessageShuffler has been given some kind of message")
		# We must be online if we've received a message
		Contacts.instance().comeOnline(DbI.getOwnTorid())

		if message.senderMustBeTrusted:
			sender = DbI.getProfile(message.senderId)
			if not sender or sender['status'] != "trusted":
				return # throw message away

		if not message.isComplete():
			print("A message of type", message.encryptionType, "was received but it's not complete - throwing away")
			return # throw message away

		# if it's not encrypted, it's for us -> save in inbox
		if message.encryptionType == Message.ENCTYPE_NONE:
			MessageShuffler.dealWithUnencryptedMessage(message)

		elif message.encryptionType == Message.ENCTYPE_SYMM:
			# if it's symmetric, forget it for now
			pass

		elif message.encryptionType == Message.ENCTYPE_ASYM:
			MessageShuffler.dealWithAsymmetricMessage(message)

		elif message.encryptionType == Message.ENCTYPE_RELAY:
			# Get received bytes of message, and add to Outbox, send to everybody EXCEPT the sender
			bytesToSend = message.createOutput(None)
			if bytesToSend:
				# add to outbox, but don't send it back to message.senderId
				DbI.addRelayMessageToOutbox(bytesToSend, message.senderId)
		else:
			print("Hä?  What kind of encryption type is that? ", message.encryptionType)

		# Log receipt of message (do we want to know about relays at all?)
		if message.encryptionType in [Message.ENCTYPE_NONE, Message.ENCTYPE_ASYM]:
			logMessage = "Message of type: %s received from %s" % (message.getMessageTypeKey(), message.senderId)
			MessageShuffler.getTannoy().shout(logMessage)


	@staticmethod
	def _isProfileStatusOk(torId, allowedStatuses):
		profile = DbI.getProfile(torId)
		status = profile.get("status", None) if profile else None
		return status in allowedStatuses

	@staticmethod
	def dealWithUnencryptedMessage(message):
		'''Decide what to do with the given unencrypted message'''
		if message.messageType == Message.TYPE_CONTACT_REQUEST:
			print("Received a contact request from", message.senderId)
			# Check config to see whether we accept these or not
			if Config.getProperty(Config.KEY_ALLOW_FRIEND_REQUESTS) \
			  and MessageShuffler._isProfileStatusOk(message.senderId, [None, 'requested', 'untrusted', 'trusted']):
				# Store new message in inbox
				rowToStore = {"messageType":"contactrequest", "fromId":message.senderId,
					"fromName":message.senderName, "messageBody":message.message,
					"publicKey":message.publicKey, "timestamp":message.timestamp,
					"messageRead":False, "messageReplied":False}
				DbI.addToInbox(rowToStore)
		elif message.messageType == Message.TYPE_CONTACT_RESPONSE:
			print("It's an unencrypted contact response, so it must be a refusal")
			sender = DbI.getProfile(message.senderId)
			if MessageShuffler._isProfileStatusOk(message.senderId, ['requested']):
				senderName = sender.get("displayName") if sender else ""
				ContactMaker.handleReceiveDeny(message.senderId)
				# Store new message in inbox
				rowToStore = {"messageType":"contactresponse", "fromId":message.senderId,
					"fromName":senderName, "messageBody":"", "accepted":False,
					"messageRead":False, "messageReplied":False, "timestamp":message.timestamp,
					"recipients":DbI.getOwnTorid()}
				DbI.addToInbox(rowToStore)
		else:
			print("Hä?  It's unencrypted but the message type is", message.messageType)

	@staticmethod
	def dealWithAsymmetricMessage(message):
		'''Decide what to do with the given asymmetric message'''
		if message.senderId == DbI.getOwnTorid():
			print("*** Shouldn't receive a message from myself!")
			return
		# Sort message according to type
		if message.messageType == Message.TYPE_CONTACT_RESPONSE:
			print("Received a contact accept from", message.senderId, "name", message.senderName)
			if MessageShuffler._isProfileStatusOk(message.senderId, ['pending', 'requested', 'untrusted']):
				print(message.senderName, "'s public key is", message.senderKey)
				ContactMaker.handleReceiveAccept(message.senderId, message.senderName, message.senderKey)
				# Store new message in inbox
				rowToStore = {"messageType":"contactresponse", "fromId":message.senderId,
					"fromName":message.senderName, "messageBody":message.introMessage, "accepted":True,
					"messageRead":False, "messageReplied":False, "timestamp":message.timestamp,
					"recipients":DbI.getOwnTorid()}
				DbI.addToInbox(rowToStore)
			elif MessageShuffler._isProfileStatusOk(message.senderId, [None, 'blocked']):
				print("Received a contact response but I didn't send them a request!")
				print("Encrypted contents are:", message.encryptedContents)
				rowToStore = {"messageType":"contactresponse", "fromId":message.senderId,
					"fromName":message.senderName, "messageBody":message.introMessage, "accepted":True,
					"timestamp":message.timestamp, "encryptedMsg":message.encryptedContents}
				DbI.addMessageToPendingContacts(rowToStore)
		elif message.messageType == Message.TYPE_STATUS_NOTIFY:
			if message.online:
				print("One of our contacts has just come online- ", message.senderId,
					"and hash is", message.profileHash)
				prof = DbI.getProfile(message.senderId)
				if prof:
					storedHash = prof.get("profileHash", "empty")
					if message.profileHash != storedHash:
						reply = InfoRequestMessage(infoType=InfoRequestMessage.INFO_PROFILE)
						reply.recipients = [message.senderId]
						DbI.addToOutbox(reply)
					if message.ping:
						print("Now sending back a pong, too")
						reply = StatusNotifyMessage(online=True, ping=False, profileHash=None)
						reply.recipients = [message.senderId]
						DbI.addToOutbox(reply)
					else:
						print("It's already a pong so I won't reply")
				Contacts.instance().comeOnline(message.senderId)
			else:
				print("One of our contacts is going offline -", message.senderId)
				Contacts.instance().goneOffline(message.senderId)
		elif message.messageType == Message.TYPE_INFO_REQUEST:
			print("I've received an info request message for type", message.infoType)
			if MessageShuffler._isProfileStatusOk(message.senderId, ['trusted']):
				reply = InfoResponseMessage(message.messageType)
				reply.recipients = [message.senderId]
				DbI.addToOutbox(reply)
		elif message.messageType == Message.TYPE_INFO_RESPONSE:
			if message.profile and MessageShuffler._isProfileStatusOk(message.senderId, ['trusted', 'untrusted']):
				if message.profileHash:
					message.profile['profileHash'] = message.profileHash
				DbI.updateProfile(message.senderId, message.profile, Config.getWebCacheDir())
		elif message.messageType == Message.TYPE_FRIEND_REFERRAL:
			print("I've received a friend referral message from:", message.senderId, "for:", message.friendName)
			if MessageShuffler._isProfileStatusOk(message.senderId, ['trusted']):
				# Store new referral message in inbox
				rowToStore = {"messageType":"contactrefer", "fromId":message.senderId,
					"friendId":message.friendId, "friendName":message.friendName,
					"messageBody":message.message, "publicKey":message.publicKey,
					"timestamp":message.timestamp, "messageRead":False, "messageReplied":False}
				DbI.addToInbox(rowToStore)
		elif message.messageType == Message.TYPE_FRIENDREFER_REQUEST:
			print("I've received a friend referral request from:", message.senderId, "who wants me to refer:", message.friendId)
			if MessageShuffler._isProfileStatusOk(message.senderId, ['trusted']):
				# Store message in the inbox
				rowToStore = {"messageType":"referrequest", "fromId":message.senderId,
					"friendId":message.friendId, "friendName":message.friendName,
					"messageBody":message.message, "publicKey":message.publicKey,
					"timestamp":message.timestamp, "messageRead":False, "messageReplied":False}
				DbI.addToInbox(rowToStore)
		elif message.messageType == Message.TYPE_ASYM_MESSAGE:
			print("It's a general kind of message, this should go in the Inbox, right?")
			if MessageShuffler._isProfileStatusOk(message.senderId, ['trusted', 'untrusted']):
				rowToStore = {"messageType":"normal", "fromId":message.senderId,
					"messageBody":message.messageBody, "timestamp":message.timestamp,
					"messageRead":False, "messageReplied":False,
					"recipients":message.sendTo, "parentHash":message.replyToHash}
				DbI.addToInbox(rowToStore)
				Contacts.instance().comeOnline(message.senderId)
		else:
			# It's another asymmetric message type
			print("Hä?  What kind of asymmetric message type is that? ", message.messageType)