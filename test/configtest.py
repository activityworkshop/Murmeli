'''Module for testing the config'''

import os
import unittest
from murmeli.config import Config


class ConfigTest(unittest.TestCase):
    '''Tests for the config'''

    def test_empty_config(self):
        '''Test an empty config'''
        conf = Config(None)
        self.assertIsNotNone(conf, "Config created")
        self.assertIsNone(conf.get_property("haddock"), "Config empty")

    def test_set_get_config(self):
        '''Test setting and getting from a config object'''
        conf = Config(None)
        conf.set_property("haddock", "snowflake")
        self.assertIsNotNone(conf.get_property("haddock"), "Config no longer empty")
        self.assertEqual(conf.get_property("haddock"), "snowflake", "Get matches set")
        self.assertNotEqual(conf.get_property("haddock"), "xylophone", "Get still matches set")
        conf.set_property("haddock", "xylophone")
        self.assertEqual(conf.get_property("haddock"), "xylophone", "property overwritten")
        conf.set_property(Config.KEY_DATA_DIR, "/temp")
        self.assertEqual(conf.get_web_cache_dir(), "/temp/cache", "cache path correct")

    def test_save_load_config(self):
        '''Test saving to a config file and loading it again'''
        conf = Config(None)
        conf.set_property("house.name", "Sea View")
        conf.set_property("house.bedrooms", "3")
        conf.set_property("house.furniture", True)
        conf.set_property(Config.KEY_LET_FRIENDS_SEE_FRIENDS, True)
        conf.set_property(Config.KEY_ALLOW_FRIEND_REQUESTS, False)
        test_file = os.path.join("test", "outputdata", "config.txt")
        conf.save(test_file)
        # Now load this file back into a new object
        conf = None
        conf2 = Config(None)
        conf2.load(test_file)
        self.assertEqual(conf2.get_property("house.name"), "Sea View", "got house name")
        self.assertEqual(conf2.get_property("house.bedrooms"), "3", "got bedrooms")
        self.assertEqual(conf2.get_property("house.furniture"), "True", "got furniture")
        # These two are recognised as specially "boolean" and are converted back to flags
        self.assertEqual(conf2.get_property(Config.KEY_LET_FRIENDS_SEE_FRIENDS), True, "got true")
        self.assertEqual(conf2.get_property(Config.KEY_ALLOW_FRIEND_REQUESTS), False, "got false")


if __name__ == "__main__":
    unittest.main()
