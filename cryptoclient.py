###############################
## Crypto client for Murmeli ##
###############################

# Only classes inside this file should care about encryption / decryption details
# (except maybe the startup wizard which can check for python-gnupg availability)
# Here we use GPG for key management, en/decryption, signatures etc but this is the
# only place where that implementation detail is necessary

import os.path
from config import Config
from gnupg  import GPG
from random import SystemRandom

# Exception if something went wrong with encryption
class CryptoError(Exception):
	pass


class CryptoClient:
	'''The CryptoClient is the only class you need to reference when accessing the crypto functions.'''

	# Random number generator
	randgen = SystemRandom()
	# static variable to hold GPG object
	_gpg = None
	'''Constant string used for wrapping signed data '''
	SIGNATURE_WRAP_TEXT = ":murmeli:".encode("utf-8")


	@staticmethod
	# Return whether the GPG object could be initialised or not
	def checkGpg():
		CryptoClient._gpg = None
		found, privKeys = CryptoClient._checkPrivateKeys()
		return found

	@staticmethod
	def initGpg():
		'''init the _gpg object if it's not been done yet'''
		if CryptoClient._gpg is None:
			# Get keyring path
			keyring = Config.getKeyringDir()
			print("keyring is", keyring)
			if keyring is not None and os.path.exists(keyring):
				print("keyring exists")
				try:
					gpgexe = Config.getProperty(Config.KEY_GPG_EXE)
					if not gpgexe: gpgexe = "gpg"
					CryptoClient._gpg = GPG(gnupghome=keyring, gpgbinary=gpgexe)
				except:
					print("exception thrown")
					CryptoClient._gpg = None

	@staticmethod
	def _checkPrivateKeys():
		CryptoClient.initGpg()
		if CryptoClient._gpg is None:
			return (False, [])
		return (True, CryptoClient._gpg.list_keys(True)) # True for just the private keys

	@staticmethod
	def getPrivateKeys():
		found, privKeys = CryptoClient._checkPrivateKeys()
		return privKeys

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
		#print "GPG client will now generate a keypair for %s, %s, %s." % (name, email, comment)
		inputdata = CryptoClient._gpg.gen_key_input(key_type="RSA", key_length=4096, \
			name_real = name, name_email=email, name_comment=comment)
		key = CryptoClient._gpg.gen_key(inputdata)
		return key


	########## Asymmetric encryption ##############

	@staticmethod
	def encryptAndSign(message, recipient, ownkey):
		if not recipient:
			print("Can't encryptAndSign without a recipient!")
			raise CryptoError()
		if not ownkey:
			print("Can't encryptAndSign without an own key!")
			raise CryptoError()
		CryptoClient.initGpg()
		# TODO: Check that message is a Message, don't allow other encryptions?
		# Try to encrypt and sign, throw exception if it didn't work
		cryptoResult = CryptoClient._gpg.encrypt(message, recipients=recipient, sign=ownkey,
			 armor=False, always_trust=True)
		if not cryptoResult.ok:
			raise CryptoError()
		return cryptoResult.data

	@staticmethod
	def decryptAndCheckSignature(message):
		'''Returns the decrypted contents if possible, and the signing keyid if recognised, otherwise None'''
		CryptoClient.initGpg()
		cryptoResult = CryptoClient._gpg.decrypt(message)
		# If the signature can't be checked, then cryptoResult.valid will be False
		# - this is ok for a ContactResponse but not for any other kind of message
		print("Decrypt and check: ok is ", cryptoResult.ok, " and valid is ", cryptoResult.valid, " and keyid is", cryptoResult.key_id)
		if cryptoResult.ok:
			return (cryptoResult.data, cryptoResult.key_id if cryptoResult.valid else None)
		return (None, None)
