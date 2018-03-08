'''Command-line tools to setup the murmeli system.
   Without dependencies to Qt, it could also be used to
   setup a robot system on a screenless pi, for example.'''

import sys
import pkg_resources as pkgs
from murmeli.system import System
from murmeli.config import Config
from murmeli.cryptoclient import CryptoClient
from murmeli.i18n import I18nManager


def check_dependencies():
    '''Check whether all required software is installed'''
    # Check python
    python_version = (sys.version_info.major, sys.version_info.minor,
                      sys.version_info.micro)
    print("Python verson: %d.%d.%d" % python_version)
    if python_version < (3, 4):
        print("Murmeli needs at least version 3.4 to run.  Ending.")
        sys.exit(1)

    # Try to import python-gnupg, just to see if it's there
    try:
        from gnupg import GPG
        if GPG.verify:
            print("Found GnuPG")
    except ImportError:
        print("Murmeli needs python-gnupg to run.  Ending.")
        sys.exit(1)
    try:
        print("Found GnuPG version: %s" % pkgs.get_distribution("python-gnupg").version)
    except Exception:
        print("Could not find GnuPG version")

    found_qt = False
    # Check Qt5
    try:
        from PyQt4 import QtCore
        print("Found PyQt4, using Qt:", QtCore.QT_VERSION_STR)
        found_qt = True
    except ImportError:
        pass
    # Check Qt4
    if not found_qt:
        try:
            from PyQt5 import QtCore
            print("Found PyQt5, using Qt:", QtCore.QT_VERSION_STR)
            found_qt = True
        except ImportError:
            print("Didn't find either PyQt4 or PyQt5.  No gui will be possible.")

    # TODO: Check tor

def check_config(system):
    '''Look for a config file, and load it if possible'''
    conf = Config(system)
    conf.load()
    system.invoke_call(System.COMPNAME_I18N, "set_language")
    if conf.from_file:
        print("Found existing config file")
    else:
        print("Found no config file, need to create one")
        # Select which language to use
        selected_language = ask_question(system, "setup.language", ["setup.lang.en", "setup.lang.de"])
        if selected_language == "q":
            print("Aborting setup")
            sys.exit(1)
        lang = "de" if selected_language == "2" else "en"
        conf.set_property(conf.KEY_LANGUAGE, lang)
        system.invoke_call(System.COMPNAME_I18N, "set_language")
        print(get_text(system, "setup.languageselected"))


def check_keyring(system):
    '''Given the data directory, is there a keyring and are there keys in it?'''
    crypto = CryptoClient(system)
    gpg_version = crypto.get_gpg_version()
    if gpg_version:
        print(get_text(system, "setup.foundgpgversion") % gpg_version)
    else:
        print(get_text(system, "setup.notfoundgpgversion"))
    print(get_text(system, "setup.foundkeyring" if crypto.found_keyring() else "setup.nokeyring"))
    print(get_text(system, "setup.foundkeys") % (crypto.get_num_keys(private_keys=True),
                                                 crypto.get_num_keys(public_keys=True)))

def ask_question(system, question_key, answer_keys):
    '''Use the console to ask the user a question and collect the answer'''
    # Loop until a valid answer is given
    while True:
        try:
            print("\n", get_text(system, question_key), get_text(system, "setup.qtoquit"))
            allowed_answers = ["q"]
            for index, key in enumerate(answer_keys):
                print("%d : %s" % (index + 1, get_text(system, key)))
                allowed_answers += str(index + 1)
            answer = input("? ")
            if answer in allowed_answers:
                return answer
        except KeyboardInterrupt:
            return "q"

def get_text(system, key):
    '''Convenience methods for getting texts from the system's i18n'''
    return system.invoke_call(System.COMPNAME_I18N, "get_text", key=key)

if __name__ == "__main__":
    check_dependencies()
    SYSTEM = System()
    I18N = I18nManager(SYSTEM)
    check_config(SYSTEM)
    check_keyring(SYSTEM)
