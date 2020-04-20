'''Module for testing the system and components'''

import unittest
from murmeli import system
from murmeli.config import Config
from murmeli.i18n import I18nManager


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
        sys.add_component(config)
        # test access to non-existent keys
        self.assertIsNone(accessor.get_config_value("daffodil"), "no value yet")
        config.set_property("daffodil", "peanut")
        self.assertEqual(accessor.get_config_value("daffodil"), "peanut", "peanut set")

    def test_config_subscriber_conffirst(self):
        '''Test that i18n properly subscribes to changes in config, when config added to system first'''
        sys = system.System()
        config = Config(sys)
        sys.add_component(config)
        i18n = I18nManager(sys)
        sys.add_component(i18n)
        self.check_config_subscribing(sys)

    def test_config_subscriber_i18nfirst(self):
        '''Test that i18n properly subscribes to changes in config, when i18n added to system first'''
        sys = system.System()
        i18n = I18nManager(sys)
        sys.add_component(i18n)
        # Here the i18n component fails to attach to Config because it's not present in the system yet
        config = Config(sys)
        sys.add_component(config)
        self.check_config_subscribing(sys)

    def check_config_subscribing(self, sys):
        '''Check that with the given system, the i18n component reacts to changes in config'''
        sys.invoke_call(sys.COMPNAME_CONFIG, "set_property", key=Config.KEY_LANGUAGE, value="en")
        en_title = sys.invoke_call(sys.COMPNAME_I18N, "get_text", key="settings.title")
        self.assertEqual(en_title, "Settings", "Settings title retrieved in English")
        sys.invoke_call(sys.COMPNAME_CONFIG, "set_property", key=Config.KEY_LANGUAGE, value="de")
        de_title = sys.invoke_call(sys.COMPNAME_I18N, "get_text", key="settings.title")
        self.assertEqual(de_title, "Einstellungen", "Settings title retrieved in German")


if __name__ == "__main__":
    unittest.main()
