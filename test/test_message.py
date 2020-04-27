'''Module for testing the different message types'''

import unittest
from murmeli import message


class ChomperTest(unittest.TestCase):
    '''Tests for the chomper'''

    def test_chomping_other_types(self):
        '''Test what happens when a chomper gets something that is not bytes or is empty'''
        chomper = message.ByteChomper(None)
        self.assertFalse(chomper.get_rest(), "Empty chomper")
        chomper = message.ByteChomper([13, 24, 1])
        self.assertFalse(chomper.get_field(2), "Empty chomper")
        self.assertFalse(chomper.get_rest(), "Empty chomper")
        chomper = message.ByteChomper("seven")
        self.assertFalse(chomper.get_byte_value(1), "Empty chomper")
        self.assertFalse(chomper.get_string(3), "Empty chomper")
        self.assertFalse(chomper.get_string_with_length(2), "Empty chomper")
        self.assertFalse(chomper.get_rest(), "Empty chomper")
        chomper = message.ByteChomper(bytes())
        self.assertEqual(chomper.get_byte_value(1), 0, "Empty chomper")

    def test_chomping_string(self):
        '''Test what happens when a chomper gets a simple string'''
        chomper = message.ByteChomper("multiple parrots".encode("utf-8"))
        self.assertEqual(chomper.get_string(5), "multi", "Substring of 5")
        self.assertEqual(chomper.get_string(7), "ple par", "Substring of 7")
        self.assertEqual(chomper.get_string(7), "rots", "Substring past end")
        self.assertFalse(chomper.get_rest(), "Empty chomper")

    def test_chomping_bytevalues(self):
        '''Test what happens when a chomper gets single byte values'''
        vals = bytearray([val*2 for val in range(8)])
        chomper = message.ByteChomper(bytes(vals))
        self.assertEqual(chomper.get_byte_value(1), 0, "0 matches")
        self.assertEqual(chomper.get_byte_value(1), 2, "1 matches")
        self.assertEqual(chomper.get_byte_value(1), 4, "2 matches")
        self.assertEqual(chomper.get_byte_value(1), 6, "3 matches")
        three_bytes = 8 + (10 * 256) + (12 * 256 * 256) # lowest byte first
        self.assertEqual(chomper.get_byte_value(3), three_bytes, "Last three matches")


class TimestampTest(unittest.TestCase):
    '''Tests for the timestamp handling'''
    def test_string_conversion(self):
        '''Test converting a timestamp to a string and back again'''
        now = message.Message.make_current_timestamp()
        self.assertTrue(isinstance(now, float))
        as_string = message.Message.timestamp_to_string(now)
        self.assertIsNotNone(as_string, "stamp converted to string")
        self.assertTrue(isinstance(as_string, str), "String created")
        self.assertEqual(len(as_string), 16, "Should be 16 chars long")
        back_again = message.Message.string_to_timestamp(as_string)
        self.assertIsNotNone(back_again, "string converted back again")
        self.assertTrue(isinstance(back_again, float))
        timediff = abs(now - back_again)
        self.assertTrue(timediff < 60.0, "Floats should be equal to the nearest minute")


