'''Start script for Murmeli
   Copyright activityworkshop.net and released under the GPL v2.'''

from i18n import I18nManager
from murmeli import MainWindow
from startupwizard import StartupWizard
from dbclient import DbClient

# First, check PyQt availability, if we haven't got that then we can't show any gui
try:
	from PyQt4 import QtGui, QtCore
except ImportError:
	print("ERROR: Can't find PyQt.  Please install both Qt and PyQt.")
	print("       On linux you may be able to do this by installing a package called 'python3-qt4'.")
	exit()

# Try and load the config from the default file
from config import Config
canStartMurmeli = Config.foundConfigFile()
Config.load()  # get some defaults even if file wasn't there

# Try to import pymongo and python-gnupg, just to see if they're there
try:
	import pymongo
	from gnupg import GPG
	# found them
except ImportError:
	canStartMurmeli = False

# if it all looks ok so far, we need to check the database
dbStatus = DbClient.getDatabaseRunStatus()
if dbStatus == DbClient.RUNNING_WITHOUT_AUTH:
	print("Database service mongod is already running without authentication switched on.")
	print("Please stop this mongod service before running Murmeli.")
	exit()

if not DbClient.isPasswordAvailable():
	if dbStatus == DbClient.RUNNING_SECURE:
		print("Database service mongod is already running with authentication but we don't have a password.")
		print("Please stop this mongod service before running Murmeli.")
		exit()
	print("No password is saved, so we can't use Auth on the db: go to startupwizard")
	canStartMurmeli = False

if canStartMurmeli:
	print("I think I can start Murmeli, checking database status")
	if dbStatus == DbClient.NOT_RUNNING:
		canStartMurmeli = DbClient.startDatabase(useAuth=True)

	# Either the database was already running with auth, or we've just started it with auth
	if canStartMurmeli:
		# if we can't connect, or if we haven't got our own keypair stored, then we need the startupwizard
		print("Database is now running, now checking for profile")
		try:
			ownprofile = DbClient.getProfile()
			if ownprofile is None or ownprofile.get("keyid", None) is None:
				print("I didn't get a profile or didn't get a key, so I can't start Murmeli")
				canStartMurmeli = False
			else:
				print("I think I got a profile and a keyid: '", ownprofile.get("keyid", ""), "' so I'm going to start Murmeli")
		except Exception:
			canStartMurmeli = False # maybe authentication failed?

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
	from murmeli import MainWindow
	win = MainWindow()
	Config.registerSubscriber(win)
	win.show()
else:
	win = StartupWizard()
	win.show()

app.exec_()
