
'''Messages and their types for Murmeli'''

from random import SystemRandom
import hashlib
import datetime
import dbutils
from dbclient import DbClient
from cryptoclient import CryptoClient


class StringChomper:
	'''Class for splitting up data strings according to different-sized fields'''
	def __init__(self, data):
		self.data = data
		self.pos  = 0

	def getField(self, numBytes):
		'''Extracts a series of bytes and returns them as a bytes sequence'''
		if not self.data:
			return bytes()
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
	TYPE_FRIEND_REFERRAL = 7
	TYPE_FRIENDREFER_REQUEST = 8
	TYPE_ASYM_MESSAGE        = 20
	TYPE_SYMMETRIC_KEY       = 21

	ENCTYPE_NONE = 0
	ENCTYPE_ASYM = 1
	ENCTYPE_SYMM = 2
	ENCTYPE_RELAY = 3

	MAGIC_TOKEN = "murmeli"

	def __init__(self):
		'''Constructor'''
		self.shouldBeQueued = True   # Most should be queued, just certain subtypes not
		self.senderMustBeTrusted = True  # Most should only be accepted if sender is trusted
		self.timestamp = None

	def createOutput(self, recipientKeyId):
		'''Make the regular output of the message including encryption if required'''
		return self._packOutput(self._createPayload(recipientKeyId))

	def createUnencryptedOutput(self):
		'''Make the UNENCRYPTED output of the message, only used for testing!'''
		return self._packOutput(self._createUnencryptedPayload())

	def _packOutput(self, payload):
		'''Take the given payload and pack it together with the general Message fields'''
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

	@staticmethod
	def strToInt(s):
		'''Hopefully s is a one-character string, we want the character code'''
		if s and len(s) == 1:
			return ord(s)
		return 0

	def getOwnPublicKey(self):
		'''Get our own public key by using an empty torid'''
		return self.getPublicKey(torid=None)

	def getPublicKey(self, torid):
		'''Use the keyid stored in mongo, and get the corresponding public key from the Crypto module'''
		profile = DbClient.getProfile(torid)
		if profile is not None:
			keyid = profile.get('keyid', None)
			if keyid is not None:
				return CryptoClient.getPublicKey(keyid)

	@staticmethod
	def MessageFromReceivedData(data, isEncrypted=True):
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
		elif encType == Message.ENCTYPE_ASYM:
			message = AsymmetricMessage.construct(payload, isEncrypted)
		elif encType == Message.ENCTYPE_RELAY:
			message = RelayingMessage.construct(payload, isEncrypted)
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

	def getMessageTypeKey(self):
		'''Used for looking up description texts to display the message type'''
		return "unknown"

	def isComplete(self):
		'''Used to tell if all the required fields are present'''
		return False


class UnencryptedMessage(Message):
	'''Message without symmetric or asymmetric encryption
	   Used only for requesting or rejecting contact, as we haven't got the
	   recipient's public key yet'''
	def __init__(self, senderId=None):
		'''Constructor using the fields to send'''
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

	@staticmethod
	def constructFrom(payload):
		'''Factory constructor using a given payload and extracting the fields'''
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


class ContactRequestMessage(UnencryptedMessage):
	'''Message for requesting contact, which has to be unencrypted as we haven't got the
	   recipient's public key yet'''

	def __init__(self, senderId=None, senderName=None, introMessage=None):
		'''Constructor using the fields to send'''
		UnencryptedMessage.__init__(self, senderId)
		self.messageType = Message.TYPE_CONTACT_REQUEST
		self.message = "" if introMessage is None else introMessage
		self.senderName = senderName
		self.publicKey = None

	def _createSubpayload(self):
		'''Pack the specific fields into the subpayload'''
		# Get own name
		if self.senderName is None:
			self.senderName = DbClient.getProfile(None).get('name', self.senderId)
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

	@staticmethod
	def constructFrom(subpayload):
		'''Factory constructor using a given subpayload and extracting the fields'''
		chomper = StringChomper(subpayload)
		senderName = chomper.getStringWithLength(4)
		introMessage = chomper.getStringWithLength(4)
		m = ContactRequestMessage(senderName=senderName, introMessage=introMessage)
		m.publicKey = chomper.getRest()
		return m

	def getMessageTypeKey(self):
		return "contactrequest"

	def isComplete(self):
		'''The message can be empty but the name and public key are required, otherwise it won't be saved'''
		return self.senderName is not None and len(self.senderName) > 0 \
			and self.publicKey is not None and len(self.publicKey) > 80


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

	def getMessageTypeKey(self):
		return "contactdeny"

	def isComplete(self):
		return True