class UnencMessageTest(unittest.TestCase):
    '''Tests for the unencrypted messages'''

    def test_unencrypted_message(self):
        '''Test an arbitrary unencrypted message'''
        test_type = 19
        unenc = message.UnencryptedMessage(test_type)
        self.assertIsNotNone(unenc, "Message created")
        self.assertEqual(unenc.enc_type, message.Message.ENCTYPE_NONE, "Not encrypted")
        self.assertEqual(unenc.msg_type, 19, "Type passed in")
        unenc.set_field("roundabout", 14)
        self.assertTrue("roundabout" in unenc.body, "arbitrary field stored")

        output = unenc.create_output()
        self.assertTrue(output.startswith(message.Message.MAGIC_TOKEN.encode("utf-8")),
                        "Begins with magic")
        enc_type = output[len(message.Message.MAGIC_TOKEN) + 16]
        self.assertEqual(enc_type, message.Message.ENCTYPE_NONE, "Not encrypted")
        msg_len = output[len(message.Message.MAGIC_TOKEN) + 17]
        self.assertEqual(msg_len, 4, "Length 4")
        msg_type = output[len(message.Message.MAGIC_TOKEN) + 21]
        self.assertEqual(msg_type, test_type, "Type matches")
        msg_ver = output[len(message.Message.MAGIC_TOKEN) + 22]
        self.assertEqual(msg_ver, 1, "Version always 1")
        self.assertTrue(output.endswith(("{}" + message.Message.MAGIC_TOKEN).encode("utf-8")),
                        "Ends with magic")

    def test_contact_request_message(self):
        '''Test construction of contact request message'''
        req = message.ContactRequestMessage()
        self.assertIsNotNone(req, "Request created")
        self.assertFalse(req.is_complete_for_sending(), "Not complete yet")
        empty_checksum = message.Message.make_checksum(req.create_payload())
        self.assertTrue(isinstance(empty_checksum, bytes), "Correct type")
        self.assertEqual(len(empty_checksum), 16, "Correct length")
        self.assertTrue(empty_checksum.startswith("i".encode("utf-8")), "starts with i")
        unenc_output = req.create_output(encrypter=None)
        self.assertIsNotNone(unenc_output, "Output created")
        self.assertTrue(isinstance(unenc_output, bytes), "Correct type")
        # can we convert back again?
        back_again = message.Message.from_received_data(unenc_output)
        self.assertIsNotNone(back_again, "Recreated message")
        self.assertTrue(isinstance(back_again, message.ContactRequestMessage), "Correct type")
        self.assertFalse(back_again.body, "Empty body")
        self.assertEqual(1, back_again.version_number, "Version 1")

    def test_contactrequest_with_fields(self):
        '''Test construction of contact request message with fields'''
        test_id = "hijklm1234567890"
        test_name = "Michael Palin"
        test_msg = "I'm a lumberjack and I'm ok"
        test_key = "some-kind-of-key"
        req = message.ContactRequestMessage()
        req.set_field(req.FIELD_SENDER_ID, test_id)
        req.set_field(req.FIELD_SENDER_NAME, test_name)
        req.set_field(req.FIELD_MESSAGE, test_msg)
        self.assertFalse(req.is_complete_for_sending(), "Not complete yet")
        req.set_field(req.FIELD_SENDER_KEY, test_key)
        self.assertTrue(req.is_complete_for_sending(), "Complete")
        unenc_output = req.create_output(encrypter=None)
        # can we convert back again?
        back_again = message.Message.from_received_data(unenc_output)
        self.assertTrue(isinstance(back_again, message.ContactRequestMessage), "Correct type")
        self.assertEqual(back_again.msg_type, req.TYPE_CONTACT_REQUEST, "Typenum match")
        self.assertEqual(back_again.body[req.FIELD_SENDER_NAME], test_name, "Name match")
        self.assertEqual(back_again.body[req.FIELD_SENDER_ID], test_id, "Id match")
        self.assertEqual(back_again.body[req.FIELD_MESSAGE], test_msg, "Msg match")
        self.assertEqual(back_again.body[req.FIELD_SENDER_KEY], test_key, "Key match")
        self.assertEqual(1, back_again.version_number, "Version 1")

    def test_contact_deny_message(self):
        '''Test construction of contact deny message'''
        req = message.ContactDenyMessage()
        test_id = "1234567890hijklm"
        req.set_field(req.FIELD_SENDER_ID, test_id)
        self.assertTrue(req.is_complete_for_sending(), "Complete")
        unenc_output = req.create_output(encrypter=None)
        # can we convert back again?
        back_again = message.Message.from_received_data(unenc_output)
        self.assertTrue(isinstance(back_again, message.ContactDenyMessage), "Correct type")
        self.assertEqual(back_again.msg_type, req.TYPE_CONTACT_RESPONSE, "Typenum match")
        self.assertEqual(back_again.body[req.FIELD_SENDER_ID], test_id, "Id match")
        self.assertEqual(1, back_again.version_number, "Version 1")


