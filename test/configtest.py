'''Module for testing the config'''

import unittest
from murmeli.config import Config


class ConfigTest(unittest.TestCase):
    '''Tests for the config'''

    def test_empty_config(self):
        '''Test an empty config file'''
        conf = Config(None)
        self.assertIsNotNone(conf, "Config created")
        self.assertIsNone(conf.get_property("haddock"), "Config empty")

    def test_set_get_config(self):
        '''Test setting and getting from a config file'''
        conf = Config(None)
        conf.set_property("haddock", "snowflake")
        self.assertIsNotNone(conf.get_property("haddock"), "Config no longer empty")
        self.assertEqual(conf.get_property("haddock"), "snowflake", "Get matches set")
        self.assertNotEqual(conf.get_property("haddock"), "xylophone", "Get still matches set")
        conf.set_property("haddock", "xylophone")
        self.assertEqual(conf.get_property("haddock"), "xylophone", "property overwritten")
        conf.set_property(Config.KEY_DATA_DIR, "/temp")
        self.assertEqual(conf.get_web_cache_dir(), "/temp/cache", "cache path correct")


if __name__ == "__main__":
    unittest.main()
