'''Internationalization functions for looking up tokens'''

import configparser
from config import Config

class I18nManager:
	'''Manager for translations'''
	# dictionary of keys and texts
	texts = {}
	# currently used language
	lang = None
	# singleton object
	singleton = None

	@staticmethod
	def setLanguage():
		lang = Config.getProperty(Config.KEY_LANGUAGE)
		# First load English texts as default values
		I18nManager._loadLanguage('en')
		# Now load selected language over the top
		if lang and len(lang) == 2 and lang != 'en':
			I18nManager._loadLanguage(lang)

	@staticmethod
	def _loadLanguage(lang):
		parser = configparser.RawConfigParser()
		parser.read('lang/murmeli-texts-%s.txt' % lang)
		for sec in parser.sections():
			for opt in parser.options(sec):
				I18nManager.texts[sec + '.' + opt] = parser.get(sec, opt)
		I18nManager.lang = lang

	@staticmethod
	def getText(key):
		return I18nManager.texts.get(key, key)

	@staticmethod
	def instance():
		'''An instance is needed for listening to the Config changes'''
		if not I18nManager.singleton:
			I18nManager.singleton = I18nManager()
		return I18nManager.singleton

	def configUpdated(self):
		I18nManager.setLanguage()