class AsymmetricMessage(Message):
	'''Message using asymmetric encryption
	   This is the regular mechanism used by most message types'''
	def __init__(self):
		Message.__init__(self)
		self.encryptionType = Message.ENCTYPE_ASYM
		self.timestamp      = None
		self.senderId       = None
		self.shouldBeRelayed = True  # Most should be relayed
		self.encryptedContents = None

	def createRandomToken(self):
		'''Create a random byte sequence to use as a repeating token'''
		r = SystemRandom()
		token = bytearray()
		numBytes = r.choice([3, 4, 5, 6])
		for i in range(numBytes):
			token.append(r.randrange(256))
		return token

	def _createPayload(self, recipientKeyId):
		'''Create the encrypted output for the given recipient'''
		total = self._createUnencryptedPayload()
		# Encrypt and sign the result
		ownKeyId = DbClient.getOwnKeyId()
		return CryptoClient.encryptAndSign(total, recipientKeyId, ownKeyId)

	def _createUnencryptedPayload(self):
		'''Construct the subpayload according to the subclass's rules and data'''
		subpayload = self._createSubpayload()
		timestr = self.makeCurrentTimestamp()
		self.timestamp = Message.convertTimestampFromString(timestr)
		# prepend and append payload with our own general tokens
		token = self.createRandomToken()
		total = self.packBytesTogether([
			token, Message.MAGIC_TOKEN, token,
			self.encodeNumberToBytes(self.messageType, 1),
			subpayload,
			timestr])
		return total

	def _createSubpayload(self):
		'''Default method with no actual contents - to be overwritten by subclasses'''
		return "nocontents"

	def acceptUnrecognisedSignature(self):
		'''Usually we don't accept messages without a recognised signature, except for certain subclasses'''
		return False

	@staticmethod
	def construct(payload, isEncrypted=True):
		'''Factory constructor using a given payload and extracting the fields'''
		if not payload:
			return None
		signatureKey = None
		if isEncrypted:
			# Decrypt the payload with our key
			decrypted, signatureKey = CryptoClient.decryptAndCheckSignature(payload)
		else:
			decrypted = payload
		if decrypted:
			print("Asymmetric message, length of decrypted is", len(decrypted))
		else:
			print("Asymmetric message has no decrypted")
		# Separate fields of message into common ones and the type-specific payload
		msgType, subpayload, tstmp = AsymmetricMessage._stripFields(decrypted)
		print("Recovered timestamp='", tstmp, "' (", len(tstmp), ")")

		# Find a suitable subclass to call using the messageType
		msg = None
		if msgType == Message.TYPE_CONTACT_RESPONSE:
			msg = ContactResponseMessage.constructFrom(subpayload)
		elif msgType == Message.TYPE_STATUS_NOTIFY:
			msg = StatusNotifyMessage.constructFrom(subpayload)
		elif msgType == Message.TYPE_ASYM_MESSAGE:
			msg = RegularMessage.constructFrom(subpayload)
		elif msgType == Message.TYPE_INFO_REQUEST:
			msg = InfoRequestMessage.constructFrom(subpayload)
		elif msgType == Message.TYPE_INFO_RESPONSE:
			msg = InfoResponseMessage.constructFrom(subpayload)
		elif msgType == Message.TYPE_FRIEND_REFERRAL:
			msg = ContactReferralMessage.constructFrom(subpayload)
		# Ask the message if it's ok to have no signature
		if isEncrypted and msg:
			if msg.acceptUnrecognisedSignature():
				# Save the encrypted contents so we can verify it later
				msg.encryptedContents = payload
			elif not signatureKey:
				msg = None
		if msg:
			try:
				msgTimestamp = tstmp.decode('utf-8')
			except:
				msgTimestamp = msg.makeCurrentTimestamp()
			msg.timestamp = Message.convertTimestampFromString(msgTimestamp)
			msg.signatureKeyId = signatureKey
			if signatureKey:
				print("Asymm setting senderId because I've got a signatureKey: '%s'" % signatureKey)
				signatureId = DbClient.findUserIdFromKeyId(signatureKey)
				if signatureId:
					msg.senderId = signatureId
		return msg

	@staticmethod
	def _stripFields(payload):
		'''Try to remove the random tokens from the start of the payload
		   If successful, return a triplet containing the message type, timestamp and payload'''
		if payload:
			for tokenlen in [3, 4, 5, 6]:
				r1 = payload[:tokenlen]
				t1 = payload[tokenlen : tokenlen + len(Message.MAGIC_TOKEN)]
				r2 = payload[tokenlen + len(Message.MAGIC_TOKEN) : 2*tokenlen + len(Message.MAGIC_TOKEN)]
				#print("Comparing '%s', '%s', '%s'" % (r1, t1, r2))
				if len(r1) == tokenlen and r1 == r2 and t1.decode('utf-8') == Message.MAGIC_TOKEN:
					#print("Found beginning!", r1, t1, r2)
					startPos = 2*tokenlen + len(Message.MAGIC_TOKEN)
					return (payload[startPos], payload[startPos+1:-16], payload[-16:])
		return ("", "", "")


