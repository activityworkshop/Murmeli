'''Startup Wizard for Murmeli'''

import os
import time
import re
from PyQt5 import QtWidgets, QtCore, QtGui
from i18n import I18nManager
from config import Config
from cryptoclient import CryptoClient
from dbinterface import DbI
from torclient import TorClient
from murmeli import MainWindow
from supersimpledb import MurmeliDb


class StartupWizard(QtWidgets.QMainWindow):
	'''Class to act as the main startup wizard using Qt'''

	def __init__(self, *args):
		'''Constructor'''
		QtWidgets.QMainWindow.__init__(*(self,) + args)
		self.setWindowTitle(I18nManager.getText("startupwizard.title"))

		# main pane with the stack and the button panel
		mainpane = QtWidgets.QWidget(self)
		mainlayout = QtWidgets.QVBoxLayout()
		mainpane.setLayout(mainlayout)
		self.setCentralWidget(mainpane)

		self.cardstack = QtWidgets.QStackedWidget(mainpane)

		self.cardPanels = [IntroPanel(), DependenciesPanel(), PathsPanel(), ServicesPanel(), \
			KeygenPanel(), FinishedPanel()]
		for card in self.cardPanels:
			panel = card.getPanel()
			self.cardstack.addWidget(panel)
			card.redrawNavButtonsSignal.connect(self.redrawButtons)

		# button panel at the bottom
		buttonPanel = QtWidgets.QFrame(self.cardstack)
		buttonPanel.setFrameStyle(QtWidgets.QFrame.Box + QtWidgets.QFrame.Sunken)
		self.backButton = QtWidgets.QPushButton(I18nManager.getText("button.exit"))
		self.nextButton = QtWidgets.QPushButton(I18nManager.getText("button.next"))
		layout = QtWidgets.QHBoxLayout()
		layout.addWidget(self.backButton)
		layout.addStretch(1)
		layout.addWidget(self.nextButton)
		buttonPanel.setLayout(layout)

		self.backButton.clicked.connect(self.backButtonClicked)
		self.nextButton.clicked.connect(self.nextButtonClicked)

		mainlayout.addWidget(self.cardstack)
		mainlayout.addWidget(buttonPanel)
		self.nextButton.setFocus()

	def backButtonClicked(self):
		'''Called when the 'Back' or 'Exit' buttons are pressed'''
		#print "back clicked"
		currIndex = self.cardstack.currentIndex()
		if currIndex == 0:
			# Do a controlled shutdown?  Close Db, Tor?
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
				# close this wizard but keep Tor, Db running
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

class WizardPanel(QtCore.QObject):
	redrawNavButtonsSignal = QtCore.pyqtSignal()
	def __init__(self):
		QtCore.QObject.__init__(self)
	def getPanel(self):
		return QtWidgets.QLabel("<i>TODO</i>")
	def prepare(self):
		pass
	def finish(self):
		return True
	def cancel(self):
		pass

	def _makeHeadingLabel(self, token):
		'''Convenience method for making a bold label for each panel'''
		label = QtWidgets.QLabel(I18nManager.getText(token))
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
	def __init__(self):
		WizardPanel.__init__(self)
	def getName(self):
		return "intro"
	def getPanel(self):
		# first panel, for intro
		self.panel = QtWidgets.QWidget()
		layout = QtWidgets.QVBoxLayout()
		# Make labels in advance
		self.labels = {}
		for k in ["heading", "description1", "description2", "description3"]:
			self.labels[k] = QtWidgets.QLabel()
		self._makeLabelHeading(self.labels["heading"])
		layout.addWidget(self.labels["heading"])
		self.labels["description1"].setWordWrap(True)
		layout.addWidget(self.labels["description1"])
		# language selection
		langFrame = QtWidgets.QWidget()
		langLayout = QtWidgets.QHBoxLayout()
		langFrame.setLayout(langLayout)
		self.languageCombo = QtWidgets.QComboBox()
		self.languageCombo.addItem("English")
		self.languageCombo.addItem("Deutsch")
		self.languageCombo.setCurrentIndex(1 if Config.getProperty(Config.KEY_LANGUAGE) == "de" else 0)
		self.languageCombo.currentIndexChanged.connect(self.languageChanged)
		langLayout.addStretch(1)
		langLayout.addWidget(self.languageCombo)
		layout.addWidget(langFrame)
		# image
		logoimage = QtWidgets.QLabel()
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
		self.redrawNavButtonsSignal.emit()

	def getButtonKeys(self):
		'''exit button, not back'''
		return ("exit", "next")

# ================Dependencies===================

