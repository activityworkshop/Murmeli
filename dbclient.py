'''Database client for Murmeli

   Only classes inside this file should care about mongo database details
   (except maybe the startup wizard which can check for pymongo's availability)'''

import os.path
import shutil
import subprocess
import time
import hashlib # for calculating checksums
from random import SystemRandom
import pymongo
from bson import ObjectId
from bson.binary import Binary
from config import Config
from cryptoclient import CryptoError
from dbnotify import DbResourceNotifier, DbMessageNotifier
import imageutils


class DaemonLauncher:
	'''Separate class to launch the mongod executable, and then
	   shut it down properly when finished.'''
	# Constructor
	def __init__(self, exepath, dbpath, useAuth=True):
		self.exepath = exepath
		self.dbpath  = dbpath
		self.useAuth = useAuth
		self.daemon  = None

	def start(self):
		'''Start subprocess'''
		print("Starting mongod...")
		try:
			self.daemon = subprocess.Popen([self.exepath, "--dbpath", self.dbpath,
				"--bind_ip", "localhost", "--nohttpinterface", "--noscripting",
				"--auth" if self.useAuth else "--noauth"])
			print("started db daemon!")
		except:
			pass # if it fails, it fails

	def terminate(self):
		'''Called if the DbClient wants to stop mongod'''
		if self.daemon:
			self.daemon.terminate()
			print("called terminate on the db daemon")


