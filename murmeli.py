###################################################
#  Murmeli, an encrypted communications platform  #
#             by activityworkshop                 #
#  Based on Tor's hidden services and torchat_py  #
#  Licensed to you under the GPL v3               #
###################################################

# This file contains the entry point of the application
# and the construction of the main Qt window

from PyQt4 import QtGui, QtCore
from gui import GuiWindow
from i18n import I18nManager
from config import Config
from pages import PageServer
from dbclient import DbClient
from torclient import TorClient
import postmen


# Hack to allow Ctrl-C to work
import signal
signal.signal(signal.SIGINT, signal.SIG_DFL)

# Class for main window
class MainWindow(GuiWindow):
	def __init__(self, *args):
		GuiWindow.__init__(*(self,) + args)
		self.postmen = None
		self.toolbar = self.makeToolbar([
			("images/toolbar-home.png",     self.onHomeClicked,     "mainwindow.toolbar.home"),
			("images/toolbar-people.png",   self.onContactsClicked, "mainwindow.toolbar.contacts"),
			("images/toolbar-messages.png", self.onMessagesClicked, "mainwindow.toolbar.messages"),
			("images/toolbar-calendar.png", self.onCalendarClicked, "mainwindow.toolbar.calendar"),
			("images/toolbar-settings.png", self.onSettingsClicked, "mainwindow.toolbar.settings") ])
		self.addToolBar(self.toolbar)
		self.setContextMenuPolicy(QtCore.Qt.NoContextMenu)
		# status bar
		self.statusbar = QtGui.QStatusBar(self)
		self.statusbar.setObjectName("statusbar")
		self.setStatusBar(self.statusbar)

		self.setWindowTitle(I18nManager.getText("mainwindow.title"))

		self.setStatusTip("Murmeli")
		self.setPageServer(PageServer())
		self.navigateTo("/")
		# we want to be notified of Config changes
		Config.registerSubscriber(self)
		self.postmen = [postmen.IncomingPostman(self), postmen.OutgoingPostman(self)]

		# TODO: tor should be stopped on exit, but for now we don't need it
		TorClient.stopTor()

	def makeToolbar(self, deflist):
		'''Given a list of (image, method, tooltip), make a QToolBar with those actions'''
		toolbar = QtGui.QToolBar(self)
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

	def onHomeClicked(self):     self.navigateTo("/")
	def onContactsClicked(self): self.navigateTo("/contacts/")
	def onMessagesClicked(self): self.navigateTo("/messages/")
	def onCalendarClicked(self): self.navigateTo("/calendar/")
	def onSettingsClicked(self): self.navigateTo("/settings/")

	def configUpdated(self):
		for a in self.toolbarActions:
			a.setToolTip(I18nManager.getText(a.tooltipkey))

	def postmanKnock(self):
		# Maybe we don't care about the outgoing postman knocking actually...
		highlightInbox = self.postmen[0].isSomethingInInbox() if self.postmen else False
		if highlightInbox:
			print("Calling modify with value", ("yes" if highlightInbox else "no"))


	def closeEvent(self, event):
		print("Closing Murmeli")
		# Tell postmen to stop working
		for p in self.postmen:
			p.stop()
		DbClient.stopDatabase()
		TorClient.stopTor()
		event.accept()

