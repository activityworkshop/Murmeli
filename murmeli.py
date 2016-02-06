###################################################
#  Murmeli, an encrypted communications platform  #
#             by activityworkshop                 #
#  Based on Tor's hidden services and torchat_py  #
#  Licensed to you under the GPL v3               #
###################################################

# This file contains the entry point of the application
# and the construction of the main Qt window

import sys
from PyQt4 import QtGui, QtCore
from gui import GuiWindow
from i18n import I18nManager
from config import Config
from pages import PageServer
from dbclient import DbClient
from torclient import TorClient


# Hack to allow Ctrl-C to work
import signal
signal.signal(signal.SIGINT, signal.SIG_DFL)

# Class for main window
class MainWindow(GuiWindow):
	def __init__(self, *args):
		GuiWindow.__init__(*(self,) + args)
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

		icon = QtGui.QIcon()
		icon.addPixmap(QtGui.QPixmap("images/window-icon.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
		self.setWindowIcon(icon)

		self.setStatusTip("Murmeli")
		self.setPageServer(PageServer())
		self.navigateTo("/")
		# we want to be notified of Config changes
		Config.registerSubscriber(self)

		# TODO: Both tor and mongo should be stopped on exit, but for now we don't need them
		DbClient.stopDatabase()
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

