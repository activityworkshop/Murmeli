import unittest
from config import Config
from cryptoclient import CryptoClient
from fingerprints import FingerprintChecker
from testutils import TestUtils


class FingerprintTest(unittest.TestCase):
	'''Tests for the key fingerprints'''
	def setUp(self):
		Config.load()
		CryptoClient.useTestKeyring()
		TestUtils.setupKeyring(["key1_private", "key1_public", "key2_public"])
		self.KEYID_1 = "46944E14D24D711B"
		self.KEYID_2 = "3B898548F994C536"

	def testFingerprints12(self):
		'''Test the fingerprints of our loaded keys 1 and 2 together'''
		ourFingerprint = CryptoClient.getFingerprint(self.KEYID_1)
		self.assertIsNotNone(ourFingerprint, "Our fingerprint shouldn't be blank")
		theirFingerprint = CryptoClient.getFingerprint(self.KEYID_2)
		self.assertIsNotNone(theirFingerprint, "Their fingerprint shouldn't be blank")
		self.assertNotEqual(ourFingerprint, theirFingerprint, "Fingerprints shouldn't be equal")
		print(ourFingerprint, theirFingerprint)
		# Generate our set of words
		checker = FingerprintChecker(ourFingerprint, theirFingerprint)
		self.assertEqual(checker.getCorrectAnswer(), 0, "Correct answer should be 0")
		myWords = checker.getCodeWords(True, 0, "en")
		self.assertEqual(myWords, "connection microscope secrecy power dragon")
		myWordsGerman = checker.getCodeWords(True, 0, "de")
		self.assertEqual(myWordsGerman, "Nachbarn Navigation Fußball Tintenfisch abwaschen")
		theirWords0 = checker.getCodeWords(False, 0, "en")
		theirWords1 = checker.getCodeWords(False, 1, "en")
		theirWords2 = checker.getCodeWords(False, 2, "en")
		self.assertNotEqual(theirWords0, theirWords1, "Generated words 0 shouldn't equal 1")
		self.assertNotEqual(theirWords0, theirWords2, "Generated words 0 shouldn't equal 2")
		self.assertNotEqual(theirWords1, theirWords2, "Generated words 1 shouldn't equal 2")
		# Now again but from their side
		checker = FingerprintChecker(theirFingerprint, ourFingerprint)
		self.assertEqual(checker.getCorrectAnswer(), 0, "Correct answer should be 0")
		theirCorrectWords = checker.getCodeWords(True, 0, "en")
		self.assertEqual(theirWords0, theirCorrectWords, "Their words should match what we calculate")
		myWords0 = checker.getCodeWords(False, 0, "en")
		myWords1 = checker.getCodeWords(False, 1, "en")
		myWords2 = checker.getCodeWords(False, 2, "en")
		self.assertNotEqual(myWords0, myWords1, "Generated words 0 shouldn't equal 1")
		self.assertNotEqual(myWords0, myWords2, "Generated words 0 shouldn't equal 2")
		self.assertNotEqual(myWords1, myWords2, "Generated words 1 shouldn't equal 2")
		self.assertEqual(myWords0, myWords, "My words should match what they calculate")

	def testRawFingerprints(self):
		'''Check all combinations of the following three fingerprints for their correct answer'''
		finger1 = "776034AEB5AD7A6FF668E2DD0C2C0FC8ED5118F6"
		finger2 = "4DA0047805B862B90467AD2B886A6C843297E297"
		finger3 = "3170224BCD5760F16C3A64F2CED5C733012854DB"
		self._testFingerPair(finger1, finger2, 0)
		self._testFingerPair(finger1, finger3, 2)
		self._testFingerPair(finger2, finger3, 0)
		self._testFingerPair(finger2, finger1, 1)
		self._testFingerPair(finger3, finger1, 1)
		self._testFingerPair(finger3, finger2, 0)

	def _testFingerPair(self, finger1, finger2, expectedAnswer):
		'''Internal helper method to check the correct answer for the given print pair'''
		checker = FingerprintChecker(finger1, finger2)
		self.assertEqual(checker.getCorrectAnswer(), expectedAnswer, "Expected answer didn't match")
		# Use the other person's checker to get their word sequence
		otherChecker = FingerprintChecker(finger2, finger1)
		words1 = otherChecker.getCodeWords(True, 0, "en")
		words2 = checker.getCodeWords(False, expectedAnswer, "en")
		# Check that our calculated answer is the same as theirs
		self.assertEqual(words1, words2, "word sequences don't match")

if __name__ == "__main__":
	unittest.main()
