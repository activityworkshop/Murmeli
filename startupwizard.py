'''Startup Wizard for Murmeli'''

import os
import time
import re
from PyQt4 import QtGui, QtCore
from i18n import I18nManager
from config import Config
from dbclient import DbClient, AuthSetterUpper
from cryptoclient import CryptoClient
from torclient import TorClient
from murmeli import MainWindow


class StartupWizard(QtGui.QMainWindow):
	'''Class to act as the main startup wizard using Qt'''

	def __init__(self, *args):
		'''Constructor'''
		QtGui.QMainWindow.__init__(*(self,) + args)
		self.setWindowTitle(I18nManager.getText("startupwizard.title"))

		# main pane with the stack and the button panel
		mainpane = QtGui.QWidget(self)
		mainlayout = QtGui.QVBoxLayout()
		mainpane.setLayout(mainlayout)
		self.setCentralWidget(mainpane)

		self.cardstack = QtGui.QStackedWidget(mainpane)

		self.cardPanels = [IntroPanel(), DependenciesPanel(), PathsPanel(), ServicesPanel(), \
			KeygenPanel(), FinishedPanel()]
		for card in self.cardPanels:
			panel = card.getPanel()
			self.cardstack.addWidget(panel)
			self.connect(panel, QtCore.SIGNAL("redrawNavButtons()"), self.redrawButtons)

		# button panel at the bottom
		buttonPanel = QtGui.QFrame(self.cardstack)
		buttonPanel.setFrameStyle(QtGui.QFrame.Box + QtGui.QFrame.Sunken)
		self.backButton = QtGui.QPushButton(I18nManager.getText("button.exit"))
		self.nextButton = QtGui.QPushButton(I18nManager.getText("button.next"))
		layout = QtGui.QHBoxLayout()
		layout.addWidget(self.backButton)
		layout.addStretch(1)
		layout.addWidget(self.nextButton)
		buttonPanel.setLayout(layout)

		self.connect(self.backButton, QtCore.SIGNAL("clicked()"), self.backButtonClicked)
		self.connect(self.nextButton, QtCore.SIGNAL("clicked()"), self.nextButtonClicked)

		mainlayout.addWidget(self.cardstack)
		mainlayout.addWidget(buttonPanel)
		self.nextButton.setFocus()

	def backButtonClicked(self):
		'''Called when the 'Back' or 'Exit' buttons are pressed'''
		#print "back clicked"
		currIndex = self.cardstack.currentIndex()
		if currIndex == 0:
			# Do a controlled shutdown?  Close Mongo, Tor?
			self.close()
		else:
			self.cardPanels[currIndex].cancel()
			self.cardPanels[currIndex-1].prepare()
			self.enableButtons(self.cardPanels[currIndex-1])
			self.cardstack.setCurrentIndex(currIndex - 1)

	def nextButtonClicked(self):
		'''Called when the 'Next' or 'Finish' buttons are pressed'''
		currIndex = self.cardstack.currentIndex()
		currCard = self.cardPanels[currIndex] # TODO: or get this direct from self.cardstack?
		if currCard.finish():
			# Tab was successful, so we can go forward
			try:
				# prepare the coming tab, if necessary
				self.cardPanels[currIndex + 1].prepare()
				self.cardPanels[currIndex + 1].redrawLabels()
				self.cardstack.setCurrentIndex(currIndex + 1)
				self.enableButtons(self.cardPanels[currIndex + 1])
			except IndexError:  # we've gone past the end of the wizard, time to quit
				# Launch Murmeli
				self.murmeliWindow = MainWindow()
				self.murmeliWindow.show()
				# close this wizard but keep Tor, Mongo running
				self.close()

	def enableButtons(self, card):
		'''Ask the card what the button texts and enabled status should be'''
		backKey, nextKey = card.getButtonKeys()
		self.backButton.setText(I18nManager.getText("button." + backKey))
		self.nextButton.setText(I18nManager.getText("button." + nextKey))
		backEnabled, nextEnabled = card.getButtonsEnabled()
		self.backButton.setEnabled(backEnabled)
		self.nextButton.setEnabled(nextEnabled)

	def redrawButtons(self):
		'''Change the texts of the back/next buttons and enable them both'''
		currIndex = self.cardstack.currentIndex()
		currCard = self.cardPanels[currIndex]
		self.enableButtons(currCard)


