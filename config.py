'''Configuration module, including loading and saving to file'''

import configparser
import os.path
from PyQt4.QtCore import QObject, SIGNAL

class ConfigTannoy(QObject):
	'''Class to emit changed signals from the Config class'''
	def __init__(self):
		QObject.__init__(self)
	def connectListener(self, sub):
		self.connect(self, SIGNAL("fireUpdated()"), sub.configUpdated)
	def shout(self):
		self.emit(SIGNAL("fireUpdated()"))


class Config():
	'''Class to store application-wide config'''
	# static tannoy for broadcasting changes
	tannoy = None
	# Fixed location of config file
	CONFIG_FILE_PATH = os.path.expanduser("~/.murmeli")
	# Fixed location of config file
	DEFAULT_DATA_PATH = os.path.expanduser("~/murmeli")
	# static dictionary to hold values
	properties = {}
	# keys
	KEY_LANGUAGE = "gui.language"
	KEY_ALLOW_FRIENDS_TO_SEE_FRIENDS = "privacy.friendsseefriends"
	KEY_ALLOW_FRIEND_REQUESTS = "privacy.allowfriendrequests"
	KEY_SHOW_LOG_WINDOW = "gui.showlogwindow"
	# paths
	KEY_DATA_DIR = "path.data"
	KEY_MONGO_EXE = "path.mongoexe"
	KEY_TOR_EXE = "path.torexe"
	KEY_GPG_EXE = "path.gpgexe"


	@staticmethod
	def foundConfigFile():
		'''Return True if the config file was found and is readable, False otherwise'''
		try:
			with open(Config.CONFIG_FILE_PATH, 'r'):
				return True
		except:
			return False

	@staticmethod
	def load():
		'''Load the configuration from file'''
		if not Config.tannoy:
			Config.tannoy = ConfigTannoy()
		# Clear properties, and set default values
		Config.properties = {}
		Config.properties[Config.KEY_LANGUAGE]  = "en"
		Config.properties[Config.KEY_MONGO_EXE] = "mongo"
		Config.properties[Config.KEY_TOR_EXE]   = "tor"
		Config.properties[Config.KEY_GPG_EXE]   = "gpg"
		# Default privacy settings
		Config.properties[Config.KEY_ALLOW_FRIENDS_TO_SEE_FRIENDS] = True
		Config.properties[Config.KEY_ALLOW_FRIEND_REQUESTS] = True
		# Default gui settings
		Config.properties[Config.KEY_SHOW_LOG_WINDOW] = False

		# Locate file in home directory, and load it if found
		try:
			parser = configparser.RawConfigParser()
			parser.read(os.path.expanduser(Config.CONFIG_FILE_PATH))
			for sec in parser.sections():
				for opt in parser.options(sec):
					Config.properties[sec + '.' + opt] = parser.get(sec, opt)
		except configparser.MissingSectionHeaderError: pass
		# Convert strings to True/False
		Config._fixBooleanProperty(Config.KEY_ALLOW_FRIENDS_TO_SEE_FRIENDS)
		Config._fixBooleanProperty(Config.KEY_ALLOW_FRIEND_REQUESTS)
		Config._fixBooleanProperty(Config.KEY_SHOW_LOG_WINDOW)

	@staticmethod
	def _fixBooleanProperty(propName):
		'''Helper method to fix the loading of string values representing booleans'''
		value = Config.getProperty(propName)
		if value and isinstance(value, str):
			Config.properties[propName] = (value == "True")

	@staticmethod
	def getProperty(key):
		return Config.properties.get(key, None)

	@staticmethod
	def setProperty(key, value):
		Config.properties[key] = value
		Config.tannoy.shout()

	@staticmethod
	def getDatabaseDir():
		return os.path.join(Config.properties.get(Config.KEY_DATA_DIR, ""), "db")
	@staticmethod
	def getDatabasePasswordFile():
		return os.path.join(Config.getDatabaseDir(), "password_file")

	@staticmethod
	def getWebCacheDir():
		return os.path.join(Config.properties.get(Config.KEY_DATA_DIR, ""), "cache")

	@staticmethod
	def getKeyringDir():
		return os.path.join(Config.properties.get(Config.KEY_DATA_DIR, ""), "keyring")

	@staticmethod
	def getTorDir():
		return os.path.join(Config.properties.get(Config.KEY_DATA_DIR, ""), "tor")

	@staticmethod
	def registerSubscriber(sub):
		Config.tannoy.connectListener(sub)

	@staticmethod
	def save():
		writer = configparser.RawConfigParser()
		for p in Config.properties:
			dotpos = p.find('.')
			if dotpos > 0:
				section = p[0:dotpos]
				if not writer.has_section(section):
					writer.add_section(section)
				writer.set(section, p[dotpos+1:], Config.properties[p])
		try:
			with open(Config.CONFIG_FILE_PATH, 'w') as configfile:
				writer.write(configfile)
		except Exception as e:
			print("*** FAILED to save config!", e)
			# TODO: Raise exception here or use return code to show failure?
