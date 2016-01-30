##############################
## Start script for Murmeli ##
##############################

from i18n import I18nManager
from murmeli import MainWindow
from startupwizard import StartupWizard
from dbclient import DbClient

# First, check PyQt availability, if we haven't got that then we can't show any gui
foundPyQt = False
try:
	from PyQt4 import QtGui, QtCore
	foundPyQt = True
except:
	print("ERROR: Can't find PyQt.  Please install both Qt and PyQt.")
	print("       On linux you may be able to do this by installing a package called 'python3-qt4'.")

if foundPyQt:
	# Try and load the config from the default file
	from config import Config
	canStartMurmeli = Config.foundConfigFile()
	Config.load()  # get some defaults even if file wasn't there

	# Try to import pymongo and python-gnupg, just to see if they're there
	try:
		import pymongo
		from gnupg import GPG
		# found them
	except:
		canStartMurmeli = False

	# if it all looks ok so far, we need to check in the db for our keypair
	if canStartMurmeli:
		print("I think I can start Murmeli, trying to start database")
		# Ask DbClient to start mongo for us
		if not DbClient.isDatabaseRunning():
			canStartMurmeli = DbClient.startDatabase()
		# if it worked, but we haven't got our own keypair stored, then we need the startupwizard
		if canStartMurmeli:
			print("I think I started the database, now checking for profile")
			ownprofile = DbClient.getProfile()
			if ownprofile is None or ownprofile.get("keyid", None) is None:
				print("I didn't get a profile or didn't get a key, so I can't start Murmeli")
				canStartMurmeli = False
			else:
				print("I think I got a profile and a keyid: '", ownprofile.get("keyid", ""), "' so I'm going to start Murmeli")
		if not canStartMurmeli:
			# Ask DbClient to stop mongo again
			DbClient.stopDatabase()

	# Get ready to launch a Qt GUI
	I18nManager.setLanguage()
	Config.registerSubscriber(I18nManager.instance())
	app = QtGui.QApplication([])

	# Now start either the wizard or the main gui
	if canStartMurmeli:
		# Skip wizard, launch actual GUI (mongo is now started)
		win = MainWindow()
		win.show()
	else:
		win = StartupWizard()
		win.show()

	app.exec_()