# ================WizardPanel===================

class WizardPanel:
	def getPanel(self):
		return QtGui.QLabel("<i>TODO</i>")
	def prepare(self):
		pass
	def finish(self):
		return True
	def cancel(self):
		pass

	def _makeHeadingLabel(self, token):
		'''Convenience method for making a bold label for each panel'''
		label = QtGui.QLabel(I18nManager.getText(token))
		boldFont = label.font()
		boldFont.setWeight(QtGui.QFont.Bold)
		boldFont.setPointSize(boldFont.pointSize() + 1)
		label.setFont(boldFont)
		return label

	def _makeLabelHeading(self, label):
		'''Convenience method for making a label bold for headings'''
		boldFont = label.font()
		boldFont.setWeight(QtGui.QFont.Bold)
		boldFont.setPointSize(boldFont.pointSize() + 1)
		label.setFont(boldFont)

	def getButtonKeys(self):
		return ("back", "next")
	def getButtonsEnabled(self):
		return (True, True)

	def redrawLabels(self):
		'''Reset the texts for all labels if the language changes'''
		for labelKey in list(self.labels.keys()):
			textKey = "startupwizard." + self.getName() + "." + labelKey
			self.labels[labelKey].setText(I18nManager.getText(textKey))


# ================Intro===================

class IntroPanel(WizardPanel):
	'''First panel for introduction with a logo'''
	def getName(self):
		return "intro"
	def getPanel(self):
		# first panel, for intro
		self.panel = QtGui.QWidget()
		layout = QtGui.QVBoxLayout()
		# Make labels in advance
		self.labels = {}
		for k in ["heading", "description1", "description2", "description3"]:
			self.labels[k] = QtGui.QLabel()
		self._makeLabelHeading(self.labels["heading"])
		layout.addWidget(self.labels["heading"])
		self.labels["description1"].setWordWrap(True)
		layout.addWidget(self.labels["description1"])
		# language selection
		langFrame = QtGui.QWidget()
		langLayout = QtGui.QHBoxLayout()
		langFrame.setLayout(langLayout)
		self.languageCombo = QtGui.QComboBox()
		self.languageCombo.addItem("English")
		self.languageCombo.addItem("Deutsch")
		self.languageCombo.setCurrentIndex(1 if Config.getProperty(Config.KEY_LANGUAGE) == "de" else 0)
		self.panel.connect(self.languageCombo, QtCore.SIGNAL("currentIndexChanged(int)"),
			self.languageChanged)
		langLayout.addStretch(1)
		langLayout.addWidget(self.languageCombo)
		layout.addWidget(langFrame)
		# image
		logoimage = QtGui.QLabel()
		logoimage.setPixmap(QtGui.QPixmap("images/intrologo.png"))
		logoimage.setAlignment(QtCore.Qt.AlignHCenter) # horizontally centred
		layout.addWidget(logoimage)
		self.labels["description2"].setWordWrap(True)
		layout.addWidget(self.labels["description2"])
		self.labels["description3"].setWordWrap(True)
		layout.addWidget(self.labels["description3"])
		self.panel.setLayout(layout)
		# fill in the texts
		self.redrawLabels()
		return self.panel

	def languageChanged(self):
		'''React to a change in the language dropdown'''
		selectedLang = ["en", "de"][self.languageCombo.currentIndex()]
		Config.setProperty(Config.KEY_LANGUAGE, selectedLang)
		self.redrawLabels()
		self.panel.emit(QtCore.SIGNAL('redrawNavButtons()'))

	def getButtonKeys(self):
		'''exit button, not back'''
		return ("exit", "next")

