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


	def testSimpleFind(self):
		'''Testing the find operation of the super-simple db'''

		# Create new, empty database without file-storage
		db = supersimpledb.SuperSimpleDb()

		# Add a table with three rows
		t = db.getTable("cars")
		t.append({"Brand":"Continental", "Model":"Fastback", "Cylinders":6, "Exhausts":4})
		t.append({"Brand":"Continental", "Model":"Slowback", "Cylinders":4, "Exhausts":2})
		t.append({"Brand":"Continental", "Model":"Family", "Cylinders":4})
		t.append({"Brand":"Aeroglide", "Model":"Behemoth", "Cylinders":8, "Sleeps":4})
		t.append({"Brand":"Thrifty", "Model":"Commuter", "Cylinders":2, "Mpg":60})

		bigEngines = db.findInTable(t, {"Cylinders":[6,8]})
		self.assertEqual(len(bigEngines), 2, "Should have two bigEngines")
		sleepers = db.findInTable(t, {"Sleeps":[4,5,6]})
		self.assertEqual(len(sleepers), 1, "Should have one sleeper")
		continentals = db.findInTable(t, {"Brand":"Continental"})
		self.assertEqual(len(continentals), 3, "Should have three continentals")
		continentals = db.findInTable(t, {"Brand":"Continental", "Exhausts":2})
		self.assertEqual(len(continentals), 1, "Should have 1 twinexhaust")
		self.assertEqual(continentals[0]['Model'], "Slowback", "Slowback is the only twin-exhaust")
		fourCyls = db.findInTable(t, {"Cylinders":4})
		models = [i['Model'] for i in fourCyls]
		self.assertTrue("Slowback" in models)
		self.assertTrue("Family" in models)
		self.assertEqual(len(models), 2, "Should have 2 four-cylinders")
		nonSleepers = db.findInTable(t, {"Sleeps":None})
		self.assertEqual(len(nonSleepers), 4, "Should have 4 non-sleepers")
		nonBrands = db.findInTable(t, {"Brand":None})
		self.assertEqual(nonBrands, [], "Should have none without a brand")
		continentals = db.findInTable(t, {"Brand":"Continental", "Exhausts":[None,2]})
		self.assertEqual(len(continentals), 2, "Should have 2 continentals with 0/2 exhausts")
		#print(continentals)


	def testMurmeliMessageBoxes(self):
		'''Test the Murmeli specifics of messages in the inbox and outbox'''

		# Create new, empty Murmeli database without file-storage
		db = supersimpledb.MurmeliDb()
		self.assertEqual(db.getNumTables(), 2, "Database should have two empty tables at the start")
		self.assertEqual(len(db.getInbox()), 0, "Inbox should be empty at the start")
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
		self.assertEqual(len(db.getOutbox()), 0, "Outbox should be empty")


	def testMurmeliProfiles(self):
		'''Test the Murmeli specifics of profiles'''
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

		self.assertIsNone(db.getProfile(None))
		self.assertIsNone(db.getProfile(""))
		self.assertIsNone(db.getProfile("lump"))
		self.assertIsNone(db.getProfile("1234567890ABCDEE"))
		self.assertIsNone(db.getProfile("1234567890abcdef"))
		self.assertIsNotNone(db.getProfile("1234567890ABCDEF"), "profile should be found by id")
		self.assertEqual(db.getProfile("1234567890ABCDEF")['displayName'], 'cat', "displayName should be cat now")


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


	def testLoadingWithoutEmptyRows(self):
		'''Test that empty rows are ignored when loading the database from file'''
		dbFilename = "test.db"
		# Check that filename we want to use doesn't exist
		self.assertFalse(os.path.exists(dbFilename), "File %s shouldn't exist!" % dbFilename)
		db = supersimpledb.MurmeliDb(dbFilename)
		db.addMessageToOutbox({"sender":"me", "recipient":"you", "messageBody":"Here is my message"})
		db.addMessageToOutbox({"sender":"me", "recipient":"you", "messageBody":"Here is another message"})
		self.assertEqual(len(db.getOutbox()), 2, "Two messages in outbox")
		self.checkMessageIndexes(db.getOutbox())
		self.assertTrue(db.deleteFromOutbox(0), "Delete of first message should work")
		self.assertEqual(len(db.getOutbox()), 1, "Now just 1 message in outbox")
		self.assertEqual(db.getOutbox()[0]["_id"], 1, "Message 0 should have index 1")
		db.saveToFile()
		# Check that file exists now
		self.assertTrue(os.path.exists(dbFilename), "File %s should exist now!" % dbFilename)
		db = None

		loaded = supersimpledb.MurmeliDb(dbFilename)
		self.assertEqual(len(loaded.getOutbox()), 1, "Should now be only 1 message in outbox")
		self.checkMessageIndexes(loaded.getOutbox())

		# Delete file again
		os.remove(dbFilename)
		# Check that file doesn't exist any more
		self.assertFalse(os.path.exists(dbFilename), "File %s shouldn't exist!" % dbFilename)

	def checkMessageIndexes(self, table):
		'''Internal method used for checking consistency of inbox or outbox'''
		for i,r in enumerate(table):
			if r:
				self.assertEqual(i, r["_id"], "Row should have message index equal to position")

	def testReadLocking(self):
		'''Test that modifications of the Murmelidb are correctly handled by snapshotting'''
		# Create new, empty Murmeli database without file-storage
		db = supersimpledb.MurmeliDb()
		self.assertEqual(len(db.getInbox()), 0, "Inbox should be empty at the start")
		db.addMessageToInbox({"something":"amazing"})
		self.assertEqual(len(db.getInbox()), 1, "Inbox should now have one message")
		# Without locking, access to the table will follow appends
		inbox = db.getInbox()
		db.addMessageToInbox({"another":"interesting thing"})
		self.assertEqual(len(inbox), 1, "Inbox should now still have one message")
		self.assertEqual(len(db.getInbox()), 2, "Real Inbox should now have 2 message")

	def testAdminTable(self):
		'''Test the storage and retrieval from the admin table'''
		db = supersimpledb.MurmeliDb()
		self.assertIsNone(db.getAdminValue(None))
		self.assertIsNone(db.getAdminValue("crocodile"))
		self.assertIsNone(db.getAdminValue("elephant"))
		# Add a value
		db.setAdminValue("elephant", 18.1)
		self.assertIsNone(db.getAdminValue("crocodile"))
		self.assertIsNotNone(db.getAdminValue("elephant"))
		self.assertEqual(db.getAdminValue("elephant"), 18.1, "Value should be read again")
		# Change it
		db.setAdminValue("elephant", "coelecanth")
		self.assertIsNone(db.getAdminValue("crocodile"))
		self.assertNotEqual(db.getAdminValue("elephant"), 18.1, "Value should have changed")
		self.assertEqual(db.getAdminValue("elephant"), "coelecanth", "Value should be read again")


if __name__ == "__main__":
	unittest.main()
