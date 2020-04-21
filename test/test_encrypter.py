# coding=utf-8
'''Module for testing a trivial encrypter together with various messages'''

import unittest
from murmeli import message

class TrivialEncrypter:
    '''Don't need a sophisticated encryption mechanism here, just enough
       to prove that encryption and decryption methods have been called
       at the right times'''
    secret_xor_key = 50  # used for encryption and decryption

    def encrypt(self, unenc, enc_type):
        '''Encrypt the given message'''
        if enc_type == message.Message.ENCTYPE_NONE:
            return unenc
        elif enc_type == message.Message.ENCTYPE_ASYM:
            return bytes([char ^ TrivialEncrypter.secret_xor_key for char in unenc])
        return None

    def decrypt(self, enc_data, enc_type):
        '''Decrypt the given encrypted data'''
        return (self.encrypt(enc_data, enc_type), None)


class EncryptedMessageTest(unittest.TestCase):
    '''Tests for the encryption and decryption of messages.
       This doesn't use real encryption, just demonstrating
       the use of _any_ encrypter'''

    def test_unencrypted_message(self):
        '''Even with an encrypter specified, unencrypted messages should still be unencrypted'''
        encrypter = TrivialEncrypter()
        test_id = "sixteen_chars_id"
        test_name = "Dangermouse"
        test_msg = "The Finnish word for \"Good day\" is: 'Päivää'"
        test_key = "irrelevant-=-key"
        req = message.ContactRequestMessage()
        req.set_field(req.FIELD_SENDER_ID, test_id)
        req.set_field(req.FIELD_SENDER_NAME, test_name)
        req.set_field(req.FIELD_MESSAGE, test_msg)
        req.set_field(req.FIELD_SENDER_KEY, test_key)

        output_noenc = req.create_output(encrypter=None)
        output_withenc = req.create_output(encrypter=encrypter)
        self.assertEqual(output_noenc, output_withenc, "No encryption")
        self.assertTrue("Finnish word".encode("utf-8") in output_withenc, "Not encrypted")
        # Note that the quotes can be escaped differently so test_msg may not be in output_withenc
        # even if the strings are equivalent
        # can we convert back again?
        back_again = message.Message.from_received_data(output_withenc, decrypter=encrypter)
        self.assertTrue(isinstance(back_again, message.ContactRequestMessage), "Correct type")
        self.assertEqual(back_again.msg_type, req.TYPE_CONTACT_REQUEST, "Typenum match")
        self.assertEqual(back_again.body[req.FIELD_SENDER_NAME], test_name, "Name match")
        self.assertEqual(back_again.body[req.FIELD_SENDER_ID], test_id, "Id match")
        self.assertEqual(back_again.body[req.FIELD_MESSAGE], test_msg, "Msg match")
        self.assertEqual(back_again.body[req.FIELD_SENDER_KEY], test_key, "Key match")
        self.assertEqual(1, back_again.version_number, "Version 1")

    def test_regular_message(self):
        '''Test the regular message using trivial encryption'''
        encrypter = TrivialEncrypter()
        reg = message.RegularMessage()
        msg_body = "Jumping jellybabies"
        reg.set_field(reg.FIELD_MSGBODY, msg_body)
        unenc_output = reg.create_output(encrypter=None)
        # Unencrypted output should include msg_body
        self.assertTrue(msg_body.encode("utf-8") in unenc_output, "Unenc matches")
        enc_output = reg.create_output(encrypter=encrypter)
        self.assertFalse(msg_body.encode("utf-8") in enc_output, "Enc shouldn't match")
        back_again = message.Message.from_received_data(unenc_output, decrypter=encrypter)
        self.assertIsNone(back_again, "Decryption should fail")
        back_again = message.Message.from_received_data(enc_output, decrypter=encrypter)
        self.assertIsNotNone(back_again, "Decryption should succeed")
        self.assertTrue(isinstance(back_again, message.RegularMessage), "Correct type")
        self.assertEqual(back_again.body[back_again.FIELD_MSGBODY], msg_body, "Content match")
        self.assertEqual(1, back_again.version_number, "Version 1")


class ConditionalEncrypter(TrivialEncrypter):
    '''Encrypter / decrypter which conditionally returns a signature id'''
    key_present = False
    returned_keyid = "some_key"

    def decrypt(self, enc_data, enc_type):
        '''Decrypt the given encrypted data'''
        key_id = self.returned_keyid if self.key_present else None
        return (self.encrypt(enc_data, enc_type), key_id)


class EncryptedPayloadTest(unittest.TestCase):
    '''Tests for the decryption of encrypted payloads.'''

    def test_accept_message(self):
        '''Test the contact accept message payload retrieval'''
        encrypter = ConditionalEncrypter()
        req = message.ContactAcceptMessage()
        test_id = "1234567890hijklm"
        test_msg = "Nadolig llawen i bawb!"
        req.set_field(req.FIELD_SENDER_ID, test_id)
        req.set_field(req.FIELD_MESSAGE, test_msg)
        enc_output = req.create_output(encrypter=encrypter)
        # can we convert back again?
        back_again = message.Message.from_received_data(enc_output, decrypter=encrypter)
        self.assertIsNotNone(back_again, "Message built")
        self.assertTrue(isinstance(back_again, message.ContactAcceptMessage), "Correct type")
        self.assertIsNone(back_again.get_field(req.FIELD_SIGNATURE_KEYID), "Sig id absent")


if __name__ == "__main__":
    unittest.main()
