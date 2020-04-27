'''Testing of the row creation for the inbox'''

import unittest
from murmeli import inbox
from murmeli.message import RegularMessage


class InboxTest(unittest.TestCase):
    '''Tests for the inbox'''

    def test_regular_message(self):
        '''Check the creation of a row for a regular incoming message'''
        own_torid = "someLongTorId-which-can-now-be-even-longer-than-before"
        body_text = "this is the message to be received"

        msg = RegularMessage()
        msg.set_field(msg.FIELD_SENDER_ID, own_torid)
        msg.set_field(msg.FIELD_MSGBODY, body_text)
        row = inbox.create_row(msg, inbox.MC_NORMAL_INCOMING)
        self.assertIsNotNone(row)
        self.assertTrue(bool(row)) # not empty
        self.assertTrue(isinstance(row, dict))
        self.assertEqual(row.get(inbox.FN_MSG_TYPE), 'normal')
        self.assertEqual(row.get(inbox.FN_FROM_ID), own_torid)
        # timestamp should be a generated string from the current time
        stamp = row.get(inbox.FN_TIMESTAMP)
        self.assertTrue(isinstance(stamp, str))
        self.assertEqual(len(stamp), 16)
        # check body
        self.assertEqual(row.get(inbox.FN_MSG_BODY), body_text)
        # just received so shouldn't have been read yet
        self.assertFalse(row.get(inbox.FN_BEEN_READ))

    def test_sent_message(self):
        '''Check the creation of a row for a sent message'''
        own_torid = "someLongTorId-which-can-now-be-even-longer-than-before"
        body_text = "this is the message to be received"

        msg = RegularMessage()
        msg.set_field(msg.FIELD_SENDER_ID, own_torid)
        msg.set_field(msg.FIELD_MSGBODY, body_text)
        row = inbox.create_row(msg, inbox.MC_NORMAL_SENT)
        self.assertEqual(row.get(inbox.FN_MSG_TYPE), 'normal')
        self.assertEqual(row.get(inbox.FN_FROM_ID), own_torid)
        self.assertEqual(row.get(inbox.FN_MSG_BODY), body_text)
        # message has been sent so should be marked as already read
        self.assertTrue(row.get(inbox.FN_BEEN_READ))


if __name__ == "__main__":
    unittest.main()
