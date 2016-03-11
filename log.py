from PyQt4 import QtGui

class LogWindow(QtGui.QTextEdit):
	'''A logger class which appends to a scrolling Qt Widget'''

	def __init__(self):
		QtGui.QTextEdit.__init__(self)
		self.append("Murmeli")

	def notifyLogEvent(self, msgText):
		print("***** Log event:")
		print("*****", msgText)
		self.append(msgText)