# ================Dependencies===================

class DependenciesPanel(WizardPanel):
	def getName(self):
		return "dependencies"
	def __init__(self):
		# some resources
		self.yesPixmap   = QtGui.QPixmap("images/tick-yes.png")
		self.noPixmap    = QtGui.QPixmap("images/tick-no.png")
		#self.blankPixmap = QtGui.QPixmap("images/tick-blank.png")

	def getPanel(self):
		# second panel, for dependencies
		panel1 = QtGui.QWidget()
		layout = QtGui.QVBoxLayout()
		self.labels = {}
		for k in ["heading", "intro", "pyqt", "gnupg", "pymongo", "alsotor"]:
			self.labels[k] = QtGui.QLabel()
		self._makeLabelHeading(self.labels["heading"])
		layout.addWidget(self.labels["heading"])
		layout.addStretch(1)
		layout.addWidget(self.labels["intro"])
		depsbox = QtGui.QFrame(panel1)
		sublayout = QtGui.QFormLayout()
		depKeys = ['pyqt', 'gnupg', 'pymongo']
		self.dependencyLabels = [QtGui.QLabel() for k in depKeys]
		for i, k in enumerate(depKeys):
			sublayout.addRow(self.labels[k], self.dependencyLabels[i])
			self.dependencyLabels[i].depkey = k
		depsbox.setLayout(sublayout)
		sublayout.setFormAlignment(QtCore.Qt.AlignHCenter) # horizontally centred
		layout.addWidget(depsbox)
		layout.addSpacing(20)
		self.dependencyCheckLabel = self._makeHeadingLabel("")
		layout.addWidget(self.dependencyCheckLabel)
		layout.addWidget(self.labels["alsotor"])
		layout.addStretch(1)
		panel1.setLayout(layout)
		return panel1

	def prepare(self):
		'''When going from the intro page to the dependencies page, this needs to be updated'''
		depsFound = {'pyqt':True}  # PyQt must be present, otherwise we wouldn't be here!
		self.allFound = True
		try:
			import pymongo
			depsFound["pymongo"] = True
		except: self.allFound = False
		try:
			from gnupg import GPG
			depsFound["gnupg"] = True
		except: self.allFound = False

		# Update the ticks and crosses
		for l in self.dependencyLabels:
			found = depsFound.get(l.depkey, False)
			l.setPixmap(self.yesPixmap if found else self.noPixmap)
			l.setToolTip(I18nManager.getText("startupwizard.dep.found" if found else "startupwizard.dep.notfound"))

		# if not all dependencies are there, show the message
		self.dependencyCheckLabel.setText(I18nManager.getText("startupwizard.dependencies." +
			("allfound" if self.allFound else "notallfound")))

	def getButtonsEnabled(self): return (True, self.allFound)


# ================Paths=====================

