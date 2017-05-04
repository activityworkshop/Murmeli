import json
import os.path

class SuperSimpleDb:
	'''Holds a super-simple database as a dictionary in memory
       and allows read/write from a persistent file.
       The dictionary holds tables, stored by name, where each
	   table is a list of dictionaries.
	   Rows of the table (items in the list) can be added, modified
	   or deleted, although deleting a row just sets the row to an
	   empty dictionary rather than removing it from the list.
	   The key of each row is then just the index of the item in the list.
	   When saved to file, the empty rows are then ignored.'''

	def __init__(self, filePath=None, flushTime=600):
		'''Constructor.  If filePath is None, then there will be no file loading or saving.'''
		self.db = {}	# Database, holding a dictionary of lists
		self.filePath = filePath
		self.flushTime = flushTime
		if filePath:
			self.loadFromFile()
			# TODO: Start timer to save to file using flushTime

	def loadFromFile(self):
		if self.filePath and os.path.exists(self.filePath):
			with open(self.filePath, "r") as fp:
				self.db = json.load(fp)

	def saveToFile(self):
		if self.filePath:
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

	def deleteFromTable(self, tableName, index):
		'''Returns True if specified row could be deleted, otherwise False'''
		table = self.db.get(tableName, None)
		if table and len(table) > index:
			table[index] = {}
			return True
		return False

	def getNumTables(self):
		'''Only needed for testing'''
		return len(self.db)


class Profile:
	'''Wrapper class for profiles from the database'''
	def __init__(self, inDict):
		self.wrappedDict = inDict;
	def __getitem__(self, key):
		val = self.wrappedDict.get(key, None)
		if not val and key == 'displayName':
			val = self.wrappedDict.get('name', None)
		if not val and key in ['displayName', 'name']:
			val = self.wrappedDict.get('torid', None)
		return val
	def __setitem__(self, key, val):
		self.wrappedDict[key] = val
	def __len__(self):
		return len(self.wrappedDict)


class MurmeliDb:
	'''Specialization of the SuperSimpleDb to handle Murmeli specifics'''

	def __init__(self, filePath=None, flushTime=600):
		'''Constructor.  If filePath is None, then there will be no file loading or saving.'''
		self.db = SuperSimpleDb(filePath, flushTime)

	def getInbox(self):
		return self.db.getTable("inbox")

	def getProfiles(self):
		tab = self.db.getTable("profiles")
		return [Profile(i) for i in tab if i]

	def getOutbox(self):
		return self.db.getTable("outbox")

	def getNumTables(self):
		'''Only needed for testing'''
		return self.db.getNumTables()

	def addMessageToInbox(self, msg):
		self.getInbox().append(msg)

	def deleteFromInbox(self, index):
		return self.db.deleteFromTable("inbox", index)

	def addMessageToOutbox(self, msg):
		self.getOutbox().append(msg)

	def deleteFromOutbox(self, index):
		return self.db.deleteFromTable("outbox", index)

	def addOrUpdateProfile(self, prof):
		tab = self.db.getTable("profiles")
		newId = prof.get("torid", None)
		if not newId:
			return False
		for p in tab:
			if p.get("torid", None) == newId:
				p.update(prof)
				return True
		tab.append(prof)
		return True

	def loadFromFile(self):
		self.db.loadFromFile()

	def saveToFile(self):
		self.db.saveToFile()

