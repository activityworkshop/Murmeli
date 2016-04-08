import unittest
import message
from config import Config
from cryptoclient import CryptoClient, CryptoError
from dbclient import DbClient
from testutils import TestUtils


class ContactRequestTest(unittest.TestCase):
	'''Tests for the contact request messages'''
	def setUp(self):
		Config.load()
		DbClient.useTestTables()
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
		self.assertTrue(bac.publicKey.decode('utf-8').startswith(KEY_BEGINNING), "Publickey not right")

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
		self.assertTrue(bac.senderKey.decode('utf-8').startswith(KEY_BEGINNING), "Publickey not right")

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


if __name__ == "__main__":
	unittest.main()

