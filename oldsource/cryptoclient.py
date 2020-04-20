'''Crypto client for Murmeli

   Only classes inside this file should care about encryption / decryption details
   (except maybe the startup wizard which can check for python-gnupg availability)
   Here we use GPG for key management, en/decryption, signatures etc but this is the
   only place where that implementation detail is necessary.'''

import os.path
from random import SystemRandom
from gnupg  import GPG
from config import Config

class CryptoError(Exception):
	'''Exception if something went wrong with encryption'''
	pass


class CryptoClient:
	'''The CryptoClient is the only class you need to reference when accessing the crypto functions.'''

	# Random number generator
	randgen = SystemRandom()
	# static variable to hold GPG object
	_gpg = None
	# True to use the test keyring instead of the regular one
	_useTestKeyring = False
	'''Constant string used for wrapping signed data '''
	SIGNATURE_WRAP_TEXT = ":murmeli:".encode("utf-8")


	@staticmethod
	def checkGpg():
		'''Return whether the GPG object could be initialised or not'''
		CryptoClient._gpg = None
		CryptoClient.initGpg()
		return CryptoClient._gpg is not None

	@staticmethod
	def useTestKeyring():
		'''Only call this method from unit tests, so that a different keyring is used'''
		CryptoClient._useTestKeyring = True
		CryptoClient._gpg = None

	@staticmethod
	def _getKeyringPath():
		'''Get the path to the keyring, depending on whether we're testing or not'''
		keyring = Config.getKeyringDir()
		if CryptoClient._useTestKeyring:
			keyring += "test"
		return keyring

	@staticmethod
	def initGpg():
		'''init the _gpg object if it's not been done yet'''
		if CryptoClient._gpg is None:
			# Get keyring path
			keyring = CryptoClient._getKeyringPath()
			if keyring is not None and os.path.exists(keyring):
				print("keyring exists at", keyring)
				try:
					gpgexe = Config.getProperty(Config.KEY_GPG_EXE)
					if not gpgexe:
						gpgexe = "gpg"
					CryptoClient._gpg = GPG(gnupghome=keyring, gpgbinary=gpgexe)
				except:
					print("exception thrown")
					CryptoClient._gpg = None

	@staticmethod
	def getPrivateKeys():
		CryptoClient.initGpg()
		if CryptoClient._gpg is not None:
			return CryptoClient._gpg.list_keys(True) # True for just the private keys

	@staticmethod
	def getPublicKeys():
		'''Get a list of public keys - only used for testing'''
		CryptoClient.initGpg()
		if CryptoClient._gpg is None:
			return []
		return CryptoClient._gpg.list_keys(False) # False for just the public keys

	# Get an Ascii version of a public key, either ours or another one
	@staticmethod
	def getPublicKey(keyId):
		CryptoClient.initGpg()
		if CryptoClient._gpg is None:
			return "notfound"
		return str(CryptoClient._gpg.export_keys(keyId))

	@staticmethod
	def generateKeyPair(name, email, comment):
		CryptoClient.initGpg()
		#print "GPG client will generate a keypair for %s, %s, %s." % (name, email, comment)
		inputdata = CryptoClient._gpg.gen_key_input(key_type="RSA", key_length=4096, \
			name_real=name, name_email=email, name_comment=comment)
		key = CryptoClient._gpg.gen_key(inputdata)
		return key

	@staticmethod
	def importPublicKey(strkey):
		'''If the given string holds a key, then add it to the keyring and return the keyid
		   Otherwise, return None.
		   Used to import public keys from contacts, but also used for private keys by tests'''
		if strkey:
			CryptoClient.initGpg()
			res = CryptoClient._gpg.import_keys(strkey)
			if res.count == 1 and len(set(res.fingerprints)) == 1:
				# import was successful, we've now added one key
				fingerprint = res.fingerprints[0]
				if fingerprint:
					for key in CryptoClient._gpg.list_keys():
						if key.get("fingerprint", "") == fingerprint:
							return key.get("keyid", None)
		return None

	@staticmethod
	def getFingerprint(keyId):
		'''Get the fingerprint of the key with the given keyId - returns a 40-character string'''
		if keyId:
			CryptoClient.initGpg()
			for key in CryptoClient._gpg.list_keys():
				if key.get("keyid", "") == keyId:
					return key.get("fingerprint", None)


	########## Asymmetric encryption ##############

	@staticmethod
	def encryptAndSign(message, recipient, ownkey):
		'''Encrypt the given message for the given recipient, signing it with ownKey'''
		if not recipient:
			print("Can't encryptAndSign without a recipient!")
			raise CryptoError()
		if not ownkey:
			print("Can't encryptAndSign without an own key!")
			raise CryptoError()
		CryptoClient.initGpg()
		# TODO: Check that message is a Message, don't allow other encryptions?
		# Try to encrypt and sign, throw exception if it didn't work
		cryptoResult = CryptoClient._gpg.encrypt(message, recipients=recipient,
			sign=ownkey, armor=False, always_trust=True)
		if not cryptoResult.ok:
			raise CryptoError()
		return cryptoResult.data

	@staticmethod
	def decryptAndCheckSignature(message):
		'''Returns the decrypted contents if possible, and the signing keyid if recognised,
		   otherwise None'''
		CryptoClient.initGpg()
		cryptoResult = CryptoClient._gpg.decrypt(message)
		# If the signature can't be checked, then cryptoResult.valid will be False
		# - this is ok for a ContactResponse but not for any other kind of message
		print("Decrypt and check: ok is ", cryptoResult.ok, " and valid is ",
			cryptoResult.valid, " and keyid is", cryptoResult.key_id)
		if cryptoResult.ok:
			return (cryptoResult.data, cryptoResult.key_id if cryptoResult.valid else None)
		return (None, None)

	########## Signing data without encryption ##############

	@staticmethod
	def signData(message, ownkey):
		'''Wrap the given message (given as bytearray or bytes) and sign it with the specified key'''
		CryptoClient.initGpg()
		dataToSign = CryptoClient.SIGNATURE_WRAP_TEXT + bytes(message) + CryptoClient.SIGNATURE_WRAP_TEXT
		return CryptoClient._gpg.sign(dataToSign, keyid=ownkey).data

	@staticmethod
	def verifySignedData(message):
		'''Return the data which was signed, and the signing keyid if the signature is valid'''
		CryptoClient.initGpg()
		result = CryptoClient._gpg.verify(message)
		if result.valid:
			marker1 = message.find(CryptoClient.SIGNATURE_WRAP_TEXT)
			marker2 = message.rfind(CryptoClient.SIGNATURE_WRAP_TEXT)
			if marker1 > 0 and marker2 > marker1:
				return (message[marker1 + len(CryptoClient.SIGNATURE_WRAP_TEXT) : marker2], result.key_id)
		return (None, None)

	##############################################
