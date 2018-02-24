'''Configuration module, including loading and saving to file'''

import configparser
import os.path
from murmeli.system import System, Component


class Config(Component):
    '''Class to store application-wide config'''
    # Fixed location of config file
    CONFIG_FILE_PATH = os.path.expanduser("~/.murmeli")
    # Fixed location of config file
    DEFAULT_DATA_PATH = os.path.expanduser("~/murmeli")
    # keys
    KEY_LANGUAGE = "gui.language"
    KEY_LET_FRIENDS_SEE_FRIENDS = "privacy.friendsseefriends"
    KEY_ALLOW_FRIEND_REQUESTS = "privacy.allowfriendrequests"
    KEY_SHOW_LOG_WINDOW = "gui.showlogwindow"
    # paths
    KEY_DATA_DIR = "path.data"
    KEY_TOR_EXE = "path.torexe"
    KEY_GPG_EXE = "path.gpgexe"


    def __init__(self, parent):
        Component.__init__(self, parent, System.COMPNAME_CONFIG)
        self.properties = {}

    @staticmethod
    def found_config_file():
        '''Return True if the config file was found and is readable, False otherwise'''
        try:
            with open(Config.CONFIG_FILE_PATH, 'r'):
                return True
        except OSError: # file not found, or can't be read
            return False

    def start(self):
        '''Start the component'''
        self.load()

    def load(self):
        '''Load the configuration from file'''
        # Clear properties, and set default values
        self.properties = {}
        self.properties[Config.KEY_LANGUAGE] = "en"
        self.properties[Config.KEY_TOR_EXE] = "tor"
        self.properties[Config.KEY_GPG_EXE] = "gpg"
        # Default privacy settings
        self.properties[Config.KEY_LET_FRIENDS_SEE_FRIENDS] = True
        self.properties[Config.KEY_ALLOW_FRIEND_REQUESTS] = True
        # Default gui settings
        self.properties[Config.KEY_SHOW_LOG_WINDOW] = False

        # Locate file in home directory, and load it if found
        try:
            parser = configparser.RawConfigParser()
            parser.read(os.path.expanduser(Config.CONFIG_FILE_PATH))
            for sec in parser.sections():
                for opt in parser.options(sec):
                    self.properties[sec + '.' + opt] = parser.get(sec, opt)
        except configparser.MissingSectionHeaderError:
            pass
        # Convert strings to True/False
        self._fix_boolean_property(Config.KEY_LET_FRIENDS_SEE_FRIENDS)
        self._fix_boolean_property(Config.KEY_ALLOW_FRIEND_REQUESTS)
        self._fix_boolean_property(Config.KEY_SHOW_LOG_WINDOW)

    def _fix_boolean_property(self, prop_name):
        '''Helper method to fix the loading of string values representing booleans'''
        value = self.get_property(prop_name)
        if value and isinstance(value, str):
            self.properties[prop_name] = (value == "True")

    def get_property(self, key):
        '''Get the value of the specified property'''
        return self.properties.get(key, None)

    def set_property(self, key, value):
        '''Set the value of the specified property and broadcast the change'''
        self.properties[key] = value
        # Config.tannoy.shout()

    def get_database_dir(self):
        '''Get the database directory'''
        return os.path.join(self.properties.get(Config.KEY_DATA_DIR, ""), "db")

    def get_ss_database_file(self):
        '''Get the database file'''
        return os.path.join(self.get_database_dir(), "murmeli.ssdb")

    def get_web_cache_dir(self):
        '''Get the directory of the web cache'''
        return os.path.join(self.properties.get(Config.KEY_DATA_DIR, ""), "cache")

    def get_keyring_dir(self):
        '''Get the directory of the keyring'''
        return os.path.join(self.properties.get(Config.KEY_DATA_DIR, ""), "keyring")

    def get_tor_dir(self):
        '''Get the directory for the tor configuration'''
        return os.path.join(self.properties.get(Config.KEY_DATA_DIR, ""), "tor")

    def register_subscriber(self, sub):
        '''Add the given subscriber to the list of objects to be informed about changes'''
        # Config.tannoy.connectListener(sub)
        pass

    def stop(self):
        '''Stop the component'''
        self.save()

    def save(self):
        '''Save the config to file'''
        writer = configparser.RawConfigParser()
        for prop in self.properties:
            dotpos = prop.find('.')
            if dotpos > 0:
                section = prop[0:dotpos]
                if not writer.has_section(section):
                    writer.add_section(section)
                writer.set(section, prop[dotpos+1:], self.properties[prop])
        try:
            with open(Config.CONFIG_FILE_PATH, 'w') as configfile:
                writer.write(configfile)
        except OSError as exc:
            print("*** FAILED to save config!", exc)
            # TODO: Raise exception here or use return code to show failure?
            raise
