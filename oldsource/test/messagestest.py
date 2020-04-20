import unittest
import message
from config import Config
from cryptoclient import CryptoClient, CryptoError
from dbinterface import DbI
from testutils import TestUtils


class ContactRequestTest(unittest.TestCase):
	'''Tests for the contact request messages'''
	def setUp(self):
		Config.load()
		CryptoClient.useTestKeyring()
		TestUtils.setupKeyring(["key1_private", "key2_public"])
		TestUtils.setupOwnProfile("46944E14D24D711B") # id of key1

	###################################
	# Tests for encoding, decoding contact request messages
	def testMakingContactRequest(self):
		INTRO = "hello, here's a £ and a #~= î höw are you?"
		SENDER = TestUtils._ownTorId
		KEY_BEGINNING = "-----BEGIN PGP PUBLIC KEY BLOCK-----"
		m = message.ContactRequestMessage(introMessage=INTRO)
		output = m.createUnencryptedOutput()
		bac = message.Message.MessageFromReceivedData(output)
		self.assertIsNotNone(bac, "couldn't decode the data")
		self.assertEqual(bac.senderId, SENDER, "Sender not right")
		self.assertEqual(bac.message, INTRO, "Message not right")
		self.assertTrue(bac.publicKey.startswith(KEY_BEGINNING), "Publickey not right")

	def testInvalidContactRequest(self):
		'''Imagine we've received some kind of invalid content from a stranger,
		should we throw an exception or just throw it away?  Either way we shouldn't crash!'''
		b = bytearray()
		self.execInvalidContactRequest(b)
		b += "muuuurmeli".encode("utf-8")
		self.execInvalidContactRequest(b)
		b = bytearray()
		b += "murmeli".encode("utf-8")
		b.append(1)
		self.execInvalidContactRequest(b)

	def execInvalidContactRequest(self, b):
		bac = message.Message.MessageFromReceivedData(b)
		self.assertIsNone(bac, "shouldn't be None for invalid data")

	###################################
	# Tests for encoding, decoding contact response messages
	def testMakingContactDeny(self):
		SENDER = TestUtils._ownTorId
		m = message.ContactDenyMessage()
		output = m.createUnencryptedOutput()
		bac = message.Message.MessageFromReceivedData(output, False)
		self.assertIsNotNone(bac, "couldn't decode the data")
		self.assertEqual(bac.messageType, message.Message.TYPE_CONTACT_RESPONSE, "Message type not right")
		self.assertEqual(bac.senderId, SENDER, "Sender not right")

	def testMakingContactAccept(self):
		INTRO = "Jääääää, why näääät?"
		SENDER = TestUtils._ownTorId
		SENDERNAME = "Geoffrey Lancaster"
		KEY_BEGINNING = "-----BEGIN PGP PUBLIC KEY BLOCK-----"

		m = message.ContactResponseMessage(senderId=None, senderName=None, message=INTRO, senderKey=None)
		unenc = m.createUnencryptedOutput()
		bac = message.Message.MessageFromReceivedData(unenc, False)
		self.assertIsNotNone(bac, "couldn't decode the data")
		self.assertEqual(bac.messageType, message.Message.TYPE_CONTACT_RESPONSE, "Message type not right")
		print("The sender is", bac.senderId)
		print(repr(bac))
		self.assertEqual(bac.senderId, SENDER, "Sender not right")
		self.assertEqual(bac.introMessage, INTRO, "Message not right")
		self.assertEqual(bac.senderName, SENDERNAME)
		self.assertTrue(bac.senderKey.startswith(KEY_BEGINNING), "Publickey not right")

	def testMakingContactResponseNoRecpt(self):
		INTRO = "Jääääää, why näääät?"
		m = message.ContactResponseMessage(senderId=None, senderName=None, message=INTRO, senderKey=None)
		self.assertRaises(CryptoError, m.createOutput, None)

	def testMakingContactResponseEmptyRecpt(self):
		INTRO = "Jääääää, why näääät?"
		m = message.ContactResponseMessage(senderId=None, senderName=None, message=INTRO, senderKey=None)
		self.assertRaises(CryptoError, m.createOutput, "")

	def testMakingContactResponseInvalidRecpt(self):
		INTRO = "Jääääää, why näääät?"
		m = message.ContactResponseMessage(senderId=None, senderName=None, message=INTRO, senderKey=None)
		self.assertRaises(CryptoError, m.createOutput, "NOSUCH")

	def testMakingEncryptedContactAccept(self):
		INTRO = "You really shouldn't be able to read this because it should be encrypted and signed"
		RECPTKEYID = "3B898548F994C536" # id of key2

		m = message.ContactResponseMessage(senderId=None, senderName=None, message=INTRO, senderKey=None)
		output = m.createOutput(RECPTKEYID)
		print("This should be encrypted:", output)
		# Check it's really encrypted by looking for the INTRO string
		for s in range(len(output)-len(INTRO)):
			x = ""
			try:
				x = output[s : s+len(INTRO)].decode("utf-8")
				print(x)
			except Exception: pass
			self.assertNotEqual(x, INTRO, "Message wasn't encrypted properly")
		# Test decryption
		bac = message.Message.MessageFromReceivedData(output)
		self.assertIsNone(bac, "shouldn't be able to decode the data")
		# Now we can cheat and add the private key2 to the keyring, then we should be able to decode it
		TestUtils.setupKeyring(["key2_private", "key1_public"])
		bac = message.Message.MessageFromReceivedData(output)
		self.assertIsNotNone(bac, "should be able to decode the data")