class DependenciesPanel(WizardPanel):
	def getName(self):
		return "dependencies"
	def __init__(self):
		WizardPanel.__init__(self)
		# some resources
		self.yesPixmap   = QtGui.QPixmap("images/tick-yes.png")
		self.noPixmap    = QtGui.QPixmap("images/tick-no.png")
		#self.blankPixmap = QtGui.QPixmap("images/tick-blank.png")

	def getPanel(self):
		# second panel, for dependencies
		panel1 = QtWidgets.QWidget()
		layout = QtWidgets.QVBoxLayout()
		self.labels = {}
		for k in ["heading", "intro", "pyqt", "gnupg", "alsotor"]:
			self.labels[k] = QtWidgets.QLabel()
		self._makeLabelHeading(self.labels["heading"])
		layout.addWidget(self.labels["heading"])
		layout.addStretch(1)
		layout.addWidget(self.labels["intro"])
		depsbox = QtWidgets.QFrame(panel1)
		sublayout = QtWidgets.QFormLayout()
		depKeys = ['pyqt', 'gnupg']
		self.dependencyLabels = [QtWidgets.QLabel() for k in depKeys]
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
	def __init__(self):
		WizardPanel.__init__(self)
	def getName(self):
		return "paths"
	def getPanel(self):
		# third panel, for paths
		self.panel = QtWidgets.QWidget()
		layout = QtWidgets.QVBoxLayout()
		self.labels = {}
		for k in ["heading", "configfile", "datadir", "torexe", "gpgexe", "considerencryption"]:
			self.labels[k] = QtWidgets.QLabel()
		self._makeLabelHeading(self.labels["heading"])
		layout.addWidget(self.labels["heading"])
		filepathbox = QtWidgets.QFrame(self.panel)
		sublayout = QtWidgets.QFormLayout()
		sublayout.setSpacing(20)
		# Path to config file (read-only, can't be changed)
		sublayout.addRow(self.labels["configfile"], QtWidgets.QLabel(Config.CONFIG_FILE_PATH))
		# Path to data directory (input)
		datadir = Config.getProperty(Config.KEY_DATA_DIR)
		if not datadir or datadir == "": datadir = Config.DEFAULT_DATA_PATH
		self.dataDirectoryField = QtWidgets.QLineEdit(datadir)
		sublayout.addRow(self.labels["datadir"], self.dataDirectoryField)
		# Path to tor exe (input)
		self.torPathField = QtWidgets.QLineEdit("tor")
		sublayout.addRow(self.labels["torexe"], self.torPathField)
		# Path to gnupg exe (input)
		self.gpgPathField = QtWidgets.QLineEdit("gpg")
		sublayout.addRow(self.labels["gpgexe"], self.gpgPathField)
		# MAYBE: Could we check whether these paths exist, and guess alternative ones if not?
		# TODO: Browse buttons to select exes and directory
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
			QtWidgets.QMessageBox.critical(self.panel,
				I18nManager.getText("gui.dialogtitle.error"),
				I18nManager.getText("startupwizard.paths.failedtocreatedatadir"))
			return False
		# Also store selected paths to exes
		# TODO: Check the exes exist?
		Config.setProperty(Config.KEY_TOR_EXE, str(self.torPathField.text()))
		Config.setProperty(Config.KEY_GPG_EXE, str(self.gpgPathField.text()))
		Config.save()
		return True

# ================Services=====================

class ServicesPanel(WizardPanel):
	'''Wizard panel for the services page'''
	def getName(self):
		return "services"
	def __init__(self):
		WizardPanel.__init__(self)
		# some resources
		self.yesPixmap   = QtGui.QPixmap("images/tick-yes.png")
		self.noPixmap    = QtGui.QPixmap("images/tick-no.png")
		self.blankPixmap = QtGui.QPixmap("images/tick-blank.png")
		self.checksDone = False
		self.allOk = False

	def getPanel(self):
		# fourth panel, for services
		self.panel = QtWidgets.QWidget()
		layout = QtWidgets.QVBoxLayout()
		self.labels = {}
		for k in ["heading", "intro", "database", "gpg", "tor", "abouttostart"]:
			self.labels[k] = QtWidgets.QLabel()
		self._makeLabelHeading(self.labels["heading"])
		layout.addWidget(self.labels["heading"])
		layout.addStretch(1)
		layout.addWidget(self.labels["intro"])
		servicesbox = QtWidgets.QFrame(self.panel)
		sublayout = QtWidgets.QFormLayout()
		servicesKeys = ['database', 'gpg', 'tor']
		self.servicesLabels = [QtWidgets.QLabel() for k in servicesKeys]
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
		self.checkerThread.finished.connect(self.finishedServiceCheck)
		self.checkerThread.updatedSignal.connect(self.updatedServiceCheck)
		self.checkerThread.start()

	def updatedServiceCheck(self):
		'''Called when service check has been updated (not yet completed) by the other thread'''
		servicesKeys = ['database', 'gpg', 'tor']
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
		self.redrawNavButtonsSignal.emit()

	def cancel(self):
		'''Coming back from services start - need to stop them'''
		# If we're cancelling, we don't want to save anything - need method?
		DbI.releaseDb()
		TorClient.stopTor()


