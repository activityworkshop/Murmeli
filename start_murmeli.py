'''Start script for Murmeli
   Copyright activityworkshop.net and released under the GPL v2.'''

import os
import sys
import pkg_resources as pkgs

try:
    from PyQt5 import QtCore
    from PyQt5.QtWidgets import QApplication
except ImportError:
    print("ERROR: Can't find PyQt.  Please install both Qt and PyQt.")
    print("       On linux you may be able to install a package called 'python3-pyqt5'")
    print("       together with the package 'python3-pyqt5.qtwebengine'.")
    print("       If you don't need a gui, you can run setup_murmeli for a headless system.")
from murmeli.system import System
from murmeli.config import Config
from murmeli.i18n import I18nManager
from murmeli.supersimpledb import MurmeliDb
from murmeli.mainwindow import MainWindow
from murmeli.startupwizard import StartupWizard


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

    # Check Qt5
    try:
        print("Found PyQt5, using Qt:", QtCore.QT_VERSION_STR)
    except TypeError:
        print("Cannot find version of PyQt5")
        return False
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
        system.add_component(database)
        own_profile = None
        try:
            own_profile = database.get_profile()
            if own_profile and own_profile.get("keyid", None):
                print("I got a profile and keyid: '%s' so I can start Murmeli"
                      % own_profile.get("keyid", ""))
        except Exception as exc:
            print("Exception thrown trying to get profile, so I can't start Murmeli:", exc)
        if own_profile:
            return True
        else:
            # Close database, ready for the startup wizard
            system.remove_component(System.COMPNAME_DATABASE)
            database = None
    return False


def launch_gui(system):
    '''Launch either the startup wizard or the real gui'''
    win = None
    # Now start either the wizard or the main gui
    if check_profile(system):
        # Skip wizard, launch actual GUI (and pass half-built system)
        print("Launch real GUI")
        win = MainWindow(system)
    else:
        # launch wizard (and pass half-built system)
        print("Can't launch gui, launch startup wizard instead")
        win = StartupWizard(system)
    return win


if __name__ == "__main__":
    if check_dependencies():
        SYSTEM = create_system()
        APP = QApplication([])
        WIN = launch_gui(SYSTEM)
        if WIN:
            WIN.show()
            APP.exec_()
            # Window has closed, stop the system
            WIN.finish()
