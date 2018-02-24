import unittest
from contacts import Contacts


class ContactListTest(unittest.TestCase):
	'''Tests for the in-memory contact list for logging when contacts
	   come online and go offline again'''

	def testEmptyList(self):
		'''Check that an empty list is handled properly'''
		contacts = Contacts()
		self.assertFalse(contacts.isOnline("abcdef"))
		self.assertIsNone(contacts.lastSeen("abcdef"), "last seen time should be None")
		self.assertIsNone(contacts.lastSeen(None), "last seen time should be None")
		self.assertIsNone(contacts.lastSeen(""), "last seen time should be None")

	def testComingOnline(self):
		'''Check that a contact coming online is handled properly'''
		contacts = Contacts()
		contacts.comeOnline("abcdef")
		self.assertTrue(contacts.isOnline("abcdef"))
		self.assertIsNotNone(contacts.lastSeen("abcdef"), "last seen time should be filled now")
		# Other contacts should still be offline
		self.assertFalse(contacts.isOnline("abcdef2"))
		self.assertFalse(contacts.isOnline("ABCDEF"))
		self.assertFalse(contacts.isOnline("ghijklmn"))
		self.assertIsNone(contacts.lastSeen("ghijklmn"), "last seen time should be None")
		self.assertIsNone(contacts.lastSeen(None), "last seen time should be None")
		self.assertIsNone(contacts.lastSeen(""), "last seen time should be None")

	def testGoingOffline(self):
		'''Check that a contact going offline is handled properly'''
		contacts = Contacts()
		contacts.comeOnline("abcdef")
		self.assertTrue(contacts.isOnline("abcdef"))
		self.assertIsNotNone(contacts.lastSeen("abcdef"), "last seen time should be filled now")
		goOnlineTime = contacts.lastSeen("abcdef")
		# Now go offline again
		contacts.goneOffline("abcdef")
		self.assertFalse(contacts.isOnline("abcdef"))
		self.assertIsNotNone(contacts.lastSeen("abcdef"), "last seen time should be filled now")
		goOfflineTime = contacts.lastSeen("abcdef")
		self.assertNotEqual(goOnlineTime, goOfflineTime)
		# Reappear
		contacts.comeOnline("abcdef")
		self.assertTrue(contacts.isOnline("abcdef"))
		self.assertIsNotNone(contacts.lastSeen("abcdef"), "last seen time should be filled now")
		reappearTime = contacts.lastSeen("abcdef")
		self.assertNotEqual(goOnlineTime, reappearTime)
		self.assertNotEqual(goOfflineTime, reappearTime)


if __name__ == "__main__":
	unittest.main()

