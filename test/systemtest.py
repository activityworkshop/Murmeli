'''Module for testing the system and components'''

import unittest
from murmeli import system


class SystemTest(unittest.TestCase):
    '''Tests for the system'''

    def test_empty_system(self):
        '''Test an empty system'''
        sys = system.System()
        self.assertIsNotNone(sys, "System created")
        self.assertFalse(sys.components, "System empty")

    def test_add_component(self):
        '''Test adding component to system'''
        sys = system.System()
        comp = system.Component(sys, "barney")
        self.assertFalse(comp.started, "Component not started yet")
        sys.invoke_call("marigold", "tomato")	# shouldn't do anything, no exception raised
        sys.start()
        self.assertTrue(comp.started, "Component started now")
        self.assertRaises(AttributeError, sys.invoke_call, "barney", "tomato")

    class SimpleComponent(system.Component):
        '''Component with a simple additional method'''
        def __init__(self, parent, name):
            system.Component.__init__(self, parent, name)
            self.num_fish = 17
        def count_fish(self):
            '''Count the fish in the fishpond'''
            return self.num_fish

    def test_invoke_component(self):
        '''Test invoking methods on an added component'''
        sys = system.System()
        comp = SystemTest.SimpleComponent(sys, "barney")
        self.assertFalse(comp.started, "Component not started yet")
        self.assertRaises(AttributeError, sys.invoke_call, "barney", "tomato")
        self.assertEqual(sys.invoke_call("barney", "count_fish"), 17, "Method invoked")


if __name__ == "__main__":
    unittest.main()