class ContactResponseMessage(AsymmetricMessage):
	'''Message to reply to and accept a contact request, message is optional'''
	def __init__(self, senderId=None, senderName=None, message=None, senderKey=None):
		print("Constructing a contact response with senderid %s, sendername %s, message '%s'" % (senderId, senderName, message))
		AsymmetricMessage.__init__(self)
		self.senderId = senderId
		print("ContactResponseMessage constructor: Got a senderId: ", senderId)
		self.senderName = senderName
		self.introMessage = "" if message is None else message
		self.senderKey = senderKey
		self.messageType = Message.TYPE_CONTACT_RESPONSE
		self.senderMustBeTrusted = False  # ok if sender unknown

	def _createSubpayload(self):
		'''Use the stored fields to pack the payload contents together'''
		if self.senderKey is None: self.senderKey = self.getOwnPublicKey()
		# Get own torid and name
		if not self.senderId: self.senderId = DbClient.getOwnTorId()
		if not self.senderName:
			self.senderName = DbClient.getProfile(None).get('name', self.senderId)
		if not self.introMessage: self.introMessage = ""
		nameAsBytes = self.senderName.encode('utf-8')
		messageAsBytes = self.introMessage.encode('utf-8')
		print("Packing contact request with senderId", self.senderId)
		return self.packBytesTogether([
			self.senderId,
			self.encodeNumberToBytes(len(nameAsBytes), 4),
			nameAsBytes,
			self.encodeNumberToBytes(len(messageAsBytes), 4),
			messageAsBytes,
			self.senderKey])

	def acceptUnrecognisedSignature(self):
		'''Only for this subclass is it ok for the signature to be unrecognised, because we haven't got their key yet'''
		return True

	@staticmethod
	def constructFrom(payload):
		'''Factory constructor using a given payload and extracting the fields'''
		if payload:
			print("ContactResponse with payload:", len(payload))
		else:
			print("ContactResponse.construct with an empty payload")
		chomper = StringChomper(payload)
		# sender id and name
		senderId = chomper.getString(16) # Id is always 16 chars
		print("Got a senderId: ", senderId)
		senderName = chomper.getStringWithLength(4)
		introMessage = chomper.getStringWithLength(4)
		publicKey = chomper.getRest()
		return ContactResponseMessage(senderId, senderName, introMessage, publicKey)

	def getMessageTypeKey(self):
		return "contactaccept"

	def isComplete(self):
		'''The public key is required, otherwise it won't be saved'''
		return self.senderKey is not None and len(self.senderKey) > 80


class StatusNotifyMessage(AsymmetricMessage):
	'''Message to send a notification of status, either coming online or about to go offline
	   Includes a hash of the current profile so that receivers can compare with their stored hash'''
	def __init__(self, online=True, ping=True, profileHash=None):
		AsymmetricMessage.__init__(self)
		self.online = online
		self.ping = ping
		self.profileHash = profileHash
		self.messageType = Message.TYPE_STATUS_NOTIFY
		self.shouldBeRelayed = False
		self.shouldBeQueued  = False

	def _createSubpayload(self):
		'''Use the stored fields to pack the payload contents together'''
		if self.profileHash is None or self.profileHash == "":
			self.profileHash = DbClient.calculateHash(DbClient.getProfile())
		return self.packBytesTogether([
			self.encodeNumberToBytes(1 if self.online else 0, 1),
			self.encodeNumberToBytes(1 if self.ping else 0, 1),
			self.profileHash])

	@staticmethod
	def constructFrom(payload):
		'''Factory constructor using a given payload and extracting the fields'''
		chomper = StringChomper(payload)
		online = Message.strToInt(chomper.getField(1)) > 0
		ping   = Message.strToInt(chomper.getField(1)) > 0
		profileHash = chomper.getRest().decode("utf-8")
		return StatusNotifyMessage(online, ping, profileHash)

	def getMessageTypeKey(self):
		return "statusnotify"

	def isComplete(self):
		return True


