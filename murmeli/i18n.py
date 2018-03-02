'''Module for internationalisation of murmeli'''

import configparser
from murmeli.system import System, Component
from murmeli.config import Config


class I18nManager(Component):
    '''Manager class of internationalisation'''

    def __init__(self, parent):
        Component.__init__(self, parent, System.COMPNAME_I18N)
        self.texts = {}
        self.current_lang = None

    def set_language(self):
        '''Get the language from the config and use it to setup the I18n'''
        lang = self.call_component(System.COMPNAME_CONFIG, "get_property", key=Config.KEY_LANGUAGE)
        # First load English texts as default values
        self._load_language('en')
        # Now load selected language over the top
        if lang and len(lang) == 2 and lang != 'en':
            self._load_language(lang)

    def _load_language(self, lang):
        '''Load the specified language from a composed filename'''
        parser = configparser.RawConfigParser()
        parser.read('lang/murmeli-texts-%s.txt' % lang)
        for sec in parser.sections():
            for opt in parser.options(sec):
                self.texts[sec + '.' + opt] = parser.get(sec, opt)
        self.current_lang = lang

    def get_text(self, key):
        '''Get the i18n of the key if found, otherwise return the key'''
        return self.texts.get(key, key)

    def config_updated(self):
        '''The config has changed, so set the language in case it has changed'''
        self.set_language()
