'''Module for testing the SuperSimpleDataBase'''
import unittest
import os.path
from murmeli import supersimpledb


class SsdbTest(unittest.TestCase):
    '''Tests for the super-simple database'''

    def test_simple_db(self):
        '''Testing the super-simple db with no Murmeli specifics'''

        # Create new, empty database without file-storage
        ssdb = supersimpledb.SuperSimpleDb()
        self.assertEqual(ssdb.get_num_tables(), 0, "Database should be empty at the start")

        # Add two empty tables
        ssdb.get_table("marshmallow")
        ssdb.get_table("unicorn")
        self.assertEqual(ssdb.get_num_tables(), 2, "Database should now have two (empty) tables")
        self.assertEqual(len(ssdb.get_table("marshmallow")), 0, "Table should be empty")
        self.assertEqual(len(ssdb.get_table("unicorn")), 0, "Table should be empty")

        # Add a dict to unicorn table
        ssdb.get_table("unicorn").append({"acrobat":141, "crafty":"oh yes"})
        self.assertEqual(ssdb.get_num_tables(), 2, "Database should still have two tables")
        self.assertEqual(len(ssdb.get_table("marshmallow")), 0, "Table should still be empty")
        self.assertEqual(len(ssdb.get_table("unicorn")), 1, "Table should have one entry now")
        self.assertEqual(len(ssdb.get_table("unicorn")[0]), 2, "1st entry in unicorn has 2 entries")

        # Add a second dict to unicorn table
        ssdb.get_table("unicorn").append({"baboon":0.813, "flexible":[1, 2, 3], "aghast":0})
        self.assertEqual(ssdb.get_num_tables(), 2, "Database should still have two tables")
        self.assertEqual(len(ssdb.get_table("marshmallow")), 0, "Table should still be empty")
        self.assertEqual(len(ssdb.get_table("unicorn")), 2, "Table should have two entries now")
        self.assertEqual(len(ssdb.get_table("unicorn")[0]), 2, "1st entry in unicorn has 2 entries")
        self.assertEqual(len(ssdb.get_table("unicorn")[1]), 3, "2nd entry in unicorn has 3 entries")

        # Delete the first one we added
        self.assertTrue(ssdb.delete_from_table("unicorn", 0))
        self.assertEqual(ssdb.get_num_tables(), 2, "Database should still have two tables")
        self.assertEqual(len(ssdb.get_table("marshmallow")), 0, "Table should still be empty")
        self.assertEqual(len(ssdb.get_table("unicorn")), 2, "Table has 2 entries, one is deleted")
        self.assertEqual(len(ssdb.get_table("unicorn")[0]), 0, "1st entry in unicorn is empty now")
        self.assertEqual(len(ssdb.get_table("unicorn")[1]), 3, "2nd in unicorn has three entries")


    def test_simple_find(self):
        '''Testing the find operation of the super-simple db'''

        # Create new, empty database without file-storage
        ssdb = supersimpledb.SuperSimpleDb()

        # Add a table with three rows
        cars = ssdb.get_table("cars")
        cars.append({"Brand":"Continental", "Model":"Fastback", "Cylinders":6, "Exhausts":4})
        cars.append({"Brand":"Continental", "Model":"Slowback", "Cylinders":4, "Exhausts":2})
        cars.append({"Brand":"Continental", "Model":"Family", "Cylinders":4})
        cars.append({"Brand":"Aeroglide", "Model":"Behemoth", "Cylinders":8, "Sleeps":4})
        cars.append({"Brand":"Thrifty", "Model":"Commuter", "Cylinders":2, "Mpg":60})

        big_engines = ssdb.find_in_table(cars, {"Cylinders":[6, 8]})
        self.assertEqual(len(big_engines), 2, "Should have two big_engines")
        sleepers = ssdb.find_in_table(cars, {"Sleeps":[4, 5, 6]})
        self.assertEqual(len(sleepers), 1, "Should have one sleeper")
        continentals = ssdb.find_in_table(cars, {"Brand":"Continental"})
        self.assertEqual(len(continentals), 3, "Should have three continentals")
        continentals = ssdb.find_in_table(cars, {"Brand":"Continental", "Exhausts":2})
        self.assertEqual(len(continentals), 1, "Should have 1 twinexhaust")
        self.assertEqual(continentals[0]['Model'], "Slowback", "Slowback is the only twin-exhaust")
        four_cyls = ssdb.find_in_table(cars, {"Cylinders":4})
        models = [i['Model'] for i in four_cyls]
        self.assertTrue("Slowback" in models)
        self.assertTrue("Family" in models)
        self.assertEqual(len(models), 2, "Should have 2 four-cylinders")
        non_sleepers = ssdb.find_in_table(cars, {"Sleeps":None})
        self.assertEqual(len(non_sleepers), 4, "Should have 4 non-sleepers")
        non_brands = ssdb.find_in_table(cars, {"Brand":None})
        self.assertEqual(non_brands, [], "Should have none without a brand")
        continentals = ssdb.find_in_table(cars, {"Brand":"Continental", "Exhausts":[None, 2]})
        self.assertEqual(len(continentals), 2, "Should have 2 continentals with 0/2 exhausts")
        #print(continentals)


    def test_murmeli_message_boxes(self):
        '''Test the Murmeli specifics of messages in the inbox and outbox'''

        # Create new, empty Murmeli database without file-storage
        ssdb = supersimpledb.MurmeliDb(None)
        self.assertEqual(ssdb.get_num_tables(), 2, "Database should have two empty tables at start")
        self.assertEqual(len(ssdb.get_inbox()), 0, "Inbox should be empty at the start")
        # Add a message to the inbox
        ssdb.add_row_to_inbox({"something":"amazing"})
        self.assertEqual(len(ssdb.get_inbox()), 1, "Inbox should now have one message")
        self.assertEqual(len(ssdb.get_outbox()), 0, "Outbox should be empty")
        # Add a message to the outbox
        ssdb.add_row_to_outbox({"uncertainty":3.4})
        self.assertEqual(len(ssdb.get_inbox()), 1, "Inbox should have one message")
        self.assertEqual(len(ssdb.get_outbox()), 1, "Outbox should have one message")
        self.assertEqual(ssdb.get_outbox()[0]['_id'], 0, "First message has index 0")
        # Delete message from outbox
        self.assertTrue(ssdb.delete_from_outbox(0))
        self.assertEqual(len(ssdb.get_outbox()), 0, "Outbox should be empty")
        # Add another and check its id
        ssdb.add_row_to_outbox({"another":"tantalising factlet"})
        self.assertEqual(len(ssdb.get_outbox()), 1, "Outbox should have one message")
        msg = ssdb.get_outbox()[0]
        self.assertEqual(msg['_id'], 1, "First empty message has index 1 now")
        self.assertTrue(ssdb.delete_from_outbox(msg['_id']))
        self.assertEqual(len(ssdb.get_outbox()), 0, "Outbox should be empty again")


    def test_murmeli_profiles(self):
        '''Test the Murmeli specifics of profiles'''
        ssdb = supersimpledb.MurmeliDb(None)
        self.assertFalse(ssdb.add_or_update_profile({"halloumi":"cheese"}))    # no torid given
        # Add a new profile
        self.assertTrue(ssdb.add_or_update_profile({"torid":"1234567890ABCDEF",
                                                    "halloumi":"cheese"}))
        self.assertEqual(len(ssdb.get_profiles()), 1, "Profiles should have one entry")
        prof1 = ssdb.get_profiles()[0]
        self.assertEqual(prof1['halloumi'], 'cheese', "Profile should be cheesy")
        self.assertEqual(prof1['name'], '1234567890ABCDEF', "Id should be used as name")
        # Update the profile to give a name
        self.assertTrue(ssdb.add_or_update_profile({"torid":"1234567890ABCDEF", "name":"Humphrey"}))
        prof1 = ssdb.get_profiles()[0]
        self.assertEqual(prof1['halloumi'], 'cheese', "Profile should still be cheesy")
        self.assertEqual(prof1['name'], 'Humphrey', "Name should be given now")
        self.assertEqual(prof1['displayName'], 'Humphrey', "displayName should also be given now")
        self.assertTrue(ssdb.add_or_update_profile({"torid":"1234567890ABCDEF", "displayName":"cat",
                                                    "appetite":"substantial"}))
        prof1 = ssdb.get_profiles()[0]
        self.assertEqual(prof1['name'], 'Humphrey', "Name should be set")
        self.assertEqual(prof1['displayName'], 'cat', "displayName should be cat now")
        self.assertEqual(prof1['appetite'], 'substantial', "additional fields also set")
        self.assertEqual(len(ssdb.get_profiles()), 1, "Profiles should still have only one entry")
        self.assertEqual(len(ssdb.get_profiles()[0]), 5, "Profile should have five elements now")

        self.assertIsNone(ssdb.get_profile(None))
        self.assertIsNone(ssdb.get_profile(""))
        self.assertIsNone(ssdb.get_profile("lump"))
        self.assertIsNone(ssdb.get_profile("1234567890ABCDEE"))
        self.assertIsNone(ssdb.get_profile("1234567890abcdef"))
        self.assertIsNotNone(ssdb.get_profile("1234567890ABCDEF"), "profile should be found by id")
        self.assertEqual(ssdb.get_profile("1234567890ABCDEF")['displayName'], 'cat',
                         "displayName should be cat now")


    def test_save_and_load(self):
        '''Test the manual saving and loading of the database'''
        db_filename = "test.db"
        # Check that filename we want to use doesn't exist
        self.assertFalse(os.path.exists(db_filename), "File %s shouldn't exist!" % db_filename)
        ssdb = supersimpledb.MurmeliDb(None, db_filename)
        self.assertTrue(ssdb.add_or_update_profile({"torid":"1234567890ABCDEF",
                                                    "displayName":"Lester", "name":"Lying Lion"}))
        ssdb.save_to_file()
        # Check that file exists now
        self.assertTrue(os.path.exists(db_filename), "File %s should exist now!" % db_filename)
        ssdb = None

        loaded = supersimpledb.MurmeliDb(None, db_filename)
        self.assertEqual(len(loaded.get_profiles()), 1, "Profiles should have one entry")
        prof1 = loaded.get_profiles()[0]
        self.assertEqual(prof1['name'], 'Lying Lion', "Name should be set")
        self.assertEqual(prof1['displayName'], 'Lester', "displayName should be set")
        # Delete file again
        os.remove(db_filename)
        # Check that file doesn't exist any more
        self.assertFalse(os.path.exists(db_filename), "File %s shouldn't exist!" % db_filename)


    def test_loading_without_empty_rows(self):
        '''Test that empty rows are ignored when loading the database from file'''
        db_filename = "test.db"
        # Check that filename we want to use doesn't exist
        self.assertFalse(os.path.exists(db_filename), "File %s shouldn't exist!" % db_filename)
        ssdb = supersimpledb.MurmeliDb(None, db_filename)
        ssdb.add_row_to_outbox({"sender":"me", "recipient":"you",
                                "messageBody":"Here is my message"})
        ssdb.add_row_to_outbox({"sender":"me", "recipient":"you",
                                "messageBody":"Here is another message"})
        self.assertEqual(len(ssdb.get_outbox()), 2, "Two messages in outbox")
        self.check_message_indexes(ssdb.get_outbox())
        self.assertTrue(ssdb.delete_from_outbox(0), "Delete of first message should work")
        self.assertEqual(len(ssdb.get_outbox()), 1, "Now just 1 message in outbox")
        self.assertEqual(ssdb.get_outbox()[0]["_id"], 1, "Message 0 should have index 1")
        ssdb.save_to_file()
        # Check that file exists now
        self.assertTrue(os.path.exists(db_filename), "File %s should exist now!" % db_filename)
        ssdb = None

        loaded = supersimpledb.MurmeliDb(None, db_filename)
        self.assertEqual(len(loaded.get_outbox()), 1, "Should now be only 1 message in outbox")
        self.check_message_indexes(loaded.get_outbox())

        # Delete file again
        os.remove(db_filename)
        # Check that file doesn't exist any more
        self.assertFalse(os.path.exists(db_filename), "File %s shouldn't exist!" % db_filename)

    def check_message_indexes(self, table):
        '''Internal method used for checking consistency of inbox or outbox'''
        for i, row in enumerate(table):
            if row:
                self.assertEqual(i, row["_id"], "Row should have message index equal to position")

    def test_read_locking(self):
        '''Test that modifications of the Murmelidb are correctly handled by snapshotting'''
        # Create new, empty Murmeli database without file-storage
        ssdb = supersimpledb.MurmeliDb(None)
        self.assertEqual(len(ssdb.get_inbox()), 0, "Inbox should be empty at the start")
        ssdb.add_row_to_inbox({"something":"amazing"})
        self.assertEqual(len(ssdb.get_inbox()), 1, "Inbox should now have one message")
        # Without locking, access to the table will follow appends
        inbox = ssdb.get_inbox()
        ssdb.add_row_to_inbox({"another":"interesting thing"})
        self.assertEqual(len(inbox), 1, "Inbox should now still have one message")
        self.assertEqual(len(ssdb.get_inbox()), 2, "Real Inbox should now have 2 message")

    def test_admin_table(self):
        '''Test the storage and retrieval from the admin table'''
        ssdb = supersimpledb.MurmeliDb(None)
        self.assertIsNone(ssdb.get_admin_value(None))
        self.assertIsNone(ssdb.get_admin_value("crocodile"))
        self.assertIsNone(ssdb.get_admin_value("elephant"))
        # Add a value
        ssdb.set_admin_value("elephant", 18.1)
        self.assertIsNone(ssdb.get_admin_value("crocodile"))
        self.assertIsNotNone(ssdb.get_admin_value("elephant"))
        self.assertEqual(ssdb.get_admin_value("elephant"), 18.1, "Value should be read again")
        # Change it
        ssdb.set_admin_value("elephant", "coelecanth")
        self.assertIsNone(ssdb.get_admin_value("crocodile"))
        self.assertNotEqual(ssdb.get_admin_value("elephant"), 18.1, "Value should have changed")
        self.assertEqual(ssdb.get_admin_value("elephant"), "coelecanth", "Value read again")


if __name__ == "__main__":
    unittest.main()
