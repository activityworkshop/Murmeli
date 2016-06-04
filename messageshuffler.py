'''Module for shuffling messages around when received'''

from PyQt4.QtCore import QObject, SIGNAL
from message import Message
from dbclient import DbClient
from contacts import Contacts


class MessageTannoy(QObject):
	'''Object to emit signals about incoming messages'''
	def __init__(self):
		QObject.__init__(self)
	def shout(self, msgText):
		# TODO: Pass these values with the signal as an object, not a string
		self.emit(SIGNAL("messageReceived"), msgText)


class MessageShuffler:
	'''This class is responsible for dealing with incoming messages, either
	   moving them to the inbox (if the message is for us) or to the outbox
	   (if we should relay it to a friend) or even just ignore it if it's not for us'''

	ownTorId = None
	_tannoy = None

	@staticmethod
	def getOwnTorId():
		if not MessageShuffler.ownTorId:
			MessageShuffler.ownTorId = DbClient.getOwnTorId()
		return MessageShuffler.ownTorId

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
		Contacts.comeOnline(MessageShuffler.getOwnTorId())

		if message.senderMustBeTrusted:
			sender = DbClient.getProfile(message.senderId, False)
			if not sender or sender['status'] != "trusted":
				return # throw message away

		# if it's not encrypted, it's for us -> save in inbox
		if message.encryptionType == Message.ENCTYPE_NONE:
			MessageShuffler.dealWithUnencryptedMessage(message)

		elif message.encryptionType == Message.ENCTYPE_SYMM:
			# if it's symmetric, forget it for now
			pass

		elif message.encryptionType == Message.ENCTYPE_ASYM:
			MessageShuffler.dealWithAsymmetricMessage(message)

		else:
			print("Hä?  What kind of encryption type is that? ", message.encryptionType)

		# Log receipt of message (do we want to know about relays at all?)
		if message.encryptionType in [Message.ENCTYPE_NONE, Message.ENCTYPE_ASYM]:
			logMessage = "Message of type: %s received from %s" % (message.getMessageTypeKey(), message.senderId)
			MessageShuffler.getTannoy().shout(logMessage)

	@staticmethod
	def _isProfileStatusOk(torId, allowedStatuses):
		profile = DbClient.getProfile(torId, False)
		status = profile.get("status", None) if profile else None
		return status in allowedStatuses

	@staticmethod
	def dealWithUnencryptedMessage(message):
		'''Decide what to do with the given unencrypted message'''
		pass

	@staticmethod
	def dealWithAsymmetricMessage(message):
		'''Decide what to do with the given asymmetric message'''
		pass

