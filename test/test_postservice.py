''''Testing of the functions of the PostService'''

import unittest
import time
from murmeli.system import System, Component
from murmeli.postservice import PostService

class MockDatabase(Component):
    '''Use a pretend database for the tests instead of a real one'''
    def __init__(self, parent):
        Component.__init__(self, parent, System.COMPNAME_DATABASE)
        self.inbox = []
        self.outbox = []
        self.profiles = []
        self.num_msgs_added_to_outbox = 0
        self.num_msgs_deleted_from_outbox = 0

    def add_row_to_outbox(self, msg):
        '''React to storing messages in the outbox'''
        msg["_id"] = len(self.outbox)
        self.outbox.append(msg)
        self.num_msgs_added_to_outbox += 1

    def delete_from_outbox(self, index):
        '''React to storing messages in the outbox'''
        self.outbox[index] = None
        self.num_msgs_deleted_from_outbox += 1
        return True

    def get_outbox(self):
        '''Get the list of rows in the outbox'''
        return self.outbox

    def add_row_to_inbox(self, msg):
        '''React to storing messages in the inbox'''
        self.inbox.append(msg)

    def get_profile(self, torid=None):
        '''Get the profile for this torid'''
        for profile in self.profiles:
            if profile and profile.get('torid') == torid:
                return profile
        return None

    def get_profiles_with_status(self, status):
        '''Return list of profiles with the given status'''
        if isinstance(status, str):
            return [profile for profile in self.profiles if profile.get('status') == status]
        if isinstance(status, list):
            return [profile for profile in self.profiles if profile.get('status') in status]
        return []

    def add_or_update_profile(self, profile):
        '''Add or update the given profile'''
        self.profiles.append(profile)


class MockCrypto(Component):
    '''Use a pretend crypto system for the tests instead of a real one'''
    def __init__(self, parent):
        Component.__init__(self, parent, System.COMPNAME_CRYPTO)

    def import_public_key(self, strkey):
        '''Fake the import of a key, return a fake keyid'''
        return strkey + "_keyid"

    def encrypt_and_sign(self, message, recipient, own_key):
        '''Fake the encryption of the given message for the given recipient'''
        result = "'%s' for '%s' signed by '%s'" % (message, recipient, own_key)
        return result.encode("utf-8")


class MockTransport:
    '''Class to replace the regular message-sending mechanism with a mock'''
    def __init__(self, succeed):
        self.succeed = succeed
        self.num_sent = 0

    def send_message(self, msg, whoto):
        '''Pretend to send the given message'''
        if msg and whoto:
            self.num_sent += 1
            return self.succeed
        return False


class PostServiceTest(unittest.TestCase):
    '''Tests for the handling of messages by the postal service'''
    def setUp(self):
        '''Setup the tests'''
        self.sys = System()
        self.fakedb = MockDatabase(self.sys)
        self.sys.add_component(self.fakedb)
        self.fakecrypto = MockCrypto(self.sys)
        self.sys.add_component(self.fakecrypto)

    def tearDown(self):
        '''Stop the system'''
        self.sys.stop()

    def test_broadcast_no_profiles(self):
        '''Check that broadcast with no friends doesn't add to outbox'''
        postman = PostService(self.sys)
        postman.set_timer_interval(0)
        self.sys.add_component(postman)
        # Add an untrusted friend
        self.fakedb.add_or_update_profile({"torid":"abc1", "status":"untrusted"})
        # Trigger broadcast, wait for it to finish
        postman.request_broadcast()
        time.sleep(3)
        # Check outbox
        self.assertEqual(0, self.fakedb.num_msgs_added_to_outbox, "0 messages added")

    def test_broadcast_one_profile(self):
        '''Check that broadcast with one friend does add to outbox'''
        transport = MockTransport(False)
        postman = PostService(self.sys, transport)
        postman.set_timer_interval(0)
        self.sys.add_component(postman)
        # Add self (torid None)
        self.fakedb.add_or_update_profile({"torid":None, "status":"self"})
        # Add two friends
        self.fakedb.add_or_update_profile({"torid":"abc1def2ghi3jkl4", "status":"untrusted"})
        self.fakedb.add_or_update_profile({"torid":"def1ghi2jkl3mno4", "status":"trusted",
                                           "keyid":"somekey"})
        # Trigger broadcast, wait for it to finish
        postman.request_broadcast()
        postman.request_flush()
        time.sleep(8)
        # Check outbox
        self.assertEqual(1, self.fakedb.num_msgs_added_to_outbox, "1 message added")
        # Broadcasted status messages should not be queued, so message in outbox should be empty
        for msg in self.fakedb.get_outbox():
            self.assertIsNone(msg, "Message should be deleted")
        # Check transport
        self.assertEqual(1, transport.num_sent, "1 message sent")

        # Stop system again
        self.sys.stop()


    def test_flush_one_message(self):
        '''Check that flushing a normal queued message passes it to the transport'''
        transport = MockTransport(False)
        postman = PostService(self.sys, transport)
        postman.set_timer_interval(0)
        self.sys.add_component(postman)
        # Add friend
        self.fakedb.add_or_update_profile({"torid":"def1ghi2jkl3mno4", "status":"trusted"})
        # Add message for this friend
        self.fakedb.add_row_to_outbox({"recipient":"def1ghi2jkl3mno4", "relays":None,
                                       "message":"a1fa8008",
                                       "queue":True,
                                       "msgType":1})
        postman.request_flush()
        time.sleep(8)
        # Check outbox, message should still be there as it's queued
        self.assertEqual(1, self.fakedb.num_msgs_added_to_outbox, "1 message added")
        for msg in self.fakedb.get_outbox():
            self.assertIsNotNone(msg, "Message should still be there")
        # Check transport
        self.assertEqual(1, transport.num_sent, "1 message sent")

        # Stop system again
        self.sys.stop()


if __name__ == "__main__":
    unittest.main()
