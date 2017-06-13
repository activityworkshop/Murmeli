import unittest
from messageutils import MessageTree

class MessageTreeTest(unittest.TestCase):
	'''Tests for the message tree'''
	def setUp(self):
		pass

	def testBasicTree(self):
		'''Test adding leafs to a tree without any parents'''
		mess1 = {"messageHash":"abc123", "msgBody":"Message 1"}
		mess2 = {"messageHash":"def234", "msgBody":"Message 2"}
		mess3 = {"messageHash":"ghi345", "msgBody":"Message 3"}
		tree = MessageTree()
		for m in [mess1, mess2, mess3]:
			tree.addMsg(m)
		result = tree.build()
		self.assertEqual(len(result), 3, "Result should have 3 entries")
		for i in range(3):
			self.assertEqual(result[i].level, 0, "Messages should have level 0")
		self.assertEqual(result[0].msg['msgBody'], "Message 1", "Message 1 should match")
		self.assertEqual(result[1].msg['msgBody'], "Message 2", "Message 2 should match")
		self.assertEqual(result[2].msg['msgBody'], "Message 3", "Message 3 should match")


	def testBranchedTree(self):
		'''Test adding children to parents in tree (children appear before parents)'''
		mess1 = {"messageHash":"abc123", "msgBody":"Message 1", "parentHash":"def234"}
		mess2 = {"messageHash":"def234", "msgBody":"Message 2", "parentHash":"ghi345"}
		mess3 = {"messageHash":"ghi345", "msgBody":"Message 3", "parentHash":"xyz151"}
		tree = MessageTree()
		for m in [mess1, mess2, mess3]:
			tree.addMsg(m)
		result = tree.build()
		self.assertEqual(len(result), 3, "Result should have 3 entries")
		for i in range(3):
			self.assertEqual(result[i].level, i, "Messages should have level 0,1,2")
		self.assertEqual(result[0].msg['msgBody'], "Message 1", "Message 1 should match")
		self.assertEqual(result[1].msg['msgBody'], "Message 2", "Message 2 should match")
		self.assertEqual(result[2].msg['msgBody'], "Message 3", "Message 3 should match")

	def testReversedTree(self):
		'''Test building of tree when children appear after parents'''
		mess1 = {"messageHash":"abc123", "msgBody":"Message 1", "parentHash":"xyz151"}
		mess2 = {"messageHash":"def234", "msgBody":"Message 2", "parentHash":"abc123"}
		mess3 = {"messageHash":"ghi345", "msgBody":"Message 3", "parentHash":"def234"}
		tree = MessageTree()
		for m in [mess1, mess2, mess3]:
			tree.addMsg(m)
		result = tree.build()
		self.assertEqual(len(result), 3, "Result should have 3 entries")
		for i in range(3):
			self.assertEqual(result[i].level, i, "Messages should have level 0,1,2")
		self.assertEqual(result[0].msg['msgBody'], "Message 3", "Message 3 should match")
		self.assertEqual(result[1].msg['msgBody'], "Message 2", "Message 2 should match")
		self.assertEqual(result[2].msg['msgBody'], "Message 1", "Message 1 should match")

	def testComplexTree(self):
		'''Test building of complex tree with multiple siblings'''
		messages = [{"messageHash":"abc123", "msgBody":"Message 1", "parentHash":"def234"},
			{"messageHash":"def234", "msgBody":"Message 2", "parentHash":"ghi345"},
			{"messageHash":"ghi345", "msgBody":"Message 3", "parentHash":"xyz151"},
			{"messageHash":"jkl455", "msgBody":"Message 4", "parentHash":"xyz151"},
			{"messageHash":"qrs936", "msgBody":"Message 5", "parentHash":"mno004"},
			{"messageHash":"uvw707", "msgBody":"Message 6", "parentHash":"jkl455"},
			{"messageHash":"xyz151", "msgBody":"Message 7", "parentHash":"tuv335"},
		]
		tree = MessageTree()
		for m in messages:
			tree.addMsg(m)
		result = tree.build()
		self.assertEqual(len(result), 7, "Result should have 7 entries")
		expectedLevels = [0, 1, 2, 1, 2, 3, 0]
		expectedMsgs = [1, 2, 3, 6, 4, 7, 5]
		for i in range(len(messages)):
			# print(" " * result[i].level, result[i].msg['msgBody'])
			self.assertEqual(result[i].level, expectedLevels[i], "Messages should have expected levels")
			self.assertEqual(result[i].msg['msgBody'], "Message " + str(expectedMsgs[i]), "Message index should match")


if __name__ == "__main__":
	unittest.main()
