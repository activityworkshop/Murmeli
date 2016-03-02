##########################################
## Messages and their types for Murmeli ##
##########################################

from dbclient import DbClient
from cryptoclient import CryptoClient
import hashlib
import datetime


# Class for splitting up data strings according to different-sized fields
class StringChomper:
	def __init__(self, data):
		self.data = data
		self.pos  = 0
	def getField(self, numBytes):
		'''Extracts a series of bytes and returns them as a bytes sequence'''
		if not self.data: return bytes()
		f = self.data[self.pos : self.pos + numBytes]
		self.pos += numBytes
		return f
	def getByteValue(self, numBytes):
		'''Decode the series of bytes into a value, lowest byte first)'''
		n = 0
		m = 1
		for s in self.getField(numBytes):
			n = n + s * m
			m = m * 256
		return n
	def getString(self, numBytes):
		return self.getField(numBytes).decode('utf-8')
	def getFieldWithLength(self, numBytes):
		str_len = self.getByteValue(numBytes)
		return self.getField(str_len)
	def getStringWithLength(self, numBytes):
		return self.getFieldWithLength(numBytes).decode('utf_8')
	def getRest(self):
		if not self.data: return bytes()
		return self.data[self.pos:]

class Message:
	'''Superclass for all Messages'''

	VERSION_NUMBER = 1

	TYPE_CONTACT_REQUEST  = 1
	TYPE_CONTACT_RESPONSE = 2
	TYPE_STATUS_NOTIFY   = 3
	TYPE_SYMMETRIC_BLOB  = 4
	TYPE_INFO_REQUEST = 5
	TYPE_INFO_RESPONSE = 6
	TYPE_FRIENDINTRO_REQUEST = 7
	TYPE_ASYM_MESSAGE        = 8
	TYPE_SYMMETRIC_KEY       = 9

	ENCTYPE_NONE = 0
	ENCTYPE_ASYM = 1
	ENCTYPE_SYMM = 2
	ENCTYPE_RELAY = 3

	MAGIC_TOKEN = "murmeli"

	def __init__(self):
		'''Constructor'''
		self.shouldBeQueued = True   # Most should be queued, just certain subtypes not
		self.senderMustBeTrusted = True  # Most should only be accepted if sender is trusted

	# Make the regular output of the message including encryption if required
	def createOutput(self, recipientKeyId):
		return self._packOutput(self._createPayload(recipientKeyId))

	# Make the UNENCRYPTED output of the message, only used for testing!
	def createUnencryptedOutput(self):
		return self._packOutput(self._createUnencryptedPayload())

	# Take the given payload and pack it together with the general Message fields
	def _packOutput(self, payload):
		checksum    = Message.makeChecksum(payload)
		payloadsize = len(payload)
		messComponents = [Message.MAGIC_TOKEN,
			self.encodeNumberToBytes(Message.VERSION_NUMBER, 2),
			checksum, # 16 bytes
			chr(1 if self.shouldBeRelayed else 0),
			chr(self.encryptionType),
			self.encodeNumberToBytes(payloadsize, 4),
			payload,
			Message.MAGIC_TOKEN]
		return Message.packBytesTogether(messComponents)

	@staticmethod
	def packBytesTogether(contents):
		total = bytearray()
		for c in contents:
			total += (c.encode('utf-8') if isinstance(c, str) else c)
		return bytes(total)

	# Maybe change from MD5 to SHA256 for these - is there any advantage?
	@staticmethod
	def makeChecksum(payload):
		return hashlib.md5(payload).digest()

	def encodeNumberToBytes(self, num, numBytes=1):
		'''Pack the given number into a series of bytes'''
		res = bytearray()
		n = num
		for i in range(numBytes):
			res.append(n % 256)
			n = int(n/256)
		return res

	# Hopefully s is a one-character string, we want the character code
	@staticmethod
	def strToInt(s):
		if s and len(s) == 1:
			return ord(s)
		return 0

	def getOwnPublicKey(self):
		'''Use the keyid stored in mongo, and get the corresponding public key from the Crypto module'''
		ownprofile = DbClient.getProfile()
		if ownprofile is not None:
			keyid = ownprofile.get('keyid', None)
			if keyid is not None:
				return CryptoClient.getPublicKey(keyid)

	@staticmethod
	def MessageFromReceivedData(data, isEncrypted = True):
		'''Use the received data to rebuild the contents of the message'''
		if data is None or len(data) <= 16: return None                # empty or too short
		chomper = StringChomper(data)
		magic = chomper.getString(len(Message.MAGIC_TOKEN))
		if magic != Message.MAGIC_TOKEN:
			print("found '%s', expected '%s'" % (magic, Message.MAGIC_TOKEN))
			return None   # doesn't begin with magic
		versionNum = chomper.getByteValue(2)
		print("version is", versionNum)
		if versionNum != 1: return None		# version number not supported
		# TODO: The following code must be able to support multiple version numbers, also passed to subclasses
		checksum = chomper.getField(16)
		if len(checksum) != 16: return None         # must be exactly 16 long
		shouldRelay = (chomper.getField(1) == "1")
		encType = Message.strToInt(chomper.getField(1))
		payload = chomper.getFieldWithLength(4)
		magic = chomper.getString(len(Message.MAGIC_TOKEN))
		if magic != Message.MAGIC_TOKEN: return None   # no magic after the payload
		# TODO: Check chomper.getRest() to see if there's too much extra stuff there?  Or just throw away?
		if len(payload) < 17: return None  # payload too small
		# Calculate checksum from payload and compare with given checksum
		calcCheck = Message.makeChecksum(payload)
		if calcCheck != checksum: return None		# checksum doesn't match
		# Make Message object using type and payload
		message = None
		if encType == Message.ENCTYPE_NONE:
			message = UnencryptedMessage.constructFrom(payload)
		if message is not None:
			message.shouldBeRelayed = shouldRelay
			return message

	def makeCurrentTimestamp(self):
		'''Make a timestamp string according to UTC'''
		utcnow = datetime.datetime.now(datetime.timezone.utc)
		timestr = "%d-%02d-%02d-%02d-%02d" % (utcnow.year, utcnow.month, utcnow.day, utcnow.hour, utcnow.minute)
		#print("Generated timestamp='", timestr, "' (", len(timestr), "), (", type(timestr), ")")
		return timestr

	@staticmethod
	def convertTimestampFromString(timestr):
		'''Convert a timestamp in the string form 'YYYY-MM-DD-HH-MM' (in UTC) to a float'''
		try:
			(year, month, day, hour, minute) = [int(i) for i in timestr.split("-")]
			dt = datetime.datetime(year, month, day, hour, minute, tzinfo=datetime.timezone.utc)
		except:
			print("Failed to parse timestamp '", timestr, "'")
			dt = datetime.datetime.now()
		return dt.timestamp()


