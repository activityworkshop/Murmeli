'''Main window for Murmeli GUI
   Copyright activityworkshop.net and released under the GPL v2.'''

import os
import shutil
from PyQt5 import QtWidgets, QtGui, QtCore
from murmeli.gui import GuiWindow
from murmeli.config import Config
from murmeli.contacts import Contacts
from murmeli.cryptoclient import CryptoClient
from murmeli import dbutils
from murmeli.i18n import I18nManager
from murmeli.logger import Logger, PlainLogSink
from murmeli.loggergui import GuiLogSink
from murmeli.messagehandler import RegularMessageHandler
from murmeli.pageserver import MurmeliPageServer
from murmeli.postservice import PostService
from murmeli.supersimpledb import MurmeliDb
from murmeli.system import System
from murmeli.torclient import TorClient


VERSION_NUM = 1

class MainWindow(GuiWindow):
    '''Class for the main GUI window using Qt'''

    def __init__(self, system, *args):
        '''Constructor'''
        self.log_panel = GuiLogSink()
        GuiWindow.__init__(self, lower_item=self.log_panel)
        self.resize(650, 450)
        self.system = self.ensure_system(system)
        # we want to be notified of Config changes
        self.system.invoke_call(System.COMPNAME_CONFIG,
                                "add_listener", sub=self)
        self.toolbar_actions = []
        title = self.system.invoke_call(System.COMPNAME_I18N, "get_text",
                                        key="mainwindow.title")
        self.setWindowTitle(title or "Cannot get texts")
        self.clear_web_cache()
        self.toolbar = self.make_toolbar([
            ("toolbar-home.png", self.on_home_clicked, "mainwindow.toolbar.home"),
            ("toolbar-people.png", self.on_contacts_clicked, "mainwindow.toolbar.contacts"),
            ("toolbar-messages.png", self.on_messages_clicked, "mainwindow.toolbar.messages"),
            ("toolbar-settings.png", self.on_settings_clicked, "mainwindow.toolbar.settings")
        ])
        self.addToolBar(self.toolbar)
        self.setContextMenuPolicy(QtCore.Qt.NoContextMenu)
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
        # Add database
        if not my_system.has_component(System.COMPNAME_DATABASE):
            db_file_path = my_system.invoke_call(System.COMPNAME_CONFIG, "get_ss_database_file")
            if os.path.exists(db_file_path):
                database = MurmeliDb(system, db_file_path)
                my_system.add_component(database)
        dbutils.set_own_murmeli_version(my_system.get_component(System.COMPNAME_DATABASE),
                                        VERSION_NUM)
        # Add crypto
        if not my_system.has_component(System.COMPNAME_CRYPTO):
            crypto = CryptoClient(my_system)
            my_system.add_component(crypto)
        if not my_system.has_component(System.COMPNAME_MSG_HANDLER):
            msg_handler = RegularMessageHandler(my_system)
            my_system.add_component(msg_handler)
        # Add tor proxy service
        if not my_system.has_component(System.COMPNAME_TRANSPORT):
            config = my_system.get_component(System.COMPNAME_CONFIG)
            tor_client = TorClient(my_system, config.get_tor_dir(),
                                   config.get_property(config.KEY_TOR_EXE))
            my_system.add_component(tor_client)
        # Add contact list
        if not my_system.has_component(System.COMPNAME_CONTACTS):
            contacts = Contacts(my_system)
            my_system.add_component(contacts)
        # Add post service
        if not my_system.has_component(System.COMPNAME_POSTSERVICE):
            post = PostService(my_system)
            my_system.add_component(post)
        # Add log
        if not my_system.has_component(System.COMPNAME_LOGGING):
            logger = Logger(my_system)
            logger.add_sink(PlainLogSink())
            logger.add_sink(self.log_panel)
            my_system.add_component(logger)
        # Use config to activate current language
        my_system.invoke_call(System.COMPNAME_I18N, "set_language")
        print("Using system:", list(my_system.components))
        return my_system

    def make_toolbar(self, deflist):
        '''Given a list of (image, method, tooltip), make a QToolBar with those actions'''
        toolbar = QtWidgets.QToolBar(self)
        toolbar.setFloatable(False)
        toolbar.setMovable(False)
        toolbar.setIconSize(QtCore.QSize(48, 48))
        self.toolbar_actions = []
        for action_def in deflist:
            action = toolbar.addAction(QtGui.QIcon("images/" + action_def[0]), "_", action_def[1])
            action.tooltip_key = action_def[2]
            self.toolbar_actions.append(action)
        self.config_updated()  # to set the tooltips
        return toolbar

    def clear_web_cache(self):
        '''Delete all the files in the web cache'''
        cache_dir = self.system.invoke_call(System.COMPNAME_CONFIG,
                                            "get_web_cache_dir")
        if cache_dir and os.path.exists(cache_dir):
            shutil.rmtree(cache_dir, ignore_errors=True)
            os.makedirs(cache_dir)

    def on_home_clicked(self):
        '''home button on toolbar clicked'''
        self.navigate_to("/")
    def on_contacts_clicked(self):
        '''contacts button on toolbar clicked'''
        self.navigate_to("/contacts/")
    def on_messages_clicked(self):
        '''messages button on toolbar clicked'''
        self.navigate_to("/messages/")
    def on_settings_clicked(self):
        '''settings button on toolbar clicked'''
        self.navigate_to("/settings/")

    def config_updated(self):
        '''React to changes in config by changing tooltips'''
        self.system.invoke_call(System.COMPNAME_I18N, "set_language")
        for action in self.toolbar_actions:
            tip = self.system.invoke_call(System.COMPNAME_I18N, "get_text", key=action.tooltip_key)
            action.setToolTip(tip)
        if self.system.invoke_call(System.COMPNAME_CONFIG, "get_property",
                                   key=Config.KEY_SHOW_LOG_WINDOW):
            self.log_panel.show()
        else:
            self.log_panel.hide()
