'''Module for testing the system and components'''

import unittest
from murmeli import system
from murmeli.config import Config


class AccessorComponent(system.Component):
    '''Class to test access to other components'''
    def __init__(self, parent):
        system.Component.__init__(self, parent, "test.accessor")

    def get_config_value(self, key):
        '''Try to get the value of the specified key from the config'''
        return self.call_component(system.System.COMPNAME_CONFIG, "get_property", key=key)


class ConfigSystemTest(unittest.TestCase):
    '''Tests for accessing config via the system'''

    def test_config_in_system(self):
        '''Test a system with a config component'''
        # Construct system with two components
        sys = system.System()
        accessor = AccessorComponent(sys)
        self.assertIsNone(accessor.get_config_value("daffodil"), "no config yet")
        config = Config(sys)
        # test access to non-existent keys
        self.assertIsNone(accessor.get_config_value("daffodil"), "no value yet")
        config.set_property("daffodil", "peanut")
        self.assertEqual(accessor.get_config_value("daffodil"), "peanut", "peanut set")


if __name__ == "__main__":
    unittest.main()
