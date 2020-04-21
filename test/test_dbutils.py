'''Module for testing the database utils'''

import unittest
from murmeli import dbutils


class DbUtilsTest(unittest.TestCase):
    '''Tests for the Db utils'''

    def test_dict_conversion(self):
        '''Test conversion from dict to string and back'''
        test_profile = {"first" : "Leopard", "displayName" : "Llywelyn", "third" : "Balaclava"}
        profile_as_string = dbutils.get_profile_as_string(test_profile)
        self.assertTrue("Leopard" in profile_as_string, "Has a leopard")
        self.assertFalse("Llywelyn" in profile_as_string, "No Llywelyn") # blocked field
        self.assertTrue("Balaclava" in profile_as_string, "Has a balaclava")
        # back to a dictionary
        result = dbutils.convert_string_to_dictionary(profile_as_string)
        self.assertEqual(result['first'], "Leopard", "Leopard is back")
        self.assertEqual(result['third'], "Balaclava", "Balaclava is back")
        self.assertIsNone(result.get('displayName'), "displayName is no more")

    def test_dict_reconstruction(self):
        '''Test conversion from an invalid string to a dict'''
        self.assertIsNone(dbutils.convert_string_to_dictionary(None), "create from None")
        self.assertIsNone(dbutils.convert_string_to_dictionary(""), "create from blank")
        self.assertIsNone(dbutils.convert_string_to_dictionary("wron{g"), "create from wrong")
        self.assertIsNone(dbutils.convert_string_to_dictionary("6"), "create from number")

    def test_hashes(self):
        '''Test the creation of hashes from a profile dictionary'''
        test_profile = {"first" : "pangolin", "second" : -1, "third" : "elk"}
        used_fields = {}
        result = dbutils.calculate_hash(test_profile, used_fields)
        self.assertTrue("first" in used_fields, "used first")
        self.assertFalse("second" in used_fields, "second ignored")
        self.assertTrue("third" in used_fields, "used third")
        self.assertEqual(result, "0205fc9525edeca3cf665098f68c279d", "hash as expected")
        # add a list
        test_profile['fruits'] = ["lemons", "kiwis", "dates"]
        self.assertEqual(dbutils.calculate_hash(test_profile), result, "hash still as expected")
        # add an extra string
        test_profile['veg'] = "cabbage, peas"
        self.assertNotEqual(dbutils.calculate_hash(test_profile), result, "hash changed")
        # add an empty value
        test_profile['koalas'] = None
        self.assertNotEqual(dbutils.calculate_hash(test_profile), result, "hash changed")


if __name__ == "__main__":
    unittest.main()
