'''Command-line tools to setup the murmeli system.
   Without dependencies to Qt, it could also be used to
   setup a robot system on a screenless pi, for example.'''

import os
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
        from PyQt4 import QtCore as QtCore4
        print("Found PyQt4, using Qt:", QtCore4.QT_VERSION_STR)
        found_qt = True
    except ImportError:
        pass
    # Check Qt4
    if not found_qt:
        try:
            from PyQt5 import QtCore as QtCore5
            print("Found PyQt5, using Qt:", QtCore5.QT_VERSION_STR)
            found_qt = True
        except ImportError:
            print("Didn't find either PyQt4 or PyQt5.  No gui will be possible.")

    # TODO: Check tor

def check_config(system):
    '''Look for a config file, and load it if possible'''
    conf = Config(system)
    conf.load()
    system.invoke_call(System.COMPNAME_I18N, "set_language")
    print(make_heading(system, "startupwizard.title"))
    # Select which language to use
    selected_language = ask_question(system, "setup.language", ["setup.lang.en", "setup.lang.de"])
    check_abort(selected_language, system)
    lang = "de" if selected_language == "2" else "en"
    conf.set_property(conf.KEY_LANGUAGE, lang)
    system.invoke_call(System.COMPNAME_I18N, "set_language")
    print(get_text(system, "setup.languageselected"))
    if not conf.from_file:
        conf.save()
        print(get_text(system, "setup.configsaved"))


def check_keyring(system):
    '''Given the data directory, is there a keyring and are there keys in it?'''
    crypto = CryptoClient(system)
    gpg_version = None
    while not gpg_version:
        gpg_version = crypto.get_gpg_version()
        if gpg_version:
            print(get_text(system, "setup.foundgpgversion") % gpg_version)
        else:
            print(get_text(system, "setup.entergpgpath"))
            gpg_path = input("? ")
            if gpg_path in ["", "q"]:
                check_abort("q", system)
            system.invoke_call(System.COMPNAME_CONFIG, "set_property",
                               key=Config.KEY_GPG_EXE, value=gpg_path)
    print(get_text(system, "setup.foundkeyring" if crypto.found_keyring() else "setup.nokeyring"))
    print(get_text(system, "setup.foundkeys") % (crypto.get_num_keys(private_keys=True),
                                                 crypto.get_num_keys(public_keys=True)))
    if crypto.get_num_keys(private_keys=True) < 1:
        gen_pair = ask_question(system, "setup.genkeypair", ["setup.genkeypair.rsa"])
        check_abort(gen_pair, system)
        generate_keypair(crypto, system)

def generate_keypair(crypto, system):
    '''Generate a new private/public key pair using the given data'''
    key_name = None
    while not key_name:
        key_name = input(get_text(system, "setup.genkeypair.name") + ": ")
    key_email = input(get_text(system, "setup.genkeypair.email") + ": ")
    key_comment = input(get_text(system, "setup.genkeypair.comment") + ": ")
    # Pass these fields to gpg
    print(get_text(system, "setup.genkeypair.pleasewait"))
    result = crypto.generate_key_pair(key_name, key_email, key_comment)
    print(get_text(system, "setup.genkeypair.complete"))
    return result

def check_data_path(system):
    '''Check if the data path is configured and if it exists or not'''
    data_path = system.invoke_call(System.COMPNAME_CONFIG, "get_data_dir")
    if data_path:
        print(get_text(system, "setup.datadir"), ":", data_path)
    selected_data_path = None
    while not selected_data_path:
        selected_data_path = input(get_text(system, "setup.datadir") + "? ")
        if selected_data_path:
            data_path = selected_data_path
        else:
            selected_data_path = data_path
        if data_path:
            data_path = os.path.abspath(os.path.expanduser(data_path))
            if not os.path.exists(data_path):
                # Confirm before creation
                print(get_text(system, "setup.datadir"), ":", data_path)
                create_dir = ask_question(system, "setup.createdatadir",
                                          ["setup.createdir.create", "setup.createddir.cancel"])
                check_abort(create_dir, system)
                if create_dir == "2":
                    selected_data_path = None

    system.invoke_call(System.COMPNAME_CONFIG, "set_property",
                       key=Config.KEY_DATA_DIR, value=data_path)
    if not os.path.exists(data_path):
        print(get_text(system, "setup.datadir.creating"))
    os.makedirs(system.invoke_call(System.COMPNAME_CONFIG, "get_database_dir"), exist_ok=True)
    os.makedirs(system.invoke_call(System.COMPNAME_CONFIG, "get_web_cache_dir"), exist_ok=True)
    os.makedirs(system.invoke_call(System.COMPNAME_CONFIG, "get_keyring_dir"), exist_ok=True)
    os.makedirs(system.invoke_call(System.COMPNAME_CONFIG, "get_tor_dir"), exist_ok=True)


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

def check_abort(answer, system):
    '''Check the returned answer and abort if requested'''
    if answer == 'q':
        print(get_text(system, "setup.abort"))
        sys.exit(1)

def make_heading(system, key):
    '''Make a heading string for printing to the console'''
    title = get_text(system, key)
    return "\n".join(["", title, "-" * len(title)])

def get_text(system, key):
    '''Convenience methods for getting texts from the system's i18n'''
    return system.invoke_call(System.COMPNAME_I18N, "get_text", key=key)

if __name__ == "__main__":
    check_dependencies()
    SYSTEM = System()
    I18N = I18nManager(SYSTEM)
    check_config(SYSTEM)
    check_data_path(SYSTEM)
    # TODO: Define where tor is - do we want to insist on tor here?
    check_keyring(SYSTEM)
    # TODO: Select which keypair to use
    # TODO: Define robot parameters
    # Save config
    SYSTEM.invoke_call(System.COMPNAME_CONFIG, "save")