class AsymmMessageTest(unittest.TestCase):
    '''Tests for the asymmetric messages'''

    def test_contact_accept_message(self):
        '''Test the contact accept message (still without encryption though)'''
        req = message.ContactAcceptMessage()
        self.assertTrue(isinstance(req, message.AsymmetricMessage), "Correct type")
        test_id = "1234567890hijklm"
        test_msg = "She said, \"he's a very naughty boy\"."
        req.set_field(req.FIELD_SENDER_ID, test_id)
        req.set_field(req.FIELD_MESSAGE, test_msg)
        unenc_output = req.create_output(encrypter=None)
        # can we convert back again?
        back_again = message.Message.from_received_data(unenc_output)
        self.assertTrue(isinstance(back_again, message.ContactAcceptMessage), "Correct type")
        self.assertTrue(isinstance(back_again, message.AsymmetricMessage), "Correct type")
        self.assertEqual(back_again.msg_type, req.TYPE_CONTACT_RESPONSE, "Typenum match")
        self.assertEqual(back_again.body[req.FIELD_SENDER_ID], test_id, "Id match")
        self.assertEqual(back_again.body[req.FIELD_MESSAGE], test_msg, "Msg match")
        self.assertEqual(1, back_again.version_number, "Version 1")

    def test_status_notify_message(self):
        '''Test the status notify message (still without encryption though)'''
        notify = message.StatusNotifyMessage()
        self.assertTrue(isinstance(notify, message.StatusNotifyMessage), "Correct type")
        test_hash = "AlphaNum3ric_str1ng"
        notify.set_field(notify.FIELD_PROFILE_HASH, test_hash)
        unenc_output = notify.create_output(encrypter=None)
        # can we convert back again?
        back_again = message.Message.from_received_data(unenc_output)
        self.assertTrue(isinstance(back_again, message.StatusNotifyMessage), "Correct type")
        self.assertTrue(isinstance(back_again, message.AsymmetricMessage), "Correct type")
        self.assertEqual(back_again.msg_type, notify.TYPE_STATUS_NOTIFY, "Typenum match")
        self.assertEqual(back_again.body[notify.FIELD_PROFILE_HASH], test_hash, "Hash match")
        self.assertTrue(back_again.body[notify.FIELD_PING], "Ping match")
        self.assertTrue(back_again.body[notify.FIELD_ONLINE], "Online match")
        self.assertIsNotNone(back_again.timestamp, "Timestamp given")
        # Check that a ping of 0 (false) also gets transferred
        notify.set_field(notify.FIELD_PING, 0)
        unenc_output = notify.create_output(encrypter=None)
        back_again = message.Message.from_received_data(unenc_output)
        self.assertFalse(back_again.body[notify.FIELD_PING], "Pong match")
        # and an online flag of false
        notify.set_field(notify.FIELD_ONLINE, 0)
        unenc_output = notify.create_output(encrypter=None)
        back_again = message.Message.from_received_data(unenc_output)
        self.assertFalse(back_again.body[notify.FIELD_ONLINE], "Online match")
        self.assertEqual(1, back_again.version_number, "Version 1")

    def test_info_request_message(self):
        '''Test the info request message (still without encryption)'''
        req = message.InfoRequestMessage()
        self.assertTrue(isinstance(req, message.InfoRequestMessage), "Correct type")
        self.assertTrue(isinstance(req, message.AsymmetricMessage), "Correct type")
        unenc_output = req.create_output(encrypter=None)
        back_again = message.Message.from_received_data(unenc_output)
        self.assertTrue(isinstance(back_again, message.InfoRequestMessage), "Correct type")
        self.assertEqual(back_again.body[req.FIELD_INFOTYPE], req.INFO_PROFILE, "Content match")
        self.assertEqual(1, back_again.version_number, "Version 1")

    def test_info_response_message(self):
        '''Test the info response message for a profile (still without encryption)'''
        resp = message.InfoResponseMessage()
        self.assertTrue(isinstance(resp, message.InfoResponseMessage), "Correct type")
        self.assertTrue(isinstance(resp, message.AsymmetricMessage), "Correct type")
        self.assertFalse(resp.is_complete_for_sending(), "Not complete yet")
        test_profile = "example profile string"
        resp.set_field(resp.FIELD_RESULT, test_profile)
        self.assertTrue(resp.is_complete_for_sending(), "complete")
        unenc_output = resp.create_output(encrypter=None)
        back_again = message.Message.from_received_data(unenc_output)
        self.assertTrue(isinstance(back_again, message.InfoResponseMessage), "Correct type")
        self.assertEqual(back_again.body[resp.FIELD_INFOTYPE], resp.INFO_PROFILE, "Content match")
        self.assertEqual(back_again.body[resp.FIELD_RESULT], test_profile, "Content match")
        self.assertEqual(1, back_again.version_number, "Version 1")

    def test_regular_message(self):
        '''Test the regular message (still without encryption)'''
        reg = message.RegularMessage()
        self.assertTrue(isinstance(reg, message.RegularMessage), "Correct type")
        msg_body = "Jumping jellybabies"
        reg.set_field(reg.FIELD_MSGBODY, msg_body)
        unenc_output = reg.create_output(encrypter=None)
        back_again = message.Message.from_received_data(unenc_output)
        self.assertTrue(isinstance(back_again, message.RegularMessage), "Correct type")
        self.assertEqual(back_again.body[back_again.FIELD_MSGBODY], msg_body, "Content match")
        self.assertEqual(1, back_again.version_number, "Version 1")

    def test_referral_message(self):
        '''Test the contact referral message (still without encryption)'''
        referral = message.ContactReferralMessage()
        self.assertTrue(isinstance(referral, message.ContactReferralMessage), "Correct type")
        msg_body = "Snoring snowflakes"
        friend_id = "ISO-8859-1"
        friend_name = "Adrian Mole"
        friend_key = "Some really long string describing the whole public key for this person..."
        referral.set_field(referral.FIELD_MSGBODY, msg_body)
        referral.set_field(referral.FIELD_FRIEND_ID, friend_id)
        referral.set_field(referral.FIELD_FRIEND_NAME, friend_name)
        referral.set_field(referral.FIELD_FRIEND_KEY, friend_key)
        unenc_output = referral.create_output(encrypter=None)
        back_again = message.Message.from_received_data(unenc_output)
        self.assertTrue(isinstance(back_again, message.ContactReferralMessage), "Correct type")
        self.assertEqual(back_again.body[back_again.FIELD_MSGBODY], msg_body, "Content match")
        self.assertEqual(back_again.body[back_again.FIELD_FRIEND_ID], friend_id, "Id match")
        self.assertEqual(back_again.body[back_again.FIELD_FRIEND_NAME], friend_name, "Name match")
        self.assertEqual(back_again.body[back_again.FIELD_FRIEND_KEY], friend_key, "Key match")
        self.assertTrue(back_again.is_normal_referral(), "Correct type of referral")
        self.assertEqual(1, back_again.version_number, "Version 1")

    def test_referral_message_types(self):
        '''Test the types of the contact referral message'''
        referral = message.ContactReferralMessage()
        self.assertTrue(referral.is_normal_referral(), "Correct type of referral")
        self.assertFalse(referral.is_robot_referral(), "Not a robot referral")
        self.assertFalse(referral.is_robot_removal(), "Not a robot removal")
        referral.set_field(referral.FIELD_REFERRAL_TYPE, referral.REFERTYPE_ROBOT)
        self.assertFalse(referral.is_normal_referral(), "Not normal referral")
        self.assertTrue(referral.is_robot_referral(), "Robot referral")
        self.assertFalse(referral.is_robot_removal(), "Not a robot removal")
        referral.set_field(referral.FIELD_REFERRAL_TYPE, referral.REFERTYPE_REMOVEROBOT)
        self.assertFalse(referral.is_normal_referral(), "Not normal referral")
        self.assertFalse(referral.is_robot_referral(), "Not a robot referral")
        self.assertTrue(referral.is_robot_removal(), "Robot removal")


    def test_request_referral(self):
        '''Test the contact referral request message (still without encryption)'''
        request = message.ContactReferRequestMessage()
        self.assertTrue(isinstance(request, message.ContactReferRequestMessage), "Correct type")
        msg_body = "(brackets and [bytes])"
        friend_id = "Crankleberries01234567890"
        request.set_field(request.FIELD_MSGBODY, msg_body)
        request.set_field(request.FIELD_FRIEND_ID, friend_id)
        unenc_output = request.create_output(encrypter=None)
        back_again = message.Message.from_received_data(unenc_output)
        self.assertTrue(isinstance(back_again, message.ContactReferRequestMessage), "Correct type")
        self.assertEqual(back_again.body[back_again.FIELD_MSGBODY], msg_body, "Content match")
        self.assertEqual(back_again.body[back_again.FIELD_FRIEND_ID], friend_id, "Id match")
        self.assertEqual(1, back_again.version_number, "Version 1")

    def test_reconstructing_message(self):
        '''Test the reconstruction of the contact accept message'''
        req = message.ContactAcceptMessage()
        test_id = "1234567890hijklm"
        test_msg = "He said, \"Schanke döhn\"."
        req.set_field(req.FIELD_SENDER_ID, test_id)
        req.set_field(req.FIELD_MESSAGE, test_msg)
        unenc_output = req.create_output(encrypter=None)
        # can we convert back again?
        back_again = message.Message.from_received_data(unenc_output)
        self.assertIsNotNone(back_again.original_payload, "Payload available")
        self.assertTrue(isinstance(back_again.original_payload, bytes), "Payload of correct type")
        reconstructed = message.AsymmetricMessage.from_received_payload(back_again.original_payload)
        self.assertIsNotNone(reconstructed, "Message reconstructed")
        self.assertTrue(isinstance(reconstructed, message.ContactAcceptMessage), "Correct type")
        self.assertEqual(reconstructed.msg_type, req.TYPE_CONTACT_RESPONSE, "Typenum match")
        self.assertEqual(reconstructed.body[req.FIELD_SENDER_ID], test_id, "Id match")
        self.assertEqual(reconstructed.body[req.FIELD_MESSAGE], test_msg, "Msg match")
        self.assertEqual(1, reconstructed.version_number, "Version 1")


