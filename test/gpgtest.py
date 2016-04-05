import unittest
from config import Config
from cryptoclient import CryptoClient
import os
import shutil


class GpgTest(unittest.TestCase):
	'''Tests for the gpg decryption and encryption'''
	def setUp(self):
		Config.load()
		CryptoClient.useTestKeyring()
		self.KEYID_1 = "46944E14D24D711B"
		self.KEYID_2 = "3B898548F994C536"
		self.MESSAGE_FROM_2_FOR_1 = b'\x85\x02\x0c\x03\xc1\xa6\x10l\x12d\r9\x01\x10\x00\x95|\xd4G\x9eD\xdc\x8a xr\xd8\xf5rN\x1e\x0el14 \xfd\x85\xd5<\x18\xb0\x7f\xc4\xed}ts\x16\x83]\xe1\xbf\xab[\xf3@Vt\x85\x95\x05e\x83\x8e>S%\x1e\xd4b\xe9\x05\xcc\x85X\x9e\xd5_\x01\x81\xba\x19\x89b\x80\x03\x00\xa7jH&\xb3\xf2\r8ew\'s\x15\xb1\x1e\xd5S\x87[%L\x96V\xf5\xd5\xe84\xd8\xff\x89\x04\x17K\x99\xea1dW\x83O\xbb\x1f\xc2\x8a\x990,\xe0[\xd0\xc9\x12}\xb30)h\xf3\x85\xef\xd0(O\xe8\xf3\xefzA\xcd\x0c\xc2\xe1\x9e^\xe4\x17\x0b\x07y{h\x12\x13\x1f\'\xc5\xab\xe1\x9fZ\xed\x05\x0fu\xa4\x82\x86;\xd0xO\x8ac>.m\x97+\x88\xd5\xdeD\xf1e?T|I\x06\xa1\xef\x19AhJ\x92o\xf2\xc4Q\'.\x93v$\x19\xfe@w\xf6.8\x88\x8d|\xd2\xd9\xb4\x99d?\nC\x1f \x82\xd3\xc2K\xf4qx;\xf4(\xeb\x04\nT\x1e{$\x1c7\x1dQ!\x7fP\x96\xb5\xb3\xe9I\xf5z\xa4\n& "\xfcg3w\xdc\x07A\xf2\xb9\x92\xc1\x91\x00\x8f%\xd2G\x8c2\x96zN\xab\x8b\xed\xf2]\x80G!\xfeQ\x8f\xdc\x1baQ\xbc\xdf\x02\xec,hFa4\x9d\xe7\x85\xf6\x02z\xe6\xbc\xae\x08%\x1d\xe1\x9aQ#\x07a\x0fy\xafw\xf9e\x1e\xd0\xa9F\x14ZO\xc5\x85\x1c\xe87\x86\xe9\xb0\x1frp\x16@V\x83\xe8&\x19\x045\xc1\xb5=\xa8\xfc\xccos\x04VJ\xec[(Y\x87\xcdV:w@\xb5\x9b\x99$\x91j\x8d\xc3\xd7\x90\xec;\x9f\xe2\x85\xa6\xf0\x9es(\xe4\xfcQ\x02O\xefe\xadOZ\xec9\x85wn\xbb\xf2\xd2T\x047@\xbb\xb7\xef\xad\x8d\xfaV\xfb_\x11ui\x06\xd0\x12z\xc9\x89R6\xfdKU\x0c1\x9b\xc0{c\xf85\xe5\x05\x0b\xd0\x97v\x98)\x97Q3\xc7\x8d\x9fn:\x0bS2R\xf8`\xf1\xe9\xcf\x07\xcd\xd7\x1de\\ \xeb\xfcT\x11\xcaQk\xdd\xf1\xe1]P\xf2cM+_\xd1x\x87\xccOo\xd9\x8f\xd2\xe9\x01F\xb3\xada/\nz\xb6\x85z\xde+\xcf\xbb\r\xb0\x98\x07\xf3\x1c\x8b\xb7\x8a2\xdfu:er\xe1\xef\\\x90\x912\x9a^r*s\x808X-\xbe\x83\xcf5+\xf3\xa7r\x05\xd9\xc9\xaeB\xb3q\x93\x11\xf1\x07%\xc0\xd8\xd8\xceF\x91\xca:\\\xa5\xd3o\x9aB\xaf\x13\x9e\xd6V\xbb\xe6\xfb\x83\x84\xb7\xfc\xc6I\xacBM\xaeP\xf1r\x84\x13\x17]hS\x813\xdb\x91\'[\xfb\xfa\xeaB\xd7\x0c~o\x9f\xb5"\xa6ISN\xb5\xb4\x8e\xb9[\x9e{\xfb?\x8c\xe4\x12\x94\x1d\x87\xa0[\x86\xd6\'9T\xe3F\x13st\x8c\xa5\xac\xee`\xa2^^\xe0\x16\xc8\x05}`\xcb\x1aS~\x86\xac\xba\x15C\xba~\xbd\xde.dL^\xcd\x14\x9b\x9b\xa4\x82\xff\xb4\x1d\x8f\xa1\x1c\x0fh\'e\xb1M?V\xd3\xf0\x04\xae\xdd\xed\xa0X\xf51\xd4\xf0\xb2\xf6|\xf6\xfa\x0c\xd7\xa1\x8cPnmv\xe9\x00C\x9b\x0c\x02\xe3J\x1f\xb8w7\x8d\xf7\xfeV\xaa\x82\xb1\xbd\xf1*\xb5i_/j\xf3\xe7|\xe1\x1d\x10s\xf1\x87\x05\xa9Nn,\xd1\xabXG\xbe\x13hq\x0blJ\xb0\xcc<\x888a;\xfe}r\xe2Q48\x9c\'\x15\xe0\x17\xe2\xcd$ua\xdf\x0e\xf5\xdc\xe6\xad\x05\xf04BB\xfd\xe3\xf0\x95~c\xe0\xcb\x9f\x04B4\xd8\xca}\x80p_\x96\x81c\xbe\x83\xb7v\x13$!\xd9\xd4\x0en\x8f\x01e\xd4\xde\x07\x9e\x13\x10\x9aRQ\x83\x0b\xa2L\x971$\xb4\x15\xed\xd4[\x1e];\x93\xd9\x08a`\xfc\t2\xe9#\xed\x80\x8dz\xfb\x85\xec\x93\x98\x03\x7fo\r\xc0\xe6+\xc6\x8b\xa3*|\xf16\xca\xd0tG\x16\xc2\xccs\x97g\xb4C\xc0\xf6\xe6\xa26\xb4~f\xf4\'\x96\xae\xc80{<\xdf\x8c\xe1Y} \xe2\xc5v\x18v\xf1"S\xfeg\xd5\x0ebA\x08\t~; \xf9\x1c\x84!\x86\xc9\xe2\x19?E\xb6\x08\x92\xe2f\x88?t\x96\xe6\x98:\xf3\xb5\x16}zNp(\xbc`\xef.71\x85g\t3i2\xe7o\xc7\r\x19AW\xe6\xb9\xdf\xa9\x1f\xc2\xc28V\xf5\x1b\xc1n\xbf\x8a\x07ab\xdb\x16 r\xc3\xd2\x1f\xc1\xd0\x81p\xb7\xe2\xa7\x84/\x9f\xb7e\xffB\xd6^F\x96j\xff\x14eF\xdci\\dX\x9a\xd6\xf43]\xc3\xfbf\x11^\xd5\xbe^\xb3B~\xc7\x8c\x1bTF\xdey\x8b\x1dq6\xf0\xb0\xc4\x89i\xc4w\xc0\xcc\x13\xeal>\xa8"v\xf3\xe6\x01\x1b\x02z|\x9a\xa7\x03\x0c\xf8~\t\x02\xbe\x0c\xa4\x06\x109"\xa5\xef\xb9(\xbcT\xffe{\r\x9f\xb7e\xbfM\xfe@\xc8\x8f\xd8T\xf4\xc9\xd0\xabF7\x8d\xa2\x8fw\x87m\xd8\x11\xc4\x04/j\x89\xe9g\x7f&jB_\x82\xd9\x07!\x1f:I2\xd3UT.\xfek\x0b\x9f\xb2,\xf4\x845I'

	def testEncryption(self):
		self._setupKeyring(["key1_private", "key1_public"])
		MESSAGE = "This is the unencrypted source text we're going to use".encode("utf-8")
		RECPTKEYID = self.KEYID_1
		# encrypt for ourselves
		ans = CryptoClient.encryptAndSign(MESSAGE, RECPTKEYID, RECPTKEYID)
		self.assertIsNotNone(ans, "Encrypted result shouldn't be none")
		self.assertNotEqual(len(ans), 0, "Encrypted result shouldn't have zero length")
		self.assertNotEqual(ans, MESSAGE, "Encrypted result shouldn't be the same as the input")

	def testEncDecryption(self):
		self._setupKeyring(["key1_private", "key1_public"])
		MESSAGE = "This is the unencrypted source text we're going to use".encode("utf-8")
		RECPTKEYID = self.KEYID_1
		# encrypt for ourselves
		ans = CryptoClient.encryptAndSign(MESSAGE, RECPTKEYID, RECPTKEYID)
		self.assertIsNotNone(ans, "Encrypted result shouldn't be none")
		backAgain, sigok = CryptoClient.decryptAndCheckSignature(ans)
		self.assertIsNotNone(backAgain, "Decrypted result shouldn't be none")
		self.assertTrue(sigok, "Signature check should be ok")
		self.assertNotEqual(len(backAgain), 0, "Decrypted result shouldn't have zero length")
		self.assertNotEqual(ans, MESSAGE, "Encrypted result shouldn't be the same as the input")
		self.assertEqual(backAgain, MESSAGE, "Decrypted result should be the same as the input")

	def testDecryptPlaintext(self):
		self._setupKeyring(["key1_private", "key1_public"])
		MESSAGE = "This is the unencrypted source text we're going to use".encode("utf-8")
		backAgain, sigok = CryptoClient.decryptAndCheckSignature(MESSAGE)
		self.assertIsNone(backAgain, "Decryption of plaintext should give none")
		self.assertFalse(sigok, "Signature check should give false")

	def testDecryptNone(self):
		self._setupKeyring(["key1_private", "key1_public"])
		backAgain, sigok = CryptoClient.decryptAndCheckSignature(None)
		self.assertIsNone(backAgain, "Decryption of None should give none")
		self.assertFalse(sigok, "Signature check should give false")

	def testDecryptBlank(self):
		self._setupKeyring(["key1_private", "key1_public"])
		backAgain, sigok = CryptoClient.decryptAndCheckSignature("")
		self.assertIsNone(backAgain, "Decryption of empty string should give none")
		self.assertFalse(sigok, "Signature check should give false")

	def testDecryptNotForMe(self):
		self._setupKeyring(["key1_public", "key2_private"])
		ENCRYPTED_MESSAGE = self.MESSAGE_FROM_2_FOR_1
		backAgain, sigok = CryptoClient.decryptAndCheckSignature(ENCRYPTED_MESSAGE)
		self.assertIsNone(backAgain, "Failed decryption should give none")
		self.assertFalse(sigok, "Signature check should give false")

	def testDecryptUnrecognisedSig(self):
		self._setupKeyring(["key1_private"])
		ENCRYPTED_MESSAGE = self.MESSAGE_FROM_2_FOR_1
		backAgain, sigok = CryptoClient.decryptAndCheckSignature(ENCRYPTED_MESSAGE)
		self.assertIsNotNone(backAgain, "Decryption of encrypted text with unrecognised signature should still give a result")
		self.assertFalse(sigok, "Signature check should give false")

	def testDecryptValid(self):
		self._setupKeyring(["key1_private", "key2_public"])
		ENCRYPTED_MESSAGE = self.MESSAGE_FROM_2_FOR_1
		backAgain, sigok = CryptoClient.decryptAndCheckSignature(ENCRYPTED_MESSAGE)
		self.assertIsNotNone(backAgain, "Decryption of valid data shouldn't give none")
		self.assertTrue(sigok, "Signature check should be ok")

	def testJustSignature(self):
		'''Test the verification of data which has been signed but not encrypted'''
		self._setupKeyring(["key1_private"])
		junk = bytearray()
		junk.append(3)
		junk.append(0)
		junk.append(9)
		MESSAGE = "This is the unencrypted source text we're going to use".encode("utf-8") + bytes(junk)
		OWNKEYID = self.KEYID_1
		self.assertFalse("BEGIN PGP SIGNED MESSAGE".encode("utf-8") in MESSAGE, "Input data shouldn't include PGP prefix")
		signed = CryptoClient.signData(MESSAGE, OWNKEYID)
		self.assertTrue(signed, "Signed data shouldn't be blank")
		self.assertTrue("BEGIN PGP SIGNED MESSAGE".encode("utf-8") in signed, "Signed data should include PGP prefix")
		retrieved, keyid = CryptoClient.verifySignedData(signed)
		self.assertEqual(MESSAGE, retrieved, "Retrieved data should be the same as the input")
		self.assertIsNotNone(keyid, "keyid which signed should not be blank")

	def testClearKeyring(self):
		'''Test removing keyring and adding keys to it'''
		keyringPath = CryptoClient._getKeyringPath()
		# Delete the entire keyring
		shutil.rmtree(keyringPath, ignore_errors=True)
		os.makedirs(keyringPath)
		self.assertEqual(len(CryptoClient.getPrivateKeys()), 0, "Keyring should be empty")
		# Add a public key from file
		self.assertIsNotNone(self._importKeyFromFile("key1_public"), "Import of public key should work")
		self.assertEqual(len(CryptoClient.getPrivateKeys()), 0, "Keyring shouldn't have private keys")
		self.assertEqual(len(CryptoClient.getPublicKeys()), 1, "Keyring should have one public key")
		# Now add the corresponding private key
		ownKeyId = self._importKeyFromFile("key1_private")
		self.assertIsNotNone(ownKeyId, "Import of private key should work")
		self.assertEqual(len(CryptoClient.getPrivateKeys()), 1, "Keyring should have one private key")
		self.assertEqual(len(CryptoClient.getPublicKeys()), 1, "Keyring should have one public key")

	def _importKeyFromFile(self, filename):
		'''Load the specified file and import the contents to the current keyring.
		   This works for text files containing either a public key or a private key.'''
		key = ""
		with open(os.path.join("inputdata", filename + ".txt"), "r") as f:
			for l in f:
				key += l
		return CryptoClient.importPublicKey(key)

	def testEncryptFromKey2(self):
		self._setupKeyring(["key1_public", "key2_private"])
		MESSAGE = "The little dog laughed to see such fun, and the dish ran away with the spoon.".encode("utf-8")
		# encrypt for public key 1 using private key 2
		ans = CryptoClient.encryptAndSign(MESSAGE, self.KEYID_1, self.KEYID_2)
		self.assertIsNotNone(ans, "Encrypted result shouldn't be none")
		self.assertNotEqual(len(ans), 0, "Encrypted result shouldn't have zero length")
		self.assertNotEqual(ans, MESSAGE, "Encrypted result shouldn't be the same as the input")
		print("Encrypted from 2:", ans)

	def _setupKeyring(self, keyNames):
		'''Set up the keyring using the specified public and private key names'''
		keyringPath = CryptoClient._getKeyringPath()
		# Delete the entire keyring
		shutil.rmtree(keyringPath, ignore_errors=True)
		os.makedirs(keyringPath)
		if keyNames:
			for k in keyNames:
				keyId = self._importKeyFromFile(k)
				print("key id for", k, "=", keyId)


if __name__ == "__main__":
	unittest.main()
