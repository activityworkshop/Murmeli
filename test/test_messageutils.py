'''Module for testing the message utils'''

import unittest
from murmeli.messageutils import MessageTree

class MessageTreeTest(unittest.TestCase):
    '''Tests for the message tree'''

    def setUp(self):
        pass

    def test_basic_tree(self):
        '''Test adding leafs to a tree without any parents'''
        mess1 = {"messageHash":"abc123", "msgBody":"Message 1"}
        mess2 = {"messageHash":"def234", "msgBody":"Message 2"}
        mess3 = {"messageHash":"ghi345", "msgBody":"Message 3"}
        tree = MessageTree()
        for msg in [mess1, mess2, mess3]:
            tree.add_msg(msg)
        result = tree.build()
        self.assertEqual(len(result), 3, "Result should have 3 entries")
        for i in range(3):
            self.assertEqual(result[i].level, 0, "Messages should have level 0")
        self.assertEqual(result[0].msg['msgBody'], "Message 1", "Message 1 should match")
        self.assertEqual(result[1].msg['msgBody'], "Message 2", "Message 2 should match")
        self.assertEqual(result[2].msg['msgBody'], "Message 3", "Message 3 should match")


    def test_branched_tree(self):
        '''Test adding children to parents in tree (children appear before parents)'''
        mess1 = {"messageHash":"abc123", "msgBody":"Message 1", "parentHash":"def234"}
        mess2 = {"messageHash":"def234", "msgBody":"Message 2", "parentHash":"ghi345"}
        mess3 = {"messageHash":"ghi345", "msgBody":"Message 3", "parentHash":"xyz151"}
        tree = MessageTree()
        for msg in [mess1, mess2, mess3]:
            tree.add_msg(msg)
        result = tree.build()
        self.assertEqual(len(result), 3, "Result should have 3 entries")
        for i in range(3):
            self.assertEqual(result[i].level, i, "Messages should have level 0,1,2")
        self.assertEqual(result[0].msg['msgBody'], "Message 1", "Message 1 should match")
        self.assertEqual(result[1].msg['msgBody'], "Message 2", "Message 2 should match")
        self.assertEqual(result[2].msg['msgBody'], "Message 3", "Message 3 should match")

    def test_reversed_tree(self):
        '''Test building of tree when children appear after parents'''
        mess1 = {"messageHash":"abc123", "msgBody":"Message 1", "parentHash":"xyz151"}
        mess2 = {"messageHash":"def234", "msgBody":"Message 2", "parentHash":"abc123"}
        mess3 = {"messageHash":"ghi345", "msgBody":"Message 3", "parentHash":"def234"}
        tree = MessageTree()
        for msg in [mess1, mess2, mess3]:
            tree.add_msg(msg)
        result = tree.build()
        self.assertEqual(len(result), 3, "Result should have 3 entries")
        for i in range(3):
            self.assertEqual(result[i].level, i, "Messages should have level 0,1,2")
        self.assertEqual(result[0].msg['msgBody'], "Message 3", "Message 3 should match")
        self.assertEqual(result[1].msg['msgBody'], "Message 2", "Message 2 should match")
        self.assertEqual(result[2].msg['msgBody'], "Message 1", "Message 1 should match")

    def test_complex_tree(self):
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
        for msg in messages:
            tree.add_msg(msg)
        result = tree.build()
        self.assertEqual(len(result), 7, "Result should have 7 entries")
        expected_levels = [0, 1, 2, 1, 2, 3, 0]
        expected_msgs = [1, 2, 3, 6, 4, 7, 5]
        for i in range(len(messages)):
            # print(" " * result[i].level, result[i].msg['msgBody'])
            self.assertEqual(result[i].level, expected_levels[i], "Msgs have expected levels")
            expected_body = "Message " + str(expected_msgs[i])
            self.assertEqual(expected_body, result[i].msg['msgBody'], "Message index should match")


if __name__ == "__main__":
    unittest.main()
