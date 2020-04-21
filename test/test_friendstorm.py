'''Testing of the friendstorm model'''

import unittest
from PyQt5.QtWidgets import QApplication
from murmeli.brainstorm import FriendStorm


class StormTest(unittest.TestCase):
    '''Tests for the storm model'''

    def test_minimum_model(self):
        '''Check that the very minimum model (just self) is consistent'''
        app = QApplication([])
        storm = FriendStorm("my_id", "my name")
        self.assertEqual(1, storm.get_num_nodes(), "one node")
        self.assertEqual(0, storm.get_num_edges(), "zero edges")

    def test_single_friend(self):
        '''Check that adding a friend increases the nodes and edges'''
        app = QApplication([])
        storm = FriendStorm("my_id", "my name")
        storm.add_friend("abc123", "Jason")
        self.assertEqual(2, storm.get_num_nodes(), "two nodes")
        self.assertEqual(1, storm.get_num_edges(), "one edge")

    def test_blank_name(self):
        '''Check that a node with no name uses the id as label'''
        app = QApplication([])
        storm = FriendStorm("waterfall", "")
        self.assertIsNone(storm.get_label("thunderstorm"), "Node not found, no label")
        self.assertEqual(storm.get_label("waterfall"), "waterfall", "label is id")

    def test_triangle(self):
        '''Check that a triangle gives three edges'''
        app = QApplication([])
        storm = FriendStorm("my_id", "my name")
        storm.add_friend("abc123", "Jason")
        storm.add_friend("xyz567", "Sophie")
        storm.connect_friends("abc123", "xyz567")
        # Same edge is added twice, should only count once
        storm.connect_friends("xyz567", "abc123")
        self.assertEqual(3, storm.get_num_nodes(), "three nodes")
        self.assertEqual(3, storm.get_num_edges(), "three edges")

    def test_friend_of_friend(self):
        '''Check that a friend of a friend is properly stored'''
        app = QApplication([])
        storm = FriendStorm("my_id", "my name")
        storm.add_friend("abc123", "Jason")
        storm.add_friend("xyz567", "Sophie")
        storm.add_friends_friend("abc123", "danger", "Zaphod")
        storm.add_friends_friend("xyz567", "danger", "Zaphod")
        self.assertEqual(4, storm.get_num_nodes(), "four nodes")
        self.assertEqual(4, storm.get_num_edges(), "four edges")
        self.assertEqual(storm.get_label("danger"), "Zaphod", "stranger's name")


if __name__ == "__main__":
    unittest.main()
