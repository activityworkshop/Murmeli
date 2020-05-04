'''Module for the special pageset for non-html functions'''

import os
from PyQt5.QtWidgets import QFileDialog # for file selection
from murmeli.pages.base import PageSet


class SpecialFunctions(PageSet):
    '''Not delivering pages, but calling special Qt functions such as select file'''
    def __init__(self, system):
        PageSet.__init__(self, system, "special")

    def serve_page(self, view, url, params):
        '''Serve a special function using the given view'''
        if url == "selectprofilepic":
            # Get home directory for file dialog
            homedir = os.path.expanduser("~/")
            fname, _ = QFileDialog.getOpenFileName(view, self.i18n("gui.dialogtitle.openimage"),
                                                   homedir,
                                                   self.i18n("gui.fileselection.filetypes.jpg"))
            if fname:
                # If selected filename has apostrophes in it, these need to be escaped
                if "'" in fname:
                    fname = fname.replace("'", "\\'")
                view.page().runJavaScript("updateProfilePic('%s');" % fname)
        elif url == "friendstorm":
            print("Generate friendstorm")
        else:
            print("Special function:", url, "params:", params)