class ServiceStarterThread(QtCore.QThread):
	'''Separate thread for starting the services and reporting back'''
	updatedSignal = QtCore.pyqtSignal()
	def run(self):
		# Check each of the services in turn
		self.successFlags = {}
		# Database
		time.sleep(0.5)
		DbI.setDb(MurmeliDb(Config.getSsDatabaseFile()))
		self.successFlags['database'] = True
		self.updatedSignal.emit()
		time.sleep(0.5)
		# Gnupg
		self.successFlags['gpg'] = CryptoClient.checkGpg()
		self.updatedSignal.emit()
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
		return self.successFlags.get('database', False) \
			and self.successFlags.get('gpg', False) \
			and self.successFlags.get('tor', False)

# ================Key generation=====================

class KeygenPanel(WizardPanel):
	'''Panel for generation of own keypair'''
	def __init__(self):
		WizardPanel.__init__(self)
	def getName(self):
		return "keygen"
	def getPanel(self):
		# fifth panel, for generating keypair
		self.panel = QtWidgets.QWidget()
		layout = QtWidgets.QVBoxLayout()
		self.labels = {}
		for k in ["heading", "introemptykeyring", "introsinglekey", "introselectkey", "param.name",
		  "param.email", "param.comment", "mighttakeawhile"]:
			self.labels[k] = QtWidgets.QLabel()
		self._makeLabelHeading(self.labels["heading"])
		layout.addWidget(self.labels["heading"])
		layout.addStretch(0.3)
		layout.addWidget(self.labels["introemptykeyring"])
		layout.addWidget(self.labels["introsinglekey"])
		layout.addWidget(self.labels["introselectkey"])
		# list of keypairs already in the keyring
		self.keypairListWidget = QtWidgets.QListWidget()
		layout.addWidget(self.keypairListWidget)
		# parameters for generation of new keypair
		self.keygenbox = QtWidgets.QFrame(self.panel)
		sublayout = QtWidgets.QFormLayout()
		self.keygenParamBoxes = {}
		for param in ['name', 'email', 'comment']:  # (no password)
			editbox = QtWidgets.QLineEdit()
			self.keygenParamBoxes[param] = editbox
			sublayout.addRow(self.labels["param." + param], editbox)
		self.keygenbox.setLayout(sublayout)
		sublayout.setFormAlignment(QtCore.Qt.AlignHCenter) # horizontally centred
		layout.addWidget(self.keygenbox)
		# 'Generate' button
		self.generateButton = QtWidgets.QPushButton(I18nManager.getText("button.generate"))
		self.generateButton.clicked.connect(self.generateKeyClicked)
		layout.addWidget(self.generateButton)
		# Progress bar (actually more of an hourglass)
		self.generateProgressbar = QtWidgets.QProgressBar()
		self.generateProgressbar.setVisible(False)
		self.generateProgressbar.setMinimum(0)
		self.generateProgressbar.setMaximum(0)
		progressPanel = QtWidgets.QFrame()
		sublayout = QtWidgets.QHBoxLayout()
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
		# Store key, name in the database for our own profile
		selectedKey = self.privateKeys[self.keypairListWidget.currentRow()]
		ownid = TorClient.getOwnId()
		# See if a name was entered before, if so use that
		myname = self.keygenParamBoxes['name'].text()
		if not myname:
			# Extract the name from the string which comes back from the key as "'Some Name (no comment) <no@email.com>'"
			myname = self.extractName(selectedKey['uids'])
		profile = {"name" : myname, "keyid" : selectedKey['keyid'], "torid" : ownid, "status" : "self", "ownprofile" : True}
		# Store this in the database
		DbI.updateProfile(ownid, profile)
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
		self.keygenThread.finished.connect(self.finishedKeyGen)
		self.keygenThread.start()

	def finishedKeyGen(self):
		'''React to finishing a key generation'''
		#print "callback, generated key is ", self.keygenThread.getKey()
		self.generateButton.setEnabled(True)
		# Update list with new key
		self.prepare()
		self.redrawNavButtonsSignal.emit()

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
	def __init__(self):
		WizardPanel.__init__(self)
	def getName(self):
		return "finished"
	def getPanel(self):
		# last panel, for confirmation
		panel5 = QtWidgets.QWidget()
		layout = QtWidgets.QVBoxLayout()
		self.labels = {}
		for k in ["heading", "congrats", "nowstart"]:
			self.labels[k] = QtWidgets.QLabel()
		self._makeLabelHeading(self.labels["heading"])
		layout.addWidget(self.labels["heading"])
		layout.addStretch(1)
		layout.addWidget(self.labels["congrats"])
		layout.addWidget(self.labels["nowstart"])
		self.youridLabel = QtWidgets.QLabel()
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
	app = QtWidgets.QApplication([])

	win = StartupWizard()
	win.show()

	app.exec_()
