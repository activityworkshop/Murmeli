'''Start script for Murmeli
   Copyright activityworkshop.net and released under the GPL v2.'''

import os
from i18n import I18nManager
from startupwizard import StartupWizard
from supersimpledb import MurmeliDb
from dbinterface import DbI

# First, check PyQt availability, if we haven't got that then we can't show any gui
try:
	from PyQt5 import QtGui, QtCore
	from PyQt5.QtWidgets import QApplication
except ImportError:
	print("ERROR: Can't find PyQt.  Please install both Qt and PyQt.")
	print("       On linux you may be able to do this by installing a package called 'python3-qt5'.")
	exit()

# Try and load the config from the default file
from config import Config
canStartMurmeli = Config.foundConfigFile()
Config.load()  # get some defaults even if file wasn't there

# Try to import python-gnupg, just to see if it's there
try:
	from gnupg import GPG
	# found them
except ImportError:
	canStartMurmeli = False

# if it all looks ok so far, we need to check the database
db = None
dbFilePath = Config.getSsDatabaseFile()
if not os.path.exists(dbFilePath):
	canStartMurmeli = False

if canStartMurmeli:
	print("I think I can start Murmeli, checking database status")
	db = MurmeliDb(dbFilePath)
	DbI.setDb(db)

	try:
		ownprofile = DbI.getProfile()
		if ownprofile is None or ownprofile.get("keyid", None) is None:
			print("I didn't get a profile or didn't get a key, so I can't start Murmeli")
			canStartMurmeli = False
		else:
			print("I think I got a profile and a keyid: '", ownprofile.get("keyid", ""), "' so I'm going to start Murmeli")
	except Exception as e:
		print("Exception thrown trying to get profile, so I can't start Murmeli:", e)
		canStartMurmeli = False # maybe authentication failed?

if not canStartMurmeli:
	# Close database, ready for the startup wizard
	DbI.releaseDb()
	db = None

# Get ready to launch a Qt GUI
I18nManager.setLanguage()
Config.registerSubscriber(I18nManager.instance())
app = QApplication([])

# Now start either the wizard or the main gui
if canStartMurmeli:
	# Skip wizard, launch actual GUI
	from murmeli import MainWindow
	win = MainWindow()
	Config.registerSubscriber(win)
	win.show()
else:
	win = StartupWizard()
	win.show()

app.exec_()
