from dbclient import DbClient
from cryptoclient import CryptoClient


class ContactMaker:
	'''Class responsible for updating the database and crypto keyring
	according to changes in contact information, like establishing
	or deleting contacts'''

	@staticmethod
	def handleInitiate(torId, displayName):
		'''We have requested contact with another id, so we can set up
		this new contact's name with a status of "requested"'''
		# TODO: If row already exists then get status (and name/displayname) and error with it
		# Add new row in db with id, name and "requested"
		if torId and torId != DbClient.getOwnTorId():
			DbClient.updateContact(torId, {'displayName':displayName, 'status':'requested'})


	@staticmethod
	def handleDeleteContact(torId):
		'''For whatever reason, we don't trust this contact any more, so status is set to "deleted"'''
		if torId and torId != DbClient.getOwnTorId():
			DbClient.updateContact(torId, {"status" : "deleted"})
		#       If torId isn't found in profiles table then do nothing

