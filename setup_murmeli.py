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
from murmeli.supersimpledb import MurmeliDb


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
    except pkgs.ResolutionError:
        print("Could not find GnuPG version")


def check_config(system):
    '''Look for a config file, and load it if possible'''
    conf = Config(system)
    system.add_component(conf)
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
    system.add_component(crypto)
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
    return torid


def select_keypair(system):
    '''If there is more than one keypair, select which one to use'''
    num_private_keys = system.invoke_call(System.COMPNAME_CRYPTO, "get_num_keys",
                                          private_keys=True)
    if num_private_keys < 1:
        print("The keyring has no private keys, wasn't one already generated?")
        return None

    private_keys = system.invoke_call(System.COMPNAME_CRYPTO, "get_keys", private_keys=True)
    key_index = "1"
    if num_private_keys > 1:
        # Need to choose which key to use
        answers = []
        for key in private_keys:
            name = key['uids']
            name = str(name[0]) if isinstance(name, list) else name
            answers.append("%s (%s)" % (key['keyid'], name))
        question = get_text(system, "setup.selectprivatekey")
        key_index = ask_question_raw(system, question, answers)
        check_abort(key_index, system)
    return private_keys[int(key_index) - 1].get('keyid')


def select_robot_status(system, private_keyid):
    '''Specify whether we're setting up a robot system or a real system'''
    system_type = ask_question(system, "setup.realorrobot",
                               ["setup.system.real", "setup.system.robot", "setup.system.parrot"])
    check_abort(system_type, system)
    # print("Selected system type:", system_type)
    data_path = system.invoke_call(System.COMPNAME_CONFIG, "get_data_dir")
    if system_type == "1":
        # Real system, not a robot
        system.invoke_call(System.COMPNAME_CONFIG, "set_property",
                           key=Config.KEY_ROBOT_OWNER_KEY, value="")
        # Check whether to export the public key or not
        export_index = ask_question(system, "setup.exportpublickey", ["setup.no", "setup.yes"])
        check_abort(export_index, system)
        if export_index == "2":
            keyfile_name = private_keyid + ".key"
            with open(os.path.join(data_path, keyfile_name), "w") as keyfile:
                keyfile.write(system.invoke_call(System.COMPNAME_CRYPTO, "get_public_key",
                                                 key_id=private_keyid))
            print(get_text(system, "setup.publickeyexported") % keyfile_name)

    elif system_type in ["2", "3"]:
        own_name = "Parrot" if system_type == "3" else "Robot"
        return (setup_robot_system(system, data_path, private_keyid), own_name)
    return (None, None)


def setup_robot_system(system, data_path, private_keyid):
    '''Choose which key to use for the robot system's owner and save this choice'''
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
        owner_key = ask_question_raw(system, get_text(system, "setup.selectrobotownerkey"),
                                     key_list)
        check_abort(owner_key, system)
        refresh_index = len(key_list)
        if owner_key != str(refresh_index):
            key_index = int(owner_key) - 1
            file_to_load = files_to_load[key_index]
            if file_to_load:
                # Selected key is in a file to load, so import into the keyring
                with open(os.path.join(data_path, file_to_load), "r") as keyfile:
                    key = "".join(keyfile.readlines())
                    key_id = system.invoke_call(System.COMPNAME_CRYPTO,
                                                "import_public_key", strkey=key)
            else:
                key_id = public_keys[key_index]['keyid']
            # Store owner key id in config
            system.invoke_call(System.COMPNAME_CONFIG, "set_property",
                               key=Config.KEY_ROBOT_OWNER_KEY, value=key_id)
            return key_id

def setup_database(system, torid, private_keyid, own_name=None):
    '''Setup database and store private key'''
    print("Storing database: tor id='%s', key id='%s'" % (torid, private_keyid))
    name = (own_name + torid[:12]) if own_name else torid
    db_filename = system.invoke_call(System.COMPNAME_CONFIG, "get_ss_database_file")
    ssdb = MurmeliDb(None, db_filename)
    ssdb.add_or_update_profile({"torid":torid, "keyid":private_keyid, "status":"self",
                                "ownprofile":True, "name":name})
    ssdb.save_to_file()

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

def setup_murmeli():
    '''Run through all the checks and setup the config, keyring and database'''
    check_dependencies()
    system = System()
    i18n = I18nManager(system)
    system.add_component(i18n)
    check_config(system)
    check_data_path(system)
    tor_id = check_tor(system)
    check_abort(tor_id or 'q', system)
    check_keyring(system)
    # Select which keypair to use
    private_keyid = select_keypair(system)
    if not private_keyid:
        print("ERROR: Failed to generate keypair.  Aborting.")
        return
    print("Selected key '%s'" % private_keyid)
    # Define robot parameters
    owner_keyid, own_name = select_robot_status(system, private_keyid)
    print("Owner keyid '%s'" % owner_keyid)
    # Setup database and store private key
    setup_database(system, tor_id, private_keyid, own_name)
    # Save config
    system.invoke_call(System.COMPNAME_CONFIG, "save")


if __name__ == "__main__":
    setup_murmeli()