class DbClient:
	'''The DbClient is the only class you need to reference when accessing the database.'''

	# static variable to hold separate launcher object
	_daemonLauncher = None
	# own torid
	_torId = None
	# password for database
	_dbPassword = None
	# set to true to use alternative db tables for testing
	_useTestTables = False

	# Constants for running status of server
	NOT_RUNNING          = 0
	RUNNING_WITHOUT_AUTH = 1
	RUNNING_SECURE       = 2

	@staticmethod
	def startDatabase(useAuth=True):
		'''Try to start the database server either with or without authentication.
		   Return True if it started properly, otherwise False.'''
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
		DbClient._daemonLauncher = DaemonLauncher(mongoexe, dbpath, useAuth)
		DbClient._daemonLauncher.start()
		# Wait a couple of seconds and then see if we can access it
		time.sleep(2)
		DbClient._dbPassword = PasswordManager.getStoredPassword()
		dbStatus = DbClient.getDatabaseRunStatus()
		if useAuth:
			return dbStatus == DbClient.RUNNING_SECURE
		else:
			return dbStatus == DbClient.RUNNING_WITHOUT_AUTH

	@staticmethod
	def getDatabaseRunStatus():
		try:
			testclient = pymongo.MongoClient()
			# TODO: This will crash on Windows if the server is not running
			_ = testclient.murmelidb.profiles.count() if testclient else 0
			# We didn't authenticate but still got a result - must be without auth
			return DbClient.RUNNING_WITHOUT_AUTH
		except pymongo.errors.ConnectionFailure: # couldn't connect to server
			return DbClient.NOT_RUNNING
		except pymongo.errors.OperationFailure:  # connected but failed to read
			return DbClient.RUNNING_SECURE

	@staticmethod
	def stopDatabase():
		print("stopping database...")
		if DbClient._daemonLauncher:
			DbClient._daemonLauncher.terminate()
			DbClient._daemonLauncher = None

	@staticmethod
	def isPasswordAvailable():
		return PasswordManager.getStoredPassword() is not None

	@staticmethod
	def useTestTables():
		'''Only call this method from unit tests, so that different db tables are used'''
		DbClient._useTestTables = True
		DbClient._torId = None

	@staticmethod
	def setupDatabaseUsers(adminPassword, userPassword):
		'''Save the root password and the user password in the database'''
		try:
			client = pymongo.MongoClient()
			client.admin.system.users.remove()
			client.admin.add_user(name="murmeliadmin", password=adminPassword)
			client.murmelidb.system.users.remove()
			client.murmelidb.add_user(name="murmeli", password=userPassword)
		except:
			print("Failed to setup database users for authentication")

	@staticmethod
	def _getAuthenticatedClient():
		client = pymongo.MongoClient()
		if not DbClient._dbPassword:
			DbClient._dbPassword = PasswordManager.getStoredPassword()
		# TODO: What to do if authentication fails?  Catch exception?
		client.murmelidb.authenticate("murmeli", DbClient._dbPassword)
		return client

	@staticmethod
	def _getProfileTable():
		'''Use a different profiles table for the unit tests so they're independent of the running db'''
		client = DbClient._getAuthenticatedClient()
		return client.murmelidb.testprofiles if DbClient._useTestTables else client.murmelidb.profiles

	@staticmethod
	def _getInboxTable():
		'''Use a different inbox table for the unit tests so they're independent of the running db'''
		client = DbClient._getAuthenticatedClient()
		return client.murmelidb.testinbox if DbClient._useTestTables else client.murmelidb.inbox

	@staticmethod
	def _getOutboxTable():
		'''Use a different outbox table for the unit tests so they're independent of the running db'''
		client = DbClient._getAuthenticatedClient()
		return client.murmelidb.testoutbox if DbClient._useTestTables else client.murmelidb.outbox

	@staticmethod
	def _getAdminTable():
		'''Use a different table for the unit tests so they're independent of the running db'''
		client = DbClient._getAuthenticatedClient()
		return client.murmelidb.testadmin if DbClient._useTestTables else client.murmelidb.admin

	@staticmethod
	def _getContactsTable():
		'''Use a different table for the unit tests so they're independent of the running db'''
		client = DbClient._getAuthenticatedClient()
		return client.murmelidb.testcontacts if DbClient._useTestTables else client.murmelidb.contacts

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
		'''Return own tor id'''
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
			profiles = DbClient._getProfileTable().find({"status":status},
				{"profilepic":0}).sort([('ownprofile', -1), ('torid', 1)])
		else:
			profiles = DbClient._getProfileTable().find({"status":{"$ne":"deleted"}},
				{"profilepic":0}).sort([('ownprofile', -1), ('torid', 1)])
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
			if not storedProfile or storedProfile.get('profilepicpath', "") != givenprofilepicpath:
				profile['profilepic'] = Binary(imageutils.makeThumbnailBinary(givenprofilepicpath))
				pic_changed = True
		elif profile.get('profilepic', None):
			pic_changed = True
		profiles.update({'torid':torid}, {"$set": profile}, True)
		if pic_changed:
			DbClient._updateAvatar(torid, Config.getWebCacheDir())
		if profile.get("status", None) in ["blocked", "deleted", "trusted"]:
			DbClient.updateContactList(Config.getProperty(Config.KEY_ALLOW_FRIENDS_TO_SEE_FRIENDS))

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
			# bsonfromdb is a bson Binary object, but it can be iterated like a bytes object
			# and written directly to the file
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
			 {"torid":1, "displayName":1, "status":1, "contactlist":1, "keyid":1}).sort([('torid', 1)])

	@staticmethod
	def getTrustedContacts():
		return DbClient._getProfileTable().find({"status":"trusted"},
			{"torid":1, "name":1, "contactlist":1}).sort([('torid', 1)])

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
			# If the message is allowed to be relayed, we need to make a list of all our contacts
			relays = []
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
					DbClient._getOutboxTable().insert({"recipient":r, "relays":relays,
						"message":messageToSend, "queue":message.shouldBeQueued,
						"msgType":message.getMessageTypeKey()})
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
		thisHash = DbClient.calculateHash({"body":message['messageBody'],
			"timestamp":message['timestamp'], "senderId":message['fromId']})
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
			print("Received message with hash '", thisHash, "but I've got that one already")

	@staticmethod
	def getInboxMessages():
		return DbClient._getInboxTable().find({"deleted":None}).sort("timestamp", -1)
		# TODO: Other sorting/paging options?

	@staticmethod
	def deleteMessageFromInbox(messageId):
		DbClient._getInboxTable().update({"_id":ObjectId(messageId)}, {"$set" : {"deleted":True}})

	@staticmethod
	def changeRequestMessagesToRegular(torId):
		'''Change all contact requests from the given id to be regular messages instead'''
		DbClient._getInboxTable().update({"fromId":torId, "messageType":"contactrequest"},
			{"$set" : {"messageType":"normal", "recipients":DbClient.getOwnTorId()}})

	@staticmethod
	def getConversationId(parentHash):
		'''Get the conversation id for the given parent hash'''
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
		cid = adminTable.find_and_modify(query={"_id":"conversationid"},
			update={"$inc":{"value":1}}, new=True)
		if cid:
			value = cid.get("value", None)
			if value:
				return value
		# Couldn't get any value, so start from 1
		adminTable.insert({"_id":"conversationid", "value":1})
		return 1

	@staticmethod
	def addMessageToPendingContacts(message):
		thisHash = DbClient.calculateHash({"body":message['messageBody'],
			"timestamp":message['timestamp'], "senderId":message['fromId']})
		# Check id or hash of message to make sure we haven't got it already!
		pendingTable = DbClient._getContactsTable()
		if not pendingTable.find_one({"messageHash" : thisHash}):
			message['messageHash'] = thisHash
			pendingTable.insert(message)

	@staticmethod
	def getPendingContactMessages(torId):
		return DbClient._getContactsTable().find({"fromId":torId})

