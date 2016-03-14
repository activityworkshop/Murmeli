import unittest
from config import Config
from dbclient import DbClient

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


if __name__ == "__main__":
	unittest.main()