class PathsPanel(WizardPanel):
	def getName(self):
		return "paths"
	def getPanel(self):
		# third panel, for paths
		self.panel = QtGui.QWidget()
		layout = QtGui.QVBoxLayout()
		self.labels = {}
		for k in ["heading", "configfile", "datadir", "mongoexe", "torexe", "gpgexe", "considerencryption"]:
			self.labels[k] = QtGui.QLabel()
		self._makeLabelHeading(self.labels["heading"])
		layout.addWidget(self.labels["heading"])
		filepathbox = QtGui.QFrame(self.panel)
		sublayout = QtGui.QFormLayout()
		sublayout.setSpacing(20)
		# Path to config file (read-only, can't be changed)
		sublayout.addRow(self.labels["configfile"], QtGui.QLabel(Config.CONFIG_FILE_PATH))
		# Path to data directory (input)
		datadir = Config.getProperty(Config.KEY_DATA_DIR)
		if not datadir or datadir == "": datadir = Config.DEFAULT_DATA_PATH
		self.dataDirectoryField = QtGui.QLineEdit(datadir)
		sublayout.addRow(self.labels["datadir"], self.dataDirectoryField)
		# Is it right that we don't need the path to gpg exe?  Or do we need to give to python-gnupg?
		# Path to mongo exe (input)
		self.mongoPathField = QtGui.QLineEdit("mongod")
		sublayout.addRow(self.labels["mongoexe"], self.mongoPathField)
		# Path to tor exe (input)
		self.torPathField = QtGui.QLineEdit("tor")
		sublayout.addRow(self.labels["torexe"], self.torPathField)
		# Path to gnupg exe (input)
		self.gpgPathField = QtGui.QLineEdit("gpg")
		sublayout.addRow(self.labels["gpgexe"], self.gpgPathField)
		# MAYBE: Could we check whether these paths exist, and guess alternative ones if not?
		# TODO: Browse buttons to select exes from file
		filepathbox.setLayout(sublayout)
		sublayout.setFormAlignment(QtCore.Qt.AlignHCenter) # horizontally centred
		layout.addWidget(filepathbox)
		layout.addWidget(self.labels["considerencryption"])
		layout.addStretch(1)
		self.panel.setLayout(layout)
		return self.panel

	def finish(self):
		'''Called when leaving the paths page'''
		datadir = str(self.dataDirectoryField.text())
		Config.setProperty(Config.KEY_DATA_DIR, datadir)
		# Make sure all the directories exist, create them if not
		try:
			for direc in [Config.getDatabaseDir(), Config.getWebCacheDir(), \
			  Config.getKeyringDir(), Config.getTorDir()]:
				if not os.path.exists(direc):
					os.makedirs(direc)
		except:
			# Couldn't create one of the directories, so show error and stay on this panel
			QtGui.QMessageBox.critical(self.panel,
				I18nManager.getText("gui.dialogtitle.error"),
				I18nManager.getText("startupwizard.paths.failedtocreatedatadir"))
			return False
		# Also store selected paths to exes
		# TODO: Check the exes exist?
		Config.setProperty(Config.KEY_MONGO_EXE, str(self.mongoPathField.text()))
		Config.setProperty(Config.KEY_TOR_EXE,   str(self.torPathField.text()))
		Config.setProperty(Config.KEY_GPG_EXE,   str(self.gpgPathField.text()))
		Config.save()
		return True

# ================Services=====================

