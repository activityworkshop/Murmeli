import json
import os.path
import threading

class SuperSimpleDb:
	'''Holds a super-simple database as a dictionary in memory
       and allows read/write from a persistent file.
       The dictionary holds tables, stored by name, where each
	   table is a list of dictionaries.
	   Rows of the table (items in the list) can be added, modified
	   or deleted, although deleting a row just sets the row to an
	   empty dictionary rather than removing it from the list.
	   The key of each row is then just the index of the item in the list.
	   When loaded from file, the empty rows are then ignored.'''

	def __init__(self, filePath=None):
		'''Constructor.  If filePath is None, then there will be no file loading or saving.'''
		self.db = {}	# Database, holding a dictionary of lists
		self.filePath = filePath
		if filePath:
			self.loadFromFile()

	def loadFromFile(self):
		if self.filePath and os.path.exists(self.filePath):
			with open(self.filePath, "r") as fp:
				self.db = json.load(fp)

	def saveToFile(self):
		# Debugging: where are the bytes coming from?
		for tName, tab in self.db.items():
			for r in tab:
				for fName, field in r.items():
					if type(field) == bytes:
						print("Table", tName, "has field", fName, "of type bytes!")
		if self.filePath:
			# Save the copy to file (overwriting what was there)
			with open(self.filePath, "w") as fp:
				json.dump(self.db, fp)

	def getTable(self, tableName):
		'''Get the table with the given name, and create it if necessary'''
		table = self.db.get(tableName, None)
		if table:
			return table
		# Table doesn't exist yet, so create it
		self.db[tableName] = []
		return self.db[tableName]

	def compressTable(self, tableName):
		if self.db.get(tableName, None):
			self.db[tableName] = [m for m in self.getTable(tableName) if m]

	def deleteFromTable(self, tableName, index):
		'''Returns True if specified row could be deleted, otherwise False'''
		table = self.db.get(tableName, None)
		index = int(index) if type(index) == str else index
		if table and len(table) > index:
			table[index] = {}
			return True
		return False

	def getNumTables(self):
		'''Only needed for testing'''
		return len(self.db)

	def findInTable(self, table, criteria):
		'''Look in the given table (obtained from eg getTable) for rows
		   matching the given criteria.  Criteria may include lists.'''
		results = []
		for item in table:
			rowMatches = True
			# Loop through criteria, checking that all of them match this row
			for cKey in criteria.keys():
				cVal = criteria.get(cKey, None)
				rowVal = item.get(cKey, None)
				if cVal is None or cVal == "":
					if rowVal:
						rowMatches = False
				elif type(cVal) in [int, str]:
					if rowVal != cVal:
						rowMatches = False
				elif type(cVal) == list:
					if not rowVal in cVal:
						rowMatches = False
			if rowMatches:
				results.append(item)

		return results


class Profile(dict):
	'''Wrapper class for profiles from the database'''
	def __init__(self, inDict):
		dict.__init__(self, inDict.copy())
	def __getitem__(self, key):
		val = dict.get(self, key, None)
		if not val and key == 'displayName':
			val = dict.get(self, 'name', None)
		if not val and key in ['displayName', 'name']:
			val = dict.get(self, 'torid', None)
		return val


