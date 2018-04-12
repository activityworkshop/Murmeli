''''Testing of the functions of the MessageHandler'''

import unittest
from murmeli.messagehandler import RobotMessageHandler
from murmeli.system import System, Component
from murmeli.config import Config
from murmeli.message import (StatusNotifyMessage, ContactRequestMessage,
                             ContactAcceptMessage, ContactReferralMessage)


class MockDatabase(Component):
    '''Use a pretend database for the tests instead of a real one'''
    def __init__(self, parent):
        Component.__init__(self, parent, System.COMPNAME_DATABASE)
        self.outbox = []
        self.profiles = []

    def add_message_to_outbox(self, msg):
        '''React to storing messages in the outbox'''
        self.outbox.append(msg)

    def get_profiles_with_status(self, status):
        '''Return list of profiles with the given status'''
        if self.profiles:
            return self.profiles[0]
        return None

    def add_or_update_profile(self, prof):
        '''Add or update the given profile'''
        self.profiles.append(prof)


class HandlerTest(unittest.TestCase):
    '''Tests for the handling of messages'''
    def setUp(self):
        self.sys = System()
        self.robot = RobotMessageHandler(self.sys)
        self.fakedb = MockDatabase(self.sys)
        config = Config(self.sys)
        config.set_property(config.KEY_ROBOT_OWNER_KEY, "EasterBunny") # keyid, not torid

    def test_sending_nonsense(self):
        '''Just check that nothing falls over when non-message objects are sent'''
        self.robot.receive(None)
        self.robot.receive("just a string")
        self.robot.receive(3.5)
        self.assertFalse(self.fakedb.outbox, "outbox still empty")

    def test_sending_pongs_pings(self):
        '''Check that pings are replied to and pongs are ignored'''
        pong = StatusNotifyMessage()
        pong.set_field(pong.FIELD_PING, 0)
        pong.set_field(pong.FIELD_SENDER_ID, "abcdefg")
        self.robot.receive(pong)
        self.assertFalse(self.fakedb.outbox, "outbox still empty after pong")
        # ping but offline - should also be ignored
        pong.set_field(pong.FIELD_PING, 1)
        pong.set_field(pong.FIELD_ONLINE, 0)
        self.robot.receive(pong)
        self.assertFalse(self.fakedb.outbox, "outbox still empty after offline ping")
        # online ping - should generate pong
        pong.set_field(pong.FIELD_ONLINE, 1)
        self.robot.receive(pong)
        self.assertEqual(len(self.fakedb.outbox), 1, "outbox now has one message")
        reply = self.fakedb.outbox.pop()
        self.assertTrue(isinstance(reply, StatusNotifyMessage), "reply is a notify")
        self.assertEqual(reply.get_field(reply.FIELD_PING), 0, "reply is a pong")
        self.assertTrue(reply.get_field(reply.FIELD_ONLINE), "reply is online")
        self.assertEqual(reply.recipients, ["abcdefg"], "reply is for abcdefg")

    def test_sending_conreqs_to_robot(self):
        '''Check that contact requests are handled properly by robot'''
        req = ContactRequestMessage()
        # send a message with a different sender key, this should be ignored
        req.set_field(req.FIELD_SENDER_KEY, "ABC987DEF")
        req.set_field(req.FIELD_SENDER_NAME, "Zürich")
        req.set_field(req.FIELD_SENDER_ID, "NOP456HAA")
        self.robot.receive(req)
        self.assertFalse(self.fakedb.outbox, "outbox still empty after invalid contactreq")
        # send a second message with a matching sender key, this should result
        # in a database update and an accept message
        req.set_field(req.FIELD_SENDER_KEY, "EasterBunny")
        self.robot.receive(req)
        self.assertEqual(len(self.fakedb.outbox), 1, "outbox now has one message")
        reply = self.fakedb.outbox.pop()
        self.assertTrue(isinstance(reply, ContactAcceptMessage), "reply is a contactaccept")

    def test_sending_conreferral_to_robot(self):
        '''Check that contact referrals are handled properly by robot'''
        owner_id = "b83jdn100uviva33"
        req = ContactReferralMessage()
        # database has no owner set, so any referrals should be ignored
        req.set_field(req.FIELD_SENDER_ID, owner_id)
        req.set_field(req.FIELD_FRIEND_NAME, "Bruce Wayne")
        req.set_field(req.FIELD_FRIEND_ID, "802.11ac")
        req.set_field(req.FIELD_FRIEND_KEY, "Really quite a rather long string of digits")
        self.robot.receive(req)
        self.assertFalse(self.fakedb.outbox, "outbox still empty after invalid referral")
        # Now add an owner to the db
        self.fakedb.profiles.append({"status":"owner", "torid":owner_id})
        self.robot.receive(req)
        self.assertEqual(len(self.fakedb.outbox), 1, "outbox now has one message")
        self.assertEqual(len(self.fakedb.profiles), 2, "now two profiles")
        reply = self.fakedb.outbox.pop()
        self.assertTrue(isinstance(reply, ContactAcceptMessage), "reply is a contactaccept")


if __name__ == "__main__":
    unittest.main()
