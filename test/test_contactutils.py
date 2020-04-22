'''Module for testing the contact utils'''

import unittest
from murmeli import contactutils


class ContactUtilsTest(unittest.TestCase):
    '''Tests for the contact utils'''

    def test_contact_list_from_none(self):
        '''Check that a missing contact list is handled properly'''
        contacts = contactutils.contacts_from_string(None)
        self.assertIsNotNone(contacts)
        self.assertEqual(0, len(contacts))

    def test_contact_list_from_empty_string(self):
        '''Check that a blank contact list is handled properly'''
        contacts = contactutils.contacts_from_string("")
        self.assertIsNotNone(contacts)
        self.assertEqual(0, len(contacts))

    def test_tooshort_contact_list(self):
        '''Check that a malformed string is handled properly'''
        contacts = contactutils.contacts_from_string("too short")
        self.assertIsNotNone(contacts)
        self.assertEqual(0, len(contacts))

    def test_single_contact_list(self):
        '''Check that a single contact is handled properly'''
        test_id = "Cauliflower leaf"
        test_name = "Po"
        contacts = []
        contacts.append((test_id, test_name))

        contacts_string = contactutils.contacts_to_string(contacts)
        reconstructed = contactutils.contacts_from_string(contacts_string)
        self.assertEqual(1, len(reconstructed))
        self.assertTrue((test_id, test_name) in reconstructed)

    def test_multiple_contact_list(self):
        '''Check that a list of several ids is handled properly'''
        id_prefix = "Cantankerous Jellyfish"
        name_prefix = "Sophie"
        contacts = []
        for i in range(5):
            contacts.append(("%s%02d" % (id_prefix, i), "%s%02d" % (name_prefix, i)))

        contacts_string = contactutils.contacts_to_string(contacts)
        reconstructed = contactutils.contacts_from_string(contacts_string)

        self.assertEqual(5, len(reconstructed))
        for i in range(5):
            expected_id = "%s%02d" % (id_prefix, i)
            expected_name = "%s%02d" % (name_prefix, i)
            self.assertTrue((expected_id, expected_name) in reconstructed)

    def test_duplicate_entries(self):
        '''Check that a list with duplicate id/name pairs is handled properly'''
        id_prefix = "Marchforgrugyn"
        name_prefix = "Awk'ward, name"
        contacts = []
        for i in range(8):
            contacts.append(("%s%02d" % (id_prefix, i%5), "%s%02d" % (name_prefix, i%5)))

        contacts_string = contactutils.contacts_to_string(contacts)
        reconstructed = contactutils.contacts_from_string(contacts_string)

        self.assertEqual(5, len(reconstructed))
        for i in range(5):
            expected_id = "%s%02d" % (id_prefix, i)
            expected_name = "%s%02d" % (name_prefix, i)
            self.assertTrue((expected_id, expected_name) in reconstructed)


if __name__ == "__main__":
    unittest.main()
