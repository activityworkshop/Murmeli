'''Module for testing the tor client'''

import unittest
import os
import time
import socks
from murmeli import system
from murmeli.torclient import TorClient
from murmeli.message import ContactRequestMessage


class FakeMessageHandler(system.Component):
    '''Handler for receiving messages from Tor'''
    def __init__(self, sys):
        system.Component.__init__(self, sys, system.System.COMPNAME_MSG_HANDLER)
        self.messages = []

    def receive(self, msg):
        '''Receive an incoming message'''
        if msg:
            self.messages.append(msg)


class TorTest(unittest.TestCase):
    '''Tests for the tor communication'''

    def test_sending(self):
        '''Test sending non-valid and valid data to the listener'''
        sys = system.System()
        tordir = os.path.join("test", "outputdata", "tor")
        os.makedirs(tordir, exist_ok=True)
        tor_client = TorClient(sys, tordir)
        sys.add_component(tor_client)
        self.assertTrue(tor_client.started, "Tor started")
        time.sleep(5)

        # invalid data
        torid = tor_client.get_own_torid()
        print("Torid:", torid)
        self.assertTrue(torid, "Tor id obtained")
        # Send a message
        success = self.send_message(torid, "abcdef".encode("utf-8"))
        self.assertTrue(self.send_message(torid, "murmeli".encode("utf-8")), "Magic sent")
        time.sleep(5)

        # Add receiver to handle the messages
        receiver = FakeMessageHandler(sys)
        sys.add_component(receiver)
        self.assertFalse(receiver.messages, "no messages received yet")

        # contact request
        req = ContactRequestMessage()
        sender_name = "Worzel Gummidge"
        sender_msg = "Watch out for the volcano, it's radioactive!"
        req.set_field(req.FIELD_SENDER_NAME, sender_name)
        req.set_field(req.FIELD_MESSAGE, sender_msg)
        unenc_output = req.create_output(encrypter=None)
        torid = tor_client.get_own_torid()
        self.assertTrue(self.send_message(torid, unenc_output), "Real message sent")
        time.sleep(5)
        # Now check it has been received
        self.assertEqual(len(receiver.messages), 1, "1 message received")
        received = receiver.messages.pop()
        print("Got message:", received)
        self.assertEqual(received.get_field(req.FIELD_SENDER_NAME), sender_name, "name match")
        self.assertEqual(received.get_field(req.FIELD_MESSAGE), sender_msg, "msg match")

        # Finished
        sys.stop()
        self.assertFalse(tor_client.started, "Tor stopped")
        time.sleep(5)


    def send_message(self, recipient, message):
        '''Send a message to the given recipient'''
        # Try a few times because the service might take a few seconds to become available
        for _ in range(10):
            try:
                socket = socks.socksocket()
                socket.setproxy(socks.PROXY_TYPE_SOCKS4, "localhost", 11109)
                socket.connect((recipient + ".onion", 11009))
                numsent = socket.send(message)
                socket.close()
                return numsent == len(message)
            except Exception as e:
                print("Woah, that threw something:", e)
            time.sleep(8)


if __name__ == "__main__":
    unittest.main()