# Message without symmetric or asymmetric encryption
# Used only for requesting or rejecting contact, as we haven't got the
# recipient's public key yet
class UnencryptedMessage(Message):
	# Constructor using the fields to send
	def __init__(self, senderId=None):
		Message.__init__(self)
		self.encryptionType = Message.ENCTYPE_NONE
		self.shouldBeRelayed = False # always direct
		self.senderMustBeTrusted = False  # ok if sender unknown
		self.senderId = senderId

	def _createPayload(self, recipientKeyId):
		'''Take the given fields and compile them all into the packed output payload'''
		return self._createUnencryptedPayload()

	def _createUnencryptedPayload(self):
		if self.senderId is None:
			self.senderId = DbClient.getOwnTorId()
		return self.packBytesTogether([
			self.encodeNumberToBytes(self.messageType, 1),
			self.senderId, self._createSubpayload()])

	# Factory constructor using a given payload and extracting the fields
	@staticmethod
	def constructFrom(payload):
		chomper = StringChomper(payload)
		messageType = chomper.getByteValue(1)
		senderId = chomper.getString(16) # Id is always 16 chars
		m = None
		if messageType == Message.TYPE_CONTACT_REQUEST:
			m = ContactRequestMessage.constructFrom(chomper.getRest())
		elif messageType == Message.TYPE_CONTACT_RESPONSE:
			m = ContactDenyMessage.constructFrom(chomper.getRest())
		if m:
			m.senderId = senderId
		# Unencrypted messages don't have timestamps, so we'll assign one on receipt
		m.timestamp = m.makeCurrentTimestamp()
		return m


# Message for requesting contact, which has to be unencrypted as we haven't got the
# recipient's public key yet
class ContactRequestMessage(UnencryptedMessage):
	# Constructor using the fields to send
	def __init__(self, senderId=None, senderName=None, introMessage=None):
		UnencryptedMessage.__init__(self, senderId)
		self.messageType = Message.TYPE_CONTACT_REQUEST
		self.message = "" if introMessage is None else introMessage
		self.senderName = senderName
		self.publicKey = None

	def _createSubpayload(self):
		'''Pack the specific fields into the subpayload'''
		# Get own name
		if self.senderName is None: self.senderName = DbClient.getProfile(None).get('name', self.senderId)
		# Get own public key (first get identifier from DbClient, then use that id to ask crypto module)
		myPublicKey = self.getOwnPublicKey()
		messageAsBytes = self.message.encode('utf-8')
		nameAsBytes = self.senderName.encode('utf-8')
		subpayload = Message.packBytesTogether([
			self.encodeNumberToBytes(len(nameAsBytes), 4),
			nameAsBytes,
			self.encodeNumberToBytes(len(messageAsBytes), 4),
			messageAsBytes, myPublicKey])
		return subpayload

	# Factory constructor using a given subpayload and extracting the fields
	@staticmethod
	def constructFrom(subpayload):
		chomper = StringChomper(subpayload)
		senderName = chomper.getStringWithLength(4)
		introMessage = chomper.getStringWithLength(4)
		m = ContactRequestMessage(senderName=senderName, introMessage=introMessage)
		m.publicKey = chomper.getRest()
		return m


class ContactDenyMessage(UnencryptedMessage):
	'''Message to deny a contact request - this can't be encrypted because we didn't
	   accept their public key to our keyring, and in any case we've decided not to
	   communicate with this person so we won't send a reason either.'''
	def __init__(self, senderId=None):
		UnencryptedMessage.__init__(self, senderId)
		self.messageType = Message.TYPE_CONTACT_RESPONSE

	def _createSubpayload(self):
		# There are no other fields here, send as little as possible
		return ""

	@staticmethod
	def constructFrom(subpayload):
		return ContactDenyMessage()
