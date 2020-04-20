'''Manual check (not a discoverable unit test) for the key import,
   to identify problems with gnupg, gpg, gpg1, gpg2 and so on'''

import os
import shutil
from gnupg import GPG

def setup_keyring(keyring_name):
    '''Setup the keyring'''
    keyring_path = os.path.join("test", "outputdata", keyring_name)
    # Delete the entire keyring
    shutil.rmtree(keyring_path, ignore_errors=True)
    os.makedirs(keyring_path)
    gpg = GPG(gnupghome=keyring_path, gpgbinary="gpg")
    for key_name in ["key1_private", "key1_public"]:
        with open(os.path.join("test", "inputdata", key_name + ".txt"), "r") as keyfile:
            key_str = "".join(keyfile.readlines())
        import_result = gpg.import_keys(key_str)
        print("Import result:", type(import_result))
        print(import_result.__dict__)
        if import_result.count == 1 and len(set(import_result.fingerprints)) == 1:
            print("Got one import result")
    return gpg

CRYPTO = setup_keyring("keyringtest")
if CRYPTO:
    print("Ready", CRYPTO)
KEY_LIST = CRYPTO.list_keys(False)
NUM_KEYS = len(KEY_LIST) if KEY_LIST else 0
print("Number of public keys:", NUM_KEYS)
if NUM_KEYS < 1:
    print("ERROR: Number of keys should be 1, not", NUM_KEYS)
KEY_LIST = CRYPTO.list_keys(True)
NUM_KEYS = len(KEY_LIST) if KEY_LIST else 0
print("Number of private keys:", NUM_KEYS)
if NUM_KEYS < 1:
    print("ERROR: Number of keys should be 1, not", NUM_KEYS)