# TODO: See if we need to call m.murmelidb.command("getLastError").get("ok") after a write
#       to check that it worked


class PasswordManager:
	'''Class responsible for the management of the mongo authentication password,
	including creation, storage and retrieval'''
	PASSWORD_LENGTH = 20

	@staticmethod
	def _getPasswordFilePath():
		'''Get the path to the password file'''
		return Config.getDatabasePasswordFile()

	@staticmethod
	def _createPassword():
		'''Create a new random password and return it'''
		randgen = SystemRandom()
		return "".join([randgen.choice("abcdefghijklmnopqrstuvwxyz0123456789_") \
			for _ in range(PasswordManager.PASSWORD_LENGTH)])

	@staticmethod
	def getStoredPassword():
		'''Return the stored password from the file, or None if not found or not valid'''
		try:
			foundLine = None
			with open(PasswordManager._getPasswordFilePath(), "r") as pwFile:
				for l in pwFile:
					if foundLine and l:
						return None
					foundLine = l
			if foundLine and len(foundLine) == PasswordManager.PASSWORD_LENGTH:
				return foundLine
		except FileNotFoundError:
			pass
		except PermissionError:
			pass

	@staticmethod
	def createAndStorePassword():
		'''Create and store a new password, and return it'''
		password = PasswordManager._createPassword()
		try:
			with open(PasswordManager._getPasswordFilePath(), "w") as pwFile:
				pwFile.write(password)
		except PermissionError:
			return None
		return password

	@staticmethod
	def deletePassword():
		try:
			os.remove(PasswordManager._getPasswordFilePath())
		except OSError: # file not found, or write-protected
			pass


class AuthSetterUpper():
	'''Class responsible for setting up the authentication on the database'''

	STATUS_NODB_NOPWD   = 0
	STATUS_NODB_PWD     = 1
	STATUS_NOAUTH_NOPWD = 2
	STATUS_NOAUTH_PWD   = 3
	STATUS_AUTH_NOPWD   = 4
	STATUS_AUTH_PWD     = 5

	def _getDbPwdStatus(self):
		'''Get the current combined status of database and password availability'''
		dbStatus = DbClient.getDatabaseRunStatus()
		status = 0 if dbStatus == DbClient.NOT_RUNNING else 2 if dbStatus == DbClient.RUNNING_WITHOUT_AUTH else 4
		if DbClient.isPasswordAvailable():
			status += 1
		return status

	def isPasswordOk(self):
		'''Assuming the server is running with auth and we have a saved password, does it work?'''
		try:
			_ = DbClient.getProfile(userid=None, extend=False)
			return True
		except:
			return False

	def setup(self):
		'''Try to setup the authentication on the database and return True if succeeded'''
		previousStatus = -1
		for step in range(6):
			currStatus = self._getDbPwdStatus()
			print("Setting up auth - step", step, ", status=", currStatus)
			if currStatus == AuthSetterUpper.STATUS_AUTH_PWD:
				# Check we've got the right password!
				if self.isPasswordOk():
					# This is the only good exit point from this method!
					return True
				else:
					# If password is wrong then delete password and stop db
					PasswordManager.deletePassword()
					DbClient.stopDatabase()
			if currStatus == previousStatus:
				return False # couldn't change state
			if currStatus == AuthSetterUpper.STATUS_NODB_NOPWD:
				# We've got no password, so we need to start db without auth
				DbClient.startDatabase(False)
			elif currStatus == AuthSetterUpper.STATUS_NODB_PWD:
				# We've got a password, so we need to start db with auth
				DbClient.startDatabase(True)
			elif currStatus == AuthSetterUpper.STATUS_NOAUTH_NOPWD:
				# Need to setup the new user with a new password
				adminPassword = PasswordManager.createAndStorePassword()
				userPassword = PasswordManager.createAndStorePassword()
				DbClient.setupDatabaseUsers(adminPassword, userPassword)
				DbClient.stopDatabase()
			elif currStatus == AuthSetterUpper.STATUS_NOAUTH_PWD \
			or currStatus == AuthSetterUpper.STATUS_AUTH_NOPWD:
				# If stopping the database doesn't work, state will remain unchanged
				DbClient.stopDatabase()
			previousStatus = currStatus
			# Wait a couple of seconds for the database to stop or start
			time.sleep(2)
		# must be stuck in a cycle if it hasn't returned already by now
		DbClient.stopDatabase()
		return False
