'''DbUtils for JSON conversion for Murmeli'''

from bson import json_util
from dbclient import DbClient

def getOwnProfileAsString():
	'''Return a string as a serialized representation of our own profile'''
	myProfile = DbClient.getProfile()
	fieldsToCopy = {}
	if myProfile:
		for k in myProfile.keys():
			if k not in ["status", "displayName", "ownprofile", "torid", "_id", "keyid", "profilepicpath"]:
				fieldsToCopy[k] = myProfile[k]
	return json_util.dumps(fieldsToCopy)

def convertStringToDictionary(profileString):
	'''Converts a profile string from an incoming message to a dictionary for update'''
	return json_util.loads(profileString)
