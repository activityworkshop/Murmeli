'''Class for a gui-less, robot relay system.
   The configuration of this system should be done separately by setup_murmeli.'''

from murmeli.system import System
from murmeli.config import Config
from murmeli.i18n import I18nManager
from murmeli.torclient import TorClient
from murmeli.supersimpledb import MurmeliDb


class Robot:
    '''The robot has a system which contains all the components it needs.'''

    def __init__(self):
        '''Constructor'''
        self.system = System()

    def start(self):
        '''Start up the system and start listening'''
        # Load config from ~/.murmeli
        config = Config(self.system)
        config.load()
        i18n = I18nManager(self.system)
        i18n.set_language()
        # Check owner id
        robot_owner_keyid = config.get_property(config.KEY_ROBOT_OWNER_KEY)
        if not robot_owner_keyid:
            print("Robot's owner not specified, please run the setup")
            self.stop()
            return
        # Instantiate database using specified directory
        database = MurmeliDb(self.system, config.get_ss_database_file())
        # Get own torid, keyid from own profile, print it out to check
        own_profile = database.get_profile()
        print("Own profile:", own_profile)
        if not own_profile:
            print("Own profile not found in database, please run the setup")
            self.stop()
            return

        print("Own torid: '%s', own keyid: '%s'" % (own_profile['torid'], own_profile['keyid']))
        print("Owner's keyid: '%s'" % robot_owner_keyid)

        # TODO: Instantiate crypto using config.get_keyring_dir

        tor_client = TorClient(self.system, config.get_tor_dir(),
                               config.get_property(config.KEY_TOR_EXE))
        # TODO: Add empty message handler
        self.system.start()

    def stop(self):
        '''Stop the whole system'''
        self.system.stop()
