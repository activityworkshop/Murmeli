'''Module for testing the contact manager class'''

import unittest
from murmeli.contactmgr import ContactManager
from murmeli import contactutils


class MockDatabase:
    '''Use a pretend database for the tests instead of a real one'''
    def __init__(self):
        self.profiles = []

    def get_profile(self, torid=None):
        '''Get the profile for this torid'''
        for profile in self.profiles:
            if profile and profile.get('torid') == torid:
                return profile
        return None

    def get_profiles_with_status(self, status):
        '''Get all the profiles with the given status'''
        if isinstance(status, list):
            return [i for i in self.profiles if i.get("status") in status]
        if status:
            return [i for i in self.profiles if i.get("status") == status]
        # status is empty, so return empty list
        return []


class ReferralCalculationsTest(unittest.TestCase):
    '''Tests for suggesting contacts'''

    def test_nodb_emptysets(self):
        '''Test that getting sets with no database gives blank sets, no errors'''
        manager = ContactManager(None, None)
        shared_ids, ids_for_them, ids_for_me, name_map = manager.get_shared_possible_contacts(None)
        self.assertFalse(shared_ids)
        self.assertFalse(ids_for_them)
        self.assertFalse(ids_for_me)
        self.assertFalse(name_map)

    def test_noprofiles_emptysets(self):
        '''Test that getting sets from empty database gives blank sets, no errors'''
        database = MockDatabase()
        manager = ContactManager(database, None)
        shared_ids, ids_for_them, ids_for_me, name_map = manager.get_shared_possible_contacts(None)
        self.assertFalse(shared_ids)
        self.assertFalse(ids_for_them)
        self.assertFalse(ids_for_me)
        self.assertFalse(name_map)

    def test_ownid_emptysets(self):
        '''Test that getting sets for own id gives blank sets, no errors'''
        database = MockDatabase()
        own_id = "ABCD1234EFGH5678"
        database.profiles.append({'torid':own_id})
        manager = ContactManager(database, None)
        shared_ids, ids_for_them, ids_for_me, names = manager.get_shared_possible_contacts(own_id)
        self.assertFalse(shared_ids)
        self.assertFalse(ids_for_them)
        self.assertFalse(ids_for_me)
        self.assertFalse(names)

    def test_onefriend_singlename(self):
        '''Test that getting sets for single friend gives entry in names'''
        database = MockDatabase()
        own_id = "ABCD1234EFGH5678"
        friend_id = "COWABUNGA1234567"
        database.profiles.append({'torid':own_id, 'status':'self'})
        database.profiles.append({'torid':friend_id, 'status':'trusted', 'displayName':'Bob'})
        manager = ContactManager(database, None)
        results = manager.get_shared_possible_contacts(friend_id)
        shared_ids, ids_for_them, ids_for_me, name_map = results
        self.assertFalse(shared_ids)
        self.assertFalse(ids_for_them)
        self.assertFalse(ids_for_me)
        self.assertEqual("Bob", name_map.get(friend_id), "Found Bob")

    def test_twofriends_refereach(self):
        '''Test that if two friends don't know each other, they will be referred'''
        database = MockDatabase()
        own_id = "ABCD1234EFGH5678"
        first_id = "JUNGLEGYM1234567"
        second_id = "TESTAROSSA123456"
        database.profiles.append({'torid':own_id, 'status':'self'})
        database.profiles.append({'torid':first_id, 'status':'trusted', 'displayName':'Bob'})
        database.profiles.append({'torid':second_id, 'status':'trusted', 'displayName':'Alice'})
        manager = ContactManager(database, None)
        for id1, id2 in [(first_id, second_id), (second_id, first_id)]:
            results = manager.get_shared_possible_contacts(id1)
            shared_ids, ids_for_them, ids_for_me, _ = results
            self.assertFalse(shared_ids)
            self.assertEqual(1, len(ids_for_them), "1 for them")
            self.assertTrue(id2 in ids_for_them, "recommend second for first")
            self.assertFalse(ids_for_me)

    def test_triangle_noreferrals(self):
        '''Test that if two friends do know each other, this gives no referrals'''
        database = MockDatabase()
        own_id = "ABCD1234EFGH5678"
        first_id = "JUNGLEGYM1234567"
        second_id = "TESTAROSSA123456ANDINFACTthisoneisextraLOOOOONG"
        database.profiles.append({'torid':own_id, 'status':'self'})
        contact_str = contactutils.contacts_to_string([(second_id, "Alys")])
        database.profiles.append({'torid':first_id, 'status':'trusted', 'displayName':'Bob',
                                  'contactlist':contact_str})
        database.profiles.append({'torid':second_id, 'status':'trusted', 'displayName':'Alice'})
        manager = ContactManager(database, None)
        for id1, id2 in [(first_id, second_id), (second_id, first_id)]:
            results = manager.get_shared_possible_contacts(id1)
            shared_ids, ids_for_them, ids_for_me, name_map = results
            self.assertEqual(1, len(shared_ids), "1 shared contact")
            self.assertTrue(id2 in shared_ids, "shared contact correct")
            self.assertFalse(ids_for_them)
            self.assertFalse(ids_for_me)
            self.assertEqual(2, len(name_map), "2 names present")
            self.assertTrue(id1 in name_map, "id1 found")
            self.assertTrue(id2 in name_map, "id2 found")

    def test_friendsfriend_referme(self):
        '''Test that if a friend has another friend, this suggests for me'''
        database = MockDatabase()
        own_id = "ABCD1234EFGH5678"
        first_id = "RASPBERRYJAM1234"
        second_id = "AQUAMARINE123456"
        database.profiles.append({'torid':own_id, 'status':'self'})
        contact_str = contactutils.contacts_to_string([(second_id, "Squid")])
        database.profiles.append({'torid':first_id, 'status':'trusted', 'displayName':'Bob',
                                  'contactlist':contact_str})
        manager = ContactManager(database, None)
        results = manager.get_shared_possible_contacts(first_id)
        shared_ids, ids_for_them, ids_for_me, _ = results
        self.assertFalse(shared_ids, "no shared contacts")
        self.assertFalse(ids_for_them, "no suggestions for them")
        self.assertEqual(1, len(ids_for_me), "1 id for me")
        self.assertTrue(second_id in ids_for_me, "Suggest second for me")
        # Also check second id
        results = manager.get_shared_possible_contacts(second_id)
        shared_ids, ids_for_them, ids_for_me, _ = results
        self.assertEqual(1, len(shared_ids), "first id is shared contact")
        self.assertFalse(ids_for_them, "no suggestions for them")
        self.assertFalse(ids_for_me, "no suggestions for me either")


if __name__ == "__main__":
    unittest.main()
