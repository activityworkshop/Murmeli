'''Murmeli, an encrypted communications platform

   By activityworkshop
   Based on Tor's hidden services and torchat_py
   Licensed to you under the GPL v2

   This file contains the entry point of the application
   and the construction of the main Qt window'''

import os, shutil
import signal, sys
from PyQt5 import QtWidgets, QtCore, QtGui
from gui import GuiWindow
from i18n import I18nManager
from config import Config
from pages import PageServer
from torclient import TorClient
import postmen
from messageshuffler import MessageShuffler
from log import LogWindow
from contactmgr import ContactMaker
from supersimpledb import MurmeliDb
from dbinterface import DbI


def closeMurmeli(signal, frame):
	'''Cleanup method called when Murmeli is killed, eg by Ctrl-C'''
	print("CloseMurmeli has been called")
	DbI.releaseDb()
	TorClient.stopTor()
	sys.exit(0)

# Bind Ctrl-C to cleanup the database and tor
signal.signal(signal.SIGINT, closeMurmeli)

class MainWindow(GuiWindow):
	'''Class for main window'''
	def __init__(self, *args):
		self.logPanel = LogWindow()
		GuiWindow.__init__(self, lowerItem=self.logPanel)
		self.clearWebCache()
		self.postmen = None
		self.toolbar = self.makeToolbar([
			("images/toolbar-home.png",     self.onHomeClicked,     "mainwindow.toolbar.home"),
			("images/toolbar-people.png",   self.onContactsClicked, "mainwindow.toolbar.contacts"),
			("images/toolbar-messages.png", self.onMessagesClicked, "mainwindow.toolbar.messages"),
			("images/toolbar-messages-highlight.png", self.onMessagesClicked, "mainwindow.toolbar.messages"),
			("images/toolbar-calendar.png", self.onCalendarClicked, "mainwindow.toolbar.calendar"),
			("images/toolbar-settings.png", self.onSettingsClicked, "mainwindow.toolbar.settings") ])
		self.addToolBar(self.toolbar)
		self.setContextMenuPolicy(QtCore.Qt.NoContextMenu)
		# status bar
		self.statusbar = QtWidgets.QStatusBar(self)
		self.statusbar.setObjectName("statusbar")
		self.setStatusBar(self.statusbar)

		self.setWindowTitle(I18nManager.getText("mainwindow.title"))

		self.setStatusTip("Murmeli")
		self.setPageServer(PageServer())
		self.navigateTo("/")
		# we want to be notified of Config changes
		Config.registerSubscriber(self)
		self.postmen = [postmen.IncomingPostman(self), postmen.OutgoingPostman(self)]
		self.postmen[1].messageSentSignal.connect(self.logPanel.notifyLogEvent)
		MessageShuffler.getTannoy().updateSignal.connect(self.logPanel.notifyLogEvent)
		# Make sure Tor client is started
		if not TorClient.isStarted():
			TorClient.startTor()
		# Create database instance if not already set
		if not DbI.hasDbSet():
			DbI.setDb(MurmeliDb(Config.getSsDatabaseFile()))
		# Make sure the status of the contacts matches our keyring
		missingKeyNames = ContactMaker.checkAllContactsKeys()
		if missingKeyNames:
			warningTexts = [I18nManager.getText("warning.keysnotfoundfor")] + missingKeyNames
			QtWidgets.QMessageBox.warning(self, "Murmeli", "\n   ".join(warningTexts))

	def makeToolbar(self, deflist):
		'''Given a list of (image, method, tooltip), make a QToolBar with those actions'''
		toolbar = QtWidgets.QToolBar(self)
		toolbar.setFloatable(False)
		toolbar.setMovable(False)
		toolbar.setIconSize(QtCore.QSize(48, 48))
		self.toolbarActions = []
		for actdef in deflist:
			action = toolbar.addAction(QtGui.QIcon(actdef[0]), "_", actdef[1])
			action.tooltipkey = actdef[2]
			self.toolbarActions.append(action)
		self.configUpdated()  # to set the tooltips
		return toolbar

	def modifyToolbar(self, highlightMessages):
		'''Either highlight (if flag True) or not-highlight the new messages toolbar icon'''
		self.toolbar.actions()[2].setVisible(not highlightMessages)
		self.toolbar.actions()[3].setVisible(highlightMessages)

	def onHomeClicked(self):
		self.navigateTo("/")
	def onContactsClicked(self):
		self.navigateTo("/contacts/")
	def onMessagesClicked(self):
		self.navigateTo("/messages/")
	def onCalendarClicked(self):
		self.navigateTo("/calendar/")
	def onSettingsClicked(self):
		self.navigateTo("/settings/")

	def configUpdated(self):
		'''React to a change in settings by changing tooltips and log panel visibility'''
		for a in self.toolbarActions:
			a.setToolTip(I18nManager.getText(a.tooltipkey))
		# Show/hide log window
		if Config.getProperty(Config.KEY_SHOW_LOG_WINDOW):
			self.logPanel.show()
		else:
			self.logPanel.hide()

	def postmanKnock(self):
		# Maybe we don't care about the outgoing postman knocking actually...
		highlightInbox = self.postmen[0].isSomethingInInbox() if self.postmen else False
		print("Calling modify with value", ("yes" if highlightInbox else "no"))
		self.modifyToolbar(highlightInbox)

	def clearWebCache(self):
		'''Delete all the files in the web cache'''
		cacheDir = Config.getWebCacheDir()
		shutil.rmtree(cacheDir, ignore_errors=True)
		os.makedirs(cacheDir)

	def closeEvent(self, event):
		'''Clean up before closing by stopping all services'''
		print("Closing Murmeli")
		# Tell postmen to stop working
		for p in self.postmen:
			p.stop()
		DbI.releaseDb()
		TorClient.stopTor()
		self.clearWebCache()
		event.accept()