class ServicesPanel(WizardPanel):
	'''Wizard panel for the services page'''
	def getName(self):
		return "services"
	def __init__(self):
		# some resources
		self.yesPixmap   = QtGui.QPixmap("images/tick-yes.png")
		self.noPixmap    = QtGui.QPixmap("images/tick-no.png")
		self.blankPixmap = QtGui.QPixmap("images/tick-blank.png")
		self.checksDone = False
		self.allOk = False

	def getPanel(self):
		# fourth panel, for services
		self.panel = QtGui.QWidget()
		layout = QtGui.QVBoxLayout()
		self.labels = {}
		for k in ["heading", "intro", "mongo", "gpg", "tor", "abouttostart"]:
			self.labels[k] = QtGui.QLabel()
		self._makeLabelHeading(self.labels["heading"])
		layout.addWidget(self.labels["heading"])
		layout.addStretch(1)
		layout.addWidget(self.labels["intro"])
		servicesbox = QtGui.QFrame(self.panel)
		sublayout = QtGui.QFormLayout()
		servicesKeys = ['mongo', 'gpg', 'tor']
		self.servicesLabels = [QtGui.QLabel() for k in servicesKeys]
		for i, k in enumerate(servicesKeys):
			sublayout.addRow(self.labels[k], self.servicesLabels[i])
			self.servicesLabels[i].servicekey = k
			self.servicesLabels[i].setPixmap(self.blankPixmap)
		servicesbox.setLayout(sublayout)
		sublayout.setFormAlignment(QtCore.Qt.AlignHCenter) # horizontally centred
		layout.addWidget(servicesbox)
		layout.addSpacing(10)
		layout.addWidget(self.labels["abouttostart"])
		layout.addSpacing(10)
		self.servicesCheckLabel = self._makeHeadingLabel("")
		layout.addWidget(self.servicesCheckLabel)
		layout.addStretch(1)
		self.panel.setLayout(layout)
		return self.panel

	def getButtonsEnabled(self):
		return (self.checksDone, self.allOk) # disable navigation until checks done

	def prepare(self):
		'''Blank out the services tab ready for starting'''
		self.allOk = False
		self.checksDone = False
		self.labels["abouttostart"].setVisible(True)
		# Blank the ticks and crosses
		for l in self.servicesLabels:
			l.setPixmap(self.blankPixmap)
		# start checking services
		self.checkerThread = ServiceStarterThread()
		# Connect signals and slots so we know what's happened
		self.panel.connect(self.checkerThread, QtCore.SIGNAL("finished()"), self.finishedServiceCheck)
		self.panel.connect(self.checkerThread, QtCore.SIGNAL("updated()"), self.updatedServiceCheck)
		self.checkerThread.start()

	def updatedServiceCheck(self):
		'''Called when service check has been updated (not yet completed) by the other thread'''
		servicesKeys = ['mongo', 'gpg', 'tor']
		for i, k in enumerate(servicesKeys):
			succ = self.checkerThread.successFlags.get(k, None)
			self.servicesLabels[i].setPixmap(self.blankPixmap if succ is None
				else self.yesPixmap if succ else self.noPixmap)


	def finishedServiceCheck(self):
		'''Called when service check has been completed by the other thread'''
		self.updatedServiceCheck()  # make sure all icons are updated
		self.checksDone = True
		self.allOk = self.checkerThread.allGood()
		self.servicesCheckLabel.setText(I18nManager.getText("startupwizard.services." + \
			("allstarted" if self.allOk else "notallstarted")))
		self.labels["abouttostart"].setVisible(False)
		# emit signal back to controller
		self.panel.emit(QtCore.SIGNAL('redrawNavButtons()'))

	def cancel(self):
		'''Coming back from services start - need to stop them'''
		DbClient.stopDatabase()
		TorClient.stopTor()


class ServiceStarterThread(QtCore.QThread):
	'''Separate thread for starting the services and reporting back'''
	def run(self):
		# Check each of the services in turn
		self.successFlags = {}
		# Mongo
		authSetup = AuthSetterUpper()
		self.successFlags['mongo'] = authSetup.setup()
		self.emit(QtCore.SIGNAL('updated()'))
		time.sleep(1)
		# Gnupg
		self.successFlags['gpg'] = CryptoClient.checkGpg()
		self.emit(QtCore.SIGNAL('updated()'))
		time.sleep(1)
		# Tor
		if TorClient.startTor():
			torid = TorClient.getOwnId()
			if torid:
				print("Started tor, our own id is: ", torid)
				self.successFlags['tor'] = True
			else: print("Failed to start tor")
		else: print("startTor returned false :(")

	def allGood(self):
		'''Check whether all have been started'''
		return self.successFlags.get('gpg', False) \
			and self.successFlags.get('mongo', False) \
			and self.successFlags.get('tor', False)

# ================Key generation=====================