class RegularMessageTest(unittest.TestCase):
	'''Tests for the regular messages'''
	def setUp(self):
		Config.load()
		CryptoClient.useTestKeyring()

	###################################
	# Tests for parsing regular messages
	def testMessageSingleRecipient(self):
		BODY = "Hey dude, have you got any €uros because I heard they were harsh to unicode?  Oh, and &ampersands and <tags> too :)"
		RECIPIENT = "1234567890123456"
		m = message.RegularMessage(sendTo=RECIPIENT, messageBody=BODY)
		output = m.createUnencryptedOutput()
		bac = message.Message.MessageFromReceivedData(output, False)
		self.assertIsNotNone(bac, "couldn't decode the data")
		self.assertEqual(bac.messageType, message.Message.TYPE_ASYM_MESSAGE, "Message type not right")
		self.assertEqual(bac.sendTo, RECIPIENT, "Recipient not right")
		self.assertEqual(bac.messageBody, BODY, "Message not right")


class StatusNotifyTest(unittest.TestCase):
	'''Tests for the status notification messages'''
	def setUp(self):
		Config.load()
		CryptoClient.useTestKeyring()

	###################################
	# Tests for encoding, decoding status notify messages
	def testStatusComingOnline(self):
		self.execStatusNotify(True, True)
	def testStatusGoingOffline(self):
		self.execStatusNotify(False, True)
	def testStatusStillOnline(self):
		self.execStatusNotify(True, False)

	def execStatusNotify(self, online, ping):
		m = message.StatusNotifyMessage(online=online, ping=ping, profileHash=None)
		output = m.createUnencryptedOutput()
		bac = message.Message.MessageFromReceivedData(output, False)
		self.assertIsNotNone(bac, "couldn't decode the data")
		self.assertEqual(online, bac.online)
		self.assertEqual(ping, bac.ping)
		print("profile hash is now", bac.profileHash)
		self.assertTrue(bac.profileHash.startswith("e3f8f001946"))


class InfoRequestTest(unittest.TestCase):
	'''Tests for the info request messages'''
	def setUp(self):
		Config.load()
		CryptoClient.useTestKeyring()

	def testProfileRequest(self):
		m = message.InfoRequestMessage(message.InfoRequestMessage.INFO_PROFILE)
		output = m.createUnencryptedOutput()
		bac = message.Message.MessageFromReceivedData(output, False)
		self.assertIsNotNone(bac, "couldn't decode the data")
		self.assertEqual(message.InfoRequestMessage.INFO_PROFILE, bac.infoType)


class InfoResponseTest(unittest.TestCase):
	'''Tests for the info response messages'''
	def setUp(self):
		Config.load()
		CryptoClient.useTestKeyring()

	def testProfileResponse(self):
		m = message.InfoResponseMessage(message.InfoRequestMessage.INFO_PROFILE)
		output = m.createUnencryptedOutput()
		bac = message.Message.MessageFromReceivedData(output, False)
		self.assertIsNotNone(bac, "couldn't decode the data")
		self.assertEqual(message.InfoRequestMessage.INFO_PROFILE, bac.infoType)
		mydescription = DbI.getProfile()['description']
		bacProfile = bac.profile
		self.assertEqual(mydescription, bacProfile['description'])


