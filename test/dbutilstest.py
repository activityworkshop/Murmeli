import unittest
import dbutils


class DbUtilsTest(unittest.TestCase):
	'''Tests for the database utils'''

	def testProfileAsString(self):
		'''Test the conversion of profiles to and from strings'''
		
		# Create fake profile for some user
		profileFromDb = {"keyid":"ZYXW987", "status":"self", "name":"That's me", "description":"It's \"complicated\"!", "some_other_field":""}

		# convert to string
		profileToSend = dbutils.getProfileAsString(profileFromDb)
		self.assertTrue(type(profileToSend) == str, "Should convert to string")
		self.assertTrue(len(profileToSend) > 10)

		# convert back to dictionary for saving
		profileToSave = dbutils.convertStringToDictionary(profileToSend)
		self.assertTrue(type(profileToSave) == dict, "Should convert back to dict")
		self.assertTrue(profileToSave, "Dictionary should not be empty")

		# excluded fields should be blank
		self.assertIsNone(profileToSave.get("status", None))
		self.assertIsNone(profileToSave.get("keyid", None))

		# apart from the excluded fields (status, keyid), other values should be the same as the input
		for k in profileFromDb:
			if k != "status" and k != "keyid":
				self.assertEqual(profileFromDb[k], profileToSave.get(k, None))

if __name__ == "__main__":
	unittest.main()