class KeygenPanel(WizardPanel):
	'''Panel for generation of own keypair'''
	def getName(self):
		return "keygen"
	def getPanel(self):
		# fifth panel, for generating keypair
		self.panel = QtGui.QWidget()
		layout = QtGui.QVBoxLayout()
		self.labels = {}
		for k in ["heading", "introemptykeyring", "introsinglekey", "introselectkey", "param.name",
		  "param.email", "param.comment", "mighttakeawhile"]:
			self.labels[k] = QtGui.QLabel()
		self._makeLabelHeading(self.labels["heading"])
		layout.addWidget(self.labels["heading"])
		layout.addStretch(0.3)
		layout.addWidget(self.labels["introemptykeyring"])
		layout.addWidget(self.labels["introsinglekey"])
		layout.addWidget(self.labels["introselectkey"])
		# list of keypairs already in the keyring
		self.keypairListWidget = QtGui.QListWidget()
		layout.addWidget(self.keypairListWidget)
		# parameters for generation of new keypair
		self.keygenbox = QtGui.QFrame(self.panel)
		sublayout = QtGui.QFormLayout()
		self.keygenParamBoxes = {}
		for param in ['name', 'email', 'comment']:  # (no password)
			editbox = QtGui.QLineEdit()
			self.keygenParamBoxes[param] = editbox
			sublayout.addRow(self.labels["param." + param], editbox)
		self.keygenbox.setLayout(sublayout)
		sublayout.setFormAlignment(QtCore.Qt.AlignHCenter) # horizontally centred
		layout.addWidget(self.keygenbox)
		# 'Generate' button
		self.generateButton = QtGui.QPushButton(I18nManager.getText("button.generate"))
		self.panel.connect(self.generateButton, QtCore.SIGNAL("clicked()"), self.generateKeyClicked)
		layout.addWidget(self.generateButton)
		# Progress bar (actually more of an hourglass)
		self.generateProgressbar = QtGui.QProgressBar()
		self.generateProgressbar.setVisible(False)
		self.generateProgressbar.setMinimum(0)
		self.generateProgressbar.setMaximum(0)
		progressPanel = QtGui.QFrame()
		sublayout = QtGui.QHBoxLayout()
		sublayout.addStretch(0.4)
		sublayout.addWidget(self.generateProgressbar)
		sublayout.addStretch(0.4)
		progressPanel.setLayout(sublayout)
		layout.addWidget(progressPanel)
		# Label to say that it might take a minute or two
		layout.addWidget(self.labels["mighttakeawhile"])
		layout.addStretch(1)
		self.panel.setLayout(layout)
		return self.panel

	def prepare(self):
		'''Called before showing the keypair page'''
		self.privateKeys = CryptoClient.getPrivateKeys()
		numKeys = len(self.privateKeys)
		self.labels["introemptykeyring"].setVisible(numKeys == 0)
		self.labels["introsinglekey"].setVisible(numKeys == 1)
		self.labels["introselectkey"].setVisible(numKeys > 1)
		self.generateProgressbar.setVisible(False)
		self.labels["mighttakeawhile"].setVisible(False)
		self.keypairListWidget.clear()
		for k in self.privateKeys:
			name = k['uids']
			if isinstance(name, list):
				name = str(name[0])
			self.keypairListWidget.addItem("%s - %s (%s)" % (k['keyid'], name, k['length']))
		self.keypairListWidget.setVisible(numKeys > 0)
		self.keypairListWidget.setCurrentRow(self.keypairListWidget.count() - 1)
		# Hide generation option if we've got a key already
		self.keygenbox.setVisible(numKeys == 0)
		self.generateButton.setVisible(numKeys == 0)
		# Rewrite button text in case language has changed
		self.generateButton.setText(I18nManager.getText("button.generate"))

	def finish(self):
		'''Finished the key gen'''
		# Store key, name in mongo under own profile
		selectedKey = self.privateKeys[self.keypairListWidget.currentRow()]
		ownid = TorClient.getOwnId()
		# See if a name was entered before, if so use that
		myname = self.keygenParamBoxes['name'].text()
		if not myname:
			# Extract the name from the string which comes back from the key as "'Some Name (no comment) <no@email.com>'"
			myname = self.extractName(selectedKey['uids'])
		profile = {"name" : myname, "keyid" : selectedKey['keyid'], "torid" : ownid, "status" : "self", "ownprofile" : True}
		DbClient.updateContact(ownid, profile)
		return True

	def extractName(self, gpgName):
		'''Extract just the name from a GPG key identifier'''
		if isinstance(gpgName, list):
			name = str(gpgName[0])
		else:
			name = str(gpgName)
		if name.startswith("'") and name.endswith("'"):
			name = name[1:-1]
		if "<" in name and ">" in name and "@" in name:
			name = re.sub("<.+@.+>", "", name)
		if "(" in name and ")" in name:
			name = re.sub("\(.+\)", "", name)
		return name.strip()

	def generateKeyClicked(self):
		'''Called when 'generate' button is clicked to make a new keypair'''
		self.generateButton.setEnabled(False)
		self.generateProgressbar.setVisible(True)
		self.labels["mighttakeawhile"].setVisible(True)
		# Get parameters out of form and substitute for blanks
		name  = self.keygenParamBoxes['name'].text()
		if not name:
			name = "no name"
		email = self.keygenParamBoxes['email'].text()
		if not email:
			email = "no@email.com"
		comment = self.keygenParamBoxes['comment'].text()
		if not comment:
			comment = "no comment"
		# Launch new keygen thread
		self.keygenThread = KeyGenThread(name, email, comment)
		self.panel.connect(self.keygenThread, QtCore.SIGNAL("finished()"), self.finishedKeyGen)
		self.keygenThread.start()

	def finishedKeyGen(self):
		'''React to finishing a key generation'''
		#print "callback, generated key is ", self.keygenThread.getKey()
		self.generateButton.setEnabled(True)
		# Update list with new key
		self.prepare()
		self.panel.emit(QtCore.SIGNAL('redrawNavButtons()'))

	def getButtonsEnabled(self):
		return (True, self.keypairListWidget.count() > 0)


