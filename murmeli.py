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
from i18n import I18nManager
from config import Config
from dbclient import DbClient
from torclient import TorClient


# Hack to allow Ctrl-C to work
import signal
signal.signal(signal.SIGINT, signal.SIG_DFL)

# Class for main window
class MainWindow(QtGui.QMainWindow):
	def __init__(self, *args):
		QtGui.QMainWindow.__init__(*(self,) + args)
		self.setContextMenuPolicy(QtCore.Qt.NoContextMenu)
		self.setCentralWidget(QtGui.QLabel("That's right, the main Murmeli bits are still missing!"))
		# status bar
		self.statusbar = QtGui.QStatusBar(self)
		self.statusbar.setObjectName("statusbar")
		self.setStatusBar(self.statusbar)

		self.setWindowTitle(I18nManager.getText("mainwindow.title"))

		icon = QtGui.QIcon()
		icon.addPixmap(QtGui.QPixmap("images/window-icon.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
		self.setWindowIcon(icon)

		self.setStatusTip("Murmeli")
		# we want to be notified of Config changes
		Config.registerSubscriber(self)

		# TODO: Both tor and mongo should be stopped on exit, but for now we don't need them
		DbClient.stopDatabase()
		TorClient.stopTor()


	def configUpdated(self):
		pass

