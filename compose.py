'''Module for composing a new message'''

from PyQt4 import QtGui
from gui import GuiWindow

# TODO: Maybe this could be moved into gui as an ExtraWindow class
#       as there's nothing left here which is specific to composing

class ComposeWindow(GuiWindow):
	'''Main class for the Compose window'''

	def __init__(self, windowTitle=None):
		'''Constructor'''
		GuiWindow.__init__(self)
		self._setupUi(windowTitle)

	def _setupUi(self, windowTitle):
		'''Initialise the user interface'''
		self.setObjectName("MainWindow") # TODO: needs to be different from MainWindow?
		self.resize(551, 343)
		self.statusbar = QtGui.QStatusBar(self)   # TODO: needed?
		self.statusbar.setObjectName("statusbar")
		self.setStatusBar(self.statusbar)
		# texts
		self.setWindowTitle("Murmeli" if windowTitle is None else windowTitle)
		self.setStatusTip("")
