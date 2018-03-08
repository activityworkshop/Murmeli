''''Testing of the basic cryptography functions of the CryptoClient'''

import unittest
import os
import shutil
from murmeli.cryptoclient import CryptoClient


class CryptoTest(unittest.TestCase):
    '''Tests for the decryption and encryption of CryptoClient'''
    def setUp(self):
        self.keyid_1 = "46944E14D24D711B"
        self.keyid_2 = "3B898548F994C536"

    def test_init(self):
        '''Just check that crypto client can be initialised and is ready'''
        crypto = self._setup_keyring("keyringtest", ["key1_private", "key1_public"])
        self.assertTrue(crypto and crypto.check_gpg(), "Crypto ready")
        self.assertEqual(crypto.get_num_keys(public_keys=True), 1, "1 public key loaded")
        self.assertEqual(crypto.get_num_keys(private_keys=True), 1, "1 private key loaded")
        self.assertTrue(crypto.get_fingerprint(self.keyid_1).startswith("C7091CE836"),
                        "fingerprint as expected")


    def _setup_keyring(self, keyring_name, key_names=None):
        '''Set up the keyring using the specified public and private key names'''
        keyring_path = os.path.join("test", "outputdata", keyring_name)
        # Delete the entire keyring
        shutil.rmtree(keyring_path, ignore_errors=True)
        os.makedirs(keyring_path)
        crypto = CryptoClient(None, keyring_path)
        if key_names:
            for key in key_names:
                key_id = self._import_key_from_file(crypto, key)
                print("key id for", key, "=", key_id)
        return crypto

    @staticmethod
    def _import_key_from_file(crypto, filename):
        '''Load the specified file and import the contents to the current keyring.
           This works for text files containing either a public key or a private key.'''
        key = ""
        with open(os.path.join("test", "inputdata", filename + ".txt"), "r") as keyfile:
            for line in keyfile:
                key += line
        return crypto.import_public_key(key)

    def test_encryption(self):
        '''Test that encryption of a simple string produces a different output'''
        crypto = self._setup_keyring("keyringtest", ["key1_private", "key1_public"])
        message = "This is the unencrypted source text we're going to use".encode("utf-8")
        recpt_keyid = self.keyid_1
        # encrypt for ourselves
        cipher_text = crypto.encrypt_and_sign(message, recpt_keyid, recpt_keyid)
        self.assertIsNotNone(cipher_text, "Encrypted result shouldn't be none")
        self.assertNotEqual(len(cipher_text), 0, "Encrypted result shouldn't have zero length")
        self.assertNotEqual(cipher_text, message, "Encrypted result not the same as the input")

    def test_enc_and_decryption(self):
        '''Test that encrypted contents can be decrypted again with the right key'''
        crypto = self._setup_keyring("keyringtest", ["key1_private", "key1_public"])
        message = "This is the unencrypted source text we're going to use".encode("utf-8")
        recpt_keyid = self.keyid_1
        # encrypt for ourselves
        cipher_text = crypto.encrypt_and_sign(message, recpt_keyid, recpt_keyid)
        self.assertIsNotNone(cipher_text, "Encrypted result shouldn't be none")
        back_again, sigok = crypto.decrypt_and_check_signature(cipher_text)
        self.assertIsNotNone(back_again, "Decrypted result shouldn't be none")
        self.assertTrue(sigok, "Signature check should be ok")
        self.assertNotEqual(len(back_again), 0, "Decrypted result shouldn't have zero length")
        self.assertNotEqual(cipher_text, message, "Encrypted result not the same as the input")
        self.assertEqual(back_again, message, "Decrypted result should be the same as the input")

    def test_decrypt_plaintext(self):
        '''Decryption of plain text should fail'''
        crypto = self._setup_keyring("keyringtest", ["key1_private", "key1_public"])
        message = "This is the unencrypted source text we're going to use".encode("utf-8")
        plain_text, sigok = crypto.decrypt_and_check_signature(message)
        self.assertIsNone(plain_text, "Decryption of plaintext should give none")
        self.assertFalse(sigok, "Signature check should give false")

    def test_decrypt_none(self):
        '''Decryption of None should give None'''
        crypto = self._setup_keyring("keyringtest", ["key1_private", "key1_public"])
        result, sigok = crypto.decrypt_and_check_signature(None)
        self.assertIsNone(result, "Decryption of None should give none")
        self.assertFalse(sigok, "Signature check should give false")

    def test_decrypt_blank(self):
        '''Decryption of an empty string should give None'''
        crypto = self._setup_keyring("keyringtest", ["key1_private", "key1_public"])
        plain_text, sigok = crypto.decrypt_and_check_signature("")
        self.assertIsNone(plain_text, "Decryption of empty string should give none")
        self.assertFalse(sigok, "Signature check should give false")

    def test_decrypt_not_for_me(self):
        '''Decryption of a message which is not for me should give None'''
        crypto = self._setup_keyring("keyringtest", ["key1_public", "key2_private"])
        with open("test/inputdata/message_from2_for1.data", "rb") as msg_file:
            encrypted_message = msg_file.read()
        plain_text, sigok = crypto.decrypt_and_check_signature(encrypted_message)
        self.assertIsNone(plain_text, "Failed decryption should give none")
        self.assertFalse(sigok, "Signature check should give false")

    def test_decrypt_unrecognised_sig(self):
        '''Decryption of an encrypted message without recognised signature'''
        crypto = self._setup_keyring("keyringtest", ["key1_private"])
        with open("test/inputdata/message_from2_for1.data", "rb") as msg_file:
            encrypted_message = msg_file.read()
        plain_text, sigok = crypto.decrypt_and_check_signature(encrypted_message)
        self.assertIsNotNone(plain_text, "Decryption with unrecognised signature "
                             "should still give a result")
        self.assertFalse(sigok, "Signature check should give false")

    def test_decrypt_valid(self):
        '''Decryption of an encrypted message with recognised signature'''
        crypto = self._setup_keyring("keyringtest", ["key1_private", "key2_public"])
        with open("test/inputdata/message_from2_for1.data", "rb") as msg_file:
            encrypted_message = msg_file.read()
        plain_text, sigok = crypto.decrypt_and_check_signature(encrypted_message)
        self.assertIsNotNone(plain_text, "Decryption of valid data shouldn't give none")
        self.assertTrue(sigok, "Signature check should be ok")

    def test_just_signature(self):
        '''Test the verification of data which has been signed but not encrypted'''
        crypto = self._setup_keyring("keyringtest", ["key1_private"])
        junk = bytes([3, 0, 9])
        message = "This is the unencrypted source text we're going to use".encode("utf-8") + junk
        own_keyid = self.keyid_1
        self.assertFalse("BEGIN PGP SIGNED MESSAGE".encode("utf-8") in message,
                         "Input data shouldn't include PGP prefix")
        signed = crypto.sign_data(message, own_keyid)
        self.assertTrue(signed, "Signed data shouldn't be blank")
        self.assertTrue("BEGIN PGP SIGNED MESSAGE".encode("utf-8") in signed,
                        "Signed data should include PGP prefix")
        retrieved, keyid = crypto.verify_signed_data(signed)
        self.assertEqual(message, retrieved, "Retrieved data should be the same as the input")
        self.assertIsNotNone(keyid, "keyid which signed should not be blank")

    def test_clear_keyring(self):
        '''Test removing keyring and adding keys to it'''
        keyring_path = "keyringtest"
        # Delete the entire keyring
        shutil.rmtree(keyring_path, ignore_errors=True)
        crypto = self._setup_keyring("keyringtest")
        self.assertEqual(crypto.get_num_keys(private_keys=True), 0, "Keyring should be empty")
        self.assertEqual(crypto.get_num_keys(public_keys=True), 0, "should have 0 public keys")
        # Add a public key from file
        self.assertIsNotNone(self._import_key_from_file(crypto, "key1_public"),
                             "Import of public key works")
        self.assertEqual(crypto.get_num_keys(private_keys=True), 0, "Keyring has no private keys")
        self.assertEqual(crypto.get_num_keys(public_keys=True), 1, "should have 1 public key")
        # Now add the corresponding private key
        own_keyid = self._import_key_from_file(crypto, "key1_private")
        self.assertIsNotNone(own_keyid, "Import of private key should work")
        self.assertEqual(crypto.get_num_keys(private_keys=True), 1, "should have 1 private key")
        self.assertEqual(crypto.get_num_keys(public_keys=True), 1, "should have 1 public key")

    def test_encrypt_from_key2(self):
        '''Encrypt a message for key1 signing with key2'''
        crypto = self._setup_keyring("keyringtest", ["key1_public", "key2_private"])
        message = "The little dog laughed to see such fün, " \
                  "and the dish ran away with the spöön.".encode("utf-8")
        # encrypt for public key 1 using private key 2
        cipher_text = crypto.encrypt_and_sign(message, self.keyid_1, self.keyid_2)
        self.assertIsNotNone(cipher_text, "Encrypted result shouldn't be none")
        self.assertTrue(len(cipher_text) > 10, "Encrypted result shouldn't have zero length")
        self.assertNotEqual(cipher_text, message, "Encrypted result shouldn't be same as input")
        # print("Encrypted from 2:", cipher_text)


if __name__ == "__main__":
    unittest.main()
