from dbinterface import DbI
from cryptoclient import CryptoClient
from supersimpledb import MurmeliDb
import os
import shutil

class TestUtils:
	'''Provide setup functions required by multiple unit tests'''

	_ownTorId = "kb83g5njhjutq7ft"

	@staticmethod
	def _importKeyFromFile(filename):
		'''Load the specified file and import the contents to the current keyring.
		   This works for text files containing either a public key or a private key.'''
		key = ""
		with open(os.path.join("inputdata", filename + ".txt"), "r") as f:
			for l in f:
				key += l
		return CryptoClient.importPublicKey(key)

	@staticmethod
	def setupKeyring(keyNames):
		'''Set up the keyring using the specified public and private key names'''
		keyringPath = CryptoClient._getKeyringPath()
		# Delete the entire keyring
		shutil.rmtree(keyringPath, ignore_errors=True)
		os.makedirs(keyringPath)
		if keyNames:
			for k in keyNames:
				keyId = TestUtils._importKeyFromFile(k)
				print("key id for", k, "=", keyId)

	@staticmethod
	def setupOwnProfile(keyId):
		tempDb = MurmeliDb()
		DbI.setDb(tempDb)
		DbI.updateProfile(TestUtils._ownTorId, {"status":"self", "ownprofile":True,
			"keyid":keyId, "name":"Geoffrey Lancaster", "displayName":"Me",
			"description":"Ä fictitious person with a couple of Umläute in his description."})
