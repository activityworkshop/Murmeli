'''Helper classes for GUI functions'''

from urllib.parse import parse_qs
from PyQt5 import QtGui, QtCore
from PyQt5.QtWidgets import QMainWindow
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEnginePage


class Webpage(QWebEnginePage):
    '''Class for webpage'''

    # Signal
    linkClickSignal = QtCore.pyqtSignal(QtCore.QUrl)

    def __init__(self):
        QWebEnginePage.__init__(self)

    def acceptNavigationRequest(self, url, navtype, ismain):
        '''Override parent method to intercept clicks'''
        navigation_type_link_clicked = 0
        navigation_type_form = 2
        if url and navtype in (navigation_type_link_clicked, navigation_type_form):
            self.linkClickSignal.emit(url)
            return False
        return True

    def set_html(self, contents):
        '''Pass up to parent method including base url'''
        QWebEnginePage.setHtml(self, contents, QtCore.QUrl("file://start"))


class WebView(QWebEngineView):
    '''View class which contains a page'''
    def __init__(self, parent):
        QWebEngineView.__init__(self)
        self._page = Webpage()
        self.setPage(self._page)
        self._page.linkClickSignal.connect(parent.slot_link_clicked)

    def set_html(self, contents):
        '''Pass request on to page'''
        return self._page.set_html(contents)

    def notifyResourceChanged(self, resource_path):
        '''Ignore notifications'''
        pass


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

    def slot_link_clicked(self, link):
        '''React to a click on the given link'''
        query_dict = parse_qs(link.query())
        # This dictionary contains lists of strings, we just take the first one in each list
        link_params = {str(k):self.take_first_string(v) for k, v in query_dict.items()}
        self.navigate_to(str(link.path()), link_params)

    @staticmethod
    def take_first_string(param_value):
        '''urllib returns the parameter values as lists, so we need to just take the first one'''
        if param_value and isinstance(param_value, str):
            return param_value
        if param_value and isinstance(param_value, list):
            return str(param_value[0])
        return ""

    def navigate_to(self, path, params=None):
        '''Navigate to the given path with the given params, using our page server'''
        print("Navigate to:", path)
        if path in ('/closewindow', 'http://murmeli/closewindow') and not params:
            self.close()
        elif self.page_server and path:
            self.page_server.serve_page(self.webpane, path, params)
        else:
            print("Cannot navigate to:", path)