class RelayTest(unittest.TestCase):
	'''Tests for the relay messages'''
	def setUp(self):
		Config.load()
		CryptoClient.useTestKeyring()
		TestUtils.setupKeyring(["key1_private", "key2_public"])

	def testMakeUnencryptedRelayMessage(self):
		BODY = "Hey dude, have you got any €uros because I heard they were harsh to ünicode?  Oh, and &ampersands and <tags> too :)"
		RECIPIENT = "1234567890123456"
		m = message.RegularMessage(sendTo=RECIPIENT, messageBody=BODY)
		relaymsg = message.RelayingMessage(parcelBytes=m.createUnencryptedOutput())
		output = relaymsg.createUnencryptedOutput()
		bac = message.Message.MessageFromReceivedData(output, False)
		self.assertIsNotNone(bac, "couldn't decode the data")
		self.assertEqual(bac.messageType, message.Message.TYPE_ASYM_MESSAGE, "Message type not right")
		self.assertEqual(bac.sendTo, RECIPIENT, "Recipient not right")
		self.assertEqual(bac.messageBody, BODY, "Message not right")

	def testMakeEncryptedRelayMessage(self):
		BODY = "Hey dude, have you got any €uros because I heard they were harsh to ünicode?  Oh, and &ampersands and <tags> too :)"
		SENDERID = TestUtils._ownTorId
		RECPTKEYID = "3B898548F994C536" # keyid of eventual target of the message (key2)
		m = message.RegularMessage(sendTo=RECPTKEYID, messageBody=BODY)
		relaymsg = message.RelayingMessage(m.createOutput(RECPTKEYID))
		output = relaymsg.createOutput(recipientKeyId=None)
		bac = message.Message.MessageFromReceivedData(output, True)
		self.assertIsNotNone(bac, "couldn't decode the data")
		self.assertEqual(bac.encryptionType, message.Message.ENCTYPE_RELAY, "Encryption type not right")
		self.assertIsNotNone(bac.payload, "Message should have a payload")
		self.assertEqual(bac.senderId, SENDERID, "Sender id not right")
		# Now fiddle with keys to let us decode it
		TestUtils.setupKeyring(["key2_private", "key1_public"])
		bac = message.Message.MessageFromReceivedData(output, True)
		self.assertIsNotNone(bac, "couldn't decode the data")
		self.assertEqual(bac.sendTo, RECPTKEYID, "Recipient not right")
		self.assertEqual(bac.messageBody, BODY, "Message not right")


class ContactReferralTest(unittest.TestCase):
	'''Tests for the contact referral messages'''
	def setUp(self):
		Config.load()
		CryptoClient.useTestKeyring()
		self.FRIEND_TORID = "zo7quhgn1nq1uppt"
		FRIEND_KEYID = "3B898548F994C536"
		TestUtils.setupOwnProfile("46944E14D24D711B") # id of key1
		DbI.updateProfile(self.FRIEND_TORID, {"status":"trusted",
			"keyid":FRIEND_KEYID, "name":"Norbert Jones", "displayName":"Uncle Norbert"})
		TestUtils.setupKeyring(["key1_private", "key2_public"])

	def testMakingContactReferral(self):
		INTRO = "hello, there's a \"friend\" I'd like you to meet"
		FRIENDNAME = "Norbert Meddwl"
		KEY_BEGINNING = "-----BEGIN PGP PUBLIC KEY BLOCK-----"
		m = message.ContactReferralMessage(friendId=self.FRIEND_TORID, friendName=FRIENDNAME, introMessage=INTRO)
		output = m.createUnencryptedOutput()
		bac = message.Message.MessageFromReceivedData(output, isEncrypted=False)
		self.assertIsNotNone(bac, "couldn't decode the data")
		#self.assertEqual(bac.senderId, SENDER, "Sender not right")
		self.assertEqual(bac.friendId, self.FRIEND_TORID, "Friend id not right")
		self.assertEqual(bac.friendName, FRIENDNAME, "Friend name not right")
		self.assertEqual(bac.message, INTRO, "Message not right")
		self.assertTrue(bac.publicKey.startswith(KEY_BEGINNING), "Publickey not right")


class ContactReferRequestTest(unittest.TestCase):
	'''Tests for the contact referral request messages'''
	def setUp(self):
		Config.load()
		CryptoClient.useTestKeyring()

	def testMakingReferRequest(self):
		INTRO = "hello, you have a \"friend\" I'd like you to introduce me to, please!"
		FRIENDID = "HIJ123KLM456NO78"
		m = message.ContactReferRequestMessage(friendId=FRIENDID, introMessage=INTRO)
		output = m.createUnencryptedOutput()
		bac = message.Message.MessageFromReceivedData(output, isEncrypted=False)
		self.assertIsNotNone(bac, "couldn't decode the data")
		self.assertEqual(bac.friendId, FRIENDID, "Friend id not right")
		self.assertEqual(bac.message, INTRO, "Message not right")


if __name__ == "__main__":
	unittest.main()
