'''Module for testing the i18n component'''

import unittest
from murmeli.i18n import I18nManager
from murmeli.system import System
from murmeli.config import Config


class I18nTest(unittest.TestCase):
    '''Tests for the i18n'''

    def test_en(self):
        '''Test using standard English texts'''
        i18n = I18nManager(None)
        i18n.set_language()
        self.assertEqual(i18n.get_text("home.title"), "Murmeli", "Title match")

    def test_de(self):
        '''Test using additional German texts'''
        i18n = I18nTest.create_system("de")
        self.assertEqual(i18n.get_text("messages.title"), "Nachrichten", "German match")

    def test_it(self):
        '''Test using missing Italian texts'''
        i18n = I18nTest.create_system("it")
        self.assertEqual(i18n.get_text("messages.title"), "Messages", "uses English not Italian")

    @staticmethod
    def create_system(language_name):
        '''Helper method to create a system configured to the given language'''
        sys = System()
        i18n = I18nManager(sys)
        sys.add_component(i18n)
        conf = Config(sys)
        sys.add_component(conf)
        conf.set_property(conf.KEY_LANGUAGE, language_name)
        i18n.set_language()
        return i18n


if __name__ == "__main__":
    unittest.main()
