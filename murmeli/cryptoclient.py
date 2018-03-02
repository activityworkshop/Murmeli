'''Crypto client for Murmeli

   Only classes inside this file should care about encryption / decryption details
   (except maybe the startup wizard which can check for python-gnupg availability)
   Here we use GPG for key management, en/decryption, signatures etc but this is the
   only place where that implementation detail is necessary.'''

import os.path
from random import SystemRandom
from gnupg import GPG
from murmeli.system import Component, System
from murmeli.config import Config


class CryptoError(Exception):
    '''Exception if something went wrong with encryption'''
    pass


class CryptoClient(Component):
    '''The CryptoClient is the only class you need to reference for the crypto functions.'''

    # Constant string used for wrapping signed data
    SIGNATURE_WRAP_TEXT = ":murmeli:".encode("utf-8")

    def __init__(self, parent, keyring_path):
        Component.__init__(self, parent, System.COMPNAME_CRYPTO)
        self.randgen = SystemRandom()
        self.keyring_path = keyring_path
        self.gpg = None


    def check_gpg(self):
        '''Return whether the GPG object could be initialised or not'''
        self.gpg = None
        self.init_gpg()
        return self.gpg is not None

    def init_gpg(self):
        '''init the _gpg object if it's not been done yet'''
        if not self.gpg:
            if self.keyring_path and os.path.exists(self.keyring_path):
                print("keyring exists at:", self.keyring_path)
                try:
                    gpgexe = self.call_component(System.COMPNAME_CONFIG, "get_property",
                                                 key=Config.KEY_GPG_EXE) or "gpg"
                    self.gpg = GPG(gnupghome=self.keyring_path, gpgbinary=gpgexe)
                except Exception as exc:
                    print("exception thrown:", exc)
                    self.gpg = None

    def get_private_keys(self):
        '''Return a list of private keys'''
        self.init_gpg()
        if self.gpg:
            return self.gpg.list_keys(True) # True for just the private keys

    def get_num_public_keys(self):
        '''Get the number of public keys - only used for testing'''
        self.init_gpg()
        if self.gpg:
            return len(self.gpg.list_keys(False)) # False for just the public keys
        return 0

    def get_public_key(self, key_id):
        '''Get a public key as ascii, either ours or another one'''
        self.init_gpg()
        if self.gpg:
            return str(self.gpg.export_keys(key_id))

    def generate_key_pair(self, name, email, comment):
        '''Create a new asymmetric keypair with the given information (slow)'''
        self.init_gpg()
        #print "GPG client will generate a keypair for %s, %s, %s." % (name, email, comment)
        inputdata = self.gpg.gen_key_input(key_type="RSA", key_length=4096, \
            name_real=name, name_email=email, name_comment=comment)
        return self.gpg.gen_key(inputdata)

    def import_public_key(self, strkey):
        '''If the given string holds a key, then add it to the keyring and return the keyid
           Otherwise, return None.
           Used to import public keys from contacts, but also used for private keys by tests'''
        if strkey and isinstance(strkey, str):
            self.init_gpg()
            res = self.gpg.import_keys(strkey)
            if res.count == 1 and len(set(res.fingerprints)) == 1:
                # import was successful, we've now added one key
                # gpg returns fingerprint but we need the key id
                fingerprint = res.fingerprints[0]
                if fingerprint:
                    for key in self.gpg.list_keys():
                        if key.get("fingerprint", "") == fingerprint:
                            return key.get("keyid", None)
        # import failed somehow, or fingerprint not found
        return None

    def get_fingerprint(self, key_id):
        '''Get the fingerprint of the key with the given key_id, returns a 40-character string'''
        if key_id:
            self.init_gpg()
            for key in self.gpg.list_keys():
                if key.get("keyid", "") == key_id:
                    return key.get("fingerprint", None)


    ########## Asymmetric encryption ##############

    def encrypt_and_sign(self, message, recipient, own_key):
        '''Encrypt the given message for the given recipient, signing it with own_key'''
        if not recipient:
            print("Can't encryptAndSign without a recipient!")
            raise CryptoError()
        if not own_key:
            print("Can't encryptAndSign without an own key!")
            raise CryptoError()
        print("EncryptAndSign: ownKey:", own_key, ", recpt:", recipient)
        self.init_gpg()
        # TODO: Check that message is a Message, don't allow other encryptions?
        #  (but that would mean tight coupling to message module)
        # Try to encrypt and sign, throw exception if it didn't work
        crypto_result = self.gpg.encrypt(message, recipients=recipient,
                                         sign=own_key, armor=False, always_trust=True)
        if not crypto_result.ok:
            print("Tried to encryptAndSign but it gave back notok:", crypto_result.__dict__)
            raise CryptoError()
        return crypto_result.data

    def decrypt_and_check_signature(self, message):
        '''Returns the decrypted contents if possible, and the signing key_id if recognised,
           otherwise the tuple (None, None)'''
        self.init_gpg()
        crypto_result = self.gpg.decrypt(message)
        # If the signature can't be checked, then crypto_result.valid will be False
        # - this is ok for a ContactResponse but not for any other kind of message
        print("Decrypt and check: ok is ", crypto_result.ok, " and valid is ",
              crypto_result.valid, " and keyid is", crypto_result.key_id)
        if crypto_result.ok:
            return (crypto_result.data, crypto_result.key_id if crypto_result.valid else None)
        return (None, None)


    ########## Signing data without encryption ##############

    def sign_data(self, message, own_key):
        '''Wrap the given message (given as bytearray or bytes) and sign it with the given key'''
        self.init_gpg()
        data_to_sign = CryptoClient.SIGNATURE_WRAP_TEXT + bytes(message) \
            + CryptoClient.SIGNATURE_WRAP_TEXT
        return self.gpg.sign(data_to_sign, keyid=own_key).data

    def verify_signed_data(self, message):
        '''Return the data which was signed, and the signing keyid if the signature is valid'''
        self.init_gpg()
        result = self.gpg.verify(message)
        if result.valid:
            marker1 = message.find(CryptoClient.SIGNATURE_WRAP_TEXT)
            marker2 = message.rfind(CryptoClient.SIGNATURE_WRAP_TEXT)
            if marker1 > 0 and marker2 > marker1:
                actual_data = message[marker1 + len(CryptoClient.SIGNATURE_WRAP_TEXT) : marker2]
                return (actual_data, result.key_id)
        return (None, None)