class KeyGenThread(QtCore.QThread):
	'''Separate thread for calling the key generation and reporting back'''
	def __init__(self, name, email, comment):
		QtCore.QThread.__init__(self)
		self.name = name
		self.email = email
		self.comment = comment
		self.keypair = None
	def run(self):
		self.keypair = CryptoClient.generateKeyPair(self.name, self.email, self.comment)
	def getKey(self):
		return self.keypair


# ================Finished=====================

class FinishedPanel(WizardPanel):
	'''Last panel, just to confirm that the wizard is finished'''
	def getName(self):
		return "finished"
	def getPanel(self):
		# last panel, for confirmation
		panel5 = QtGui.QWidget()
		layout = QtGui.QVBoxLayout()
		self.labels = {}
		for k in ["heading", "congrats", "nowstart"]:
			self.labels[k] = QtGui.QLabel()
		self._makeLabelHeading(self.labels["heading"])
		layout.addWidget(self.labels["heading"])
		layout.addStretch(1)
		layout.addWidget(self.labels["congrats"])
		layout.addWidget(self.labels["nowstart"])
		self.youridLabel = QtGui.QLabel()
		layout.addWidget(self.youridLabel)
		layout.addStretch(1)
		panel5.setLayout(layout)
		return panel5

	def prepare(self):
		'''Prepare the final panel'''
		text = (I18nManager.getText("startupwizard.finished.yourid") % TorClient.getOwnId())
		self.youridLabel.setText(text)
		# TODO: If this is just a label, then it can't be selected and copied- should it be a disabled text field instead?

	def getButtonKeys(self):
		return ("back", "finish")
	def getButtonsEnabled(self):
		return (False, True)


if __name__ == "__main__":
	# Get ready to launch a Qt GUI
	Config.load()
	I18nManager.setLanguage()
	Config.registerSubscriber(I18nManager.instance())
	app = QtGui.QApplication([])

	win = StartupWizard()
	win.show()

	app.exec_()
