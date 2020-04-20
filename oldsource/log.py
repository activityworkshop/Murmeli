from PyQt5.QtCore import pyqtSlot
from PyQt5.QtWidgets import QTextEdit

class LogWindow(QTextEdit):
	'''A logger class which appends to a scrolling Qt Widget'''

	def __init__(self):
		QTextEdit.__init__(self)
		self.append("Murmeli")

	@pyqtSlot(str)
	def notifyLogEvent(self, msgText):
		print("***** Log event:")
		print("*****", msgText)
		self.append(msgText)
