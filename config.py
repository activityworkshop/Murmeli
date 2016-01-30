from PyQt4.QtCore import QObject, SIGNAL
import configparser
import os.path

# Class to emit changed signals
class ConfigTannoy(QObject):
	def __init__(self):
		QObject.__init__(self)
	def connectListener(self, sub):
		self.connect(self, SIGNAL("fireUpdated()"), sub.configUpdated)
	def shout(self):
		self.emit(SIGNAL("fireUpdated()"))

# Class to store application-wide config
class Config():
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
	# paths
	KEY_DATA_DIR = "path.data"
	KEY_MONGO_EXE = "path.mongoexe"
	KEY_TOR_EXE = "path.torexe"


	@staticmethod
	def foundConfigFile():
		"""Return True if the config file was found and is readable, False otherwise"""
		try:
			with open(Config.CONFIG_FILE_PATH, 'r') as conffile:
				return True
		except: return False

	@staticmethod
	def load():
		if not Config.tannoy:
			Config.tannoy = ConfigTannoy()
		# Clear properties, and set default values
		Config.properties = {}
		Config.properties[Config.KEY_LANGUAGE]  = "en"
		Config.properties[Config.KEY_MONGO_EXE] = "mongo"
		Config.properties[Config.KEY_TOR_EXE]   = "tor"

		# Locate file in home directory, and load it if found
		try:
			parser = configparser.RawConfigParser()
			parser.read(os.path.expanduser(Config.CONFIG_FILE_PATH))
			for sec in parser.sections():
				for opt in parser.options(sec):
					Config.properties[sec + '.' + opt] = parser.get(sec, opt)
		except configparser.MissingSectionHeaderError: pass

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
		for p in list(Config.properties.keys()):
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

