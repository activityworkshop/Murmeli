'''Module for testing the contact list class'''

import unittest
from murmeli.contacts import Contacts


class ContactListTest(unittest.TestCase):
    '''Tests for the in-memory contact list for logging when contacts
       come online and go offline again'''

    def test_empty_list(self):
        '''Check that an empty list is handled properly'''
        contacts = Contacts(None)
        self.assertFalse(contacts.is_online("abcdef"))
        self.assertIsNone(contacts.last_seen("abcdef"), "last seen time should be None")
        self.assertIsNone(contacts.last_seen(None), "last seen time should be None")
        self.assertIsNone(contacts.last_seen(""), "last seen time should be None")

    def test_coming_online(self):
        '''Check that a contact coming online is handled properly'''
        contacts = Contacts(None)
        contacts.come_online("abcdef")
        self.assertTrue(contacts.is_online("abcdef"))
        self.assertIsNotNone(contacts.last_seen("abcdef"), "last seen time should be filled now")
        # Other contacts should still be offline
        self.assertFalse(contacts.is_online("abcdef2"))
        self.assertFalse(contacts.is_online("ABCDEF"))
        self.assertFalse(contacts.is_online("ghijklmn"))
        self.assertIsNone(contacts.last_seen("ghijklmn"), "last seen time should be None")
        self.assertIsNone(contacts.last_seen(None), "last seen time should be None")
        self.assertIsNone(contacts.last_seen(""), "last seen time should be None")

    def test_going_offline(self):
        '''Check that a contact going offline is handled properly'''
        contacts = Contacts(None)
        contacts.come_online("abcdef")
        self.assertTrue(contacts.is_online("abcdef"))
        self.assertIsNotNone(contacts.last_seen("abcdef"), "last seen time should be filled now")
        go_online_time = contacts.last_seen("abcdef")
        # Now go offline again
        contacts.gone_offline("abcdef")
        self.assertFalse(contacts.is_online("abcdef"))
        self.assertIsNotNone(contacts.last_seen("abcdef"), "last seen time should be filled now")
        go_offline_time = contacts.last_seen("abcdef")
        self.assertNotEqual(go_online_time, go_offline_time)
        # Reappear
        contacts.come_online("abcdef")
        self.assertTrue(contacts.is_online("abcdef"))
        self.assertIsNotNone(contacts.last_seen("abcdef"), "last seen time should be filled now")
        reappear_time = contacts.last_seen("abcdef")
        self.assertNotEqual(go_online_time, reappear_time)
        self.assertNotEqual(go_offline_time, reappear_time)


if __name__ == "__main__":
    unittest.main()
