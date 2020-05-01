'''Main window for Murmeli GUI
   Copyright activityworkshop.net and released under the GPL v2.'''

from murmeli.gui import GuiWindow
from murmeli.config import Config
from murmeli.i18n import I18nManager
from murmeli.pages import MurmeliPageServer
from murmeli.system import System


class MainWindow(GuiWindow):
    '''Class for the main GUI window using Qt'''

    def __init__(self, system, *args):
        '''Constructor'''
        GuiWindow.__init__(self)
        self.system = self.ensure_system(system)
        title = self.system.invoke_call(System.COMPNAME_I18N, "get_text",
                                        key="mainwindow.title")
        self.setWindowTitle(title or "Cannot get texts")
        self.show_page("<html><body><h1>Murmeli</h1><p>Welcome to Murmeli.</p></body></html>")
        self.set_page_server(MurmeliPageServer(self.system))
        self.navigate_to("/")

    def finish(self):
        '''Close the window, finish off'''
        if self.system:
            self.system.stop()

    def ensure_system(self, system):
        '''Make sure that we have a complete system'''
        my_system = system or System()
        # Add i18n
        if not my_system.has_component(System.COMPNAME_I18N):
            i18n = I18nManager(my_system)
            my_system.add_component(i18n)
        # Add config
        if not my_system.has_component(System.COMPNAME_CONFIG):
            config = Config(my_system)
            my_system.add_component(config)
        # Use config to activate current language
        my_system.invoke_call(System.COMPNAME_I18N, "set_language")
        return my_system
