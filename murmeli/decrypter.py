'''Module for the tor client'''

from murmeli.message import Message
from murmeli.cryptoclient import CryptoError


class DecrypterShim:
    '''Adapter class to provide messages with a decrypter object'''

    def __init__(self, crypto):
        self.crypto = crypto

    def decrypt(self, enc_data, enc_type):
        '''Decrypt the given encrypted data, return 2-tuple of data and sender keyid'''
        if enc_type == Message.ENCTYPE_NONE:
            return (enc_data, None)
        if enc_type == Message.ENCTYPE_ASYM:
            assert self.crypto
            return self.crypto.decrypt_and_check_signature(message=enc_data)
        if enc_type == Message.ENCTYPE_RELAY:
            assert self.crypto
            return self.crypto.verify_signed_data(message=enc_data)
        # Unsupported encryption type
        raise CryptoError()
