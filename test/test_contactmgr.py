'''Module for testing the contact manager class'''

import unittest
from murmeli.contactmgr import ContactManager
from murmeli import contactutils


class ContactMgrTest(unittest.TestCase):
    '''Tests for the contact management functions'''

    def test_getcontactname_notfound(self):
        '''Check that given torid is returned when names cannot be extracted from a profile'''
        contacts = ContactManager(None, None)
        self.assertIsNone(contacts.get_contact_name_from_profile(None, None))
        self.assertIsNone(contacts.get_contact_name_from_profile({}, None))
        self.assertIsNone(contacts.get_contact_name_from_profile({"abc":"def"}, None))
        self.assertEqual("", contacts.get_contact_name_from_profile({"abc":"def"}, ""))
        self.assertEqual("moon", contacts.get_contact_name_from_profile({"abc":"def"}, "moon"))
        self.assertEqual("_", contacts.get_contact_name_from_profile({"contactlist":None}, "_"))
        self.assertEqual("_", contacts.get_contact_name_from_profile({"contactlist":""}, "_"))
        self.assertEqual("_", contacts.get_contact_name_from_profile({"contactlist":",,,"}, "_"))

    def test_getcontactname_found(self):
        '''Check that name can be extracted from a profile'''
        contacts = ContactManager(None, None)
        torid = "1234567890abcdef"
        for details, expected in [([(torid, "")], torid),
                                  ([("1234567890Abcdef", "Mickey")], torid),
                                  ([(torid, "Mickey")], "Mickey"),
                                  ([("tooshort", ""), ("1234567890abcdef", "Jim")], "Jim"),
                                  ([("tooshort", ""), ('', ''), "", ("1234567890abcdef", "Jim")],
                                   "Jim"),
                                  ([("1234567890abcdef", "Fred"), ("tooshort", "")], "Fred")]:
            contacts_str = contactutils.contacts_to_string(details)
            profile = {"userid":"xyz", "contactlist":contacts_str}
            found_name = contacts.get_contact_name_from_profile(profile, torid)
            self.assertEqual(expected, found_name)


if __name__ == "__main__":
    unittest.main()
