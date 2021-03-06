'''Class for a gui-less, robot relay system.
   The configuration of this system should be done separately by setup_murmeli.'''

from murmeli.system import System
from murmeli.config import Config
from murmeli.i18n import I18nManager
from murmeli.torclient import TorClient
from murmeli.cryptoclient import CryptoClient
from murmeli.supersimpledb import MurmeliDb
from murmeli.messagehandler import RobotMessageHandler, ParrotMessageHandler
from murmeli.postservice import PostService
try:
    from murmeli.scrollbot import ScrollbotGuiNotifier as RobotNotifier
except ImportError:
    from murmeli.guinotification import DefaultGuiNotifier as RobotNotifier


class Robot:
    '''The robot has a system which contains all the components it needs.'''

    def __init__(self, system):
        '''Constructor'''
        self.system = system or System()

    def start(self, parrot_mode=False):
        '''Start up the system and start listening'''
        # Load config if not already there
        if not self.system.has_component(System.COMPNAME_CONFIG):
            new_config = Config(self.system)
            self.system.add_component(new_config)
        config = self.system.get_component(System.COMPNAME_CONFIG)
        if not self.system.has_component(System.COMPNAME_I18N):
            i18n = I18nManager(self.system)
            self.system.add_component(i18n)
        # Check owner id
        robot_owner_keyid = config.get_property(config.KEY_ROBOT_OWNER_KEY)
        if not robot_owner_keyid:
            print("Robot's owner not specified, please run the setup")
            self.stop()
            return
        # Instantiate database if not already there
        if not self.system.has_component(System.COMPNAME_DATABASE):
            new_database = MurmeliDb(self.system, config.get_ss_database_file())
            self.system.add_component(new_database)
        # Get own torid, keyid from own profile, print it out to check
        database = self.system.get_component(System.COMPNAME_DATABASE)
        own_profile = database.get_profile()
        print("Own profile:", own_profile)
        if not own_profile:
            print("Own profile not found in database, please run setup_murmeli")
            self.stop()
            return

        print("Own torid: '%s', own keyid: '%s'" % (own_profile['torid'], own_profile['keyid']))
        print("Owner's keyid: '%s'" % robot_owner_keyid)

        # Instantiate crypto if necessary
        if not self.system.has_component(System.COMPNAME_CRYPTO):
            new_crypto = CryptoClient(self.system, config.get_keyring_dir())
            self.system.add_component(new_crypto)
        if not self.system.invoke_call(System.COMPNAME_CRYPTO, "check_gpg"):
            print("Crypto couldn't be initialised, please run the setup_murmeli")
            self.stop()
            return
        # Add a tor service if not already present
        if not self.system.has_component(System.COMPNAME_TRANSPORT):
            tor_client = TorClient(self.system, config.get_tor_dir(),
                                   config.get_property(config.KEY_TOR_EXE))
            self.system.add_component(tor_client)
        # Add a message handler if not already present
        self._add_message_handler(parrot_mode)
        # Add post service
        if not self.system.has_component(System.COMPNAME_POSTSERVICE):
            post = PostService(self.system)
            post.should_broadcast = False
            self.system.add_component(post)
        # Add gui notifier
        self.system.remove_component(System.COMPNAME_GUI)
        notifier = RobotNotifier(self.system)
        self.system.add_component(notifier)
        # Use config to activate current language
        self.system.invoke_call(System.COMPNAME_I18N, "set_language")

    def _add_message_handler(self, parrot_mode):
        '''Add the correct kind of message handler to the system'''
        if not self.system.has_component(System.COMPNAME_MSG_HANDLER):
            if parrot_mode:
                msg_handler = ParrotMessageHandler(self.system)
            else:
                msg_handler = RobotMessageHandler(self.system)
            self.system.add_component(msg_handler)

    def stop(self):
        '''Stop the whole system'''
        self.system.stop()
