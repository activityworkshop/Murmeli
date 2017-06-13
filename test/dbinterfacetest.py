import unittest
import supersimpledb
from dbinterface import DbI
import os


class ExampleMessage:
	'''Stub for the messages, for adding to the outbox'''
	def __init__(self, recpts, messageBody, relay=False):
		self.recipients = recpts
		self.msgBody = messageBody
		self.shouldBeRelayed = relay
		self.shouldBeQueued = False
	def createOutput(self, encryptKey):
		return ("Encrypt:" + self.msgBody + ":for:" + encryptKey).encode("utf-8")
	def getMessageTypeKey(self):
		return "test"

class DbInterfaceTest(unittest.TestCase):
	'''Tests for the database interface'''

	def testBasics(self):
		'''Testing the basics of the interface with a super-simple db'''

		# Create new, empty database without file-storage
		db = supersimpledb.MurmeliDb()
		DbI.setDb(db)

		# Lists should be empty
		self.assertEqual(len(DbI.getMessageableProfiles()), 0, "Should be 0 messageables")
		self.assertEqual(len(DbI.getTrustedProfiles()), 0, "Should be 0 trusted")
		self.assertFalse(DbI.hasFriends(), "Shouldn't have any friends")

		# Store some profiles
		DbI.updateProfile("abc123", {"keyid":"ZYXW987", "status":"self", "name":"That's me"})
		DbI.updateProfile("def123", {"keyid":"JKLM987", "status":"trusted", "name":"Jimmy"})
		DbI.updateProfile("ghi123", {"keyid":"TUVWX987", "status":"untrusted", "name":"Dave"})

		# Get my ids
		self.assertEqual(DbI.getOwnTorid(), "abc123", "Should find correct tor id")
		self.assertEqual(DbI.getOwnKeyid(), "ZYXW987", "Should find correct key id")

		# Get all profiles
		self.assertEqual(len(DbI.getProfiles()), 3, "Should be three profiles in total")
		self.assertEqual(len(DbI.getMessageableProfiles()), 2, "Should be two messageables")
		self.assertEqual(len(DbI.getTrustedProfiles()), 1, "Should be one trusted")
		self.assertEqual(DbI.getTrustedProfiles()[0]['displayName'], "Jimmy", "Jimmy should be trusted")
		self.assertTrue(DbI.hasFriends(), "Should have friends")

		# Update an existing profile
		DbI.updateProfile("def123", {"displayName":"Slippin' Jimmy"})
		self.assertEqual(len(DbI.getTrustedProfiles()), 1, "Should still be one trusted")
		self.assertEqual(DbI.getTrustedProfiles()[0]['displayName'], "Slippin' Jimmy", "Slippin' Jimmy should be trusted")

		# Finished
		DbI.releaseDb()


	def testAvatars(self):
		'''Test the loading, storing and exporting of binary avatar images'''
		db = supersimpledb.MurmeliDb()
		DbI.setDb(db)
		inputPath = "testdata/example-avatar.jpg"
		outPath = "cache/avatar-deadbeef.jpg"
		if os.path.exists(outPath):
			os.remove(outPath)
		os.makedirs('cache', exist_ok=True)
		self.assertFalse(os.path.exists(outPath))
		DbI.updateProfile("deadbeef", {"profilepicpath":inputPath})
		# Output file still shouldn't exist, we didn't give a path to write picture to
		self.assertFalse(os.path.exists(outPath))
		DbI.updateProfile("deadbeef", {"profilepicpath":inputPath}, "cache")
		# Output file should exist now
		self.assertTrue(os.path.exists(outPath))
		# TODO: Any way to compare input with output?  They're not the same.
		DbI.releaseDb()


	def testOutbox(self):
		'''Test the storage and retrieval of messages in the outbox'''
		db = supersimpledb.MurmeliDb()
		DbI.setDb(db)
		self.assertEqual(len(DbI.getOutboxMessages()), 0, "Outbox should be empty")
		# Add profile for this the target recipient
		DbI.updateProfile("ABC312", {"keyid":"ZYXW987", "status":"trusted", "name":"Best friend"})

		# add one message to the outbox
		DbI.addToOutbox(ExampleMessage(["ABC312"], "Doesn't matter really what the message is"))
		self.assertEqual(len(DbI.getOutboxMessages()), 1, "Outbox should have one message")
		self.checkMessageIndexes(DbI.getOutboxMessages())
		DbI.addToOutbox(ExampleMessage(["ABC312"], "A second message"))
		self.assertEqual(len(DbI.getOutboxMessages()), 2, "Outbox should have 2 messages")
		self.checkMessageIndexes(DbI.getOutboxMessages())
		self.assertTrue(DbI.deleteFromOutbox(0))
		self.assertEqual(len(DbI.getOutboxMessages()), 1, "Outbox should only have 1 message (1 empty)")
		nonEmptyMessages = [msg for msg in DbI.getOutboxMessages() if msg]
		self.assertEqual(len(nonEmptyMessages), 1, "Outbox should only have 1 non-empty message")
		self.assertEqual(nonEmptyMessages[0]["_id"], 1, "Message 0 should have index 1")
		# done
		DbI.releaseDb()


	def checkMessageIndexes(self, table):
		'''Internal method used for checking consistency of inbox or outbox'''
		for i,r in enumerate(table):
			if r:
				self.assertEqual(i, r["_id"], "Row should have message index equal to position")

	def testSearching(self):
		'''Test the searching of the inbox'''
		db = supersimpledb.MurmeliDb()
		DbI.setDb(db)
		# Add some inbox messages with different text
		DbI.addToInbox({"messageBody":"There were some children playing in the park", "timestamp":"", "fromId":"ABC312"})
		DbI.addToInbox({"messageBody":"There was a child playing in the castle", "timestamp":"", "fromId":"ABC312"})
		DbI.addToInbox({"messageBody":"Children were making far too much noise", "timestamp":"", "fromId":"ABC312"})
		# Get this message again, and check the conversation id, should be 101
		self.assertEqual(len(DbI.getInboxMessages()), 3, "Inbox has 3")

		search1 = DbI.searchInboxMessages("child")
		self.assertEqual(len(search1), 2, "Only 2 match 'child'")
		search2 = DbI.searchInboxMessages("children")
		self.assertEqual(len(search2), 1, "Only 1 matches 'children'")
		search3 = DbI.searchInboxMessages("")
		self.assertEqual(len(search3), 3, "All match empty search string")
		search4 = DbI.searchInboxMessages("hild")
		self.assertEqual(len(search4), 3, "All match 'hild'")
		search5 = DbI.searchInboxMessages("noisy")
		self.assertEqual(len(search5), 0, "None are noisy")
		search6 = DbI.searchInboxMessages("Child")
		self.assertEqual(len(search6), 1, "Only 1 matches 'Child'")

		# done
		DbI.releaseDb()

	def testConversationIds(self):
		'''Test the increment of conversation ids'''
		db = supersimpledb.MurmeliDb()
		DbI.setDb(db)
		# If we start with an empty db, the id should start at 1
		for i in range(100):
			self.assertEqual(DbI.getNewConversationId(), i+1, "id should be 1 more than i")
		# Add profiles for us and a messages sender
		DbI.updateProfile("F055", {"keyid":"ZYXW987", "status":"self", "name":"That's me"})
		DbI.updateProfile("ABC312", {"keyid":"ZYXW987", "status":"trusted", "name":"Best friend"})
		# Add an inbox message with a conversation id
		DbI.addToInbox({"messageBody":"Gorgonzola and Camembert", "timestamp":"early 2017",
			"fromId":"ABC312"})
		# Get this message again, and check the conversation id, should be 101
		msg0 = DbI.getInboxMessages()[0]
		self.assertEqual(msg0.get("conversationid", 0), 101, "Id should now be 101")

		# Add another message with the parent hash referring to the first one
		DbI.addToInbox({"messageBody":"Fried egg sandwich", "timestamp":"middle 2017",
			"fromId":"ABC312", "parentHash":'40e98bae7a811c23b59b89bd0f11b0a0'})
		msg1 = DbI.getInboxMessages()[0]
		self.assertTrue("Fried egg" in msg1.get("messageBody", ""), "Fried egg should be first")
		self.assertEqual(msg1.get("conversationid", 0), 101, "Id should now also be 101")

		# Add another message with an unrecognised parent hash
		DbI.addToInbox({"messageBody":"Red wine and chocolate", "timestamp":"late 2017",
			"fromId":"ABC312", "parentHash":'ff3'})
		msg2 = DbI.getInboxMessages()[0]
		self.assertTrue("Red wine" in msg2.get("messageBody", ""), "Red wine should be first")
		self.assertEqual(msg2.get("conversationid", 0), 102, "Id should take 102")

		# done
		DbI.releaseDb()


if __name__ == "__main__":
	unittest.main()