class RelayMessageTest(unittest.TestCase):
    '''Tests for the relaying messages'''

    def test_pack_for_sending(self):
        '''Test the packing of arbitrary content inside a Relay message'''
        signed_output = "This should be a signed message".encode("utf-8")
        wrapped = message.RelayingMessage.wrap_outgoing_message(signed_output)
        self.assertTrue("murmeli".encode("utf-8") in wrapped, "Header present")
        self.assertTrue("signed message".encode("utf-8") in wrapped, "Payload present")

    def test_unpack_regular_message(self):
        '''Test that a regular message can be wrapped and unwrapped'''
        reg = message.RegularMessage()
        msg_body = "Smörgåsbord"
        reg.set_field(reg.FIELD_MSGBODY, msg_body)
        unenc_output = reg.create_output(encrypter=None)
        wrapped = message.RelayingMessage.wrap_outgoing_message(unenc_output)
        back_again = message.Message.from_received_data(wrapped)
        self.assertTrue(isinstance(back_again, message.RegularMessage), "Correct type")
        self.assertEqual(back_again.body[back_again.FIELD_MSGBODY], msg_body, "Content match")
        self.assertEqual(1, back_again.version_number, "Version 1")

    def test_unpack_unknown_message(self):
        '''Test that an unknown message can be forwarded'''
        signed_output = "This should be a signed message".encode("utf-8")
        wrapped = message.RelayingMessage.wrap_outgoing_message(signed_output)
        back_again = message.Message.from_received_data(wrapped)
        self.assertTrue(isinstance(back_again, message.RelayingMessage), "Correct type")
        forwarded_output = back_again.create_output(encrypter=None)
        self.assertEqual(signed_output, forwarded_output, "Forwarded data correct")


if __name__ == "__main__":
    unittest.main()
