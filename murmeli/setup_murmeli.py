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
from murmeli.torclient import TorClient


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
    key_email = input(get_text(system, "setup.genkeypair.email") + ": ") or "no@email.com"
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


def check_tor(system):
    '''Try to start tor, and get the tor id if possible'''
    print(get_text(system, "setup.entertorpath"))
    tor_path = input("? ") or "tor"
    # Save tor path in config
    system.invoke_call(System.COMPNAME_CONFIG, "set_property",
                       key=Config.KEY_TOR_EXE, value=tor_path)
    tor_dir = system.invoke_call(System.COMPNAME_CONFIG, "get_tor_dir")
    tor_client = TorClient(None, tor_dir, tor_path)
    started, torid = tor_client.ignite_to_get_tor_id()
    if not started and not torid:
        print(get_text(system, "setup.startingtorfailed"))
    elif torid:
        print(get_text(system, "setup.foundtorid") % torid)


def select_keypair(system):
    '''If there is more than one keypair, select which one to use'''
    num_private_keys = system.invoke_call(System.COMPNAME_CRYPTO, "get_num_keys",
                                          private_keys=True)
    if num_private_keys < 1:
        print("The keyring has no private keys, wasn't one already generated?")
    elif num_private_keys > 1:
        private_keys = system.invoke_call(System.COMPNAME_CRYPTO, "get_keys", private_keys=True)
        answers = []
        for key in private_keys:
            name = key['uids']
            name = str(name[0]) if isinstance(name, list) else name
            answers.append("%s (%s)" % (key['keyid'], name))
        key_index = ask_question_raw(system, get_text(system, "setup.selectprivatekey"), answers)
        check_abort(key_index, system)
        return private_keys[int(key_index) - 1].get('keyid')

def select_robot_status(system, private_keyid):
    '''Specify whether we're setting up a robot system or a real system'''
    system_type = ask_question(system, "setup.realorrobot",
                               ["setup.system.real", "setup.system.robot"])
    check_abort(system_type, system)
    # print("Selected system type:", system_type)
    data_path = system.invoke_call(System.COMPNAME_CONFIG, "get_data_dir")
    if system_type == "1":
        # Check whether to export the public key or not
        export_index = ask_question(system, "setup.exportpublickey", ["setup.no", "setup.yes"])
        check_abort(export_index, system)
        if export_index == "2":
            keyfile_name = private_keyid + ".key"
            with open(os.path.join(data_path, keyfile_name), "w") as keyfile:
                keyfile.write(system.invoke_call(System.COMPNAME_CRYPTO, "get_public_key",
                                                 key_id=private_keyid))
            print(get_text(system, "setup.publickeyexported") % keyfile_name)

    elif system_type == "2":
        print("Need to select (or load) a public key for the owner")
        while True:
            # Collect the public keys from keyring, but not own one
            public_keys = system.invoke_call(System.COMPNAME_CRYPTO, "get_keys",
                                             public_keys=True)
            public_keys = [key for key in public_keys if key['keyid'] != private_keyid]
            print("Keyring has %d public keys: %s" % (len(public_keys), public_keys))
            # Also find any .key files in data directory
            keyfiles = [file for file in os.listdir(data_path) if file.endswith(".key")
                        and os.path.isfile(os.path.join(data_path, file))]
            # Assemble list of available public keys
            key_list = ["%s (%s)" % (key['keyid'], key['uids'][0]) for key in public_keys] + \
                       [os.path.basename(file) for file in keyfiles] + \
                       [get_text(system, "setup.refreshkeylist")]
            files_to_load = [None for _ in public_keys] + keyfiles
            print(key_list, files_to_load)
            # Ask question which one to take (& mention that keys can be copied to datadir)
            owner_key = ask_question_raw(system, get_text(system, "setup.selectrobotownerkey"), key_list)
            check_abort(owner_key, system)
            refresh_index = len(key_list)
            if owner_key != str(refresh_index):
                key_index = int(owner_key) - 1
                file_to_load = files_to_load[key_index]
                if file_to_load:
                    # Selected key is in a file to load, so import into the keyring
                    with open(os.path.join(data_path, file_to_load), "r") as keyfile:
                        key = "".join(keyfile.readlines())
                        return system.invoke_call(System.COMPNAME_CRYPTO, "import_public_key", key)
                return public_keys[key_index]['keyid']


def ask_question(system, question_key, answer_keys):
    '''Use the console to ask the user a question and collect the answer, using token keys'''
    return ask_question_raw(system, get_text(system, question_key),
                            [get_text(system, key) for key in answer_keys])

def ask_question_raw(system, question_text, answer_texts):
    '''Use the console to ask the user a question and collect the answer, using strings'''
    # Loop until a valid answer is given
    while True:
        try:
            print("\n" + question_text, get_text(system, "setup.qtoquit"))
            allowed_answers = ["q"]
            for index, txt in enumerate(answer_texts):
                print("%d : %s" % (index + 1, txt))
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
    text = system.invoke_call(System.COMPNAME_I18N, "get_text", key=key)
    return text.replace("\\n", "\n") if text else ""

if __name__ == "__main__":
    check_dependencies()
    SYSTEM = System()
    I18N = I18nManager(SYSTEM)
    check_config(SYSTEM)
    check_data_path(SYSTEM)
    check_tor(SYSTEM)
    check_keyring(SYSTEM)
    # Select which keypair to use
    PRIVATE_KEYID = select_keypair(SYSTEM)
    print("Selected key '%s'" % PRIVATE_KEYID)
    # Define robot parameters
    OWNER_ID = select_robot_status(SYSTEM, PRIVATE_KEYID)
    print("Owner id '%s'" % OWNER_ID)
    # TODO: Setup database (using ssdb?) and store private key, owner key
    # Save config
    SYSTEM.invoke_call(System.COMPNAME_CONFIG, "save")