class MurmeliDb:
	'''Specialization of the SuperSimpleDb to handle Murmeli specifics'''
	dbWriteLock = threading.Lock()

	TABLE_PROFILES = "profiles"
	TABLE_PENDING = "pendingcontacts"
	TABLE_OUTBOX = "outbox"
	TABLE_INBOX = "inbox"
	TABLE_ADMIN = "admin"

	def __init__(self, filePath=None):
		'''Constructor.  If filePath is None, then there will be no file loading or saving.'''
		self.db = SuperSimpleDb(filePath)
		with threading.Condition(self.dbWriteLock):
			self.compressTable(MurmeliDb.TABLE_INBOX)
			self.compressTable(MurmeliDb.TABLE_OUTBOX)
			# TODO: Remove expired outbox messages?

	def compressTable(self, tableName):
		self.db.compressTable(tableName)
		# assume our caller already has a write lock
		for i, r in enumerate(self.db.getTable(tableName)):
			if r and r.get("_id", None) != i:
				r['_id'] = i

	def getInbox(self):
		'''Get a copy of the inbox'''
		return [m.copy() for m in self.db.getTable(MurmeliDb.TABLE_INBOX) if m]

	def getProfiles(self):
		'''Get all the (non-blank) profiles'''
		tab = self.db.getTable(MurmeliDb.TABLE_PROFILES)
		return [Profile(i) for i in tab if i]

	def getProfilesWithStatus(self, status):
		'''Get all the profiles with the given status'''
		tab = self.db.getTable(MurmeliDb.TABLE_PROFILES)
		if type(status) == list:
			return [Profile(i) for i in tab if i and i.get("status", None) in status]
		elif status:
			return [Profile(i) for i in tab if i and i.get("status", None) == status]

	def getProfile(self, torid=None):
		'''Get the profile for the given torid'''
		if torid:
			for p in self.db.getTable(MurmeliDb.TABLE_PROFILES):
				if p and p.get("torid", None) == torid:
					return Profile(p)
		else:
			# No id given, so get our own profile
			for p in self.db.getTable(MurmeliDb.TABLE_PROFILES):
				if p and p.get("status", None) == "self":
					return Profile(p)
			print(len(self.db.getTable(MurmeliDb.TABLE_PROFILES)), "rows in profiles table, but self not found?")

	def getOutbox(self):
		'''Get copies of all the messages in the outbox'''
		return [m.copy() for m in self.db.getTable(MurmeliDb.TABLE_OUTBOX) if m]

	def addPendingContact(self, message):
		'''Add the given message to the pending contacts table
		   (caller should have already checked that same hash
		   isn't there in the table already)'''
		with threading.Condition(self.dbWriteLock):
			self.db.getTable(MurmeliDb.TABLE_PENDING).append(message)

	def deleteFromPendingContacts(self, senderId):
		'''Delete all the pending contact messages from the given senderId'''
		with threading.Condition(self.dbWriteLock):
			for i, pc in enumerate(self.db.getTable(MurmeliDb.TABLE_PENDING)):
				if pc and pc.get("fromId", None) == senderId:
					self.db.deleteFromTable(MurmeliDb.TABLE_PENDING, i)

	def getPendingContactMessages(self):
		'''Get copies of all pending contact messages'''
		return [m.copy() for m in self.db.getTable(MurmeliDb.TABLE_PENDING) if m]

	def getNumTables(self):
		'''Only needed for testing'''
		return self.db.getNumTables()

	def addMessageToInbox(self, msg):
		with threading.Condition(self.dbWriteLock):
			# Get current number in inbox, use this as index for msg
			msg['_id'] = len(self.getInbox())
			self.db.getTable(MurmeliDb.TABLE_INBOX).append(msg)

	def deleteFromInbox(self, index):
		with threading.Condition(self.dbWriteLock):
			return self.db.deleteFromTable(MurmeliDb.TABLE_INBOX, index)

	def updateInboxMessage(self, index, props):
		'''Update the inbox message at the given index'''
		with threading.Condition(self.dbWriteLock):
			inbox = self.db.getTable(MurmeliDb.TABLE_INBOX)
			if len(inbox) > index:
				row = inbox[index]
				if row:
					row.update(props)
					return True

	def addMessageToOutbox(self, msg):
		with threading.Condition(self.dbWriteLock):
			# Get current number in outbox, use this as index for msg
			msg['_id'] = len(self.getOutbox())
			self.db.getTable(MurmeliDb.TABLE_OUTBOX).append(msg)

	def deleteFromOutbox(self, index):
		with threading.Condition(self.dbWriteLock):
			return self.db.deleteFromTable(MurmeliDb.TABLE_OUTBOX, index)

	def updateOutboxMessage(self, index, props):
		'''Update the outbox message at the given index'''
		with threading.Condition(self.dbWriteLock):
			outbox = self.db.getTable(MurmeliDb.TABLE_OUTBOX)
			if len(outbox) > index:
				row = outbox[index]
				if row:
					row.update(props)
					return True

	def addOrUpdateProfile(self, prof):
		with threading.Condition(self.dbWriteLock):
			tab = self.db.getTable(MurmeliDb.TABLE_PROFILES)
			newId = prof.get("torid", None)
			if not newId:
				return False
			for p in tab:
				if p.get("torid", None) == newId:
					p.update(prof)
					return True
			tab.append(prof)
			return True

	def getAdminValue(self, key):
		'''Get the value of the given key, or None if not found'''
		tab = self.db.getTable(MurmeliDb.TABLE_ADMIN)
		firstRow = tab[0] if tab else None
		if firstRow:
			return firstRow.get(key, None)

	def setAdminValue(self, key, value):
		'''Set the value of the given key'''
		tab = self.db.getTable(MurmeliDb.TABLE_ADMIN)
		firstRow = tab[0] if tab else None
		if firstRow:
			firstRow[key] = value
		else:
			tab.append({key:value})

	def loadFromFile(self):
		with threading.Condition(self.dbWriteLock):
			self.db.loadFromFile()

	def saveToFile(self):
		with threading.Condition(self.dbWriteLock):
			self.db.saveToFile()

	def stop(self):
		self.saveToFile()

	def findInTable(self, table, criteria):
		'''Look in the given table (obtained from eg getInbox) for rows
		   matching the given criteria.  Criteria may include lists.'''
		return self.db.findInTable(table, criteria)

