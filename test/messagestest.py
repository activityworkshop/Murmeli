import unittest
import message
from config import Config
from cryptoclient import CryptoError
from dbclient import DbClient


class ContactRequestTest(unittest.TestCase):
	'''Tests for the contact request messages'''
	def setUp(self):
		Config.load()

	###################################
	# Tests for encoding, decoding contact request messages
	def testMakingContactRequest(self):
		INTRO = "hello, here's a £ and a #~= î höw are you?"
		SENDER = "c5pphe4wckw4j74h"
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
		print("invalid...")
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
		SENDER = "c5pphe4wckw4j74h"
		m = message.ContactDenyMessage()
		output = m.createUnencryptedOutput()
		bac = message.Message.MessageFromReceivedData(output, False)
		self.assertIsNotNone(bac, "couldn't decode the data")
		self.assertEqual(bac.messageType, message.Message.TYPE_CONTACT_RESPONSE, "Message type not right")
		self.assertEqual(bac.senderId, SENDER, "Sender not right")


if __name__ == "__main__":
	unittest.main()

