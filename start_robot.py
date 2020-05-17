'''Start script for Murmeli Robot
   Copyright activityworkshop.net and released under the GPL v2.'''

import os
import sys
import pkg_resources as pkgs

from murmeli.system import System
from murmeli.config import Config
from murmeli.i18n import I18nManager
from murmeli.supersimpledb import MurmeliDb
from murmeli.robot import Robot


def check_dependencies():
    '''Check whether all required software is installed'''
    # Check python
    python_version = (sys.version_info.major, sys.version_info.minor,
                      sys.version_info.micro)
    print("Python verson: %d.%d.%d" % python_version)
    if python_version < (3, 5):
        print("Murmeli needs at least version 3.5 to run.  Ending.")
        return False

    # Try to import python-gnupg, just to see if it's there
    try:
        from gnupg import GPG
        if GPG.verify:
            print("Found GnuPG")
    except ImportError:
        print("Murmeli needs python-gnupg to run.  Ending.")
        return False
    try:
        print("Found GnuPG version: %s" % pkgs.get_distribution("python-gnupg").version)
    except Exception:
        print("Could not find GnuPG version")

    # Everything ok
    return True


def create_system():
    '''Create the bare system and load the config'''
    system = System()
    i18n = I18nManager(system)
    system.add_component(i18n)
    config = Config(system)
    system.add_component(config)
    config.load()
    i18n.set_language()
    if config.from_file:
        return system
    return None


def check_profile(system):
    '''Given a bare system, check that the profile can be found'''
    if not system:
        return False
    db_file_path = system.invoke_call(System.COMPNAME_CONFIG, "get_ss_database_file")
    if os.path.exists(db_file_path):
        database = MurmeliDb(system, db_file_path)
        own_profile = None
        try:
            own_profile = database.get_profile()
            if own_profile and own_profile.get("keyid", None):
                print("I got a profile and keyid: '%s' so I can start Murmeli"
                      % own_profile.get("keyid", ""))
        except Exception as exc:
            print("Exception thrown trying to get profile, so I can't start Murmeli:", exc)
        if own_profile:
            # Success
            return True

        # Close database
        system.remove_component(System.COMPNAME_DATABASE)
    return False


def launch(system):
    '''Launch the robot'''
    if check_profile(system):
        # System looks ok, pass it to Robot
        print("Creating robot...")
        return Robot(system)
    # Need to run setup tool
    print("Can't launch robot, need to run setup_murmeli")
    return None


if __name__ == "__main__":
    if check_dependencies():
        SYSTEM = create_system()
        MY_ROBOT = launch(SYSTEM)
        if MY_ROBOT:
            USE_PARROT = len(sys.argv) == 2 and sys.argv[1] == "parrot"
            MY_ROBOT.start(parrot_mode=USE_PARROT)
            input("Press Enter to close Murmeli")
            MY_ROBOT.stop()
