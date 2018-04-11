''''Testing of the functions of the MessageHandler'''

import unittest
from murmeli.handler import RobotMessageHandler
from murmeli.system import System, Component
from murmeli.message import StatusNotifyMessage


class MockDatabase(Component):
    '''Use a pretend database for the tests instead of a real one'''
    def __init__(self, parent):
        Component.__init__(self, parent, System.COMPNAME_DATABASE)
        self.outbox = []

    def add_message_to_outbox(self, msg):
        '''React to storing messages in the outbox'''
        self.outbox.append(msg)


class HandlerTest(unittest.TestCase):
    '''Tests for the handling of messages'''
    def setUp(self):
        self.sys = System()
        self.robot = RobotMessageHandler(self.sys)
        self.fakedb = MockDatabase(self.sys)
        self.sys.start()

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


if __name__ == "__main__":
    unittest.main()
