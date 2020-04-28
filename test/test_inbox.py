'''Testing of the row creation for the inbox'''

import unittest
from murmeli import inbox
from murmeli.message import RegularMessage, ContactRequestMessage
from murmeli.message import ContactAcceptMessage, ContactDenyMessage
from murmeli.message import ContactReferralMessage, ContactReferRequestMessage


class InboxTest(unittest.TestCase):
    '''Tests for the inbox'''

    def test_regular_message(self):
        '''Check the creation of a row for a regular incoming message'''
        sender_torid = "someLongTorId-which-can-now-be-even-longer-than-before"
        body_text = "this is the message to be received"

        msg = RegularMessage()
        msg.set_field(msg.FIELD_SENDER_ID, sender_torid)
        msg.set_field(msg.FIELD_MSGBODY, body_text)
        row = inbox.create_row(msg, inbox.MC_NORMAL_INCOMING)
        self.assertIsNotNone(row)
        self.assertTrue(bool(row)) # not empty
        self.assertTrue(isinstance(row, dict))
        self.assertEqual(row.get(inbox.FN_MSG_TYPE), 'normal')
        self.assertEqual(row.get(inbox.FN_FROM_ID), sender_torid)
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
        body_text = "this is the message which was sent"

        msg = RegularMessage()
        msg.set_field(msg.FIELD_SENDER_ID, own_torid)
        msg.set_field(msg.FIELD_MSGBODY, body_text)
        row = inbox.create_row(msg, inbox.MC_NORMAL_SENT)
        self.assertEqual(row.get(inbox.FN_MSG_TYPE), 'normal')
        self.assertEqual(row.get(inbox.FN_FROM_ID), own_torid)
        self.assertEqual(row.get(inbox.FN_MSG_BODY), body_text)
        # message has been sent so should be marked as already read
        self.assertTrue(row.get(inbox.FN_BEEN_READ))

    def test_contact_request(self):
        '''Check the creation of a row for a received contact request'''
        sender_torid = "someLongTorId-which-can-now-be-even-longer-than-before"
        sender_name = "Chili, cheese & chips"
        body_text = "this is the introduction, with 'quotes' and \"quotes\""

        msg = ContactRequestMessage()
        msg.set_field(msg.FIELD_SENDER_ID, sender_torid)
        msg.set_field(msg.FIELD_SENDER_NAME, sender_name)
        msg.set_field(msg.FIELD_MESSAGE, body_text)
        row = inbox.create_row(msg, inbox.MC_CONREQ_INCOMING)
        self.assertEqual(row.get(inbox.FN_MSG_TYPE), 'contactrequest')
        self.assertEqual(row.get(inbox.FN_FROM_ID), sender_torid)
        self.assertEqual(row.get(inbox.FN_FROM_NAME), sender_name)
        self.assertEqual(row.get(inbox.FN_MSG_BODY), body_text)
        # message should be marked as unread
        self.assertFalse(row.get(inbox.FN_BEEN_READ))

    def test_contact_rejection(self):
        '''Check the creation of a row for a received contact rejection'''
        sender_torid = "someLongTorId-which-can-now-be-even-longer-than-before"

        msg = ContactDenyMessage()
        msg.set_field(msg.FIELD_SENDER_ID, sender_torid)
        row = inbox.create_row(msg, inbox.MC_CONRESP_REFUSAL)
        self.assertEqual(row.get(inbox.FN_MSG_TYPE), 'contactresponse')
        self.assertEqual(row.get(inbox.FN_FROM_ID), sender_torid)
        # message should be marked as unread
        self.assertFalse(row.get(inbox.FN_BEEN_READ))
        # request wasn't accepted
        self.assertFalse(row.get(inbox.FN_ACCEPTED))

    def test_contact_accept(self):
        '''Check the creation of a row for a received contact acceptance'''
        sender_torid = "someLongTorId-which-can-now-be-even-longer-than-before"
        sender_name = "Chili, cheese & O'chips"
        body_text = "this is the reply, with :, ; and ."
        key_text = "this is some string representation of the sender's public key"

        msg = ContactAcceptMessage()
        msg.set_field(msg.FIELD_SENDER_ID, sender_torid)
        msg.set_field(msg.FIELD_SENDER_NAME, sender_name)
        msg.set_field(msg.FIELD_MESSAGE, body_text)
        msg.set_field(msg.FIELD_SENDER_KEY, key_text)
        row = inbox.create_row(msg, inbox.MC_CONRESP_ACCEPT)
        self.assertEqual(row.get(inbox.FN_MSG_TYPE), 'contactresponse')
        self.assertEqual(row.get(inbox.FN_FROM_ID), sender_torid)
        self.assertEqual(row.get(inbox.FN_MSG_BODY), body_text)
        # public key of sender shouldn't be added to inbox, already dealt with on receipt
        self.assertIsNone(row.get(inbox.FN_PUBLIC_KEY))
        # message should be marked as unread
        self.assertFalse(row.get(inbox.FN_BEEN_READ))
        # request was accepted
        self.assertTrue(row.get(inbox.FN_ACCEPTED))

    def test_referral(self):
        '''Check the creation of a row for a received contact referral'''
        sender_torid = "someLongTorId-which-can-now-be-even-longer-than-before"
        friend_torid = "another_Really_Long_Tor,Id"
        friend_name = "Bätmän"
        body_text = "this is the intro message, with :, ; and ."
        key_text = "this is some string representation of the friend's public key"

        msg = ContactReferralMessage()
        msg.set_field(msg.FIELD_SENDER_ID, sender_torid)
        msg.set_field(msg.FIELD_MSGBODY, body_text)
        msg.set_field(msg.FIELD_FRIEND_NAME, friend_name)
        msg.set_field(msg.FIELD_FRIEND_ID, friend_torid)
        msg.set_field(msg.FIELD_FRIEND_KEY, key_text)
        row = inbox.create_row(msg, inbox.MC_REFER_INCOMING)
        self.assertEqual(row.get(inbox.FN_MSG_TYPE), 'contactrefer')
        self.assertEqual(row.get(inbox.FN_FROM_ID), sender_torid)
        self.assertEqual(row.get(inbox.FN_MSG_BODY), body_text)
        self.assertEqual(row.get(inbox.FN_FRIEND_NAME), friend_name)
        self.assertEqual(row.get(inbox.FN_FRIEND_ID), friend_torid)
        self.assertEqual(row.get(inbox.FN_PUBLIC_KEY), key_text)

    def test_referral_request(self):
        '''Check the creation of a row for a received contact referral request'''
        sender_torid = "someLongTorId-which-can-now-be-even-longer-than-before"
        friend_torid = "another_Really_Long_Tor,Id"
        body_text = "this is the intro message, with :, ; and ."

        msg = ContactReferRequestMessage()
        msg.set_field(msg.FIELD_SENDER_ID, sender_torid)
        msg.set_field(msg.FIELD_MSGBODY, body_text)
        msg.set_field(msg.FIELD_FRIEND_ID, friend_torid)
        row = inbox.create_row(msg, inbox.MC_REFERREQ_INCOMING)
        self.assertEqual(row.get(inbox.FN_MSG_TYPE), 'referrequest')
        self.assertEqual(row.get(inbox.FN_FROM_ID), sender_torid)
        self.assertEqual(row.get(inbox.FN_MSG_BODY), body_text)
        self.assertEqual(row.get(inbox.FN_FRIEND_ID), friend_torid)


if __name__ == "__main__":
    unittest.main()
