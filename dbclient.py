#################################
## Database client for Murmeli ##
#################################

# Only classes inside this file should care about mongo database details
# (except maybe the startup wizard which can check for pymongo's availability)

import os.path
import subprocess
import time
import pymongo
from bson import ObjectId
from bson.binary import Binary
import hashlib # for calculating checksums
from config import Config
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
	def getProfile(userid=None, extend=True):
		client = pymongo.MongoClient()
		if userid is None:
			profile = client.murmelidb.profiles.find_one({'ownprofile': True})
		else:
			profile = client.murmelidb.profiles.find_one({'torid': userid})
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

	# TODO: Make these non-static methods and keep a hold of a MongoClient?  But who keeps hold of the DbClient?

	@staticmethod
	def getContactList(status=None):
		client = pymongo.MongoClient()
		# Ignore the "profilepic" field, to save data flow
		if status:
			profiles = client.murmelidb.profiles.find({"status":status}, {"profilepic":0}).sort([('ownprofile',-1), ('torid',1)])
		else:
			profiles = client.murmelidb.profiles.find({"status":{"$ne":"blocked"}}, {"profilepic":0}).sort([('ownprofile',-1), ('torid',1)])
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
		client = pymongo.MongoClient()
		profiles = client.murmelidb.profiles
		# If the profile pic path has changed, then we need to load the file
		givenprofilepicpath = profile.get('profilepicpath', None)
		pic_changed = False
		if givenprofilepicpath and os.path.exists(givenprofilepicpath):
			# check if it's the same path as already stored
			storedProfile = client.murmelidb.profiles.find_one({'torid': torid}, {"profilepicpath":1})
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
		client = pymongo.MongoClient()
		torids = [i['torid'] for i in client.murmelidb.profiles.find({}, {"torid":1}) if i]
		# For each one, look in outputdir to see if pic is already there
		for i in torids:
			outpath = os.path.join(outputdir, "avatar-" + i + ".jpg")
			if not os.path.exists(outpath):
				# File doesn't exist, so get profilepic data
				pic = client.murmelidb.profiles.find_one({'torid': i}, {"profilepic":1}).get('profilepic', None)
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
				print("Ignored", k, " because it has type", type(dbrow[k]))
				ignoredFields.add(k)
		print("For the hash, I used fields", usedFields, "and ignored", ignoredFields)
		return h.hexdigest()

	@staticmethod
	def getTrustedContacts():
		client = pymongo.MongoClient()
		return client.murmelidb.profiles.find({"status":"trusted"}, {"torid":1, "name":1}).sort([('torid',1)])

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
					contactlist.append(p['torid'] + name.replace(',', '.') + ',')
		profile = {'contactlist' : ''.join(contactlist)}
		DbClient.updateContact(DbClient.getOwnTorId(), profile)

