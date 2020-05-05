'''Crypto utils for various crypto-related functions for Murmeli'''

import os.path

def export_public_key(key_id, data_path, crypto):
    '''Export the specified public key to a file in the given path'''
    if not key_id or not data_path or not crypto:
        return False
    keyfile_name = key_id + ".key"
    try:
        with open(os.path.join(data_path, keyfile_name), "w") as keyfile:
            keyfile.write(crypto.get_public_key(key_id=key_id))
        return True
    except OSError:
        return False