class InfoRequestMessage(AsymmetricMessage):
	'''An info request can be a request for a profile, or for a list of friends'''
	INFO_PROFILE    = 1
	# Maybe other types of info request will be needed later?

	def __init__(self, infoType):
		AsymmetricMessage.__init__(self)
		self.infoType = infoType
		self.messageType = Message.TYPE_INFO_REQUEST
		self.shouldBeRelayed = False
		self.shouldBeQueued  = False

	def _createSubpayload(self):
		'''Use the stored fields to pack the payload contents together'''
		if self.infoType is None: self.infoType = InfoRequestMessage.INFO_PROFILE
		token = self.createRandomToken()
		return self.encodeNumberToBytes(self.infoType) + \
			token + token

	@staticmethod
	def constructFrom(payload):
		'''Factory constructor using a given payload and extracting the fields'''
		chomper = StringChomper(payload)
		infoType = Message.strToInt(chomper.getField(1))
		# TODO: Check doubled token (although I guess just zeroes would also match)
		#       Maybe all such requests should include a token broadcast (encrypted) by the online status notify message?
		return InfoRequestMessage(infoType)

	def getMessageTypeKey(self):
		return "inforequest"

	def isComplete(self):
		return self.infoType > 0


class InfoResponseMessage(AsymmetricMessage):
	'''An info response is sent to answer an info request, either returning a profile,
	   or maybe something else'''

	def __init__(self, infoType):
		AsymmetricMessage.__init__(self)
		self.infoType = infoType
		self.profileString = None
		self.profile = None
		self.profileHash = None
		self.messageType = Message.TYPE_INFO_RESPONSE
		self.shouldBeRelayed = False
		self.shouldBeQueued  = False

	def _createSubpayload(self):
		'''Use the stored fields to pack the payload contents together'''
		if self.infoType is None:
			self.infoType = InfoRequestMessage.INFO_PROFILE
		if self.profileString is None:
			self.profileString = dbutils.getOwnProfileAsString()
		self.profileHash = DbClient.calculateHash(DbClient.getProfile())
		return self.packBytesTogether([
			self.encodeNumberToBytes(self.infoType),
			self.encodeNumberToBytes(len(self.profileString), 4),
			self.profileString,
			self.encodeNumberToBytes(len(self.profileHash), 4),
			self.profileHash])

	@staticmethod
	def constructFrom(payload):
		'''Factory constructor using a given payload and extracting the fields'''
		chomper = StringChomper(payload)
		infoType = Message.strToInt(chomper.getField(1))
		msg = InfoResponseMessage(infoType)
		msg.profileString = chomper.getStringWithLength(4)
		msg.profile = dbutils.convertStringToDictionary(msg.profileString)
		msg.profileHash = chomper.getStringWithLength(4)
		return msg

	def getMessageTypeKey(self):
		return "inforesponse"

	def isComplete(self):
		return True


class RegularMessage(AsymmetricMessage):
	'''Class for a generic message to one or more contacts'''
	def __init__(self, sendTo=None, messageBody=None, replyToHash=None):
		AsymmetricMessage.__init__(self)
		self.sendTo = sendTo   # TODO: Verify length of this, must be multiple of id length
		self.messageBody = messageBody   # TODO: throw exception if empty?
		self.replyToHash = replyToHash if replyToHash else ""
		self.messageType = Message.TYPE_ASYM_MESSAGE
		self.shouldBeRelayed = True
		self.senderMustBeTrusted = False  # sender is allowed to be untrusted

	def _createSubpayload(self):
		'''Use the stored fields to pack the payload contents together'''
		messageAsBytes = self.messageBody.encode('utf-8')
		recipientsAsBytes = self.sendTo.encode('utf-8')
		replyHashAsBytes = self.replyToHash.encode('utf-8')
		return self.packBytesTogether([
			self.encodeNumberToBytes(len(recipientsAsBytes), 4),
			recipientsAsBytes,
			self.encodeNumberToBytes(len(replyHashAsBytes), 4),
			replyHashAsBytes,
			self.encodeNumberToBytes(len(messageAsBytes), 4),
			messageAsBytes])

	@staticmethod
	def constructFrom(payload):
		'''Construct a message from its payload'''
		chomper = StringChomper(payload)
		sendTo = chomper.getStringWithLength(4)
		replyHash = chomper.getStringWithLength(4)
		messageBody = chomper.getStringWithLength(4)
		return RegularMessage(sendTo, messageBody, replyHash)

	def getMessageTypeKey(self):
		return "regular"

	def isComplete(self):
		'''The message shouldn't be empty'''
		return self.messageBody is not None and len(self.messageBody) > 0


