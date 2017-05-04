import unittest
import os.path
import supersimpledb

class SsdbTest(unittest.TestCase):
	'''Tests for the super-simple database'''

	def testSimpleDb(self):
		'''Testing the super-simple db with no Murmeli specifics'''

		# Create new, empty database without file-storage
		db = supersimpledb.SuperSimpleDb()
		self.assertEqual(db.getNumTables(), 0, "Database should be empty at the start")

		# Add two empty tables
		db.getTable("marshmallow")
		db.getTable("unicorn")
		self.assertEqual(db.getNumTables(), 2, "Database should now have two (empty) tables")
		self.assertEqual(len(db.getTable("marshmallow")), 0, "Table should be empty")
		self.assertEqual(len(db.getTable("unicorn")), 0, "Table should be empty")

		# Add a dict to unicorn table
		db.getTable("unicorn").append({"acrobat":141, "crafty":"oh yes"})
		self.assertEqual(db.getNumTables(), 2, "Database should still have two tables")
		self.assertEqual(len(db.getTable("marshmallow")), 0, "Table should still be empty")
		self.assertEqual(len(db.getTable("unicorn")), 1, "Table should have one entry now")
		self.assertEqual(len(db.getTable("unicorn")[0]), 2, "First entry in unicorn table should have two entries")

		# Add a second dict to unicorn table
		db.getTable("unicorn").append({"baboon":0.813, "flexible":[1, 2, 3], "aghast":0})
		self.assertEqual(db.getNumTables(), 2, "Database should still have two tables")
		self.assertEqual(len(db.getTable("marshmallow")), 0, "Table should still be empty")
		self.assertEqual(len(db.getTable("unicorn")), 2, "Table should have two entries now")
		self.assertEqual(len(db.getTable("unicorn")[0]), 2, "First entry in unicorn table should have two entries")
		self.assertEqual(len(db.getTable("unicorn")[1]), 3, "Second entry in unicorn table should have three entries")

		# Delete the first one we added
		self.assertTrue(db.deleteFromTable("unicorn", 0))
		self.assertEqual(db.getNumTables(), 2, "Database should still have two tables")
		self.assertEqual(len(db.getTable("marshmallow")), 0, "Table should still be empty")
		self.assertEqual(len(db.getTable("unicorn")), 2, "Table should still have two entries, even though one is deleted")
		self.assertEqual(len(db.getTable("unicorn")[0]), 0, "First entry in unicorn table should be empty now")
		self.assertEqual(len(db.getTable("unicorn")[1]), 3, "Second entry in unicorn table should have three entries")


	def testMurmeliMessageBoxes(self):
		'''Test the Murmeli specifics of messages in the inbox and outbox'''

		# Create new, empty Murmeli database without file-storage
		db = supersimpledb.MurmeliDb()
		self.assertEqual(db.getNumTables(), 0, "Database should be empty at the start")
		self.assertEqual(len(db.getInbox()), 0, "Inbox should be empty at the start")
		self.assertEqual(db.getNumTables(), 1, "Database should now have an empty inbox")
		# Add a message to the inbox
		db.addMessageToInbox({"something":"amazing"})
		self.assertEqual(len(db.getInbox()), 1, "Inbox should now have one message")
		self.assertEqual(len(db.getOutbox()), 0, "Outbox should be empty")
		# Add a message to the outbox
		db.addMessageToOutbox({"uncertainty":3.4})
		self.assertEqual(len(db.getInbox()), 1, "Inbox should have one message")
		self.assertEqual(len(db.getOutbox()), 1, "Outbox should have one message")
		# Delete message from outbox
		self.assertTrue(db.deleteFromOutbox(0))
		self.assertEqual(len(db.getOutbox()), 1, "Outbox should still have one empty message")
		realMessages = [m for m in db.getOutbox() if m]
		self.assertEqual(len(realMessages), 0, "Outbox should have no non-empty messages")

	def testMurmeliProfiles(self):
		'''Test the Murmeli specifics of profiles'''

		# Create new, empty Murmeli database without file-storage
		db = supersimpledb.MurmeliDb()
		self.assertFalse(db.addOrUpdateProfile({"halloumi":"cheese"}))	# no torid given
		# Add a new profile
		self.assertTrue(db.addOrUpdateProfile({"torid":"1234567890ABCDEF", "halloumi":"cheese"}))
		self.assertEqual(len(db.getProfiles()), 1, "Profiles should have one entry")
		prof1 = db.getProfiles()[0]
		self.assertEqual(prof1['halloumi'], 'cheese', "Profile should be cheesy")
		self.assertEqual(prof1['name'], '1234567890ABCDEF', "Id should be used as name")
		# Update the profile to give a name
		self.assertTrue(db.addOrUpdateProfile({"torid":"1234567890ABCDEF", "name":"Sylvester"}))
		prof1 = db.getProfiles()[0]
		self.assertEqual(prof1['halloumi'], 'cheese', "Profile should still be cheesy")
		self.assertEqual(prof1['name'], 'Sylvester', "Name should be given now")
		self.assertEqual(prof1['displayName'], 'Sylvester', "displayName should also be given now")
		self.assertTrue(db.addOrUpdateProfile({"torid":"1234567890ABCDEF", "displayName":"cat", "appetite":"substantial"}))
		prof1 = db.getProfiles()[0]
		self.assertEqual(prof1['name'], 'Sylvester', "Name should be set")
		self.assertEqual(prof1['displayName'], 'cat', "displayName should be cat now")
		self.assertEqual(prof1['appetite'], 'substantial', "additional fields also set")
		self.assertEqual(len(db.getProfiles()), 1, "Profiles should still have only one entry")
		self.assertEqual(len(db.getProfiles()[0]), 5, "Profile should have five elements now")

	def testSaveAndLoad(self):
		'''Test the manual saving and loading of the database'''
		dbFilename = "test.db"
		# Check that filename we want to use doesn't exist
		self.assertFalse(os.path.exists(dbFilename), "File %s shouldn't exist!" % dbFilename)
		db = supersimpledb.MurmeliDb(dbFilename)
		self.assertTrue(db.addOrUpdateProfile({"torid":"1234567890ABCDEF", "displayName":"Lester", "name":"Lying Lion"}))
		db.saveToFile()
		# Check that file exists now
		self.assertTrue(os.path.exists(dbFilename), "File %s should exist now!" % dbFilename)
		db = None

		loaded = supersimpledb.MurmeliDb(dbFilename)
		self.assertEqual(len(loaded.getProfiles()), 1, "Profiles should have one entry")
		prof1 = loaded.getProfiles()[0]
		self.assertEqual(prof1['name'], 'Lying Lion', "Name should be set")
		self.assertEqual(prof1['displayName'], 'Lester', "displayName should be set")
		# Delete file again
		os.remove(dbFilename)
		# Check that file doesn't exist any more
		self.assertFalse(os.path.exists(dbFilename), "File %s shouldn't exist!" % dbFilename)


if __name__ == "__main__":
	unittest.main()

