#################################
## Database client for Murmeli ##
#################################

# Only classes inside this file should care about mongo database details
# (except maybe the startup wizard which can check for pymongo's availability)

import os.path
import shutil
import subprocess
import time
import pymongo
from bson import ObjectId
from bson.binary import Binary
import hashlib # for calculating checksums
from config import Config
from cryptoclient import CryptoError
from dbnotify import DbResourceNotifier, DbMessageNotifier
import imageutils

# Separate class to launch the mongod executable, and then
# shut it down properly when finished
class DaemonLauncher:
	# Constructor
	def __init__(self, exepath, dbpath):
		self.exepath = exepath
		self.dbpath  = dbpath
		self.daemon  = None
	# Start subprocess
	def start(self):
		print("Starting mongod...")
		try:
			self.daemon = subprocess.Popen([self.exepath, "--dbpath", self.dbpath,
				"--bind_ip", "localhost", "--nohttpinterface", "--noscripting"])
			print("started db daemon!")
		except: pass # if it fails, it fails

	# called if the DbClient wants to stop mongod
	def terminate(self):
		if self.daemon:
			self.daemon.terminate()
			print("called terminate on the db daemon")


class DbClient:
	'''The DbClient is the only class you need to reference when accessing the database.'''

	# static variable to hold separate launcher object
	_daemonLauncher = None
	# own torid
	_torId = None
	# set to true to use alternative db tables for testing
	_useTestTables = False


	@staticmethod
	def startDatabase():
		# get the path to the mongo executable and the mongodb
		mongoexe = Config.getProperty(Config.KEY_MONGO_EXE)
		dbpath   = Config.getDatabaseDir()
		if mongoexe is None or dbpath is None \
		  or not os.path.exists(dbpath) \
		  or not os.path.isdir(dbpath):
			return False
		# If there's already a daemon running, kill it
		if DbClient._daemonLauncher:
			DbClient._daemonLauncher.terminate()
		# Start a new launcher to run mongod
		DbClient._daemonLauncher = DaemonLauncher(mongoexe, dbpath)
		DbClient._daemonLauncher.start()
		# Wait a couple of seconds and then see if we can access it
		time.sleep(2)
		return DbClient.isDatabaseRunning()

	@staticmethod
	def isDatabaseRunning():
		try:
			testclient = pymongo.MongoClient()
			return True if testclient else False
		except: # couldn't connect to server
			return False

	@staticmethod
	def stopDatabase():
		print("stopping database...")
		if DbClient._daemonLauncher:
			DbClient._daemonLauncher.terminate()
			DbClient._daemonLauncher = None

	@staticmethod
	def useTestTables():
		'''Only call this method from unit tests, so that different db tables are used'''
		DbClient._useTestTables = True
		DbClient._torId = None

	@staticmethod
	def _getProfileTable():
		'''Use a different profiles table for the unit tests so they're independent of the running db'''
		client = pymongo.MongoClient()
		return client.murmelidb.testprofiles if DbClient._useTestTables else client.murmelidb.profiles

	@staticmethod
	def _getInboxTable():
		'''Use a different inbox table for the unit tests so they're independent of the running db'''
		client = pymongo.MongoClient()
		return client.murmelidb.testinbox if DbClient._useTestTables else client.murmelidb.inbox

	@staticmethod
	def _getOutboxTable():
		'''Use a different outbox table for the unit tests so they're independent of the running db'''
		client = pymongo.MongoClient()
		return client.murmelidb.testoutbox if DbClient._useTestTables else client.murmelidb.outbox

	@staticmethod
	def _getAdminTable():
		'''Use a different table for the unit tests so they're independent of the running db'''
		client = pymongo.MongoClient()
		return client.murmelidb.testadmin if DbClient._useTestTables else client.murmelidb.admin

	@staticmethod
	def getProfile(userid=None, extend=True):
		if userid is None:
			profile = DbClient._getProfileTable().find_one({'ownprofile': True})
		else:
			profile = DbClient._getProfileTable().find_one({'torid': userid})
		if extend:
			profile = DbClient.completeProfile(profile)
		return profile

	@staticmethod
	def getOwnTorId():
		# TODO: Needed?  Can't we just ask the TorClient?
		if DbClient._torId is None or DbClient._torId == "":
			ownprofile = DbClient.getProfile(None, False)
			if ownprofile:
				DbClient._torId = str(ownprofile['torid'])
		return DbClient._torId

	@staticmethod
	def getOwnKeyId():
		ownprofile = DbClient.getProfile(None, False)
		return ownprofile['keyid']

	@staticmethod
	def deleteOwnProfile():
		if DbClient._useTestTables:
			DbClient._getProfileTable().remove({"status":"self"})

	# TODO: Make these non-static methods and keep a hold of a MongoClient?  But who keeps hold of the DbClient?

	@staticmethod
	def getContactList(status=None):
		# Ignore the "profilepic" field, to save data flow
		if status:
			profiles = DbClient._getProfileTable().find({"status":status}, {"profilepic":0}).sort([('ownprofile',-1), ('torid',1)])
		else:
			profiles = DbClient._getProfileTable().find({"status":{"$ne":"deleted"}}, {"profilepic":0}).sort([('ownprofile',-1), ('torid',1)])
		# This sort option insists that our own profile will be the first in the returned set
		# This isn't what's written in the guide, so may be incompatible with newer/older mongos?
		return [DbClient.completeProfile(p) for p in profiles]


	@staticmethod
	def hasFriends():
		for c in DbClient.getContactList():
			if c['status'] == "trusted" or c['status'] == "untrusted":
				return True


	@staticmethod
	def completeProfile(profile):
		if profile:
			if not profile.get("torid", None): profile['torid'] = ""
			if not profile.get("name",  None): profile['name'] = profile['torid']
			if not profile.get("displayName", None): profile['displayName'] = profile['name']
			for k in ["description", "birthday", "interests"]:
				if not profile.get(k, None): profile[k] = ""
		return profile

	@staticmethod
	def updateContact(torid, profile):
		# Also exports avatar if profile picture has changed
		profiles = DbClient._getProfileTable()
		# If the profile pic path has changed, then we need to load the file
		givenprofilepicpath = profile.get('profilepicpath', None)
		pic_changed = False
		if givenprofilepicpath and os.path.exists(givenprofilepicpath):
			# check if it's the same path as already stored
			storedProfile = profiles.find_one({'torid': torid}, {"profilepicpath":1})
			if not storedProfile or storedProfile.get('profilepicpath',"") != givenprofilepicpath:
				profile['profilepic'] = Binary(imageutils.makeThumbnailBinary(givenprofilepicpath))
				pic_changed = True
		elif profile.get('profilepic', None):
			pic_changed = True
		profiles.update({'torid':torid}, {"$set": profile}, True)
		if pic_changed:
			DbClient._updateAvatar(torid, Config.getWebCacheDir())

	@staticmethod
	def exportAvatars(outputdir):
		# Get list of friends and their torids
		profiles = DbClient._getProfileTable()
		torids = [i['torid'] for i in profiles.find({}, {"torid":1}) if i]
		# For each one, look in outputdir to see if pic is already there
		for i in torids:
			outpath = os.path.join(outputdir, "avatar-" + i + ".jpg")
			if not os.path.exists(outpath):
				# File doesn't exist, so get profilepic data
				pic = profiles.find_one({'torid': i}, {"profilepic":1}).get('profilepic', None)
				if pic:
					print("exporting avatar from db to", outpath)
					DbClient._writeBsonObjectToFile(pic, outpath)
				else:
					print("copying blank avatar to", outpath)
					shutil.copy(os.path.join(outputdir, "avatar-none.jpg"), outpath)

	@staticmethod
	def _updateAvatar(userid, outputdir):
		picname = "avatar-" + userid + ".jpg"
		outpath = os.path.join(outputdir, picname)
		try: os.remove(outpath)
		except: pass # it wasn't there anyway
		# We export pics for all the contacts but only the ones whose jpg doesn't exist already
		DbClient.exportAvatars(outputdir)
		# Inform all interested listeners that there's been some change with the given url
		DbResourceNotifier.getInstance().notify(picname)


	@staticmethod
	def _writeBsonObjectToFile(bsonfromdb, filename):
		with open(filename, 'wb') as f:
			# bsonfromdb is a bson Binary object, but it can be iterated like a bytes object and written directly
			f.write(bsonfromdb)

	@staticmethod
	def calculateHash(dbrow):
		'''Return a hexadecimal string identifying the state of the database row, for comparison'''
		h = hashlib.md5()
		usedFields = set()
		ignoredFields = set()
		for k in sorted(dbrow.keys()):
			if isinstance(dbrow[k], str): # ignore object ids and boolean flags
				val = k + ":" + dbrow[k]
				h.update(val.encode('utf-8'))
				usedFields.add(k)
			else:
				#print("Ignored", k, " because it has type", type(dbrow[k]))
				ignoredFields.add(k)
		print("For the hash, I used fields", usedFields, "and ignored", ignoredFields)
		return h.hexdigest()

	@staticmethod
	def getMessageableContacts():
		'''Get a list of contacts we can send messages to, ie trusted or untrusted'''
		return DbClient._getProfileTable().find({"status":{"$in" : ["trusted", "untrusted"]}},
			 {"torid":1, "displayName":1, "status":1, "contactlist":1}).sort([('torid',1)])

	@staticmethod
	def getTrustedContacts():
		return DbClient._getProfileTable().find({"status":"trusted"}, {"torid":1, "name":1, "contactlist":1}).sort([('torid',1)])

	@staticmethod
	def updateContactList(showList):
		'''Depending on the setting, either clears the contact list from our own profile,
		   or populates it based on the list of contacts in the database'''
		contactlist = []
		if showList:
			# loop over trusted contacts
			for p in DbClient.getTrustedContacts():
				name = p['name']
				if not name: name = p['torid']
				if name:
					contactlist.append(p['torid'] + name.replace(',', '.'))
		profile = {'contactlist' : ','.join(contactlist)}
		DbClient.updateContact(DbClient.getOwnTorId(), profile)

	@staticmethod
	def findUserIdFromKeyId(keyid):
		prof = DbClient._getProfileTable().find_one({'keyid': keyid}, {"torid":1})
		if prof:
			return prof.get('torid', None)

	@staticmethod
	def addMessageToOutbox(message):
		'''Add the given message to the outbox for sending later'''
		if message.recipients:
			for r in message.recipients:
				# TODO: Check that len(r) == 16 ?
				print("Add outgoing message for", r)
				encryptKey = None
				prof = DbClient.getProfile(userid=r)
				if prof:
					encryptKey = prof.get("keyid", None)
				else:
					print("No profile for ", r)
				try:
					# message.output is a bytes() object, so we need to convert to Binary for storage
					messageToSend = Binary(message.createOutput(encryptKey))
					DbClient._getOutboxTable().insert({"recipient" : r, "relays" : relays, "message" : messageToSend,
						 "queue" : message.shouldBeQueued, "msgType" : message.getMessageTypeKey()})
					# Inform all interested listeners that there's been a change in the messages
					DbMessageNotifier.getInstance().notify()

				except CryptoError as e:
					print("Something has thrown a CryptoError :(  can't add message to Outbox!", e)

	@staticmethod
	def getOutboxMessages():
		return DbClient._getOutboxTable().find()

	@staticmethod
	def deleteMessageFromOutbox(messageId):
		DbClient._getOutboxTable().remove({"_id":messageId})

	@staticmethod
	def addMessageToInbox(message):
		'''A message has been received, need to add this to our inbox so it can be read'''
		# Calculate hash of message's body + timestamp + sender
		thisHash = DbClient.calculateHash({"body":message['messageBody'], "timestamp":message['timestamp'], "senderId":message['fromId']})
		# Check id or hash of message to make sure we haven't got it already!
		inbox = DbClient._getInboxTable()
		if not inbox.find_one({"messageHash" : thisHash}):
			message['messageHash'] = thisHash
			# Either take its parent's conversation id, or generate a new one
			message['conversationid'] = DbClient.getConversationId(message.get("parentHash", None))
			# print("Storing message to inbox:", message)
			inbox.insert(message)
			# Inform all interested listeners that there's been a change in the messages
			DbMessageNotifier.getInstance().notify()
		else:
			print("Received a message for the inbox with hash '", thisHash, "but I've got that one already")

	@staticmethod
	def getInboxMessages():
		return DbClient._getInboxTable().find({"deleted":None}).sort("timestamp", -1)
		# TODO: Other sorting/paging options?

	@staticmethod
	def deleteMessageFromInbox(messageId):
		DbClient._getInboxTable().update({"_id":ObjectId(messageId)}, {"$set" : {"deleted":True}})

	@staticmethod
	def getConversationId(parentHash):
		if parentHash:
			inboxTable = DbClient._getInboxTable()
			# There should be only one message with thish hash (unless it's been deleted)
			for m in inboxTable.find({"messageHash" : parentHash}):
				cid = m.get("conversationid", None)
				if cid:
					return cid
		# No such parent message found, so generate a new conversation id
		return DbClient.getNewConversationId()

	@staticmethod
	def getNewConversationId():
		adminTable = DbClient._getAdminTable()
		cid = adminTable.find_and_modify(query={"_id":"conversationid"}, update={"$inc":{"value":1}}, new=True)
		if cid:
			value = cid.get("value", None)
			if value:
				return value
		# Couldn't get any value, so start from 1
		adminTable.insert({"_id":"conversationid", "value":1})
		return 1
