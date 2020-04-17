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

    def test_check_component_presence(self):
        '''Test adding component to system and checking whether it's there or not'''
        sys = system.System()
        comp_name = "Cromulence"
        self.assertFalse(sys.has_component(comp_name), "Component not there yet")
        comp = system.Component(sys, comp_name)
        sys.add_component(comp)
        self.assertTrue(sys.has_component(comp_name), "Component now present")

    def test_add__and_call_component(self):
        '''Test adding component to system and calling it'''
        sys = system.System()
        comp = system.Component(sys, "barney")
        sys.add_component(comp)
        sys.invoke_call("marigold", "tomato")	# shouldn't do anything, no exception raised
        self.assertTrue(comp.started, "Component started now")
        self.assertRaises(AttributeError, sys.invoke_call, "barney", "tomato")

    def test_add_and_remove_component(self):
        '''Test removing an added component from the system and re-adding another'''
        sys = system.System()
        comp_name = "fortitude"
        self.assertFalse(sys.has_component(comp_name), "Component not there yet")
        comp = system.Component(sys, comp_name)
        sys.add_component(comp)
        self.assertTrue(sys.has_component(comp_name), "Component now present")
        sys.remove_component(comp_name)
        self.assertFalse(sys.has_component(comp_name), "Component not there any more")
        sys.add_component(comp)
        self.assertTrue(sys.has_component(comp_name), "Component now present again")


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
        sys.add_component(comp)
        self.assertTrue(comp.started, "Component started")
        self.assertRaises(AttributeError, sys.invoke_call, "barney", "tomato")
        self.assertEqual(sys.invoke_call("barney", "count_fish"), 17, "Method invoked")


if __name__ == "__main__":
    unittest.main()
