''''Testing of the cryptoutils'''

import unittest
import os.path
from murmeli import cryptoutils


class MockCrypto:
    '''Pretend to be a CryptoClient object'''
    @staticmethod
    def get_public_key(key_id):
        '''Return a fake key string'''
        return "PublicKey(%s)" % key_id


class ExportTest(unittest.TestCase):
    '''Tests for the export of a public key'''

    def test_noparams_fails(self):
        '''Test that trying to export without all the parameters fails'''
        self.assertFalse(cryptoutils.export_public_key(None, "output_data", "crypto"))
        self.assertFalse(cryptoutils.export_public_key("ABC123", "output_data", None))
        self.assertFalse(cryptoutils.export_public_key("ABC456", "", "crypto"))

    def test_export_succeeds(self):
        '''Test that a file is written if all the params are given'''
        crypto = MockCrypto()
        out_path = os.path.join("test", "outputdata")
        key_id = "EXAMPLEID"
        expected_file = os.path.join(out_path, key_id + ".key")
        if os.path.exists(expected_file):
            os.remove(expected_file)
        self.assertFalse(os.path.exists(expected_file))
        # export key, should create file
        self.assertTrue(cryptoutils.export_public_key(key_id, out_path, crypto))
        self.assertTrue(os.path.exists(expected_file))


if __name__ == "__main__":
    unittest.main()
