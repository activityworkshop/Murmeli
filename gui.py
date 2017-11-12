'''Helper classes for GUI functions'''

from PyQt5 import QtGui, QtCore
from PyQt5.QtWidgets import QMainWindow, QSplitter
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEnginePage
from dbnotify import DbResourceNotifier



class Webpage(QWebEnginePage):
	'''Class for webpage'''
	def __init__(self):
		QWebEnginePage.__init__(self)

	def acceptNavigationRequest(self, url, navtype, ismain):
		if navtype == 2:
			print("Form submit to", url.fileName())
		return False

	def setHtml(self, contents):
		# print("web page setting html to:", contents)
		QWebEnginePage.setHtml(self, contents, QtCore.QUrl("file://start"))


class WebView(QWebEngineView):
	def __init__(self):
		QWebEngineView.__init__(self)
		self._page = Webpage()
		self.setPage(self._page)

	def setHtml(self, contents):
		# print("web view setHtml called")
		return self._page.setHtml(contents)

	def notifyResourceChanged(self, resourcePath):
		pass


class GuiWindow(QMainWindow):
	'''Superclass of all the GUI Windows with a WebShell in the middle'''
	def __init__(self, lowerItem=None):
		QMainWindow.__init__(self)
		self.webpane = WebView()
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
		linkParams = {str(k):str(v) for k, v in link.queryItems()}
		self.navigateTo(str(link.path()), linkParams)

	def navigateTo(self, path, params=None):
		if (path == '/closewindow' or path == 'http://murmeli/closewindow') and not params:
			self.close()
		else:
			self.pageServer.servePage(self.webpane, path, params)

