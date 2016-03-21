import unittest
from config import Config
from dbclient import DbClient
from contactmgr import ContactMaker

class DatabaseTest(unittest.TestCase):
	'''Tests for the database'''
	def setUp(self):
		Config.load()
		DbClient.startDatabase()
		DbClient.useTestTables()  # important!

	def testGetProfile(self):
		# Delete whole profiles table
		DbClient._getProfileTable().remove({})
		self.assertEqual(DbClient._getProfileTable().count(), 0, "Profiles table should be empty")
		# Add own profile
		myTorId = "ABC123DEF456GH78"
		myprofile = {"name" : "Constantin Taylor", "keyid" : "someKeyId", "displayName" : "Me",
					"status" : "self", "ownprofile" : True}
		DbClient.updateContact(myTorId, myprofile)
		self.assertEqual(DbClient._getProfileTable().count(), 1, "Profiles table should have my profile in it")

		profileFromDb = DbClient.getProfile(None)
		self.assertIsNotNone(profileFromDb, "Couldn't retrieve own profile")
		profileFromDb = DbClient.getProfile(myTorId)
		self.assertIsNotNone(profileFromDb, "Couldn't retrieve profile using own id")

		# Initiate contact with a new person
		otherTorId = "PQR123STU456VWX78"
		otherName = "Olivia Barnacles"
		DbClient.updateContact(otherTorId, {"status" : "untrusted", "keyid" : "donotknow", "name" : otherName})
		self.assertEqual(DbClient._getProfileTable().count(), 2, "Profiles table should have 2 profiles")
		self.assertEqual(DbClient.getMessageableContacts().count(), 1, "Profiles table should have 1 messageable")
		self.assertEqual(DbClient.getTrustedContacts().count(), 0, "Profiles table should have 0 trusted")
		profileFromDb = DbClient.getProfile(otherTorId)
		self.assertIsNotNone(profileFromDb, "Couldn't retrieve profile using other id")
		self.assertEqual(profileFromDb.get("name", None), otherName, "Profile name doesn't match what was stored")
		self.assertEqual(profileFromDb.get("status", None), "untrusted", "Profile status doesn't match what was stored")

		# Update existing record, change status
		DbClient.updateContact(otherTorId, {"status" : "trusted"})
		self.assertEqual(DbClient._getProfileTable().count(), 2, "Profiles table should still have 2 profiles")
		profileFromDb = DbClient.getProfile(otherTorId)
		self.assertIsNotNone(profileFromDb, "Couldn't retrieve profile using other id")
		self.assertEqual(profileFromDb.get("status", None), "trusted", "Profile status should have been updated")
		self.assertEqual(DbClient.getMessageableContacts().count(), 1, "Profiles table should have 1 messageable")
		self.assertEqual(DbClient.getTrustedContacts().count(), 1, "Profiles table should have 1 trusted")

		# Delete other contact
		DbClient.updateContact(otherTorId, {"status" : "deleted"})
		self.assertEqual(DbClient.getMessageableContacts().count(), 0, "Profiles table should have 0 messageable")
		self.assertEqual(DbClient.getTrustedContacts().count(), 0, "Profiles table should have 0 trusted")
		self.assertFalse(DbClient.hasFriends(), "Shouldn't have any friends any more")

	def testProfileHash(self):
		# Clear out and reset own profile
		myTorId = "ABC123DEF456GH78"
		myprofile = {"name" : "Constantin Taylor", "keyid" : "someKeyId", "displayName" : "Me",
					"status" : "self", "ownprofile" : True, "description":"Some fairly descriptive text",
					"birthday":None, "interests":"chocolate pudding with fudge"}
		DbClient.updateContact(myTorId, myprofile)
		firstHash = DbClient.calculateHash(DbClient.getProfile())
		self.assertEqual(firstHash, "12ae5c8dc8e1c2186b4ed4918040bb16", "First hash not what I was expecting")
		# Now change interests and check that hash changes
		DbClient.updateContact(myTorId, {"interests":"roasted vegetables and hummus"})
		secondHash = DbClient.calculateHash(DbClient.getProfile())
		self.assertNotEqual(firstHash, secondHash, "Profile hash should have changed")

	def testSharedContacts(self):
		# Delete whole profiles table
		DbClient._getProfileTable().remove({})
		self.assertEqual(DbClient._getProfileTable().count(), 0, "Profiles table should be empty")
		# Add own profile
		myTorId = "ABC123DEF456GH78"
		myprofile = {"name" : "Constantin Taylor", "keyid" : "someKeyId", "displayName" : "Me",
					"status" : "self", "ownprofile" : True}
		DbClient.updateContact(myTorId, myprofile)
		# Add friend who doesn't list any contacts
		person1TorId = "DEF123GHI456JK78"
		person1profile = {"name" : "Jeremy Flintstone", "keyid" : "someKeyId", "displayName" : "Uncle Jez",
					"status" : "trusted"}
		DbClient.updateContact(person1TorId, person1profile)
		(shared, possible, _) = ContactMaker.getSharedAndPossibleContacts(person1TorId)
		self.assertFalse(shared, "person1 shouldn't have any shared contacts")
		self.assertFalse(possible, "person1 shouldn't have any possible contacts")
		# Add second friend who lists first one as contact
		person2TorId = "GHI123JKL456MN78"
		person2profile = {"name" : "Karen Millhouse", "keyid" : "someKeyId", "displayName" : "Mum",
					"status" : "trusted", "contactlist":"DEF123GHI456JK78Jeremy,ABC123DEF456GH78Constantin,"}
		DbClient.updateContact(person2TorId, person2profile)
		(shared, possible, _) = ContactMaker.getSharedAndPossibleContacts(person1TorId)
		self.assertEqual(len(shared), 1, "person1 should have exactly one shared contact now")
		self.assertTrue(person2TorId in shared, "person1 should have p2 as shared contact now")
		self.assertFalse(possible, "person1 shouldn't have any possible contacts")
		(shared, possible, _) = ContactMaker.getSharedAndPossibleContacts(person2TorId)
		self.assertEqual(len(shared), 1, "person2 should have exactly one shared contact now")
		self.assertTrue(person1TorId in shared, "person2 should have p1 as shared contact now")
		self.assertFalse(possible, "person2 shouldn't have any possible contacts")
		# Person 2 gets a new friend
		DbClient.updateContact(person2TorId, {"contactlist":"DEF123GHI456JK78Jeremy,ABC123DEF456GH78Constantin,MNO123PQR456ST78Scarlet Pimpernel"})
		(shared, possible, _) = ContactMaker.getSharedAndPossibleContacts(person1TorId)
		self.assertEqual(len(shared), 1, "person1 should still have one shared contact")
		self.assertTrue(person2TorId in shared, "person1 should have p2 as shared contact")
		self.assertFalse(possible, "person1 shouldn't have any possible contacts")
		(shared, possible, _) = ContactMaker.getSharedAndPossibleContacts(person2TorId)
		self.assertEqual(len(shared), 1, "person2 should still have one shared contact")
		self.assertTrue(person1TorId in shared, "person2 should have p1 as shared contact")
		self.assertFalse(possible, "person2 shouldn't have any possible contacts")
		# We now make friends with MNO
		person3TorId = "MNO123PQR456ST78"
		person3profile = {"name" : "Scarlet Pimpernel", "keyid" : "someKeyId", "displayName" : "Stranger",
					"status" : "trusted"}
		DbClient.updateContact(person3TorId, person3profile)
		(shared, possible, _) = ContactMaker.getSharedAndPossibleContacts(person1TorId)
		self.assertEqual(len(shared), 1, "person1 should still have one shared contact")
		self.assertTrue(person2TorId in shared, "person1 should have p2 as shared contact")
		self.assertEqual(len(possible), 1, "person1 should have one possible contact now")
		self.assertTrue(person3TorId in possible, "person1 should have p3 as possible contact")
		(shared, possible, _) = ContactMaker.getSharedAndPossibleContacts(person2TorId)
		self.assertEqual(len(shared), 2, "person2 should now have 2 shared contacts")
		self.assertTrue(person1TorId in shared, "person2 should have p1 as shared contact")
		self.assertTrue(person3TorId in shared, "person2 should have p3 as shared contact")
		self.assertFalse(possible, "person2 shouldn't have any possible contacts")


if __name__ == "__main__":
	unittest.main()
