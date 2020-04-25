# coding=utf-8
'''Module for testing the image utils'''

import os
import unittest
from murmeli import imageutils


class ImageUtilsTest(unittest.TestCase):
    '''Tests for the image utils'''

    def test_bytes_to_string(self):
        '''Testing the conversion from bytes to strings'''
        ba1 = bytearray("abc1 88ABC_ä", "utf8")
        str1 = imageutils.bytes_to_string(ba1)
        self.assertEqual(str1, "616263312038384142435fc3a4", "String 1 should match")

        ba2 = bytearray()
        ba2.append(0)
        ba2.append(1)
        ba2.append(2)
        ba2.append(13)
        str2 = imageutils.bytes_to_string(ba2)
        self.assertEqual(str2, "0001020d", "String 2 should match")

    def test_string_to_bytes(self):
        '''Testing the conversion from strings back to bytes'''
        str1 = ""
        ba1 = imageutils.string_to_bytes(str1)
        self.assertEqual(len(ba1), 0, "Empty string -> empty array")

        str2 = "24"
        ba2 = imageutils.string_to_bytes(str2)
        self.assertIsNotNone(ba2, "24 -> byte array")
        self.assertEqual(len(ba2), 1, "24 -> byte array of length 1")
        self.assertEqual(ba2[0], 36, "24 -> first element value 36")

        with self.assertRaises(IndexError):
            ba3 = imageutils.string_to_bytes("248")
            self.assertIsNone(ba3, "odd number of chars -> None")
        with self.assertRaises(ValueError):
            ba4 = imageutils.string_to_bytes("f04g")
            self.assertIsNone(ba4, "wrong chars -> None")
        with self.assertRaises(ValueError):
            ba5 = imageutils.string_to_bytes("00CD")
            self.assertIsNone(ba5, "wrong chars -> None")

    def test_bytes_to_string_to_bytes(self):
        '''Testing the conversion from strings back to bytes'''
        ba1 = bytearray([81, 119, 200, 3, 0, 9, 0, 55])
        str1 = imageutils.bytes_to_string(ba1)
        self.assertEqual(str1, "5177c80300090037", "string should match the expected one")
        ba2 = imageutils.string_to_bytes(str1)
        self.assertEqual(ba1, ba2, "byte array should be equal after conversion to string and back")

    def test_thumbnail(self):
        '''Testing the loading of an avatar jpeg from file and making a thumbnail image'''
        input_path = os.path.join("test", "inputdata", "example-avatar.jpg")
        thumbnail_bytes = imageutils.make_thumbnail_binary(input_path)
        self.assertEqual(2325, len(thumbnail_bytes), "correct number of bytes")
        thumb_str = imageutils.bytes_to_string(thumbnail_bytes)
        self.assertEqual(4650, len(thumb_str), "correct string length")
        out_bytes = imageutils.string_to_bytes(thumb_str)
        self.assertEqual(thumbnail_bytes, out_bytes, "byte arrays equal")


if __name__ == "__main__":
    unittest.main()
