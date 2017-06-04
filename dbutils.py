'''DbUtils for JSON conversion for Murmeli'''

from bson import json_util
import hashlib # for calculating checksums


def getProfileAsString(profile):
	'''Return a string as a serialized representation of the given profile'''
	fieldsToCopy = {}
	if profile:
		for k in profile.keys():
			if k not in ["status", "displayName", "ownprofile", "torid", "_id", "keyid", "profilepicpath"]:
				fieldsToCopy[k] = profile[k]
	return json_util.dumps(fieldsToCopy)

def convertStringToDictionary(profileString):
	'''Converts a profile string from an incoming message to a dictionary for update'''
	return json_util.loads(profileString)

def calculateHash(dbRow):
	'''Return a hexadecimal string identifying the state of the database row, for comparison'''
	h = hashlib.md5()
	usedFields = set()
	ignoredFields = set()
	if dbRow:
		for k in sorted(dbRow.keys()):
			if isinstance(dbRow[k], str): # ignore object ids and boolean flags
				val = k + ":" + dbRow[k]
				h.update(val.encode('utf-8'))
				usedFields.add(k)
			else:
				ignoredFields.add(k)
	return h.hexdigest()
