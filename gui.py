from PyQt4 import QtGui, QtWebKit, QtCore, QtNetwork
from dbnotify import DbResourceNotifier

# Helper classes for GUI functions


class DummyReply(QtNetwork.QNetworkReply):
	'''An empty reply class to cancel a network request that we want to deal with another way'''
	def __init__(self, parent):
		QtNetwork.QNetworkReply.__init__(self, parent)
		self.content = "<html>This is empty</html>"
	def abort(self):
		pass
	def bytesAvailable(self):
		return 0
	def isSequential(self):
		return True
	def readData(self, maxSize):
		pass

# Class for network manager
class NavigationInterceptor(QtNetwork.QNetworkAccessManager):
	def __init__(self, parent):
		QtNetwork.QNetworkAccessManager.__init__(self)
		self.parent = parent

	def createRequest(self, oper, request, formData):
		'''Intercept requests from the web view'''
		path = str(request.url().toString())
		if path.startswith("file://"):
			if "avatar" in path:
				print("Going to createRequest for avatar:", path)
			return QtNetwork.QNetworkAccessManager.createRequest(self, oper, request, formData)
		paramd = {}
		if (formData != None):
			paramStrings = bytes(formData.readAll()).decode("utf-8").split("&")
			paramList = [s.split("=") for s in paramStrings if s]
			print("paramList is:", paramList)
			paramd = {k : bytes(QtCore.QByteArray.fromPercentEncoding(v.replace("+", " "))).decode("utf-8") for k,v in paramList}
		self.parent.navigateTo(path, paramd)
		# TODO: Check this, shouldn't we be able to return None or something to cancel the form submit??
		# abandon request
		dummyResponse = DummyReply(self)
		dummyResponse.abort()
		return dummyResponse


# Class for webpage
class Webpage(QtWebKit.QWebPage):
	# is this class necessary at all?
	def acceptNavigationRequest(self, frame, request, navtype):
		print("accept navigation request:", request.url().toString())
		if navtype == QtWebKit.QWebPage.NavigationTypeFormSubmitted:
			print("It's a form submit to", request.url().toString())
			return True
		retval = QtWebKit.QWebPage.acceptNavigationRequest(self, frame, request, navtype)
		return retval

# Shell around a WebView, connecting with the NavigationInterceptor
class WebShell(QtWebKit.QWebView):
	def __init__(self, parent):
		QtWebKit.QWebView.__init__(self)
		self.parent = parent
		self.navInterceptor = NavigationInterceptor(parent)
		self.setPage(Webpage())
		self.page().setLinkDelegationPolicy(QtWebKit.QWebPage.DelegateExternalLinks)
		self.page().setNetworkAccessManager(self.navInterceptor)
		self.connect(self.page(), QtCore.SIGNAL("linkClicked(const QUrl&)"), parent.slotLinkClicked)
		DbResourceNotifier.getInstance().addListener(self)

	def notifyResourceChanged(self, resourcePath):
		'''A resource has changed, so we need to delete it from the cache'''
		# Would be nice to just clear this single resource, but clearing all of them works too
		self.settings().clearMemoryCaches()



class GuiWindow(QtGui.QMainWindow):
	'''Superclass of all the GUI Windows with a WebShell in the middle'''
	def __init__(self, lowerItem=None):
		QtGui.QMainWindow.__init__(self)
		self.webpane = WebShell(self)
		if lowerItem:
			splitter = QtGui.QSplitter(QtCore.Qt.Vertical)
			splitter.addWidget(self.webpane)
			splitter.addWidget(lowerItem)
			#lowerItem.hide()
			self.setCentralWidget(splitter)
		else:
			self.setCentralWidget(self.webpane)

		icon = QtGui.QIcon()
		icon.addPixmap(QtGui.QPixmap("images/window-icon.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
		self.setWindowIcon(icon)

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

