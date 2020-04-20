import unittest
import imageutils


class ImageUtilsTest(unittest.TestCase):
	'''Tests for the image utils'''

	def testBytesToString(self):
		'''Testing the conversion from bytes to strings'''
		b1 = bytearray("abc1 88ABC_ä", "utf8")
		s1 = imageutils.bytesToString(b1)
		self.assertEqual(s1, "616263312038384142435fc3a4", "String 1 should match")

		b2 = bytearray()
		b2.append(0)
		b2.append(1)
		b2.append(2)
		b2.append(13)
		s2 = imageutils.bytesToString(b2)
		self.assertEqual(s2, "0001020d", "String 2 should match")

	def testStringToBytes(self):
		'''Testing the conversion from strings back to bytes'''
		s1 = ""
		b1 = imageutils.stringToBytes(s1)
		self.assertEqual(len(b1), 0, "Empty string -> empty array")

		s2 = "24"
		b2 = imageutils.stringToBytes(s2)
		self.assertIsNotNone(b2, "24 -> byte array")
		self.assertEqual(len(b2), 1, "24 -> byte array of length 1")
		self.assertEqual(b2[0], 36, "24 -> first element value 36")

		with self.assertRaises(IndexError):
			b3 = imageutils.stringToBytes("248")
			self.assertIsNone(b3, "odd number of chars -> None")
		with self.assertRaises(ValueError):
			b4 = imageutils.stringToBytes("f04g")
			self.assertIsNone(b4, "wrong chars -> None")
		with self.assertRaises(ValueError):
			b5 = imageutils.stringToBytes("00CD")
			self.assertIsNone(b5, "wrong chars -> None")

	def testBytesToStringToBytes(self):
		'''Testing the conversion from strings back to bytes'''
		b1 = bytearray([81, 119, 200, 3, 0, 9, 0, 55])
		s1 = imageutils.bytesToString(b1)
		self.assertEqual(s1, "5177c80300090037", "string should match the expected one")
		b2 = imageutils.stringToBytes(s1)
		self.assertEqual(b1, b2, "byte array should be the same after conversion to string and back")


if __name__ == "__main__":
	unittest.main()
