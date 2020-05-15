'''Module for composing a new message'''

from murmeli.gui import GuiWindow

# TODO: Maybe this could be moved into gui as an ExtraWindow class
#       as there's nothing left here which is specific to composing

class ComposeWindow(GuiWindow):
    '''Main class for the Compose window'''

    def __init__(self, window_title=None):
        GuiWindow.__init__(self)
        self._setup_ui(window_title)

    def _setup_ui(self, window_title):
        '''Initialise the user interface'''
        self.setObjectName("MainWindow") # TODO: needs to be different from MainWindow?
        self.resize(551, 343)
        # possibly a status bar?
        self.setWindowTitle(window_title or "Murmeli")
