'''Helper classes for GUI functions'''

from PyQt5 import QtGui, QtCore
from PyQt5.QtWidgets import QMainWindow, QSplitter
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEnginePage
from dbnotify import DbResourceNotifier
from urllib.parse import parse_qs


class Webpage(QWebEnginePage):
	'''Class for webpage'''

	# Signal
	linkClickSignal = QtCore.pyqtSignal(QtCore.QUrl)

	def __init__(self):
		QWebEnginePage.__init__(self)

	def acceptNavigationRequest(self, url, navtype, ismain):
		if navtype == 2:
			print("Form submit to", url.fileName())
		if url:
			self.linkClickSignal.emit(url)
		return False

	def setHtml(self, contents):
		# print("web page setting html to:", contents)
		QWebEnginePage.setHtml(self, contents, QtCore.QUrl("file://start"))


class WebView(QWebEngineView):
	'''View class which contains a page'''
	def __init__(self, parent):
		QWebEngineView.__init__(self)
		self._page = Webpage()
		self.setPage(self._page)
		self._page.linkClickSignal.connect(parent.slotLinkClicked)

	def setHtml(self, contents):
		return self._page.setHtml(contents)

	def notifyResourceChanged(self, resourcePath):
		pass


class GuiWindow(QMainWindow):
	'''Superclass of all the GUI Windows with a WebView in the middle'''
	def __init__(self, lowerItem=None):
		QMainWindow.__init__(self)
		self.webpane = WebView(self)
		if lowerItem:
			splitter = QSplitter(QtCore.Qt.Vertical)
			splitter.addWidget(self.webpane)
			splitter.addWidget(lowerItem)
			self.setCentralWidget(splitter)
		else:
			self.setCentralWidget(self.webpane)

		icon = QtGui.QIcon()
		icon.addPixmap(QtGui.QPixmap("images/window-icon.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
		self.setWindowIcon(icon)
		self.pageServer = None

	def setPageServer(self, server):
		self.pageServer = server

	def showPage(self, contents):
		self.show()
		self.webpane.setHtml(contents)

	def slotLinkClicked(self, link):
		queryDict = parse_qs(link.query())
		# This dictionary contains lists of strings, we just take the first one in each list
		linkParams = {str(k):self.takeFirstString(v) for k, v in queryDict.items()}
		self.navigateTo(str(link.path()), linkParams)

	@staticmethod
	def takeFirstString(paramValue):
		'''urllib returns the parameter values as lists, so we need to just take the first one'''
		if paramValue and type(paramValue) == str:
			return paramValue
		if paramValue and type(paramValue) == list:
			return str(paramValue[0])
		return ""

	def navigateTo(self, path, params=None):
		if (path == '/closewindow' or path == 'http://murmeli/closewindow') and not params:
			self.close()
		else:
			self.pageServer.servePage(self.webpane, path, params)

