'''Module for testing the contact manager class'''

import unittest
from murmeli.contactmgr import ContactManager
from murmeli import contactutils


class MockDatabase:
    '''Use a pretend database for the tests instead of a real one'''
    def __init__(self):
        self.profiles = []
        self.inbox = []
        self.outbox = []

    def get_profile(self, torid=None):
        '''Get the profile for this torid'''
        if torid:
            for profile in self.profiles:
                if profile and profile.get('torid') == torid:
                    return profile
        else:
            # No id given, so get our own profile
            for profile in self.profiles:
                if profile and profile.get("status") == "self":
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

    def add_or_update_profile(self, inprofile):
        '''add or update the given profile'''
        for profile in self.profiles:
            if profile and profile.get('torid') == inprofile.get('torid'):
                profile.update(inprofile)
                return True
        if inprofile and inprofile.get('torid'):
            self.profiles.append(inprofile)
            return True
        return False

    def get_inbox(self):
        '''Get the whole inbox'''
        return self.inbox

    def delete_from_inbox(self, row_id):
        '''Delete a single message from the inbox'''
        if row_id is not None:
            self.inbox[row_id].update({'deleted':True})

    def add_row_to_outbox(self, inrow):
        '''add a row to the outbox'''
        self.outbox.append(inrow)


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


class InitiateWithRobotTest(unittest.TestCase):
    '''Tests for initiating contact with a robot'''

    def test_noid_fail(self):
        '''Test that initiating contact with an empty or invalid robot id fails'''
        database = MockDatabase()
        own_id = "ABCD1234EFGH5678ANDcanbeLONGERTHANTHATTOO"
        database.profiles.append({'torid':own_id, 'status':'self'})
        manager = ContactManager(database, None)
        self.assertFalse(manager.handle_initiate(None, 'robot', '', robot=True))
        self.assertFalse(manager.handle_initiate("", 'robot', '', robot=True))
        self.assertFalse(manager.handle_initiate(own_id, 'robot', '', robot=True))

    def test_request_new_robot_success(self):
        '''Test that initiating contact with valid robot id succeeds'''
        database = MockDatabase()
        own_id = "ABCD1234EFGH5678ANDcanEVENbeLONGERTHANTHAT"
        own_keyid = "KeyIdForMe"
        robot_id = "some other alphanumeric string even with spaces in"
        database.profiles.append({'torid':own_id, 'keyid':own_keyid, 'status':'self'})
        manager = ContactManager(database, None)
        self.assertTrue(manager.handle_initiate(robot_id, 'robot', '', robot=True))
        # profiles should be updated
        own_profile = database.get_profile()
        self.assertEqual(own_profile.get('robot'), robot_id)
        self.assertEqual(2, len(database.profiles))
        # message should be waiting in outbox
        self.assertEqual(1, len(database.outbox))

    def test_request_robot_existing_fail(self):
        '''Test that initiating contact with an existing contact fails'''
        database = MockDatabase()
        own_id = "ABCD1234EFGH5678ANDcanEVENbeLONGERTHANTHAT"
        own_keyid = "KeyIdForMe"
        robot_id = "some other alphanumeric string even with spaces in"
        database.profiles.append({'torid':own_id, 'keyid':own_keyid, 'status':'self'})
        database.profiles.append({'torid':robot_id, 'status':'trusted'})
        manager = ContactManager(database, None)
        self.assertFalse(manager.handle_initiate(robot_id, 'robot', '', robot=True))
        # no profile added, no message for outbox
        self.assertEqual(2, len(database.profiles))
        other_profile = database.get_profile(robot_id)
        self.assertEqual('trusted', other_profile.get('status'))
        self.assertEqual(0, len(database.outbox))

    def test_check_robotid(self):
        '''Test that checking robot id succeeds'''
        database = MockDatabase()
        own_id = "ABCD1234EFGH5678ANDcanEVENbeLONGERTHANTHAT"
        own_keyid = "KeyIdForMe"
        robot_id = "some other alphanumeric string even with spaces in"
        database.profiles.append({'torid':own_id, 'keyid':own_keyid, 'status':'self',
                                  'robot':robot_id})
        database.profiles.append({'torid':robot_id, 'status':'reqrobot'})
        manager = ContactManager(database, None)
        self.assertTrue(manager.is_robot_id(robot_id))
        self.assertFalse(manager.is_robot_id("Some other id"))


class MockCrypto:
    '''Pretend to be a crypto object'''
    def __init__(self):
        self.keys_imported = 0

    @staticmethod
    def get_public_key(_):
        '''Return the specified public key'''
        return "public key"

    def import_public_key(self, key_str):
        '''Pretend to import the key'''
        self.keys_imported += 1
        return "key-id" + key_str[:10]

    @staticmethod
    def encrypt_and_sign(message, recipient, own_key):
        '''Encrypt and sign the given message'''
        return message + recipient.encode('utf-8') + str(own_key).encode('utf-8')


class ContactResponseTest(unittest.TestCase):
    '''Tests for responding to a contact request'''

    def test_reject_without_request(self):
        '''Test that rejecting without a request sends a response'''
        database = MockDatabase()
        database.profiles.append({'torid':'pomegranate', 'status':'self'})
        manager = ContactManager(database, None)
        manager.handle_deny("abcde")
        self.assertEqual(1, len(database.outbox))
        self.assertEqual(1, len(database.profiles))


    def test_reject(self):
        '''Test that rejecting a request sends a reply and deletes the message'''
        database = MockDatabase()
        database.profiles.append({'torid':'pomegranate', 'status':'self'})
        database.inbox.append({'fromId':'abcde', 'msg':'intro', '_id':0})
        manager = ContactManager(database, None)
        manager.handle_deny("abcde")
        self.assertTrue(database.inbox[0].get('deleted'))
        self.assertEqual(1, len(database.outbox))
        self.assertEqual(1, len(database.profiles))

    def test_accept_without_crypto(self):
        '''Test that accepting without a crypto service does nothing'''
        database = MockDatabase()
        database.profiles.append({'torid':'cauliflower', 'status':'self'})
        manager = ContactManager(database, None)
        manager.handle_accept("abcde", "please")
        self.assertEqual(0, len(database.outbox))
        self.assertEqual(1, len(database.profiles))

    def test_accept_without_request(self):
        '''Test that accepting without a corresponding request does nothing'''
        database = MockDatabase()
        database.profiles.append({'torid':'cauliflower', 'status':'self'})
        crypto = MockCrypto()
        manager = ContactManager(database, crypto)
        manager.handle_accept("abcde", "please")
        self.assertEqual(0, len(database.outbox))
        self.assertEqual(1, len(database.profiles))

    def test_accept_with_request(self):
        '''Test that accepting with a corresponding request sends a reply'''
        database = MockDatabase()
        database.profiles.append({'torid':'cauliflower', 'status':'self', 'name':'Me'})
        public_key = "somelongkey" * 10
        database.inbox.append({'fromId':'abcde', 'msg':'intro', '_id':0,
                               'publicKey':public_key,
                               'messageType':'contactrequest'})
        crypto = MockCrypto()
        manager = ContactManager(database, crypto)
        manager.handle_accept("abcde", "please")
        self.assertEqual(1, len(database.outbox))
        self.assertEqual(2, len(database.profiles))
        self.assertEqual(1, crypto.keys_imported)


if __name__ == "__main__":
    unittest.main()
