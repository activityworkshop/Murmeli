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
        lang = self.get_config_property(Config.KEY_LANGUAGE) or "en"
        if lang != self.current_lang:
            # First load English texts as default values
            self._load_language('en')
            # Now load selected language over the top
            if lang and len(lang) == 2 and lang != 'en':
                self._load_language(lang)
            self.current_lang = lang

    def _load_language(self, lang):
        '''Load the specified language from a composed filename'''
        parser = configparser.RawConfigParser()
        parser.read('lang/murmeli-texts-%s.txt' % lang)
        for sec in parser.sections():
            for opt in parser.options(sec):
                self.texts[sec + '.' + opt] = parser.get(sec, opt)

    def get_all_texts(self):
        '''Return the whole map of texts'''
        return self.texts

    def get_text(self, key):
        '''Get the i18n of the key if found, otherwise return the key'''
        return self.texts.get(key, key)

    def checked_start(self):
        '''Connect to config if it's available'''
        return self.call_component(System.COMPNAME_CONFIG, "add_listener", sub=self)

    def config_updated(self):
        '''The config has changed, so set the language in case it has changed'''
        self.set_language()
