'''Module for building message trees'''

class MessageLeaf:
	'''Leaf of a message tree, including single message and its siblings
	   (which are also MessageLeafs)'''
	def __init__(self, msg):
		'''Constructor giving message object'''
		self.msg = msg
		self.level = 0
		self.children = []
		self.hasParent = False

	def addChild(self, child):
		self.children.append(child)
		child.hasParent = True

	def getMaxLevel(self):
		'''Find the minimum level of this message based on its children'''
		maxLevel = -1
		for c in self.children:
			childLevel = c.getMaxLevel()
			if childLevel > maxLevel:
				maxLevel = childLevel
		return maxLevel + 1

	def setLevel(self, level):
		'''Set the actual level of this message'''
		self.level = level
		for c in self.children:
			c.setLevel(level-1)

	def addToList(self, resultList):
		'''Add this leaf and all its children recursively to the given list'''
		for c in self.children:
			c.addToList(resultList)
		resultList.append(self)

class MessageTree:
	'''Holds a tree of MessageLeaf objects'''
	def __init__(self):
		self.msgList = []
		self.msgsByHash = {}

	def addMsg(self, msg):
		leaf = MessageLeaf(msg)
		childIndex = self._getIndexOfFirstChild(msg.get('messageHash', None))
		if childIndex >= 0:
			self.msgList.insert(childIndex, leaf)
		else:
			self.msgList.append(leaf)
		self.msgsByHash[msg['messageHash']] = leaf

	def build(self):
		'''Now that all leafs have been collected, build the tree and calculate the levels'''
		# Loop to connect children to parents
		for l in self.msgList:
			parentId = l.msg.get("parentHash", None)
			parentLeaf = self.msgsByHash.get(parentId, None) if parentId else None
			if parentLeaf:
				parentLeaf.addChild(l)
		# Loop to get and set levels
		resultList = []
		for l in self.msgList:
			if not l.hasParent:
				rootLevel = l.getMaxLevel()
				l.setLevel(rootLevel)
				l.addToList(resultList)
		return resultList

	def _getIndexOfFirstChild(self, parentHash):
		'''Look through the list of messages for one whose parent has the given hash
		   and return its index.  Returns -1 if not found.'''
		if parentHash:
			for i,m in enumerate(self.msgList):
				if m.msg.get('parentHash', None) == parentHash:
					return i
		return -1
