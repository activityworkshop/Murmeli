'''Helper classes for GUI functions'''

from PyQt5 import QtGui, QtCore
from PyQt5.QtWidgets import QMainWindow
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEnginePage


class Webpage(QWebEnginePage):
    '''Class for webpage'''

    def __init__(self):
        QWebEnginePage.__init__(self)

    def set_html(self, contents):
        '''Pass up to parent method including base url'''
        QWebEnginePage.setHtml(self, contents, QtCore.QUrl("file://start"))


class WebView(QWebEngineView):
    '''View class which contains a page'''
    def __init__(self, parent):
        QWebEngineView.__init__(self)
        self._page = Webpage()
        self.setPage(self._page)

    def set_html(self, contents):
        '''Pass request on to page'''
        return self._page.set_html(contents)


class GuiWindow(QMainWindow):
    '''Superclass of all the GUI Windows with a WebView in the middle'''
    def __init__(self):
        QMainWindow.__init__(self)
        self.webpane = WebView(self)
        self.setCentralWidget(self.webpane)

        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap("images/window-icon.png"), QtGui.QIcon.Normal,
                       QtGui.QIcon.Off)
        self.setWindowIcon(icon)
        self.page_server = None

    def set_page_server(self, server):
        '''Set the page server'''
        self.page_server = server

    def show_page(self, contents):
        '''Set the html contents'''
        self.show()
        self.webpane.set_html(contents)

    def navigate_to(self, path, params=None):
        '''Navigate to the given path with the given params, using our page server'''
        if path in ('/closewindow', 'http://murmeli/closewindow') and not params:
            self.close()
        elif self.page_server and path:
            self.page_server.serve_page(self.webpane, path, params)
        else:
            print("Cannot navigate to:", path)
