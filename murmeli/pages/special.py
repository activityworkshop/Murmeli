'''Module for the special pageset for non-html functions'''

import os
from PyQt5.QtWidgets import QFileDialog # for file selection
from murmeli.pages.base import PageSet
from murmeli import contactutils
from murmeli import dbutils
from murmeli.brainstorm import StormWindow, FriendStorm


class SpecialFunctions(PageSet):
    '''Not delivering pages, but calling special Qt functions such as select file
       or launching the wobbly network graph'''
    def __init__(self, system):
        PageSet.__init__(self, system, "special")
        self.storm_win = None

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
            database = self.system.get_component(self.system.COMPNAME_DATABASE)
            if dbutils.has_friends(database):
                self.storm_win = self.create_storm_window(database)
                if self.storm_win:
                    self.storm_win.show()
            else:
                print("No friends exist, can't draw storm")
        elif view:
            print("Special function:", url, "params:", params)

    @staticmethod
    def create_storm_window(database):
        '''Create a FriendStorm window using database contents'''
        if not database:
            return None
        own_profile = database.get_profile()
        storm = FriendStorm(own_profile['torid'], own_profile['displayName'])
        # populate storm using database
        for prof in dbutils.get_messageable_profiles(database):
            friend_id = prof.get('torid')
            storm.add_friend(friend_id, prof.get('displayName'))
            # also add friends of friends
            for ff_id, ff_name in contactutils.contacts_from_string(prof.get('contactlist')):
                storm.add_friends_friend(friend_id, ff_id, ff_name)
        # Create window and pass storm to it
        win = StormWindow()
        win.set_storm(storm)
        return win