class ContactReferralMessage(AsymmetricMessage):
	'''A message type to allow one person to refer a friend to another'''
	def __init__(self, friendId=None, friendName=None, introMessage=None):
		'''Constructor'''
		AsymmetricMessage.__init__(self)
		self.messageType = Message.TYPE_FRIEND_REFERRAL
		self.message = "" if introMessage is None else introMessage
		self.friendId = friendId
		self.friendName = friendName
		self.publicKey = None

	def _createSubpayload(self):
		'''Pack the specific fields into the subpayload'''
		# Get own name
		if self.friendName is None:
			self.friendName = DbClient.getProfile(self.friendId).get('name', self.friendId)
		publicKey = self.getPublicKey(torid=self.friendId)
		# TODO: Complain if publicKey is empty
		messageAsBytes = self.message.encode('utf-8')
		nameAsBytes = self.friendName.encode('utf-8')
		subpayload = Message.packBytesTogether([
			self.friendId,
			self.encodeNumberToBytes(len(nameAsBytes), 4),
			nameAsBytes,
			self.encodeNumberToBytes(len(messageAsBytes), 4),
			messageAsBytes, publicKey])
		return subpayload

	@staticmethod
	def constructFrom(subpayload):
		'''Factory constructor using a given subpayload and extracting the fields'''
		chomper = StringChomper(subpayload)
		friendId = chomper.getString(16) # Id is always 16 chars
		friendName = chomper.getStringWithLength(4)
		introMessage = chomper.getStringWithLength(4)
		m = ContactReferralMessage(friendId=friendId, friendName=friendName, introMessage=introMessage)
		m.publicKey = chomper.getRest()
		return m

	def getMessageTypeKey(self):
		return "contactreferral"

	def isComplete(self):
		'''The message can be empty but the name and public key are required, otherwise it won't be saved'''
		return self.friendId is not None and len(self.friendId) > 0 \
			and self.publicKey is not None and len(self.publicKey) > 80


class RelayingMessage(Message):
	'''A relaying message is some (unknown) kind of asymmetrically-encrypted message
	   which we cannot decrypt but we will just store it and relay it on to our contacts'''

	def __init__(self, parcelBytes=None, rcvdBytes=None):
		'''Constructor giving either the bytes of an outgoing message which we want to wrap,
		or the received bytes from an incoming message'''
		Message.__init__(self)
		self.encryptionType = Message.ENCTYPE_RELAY
		self.origParcel = parcelBytes
		self.payload = rcvdBytes
		self.shouldBeRelayed = True

	@staticmethod
	def construct(payload, isEncrypted):
		'''Construct a message from its payload'''
		originalPayload, signKey = CryptoClient.verifySignedData(payload) if isEncrypted else (payload, None)
		if originalPayload:
			# The payload could be verified and extracted, but we still don't know
			# if the contents are for me or for somebody else (probably for somebody else!)
			messageForMe = Message.MessageFromReceivedData(originalPayload, isEncrypted)
			if messageForMe:
				return messageForMe
			else:
				msg = RelayingMessage(rcvdBytes=originalPayload)
				msg.senderId = DbClient.findUserIdFromKeyId(signKey)
				return msg

	def _createPayload(self, recipientKeyId):
		'''Get the original message, and then sign it with our key'''
		if self.origParcel:
			ownKeyId = DbClient.getOwnKeyId()
			return CryptoClient.signData(self.origParcel, ownKeyId)
		# or maybe we received the message as bytes, in which case we shouldn't come here

	def _createUnencryptedPayload(self):
		'''Only makes sense for testing, if provided with original message'''
		if self.origParcel:
			return self.origParcel
		# or maybe we received the message as bytes, in which case we shouldn't come here

	# Override the regular header packing if we've got the wrapped message
	def createOutput(self, recipientKeyId):
		if self.payload:
			return self.payload
		return Message.createOutput(self, recipientKeyId)

	def createUnencryptedOutput(self):
		'''Make the UNENCRYPTED output of the message, only used for testing!'''
		if self.payload:
			return self.payload
		return Message.createUnencryptedOutput(self)

	def isComplete(self):
		'''Either a parcel or a payload is required'''
		return (self.origParcel is not None and len(self.origParcel) > 0) \
			or (self.payload is not None and len(self.payload) > 0)
