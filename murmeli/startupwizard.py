'''Startup wizard for Murmeli
   Copyright activityworkshop.net and released under the GPL v2.'''

import os
import time
import re
from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtWidgets import QMessageBox
from murmeli.system import System
from murmeli.config import Config
from murmeli.i18n import I18nManager
from murmeli.cryptoclient import CryptoClient
from murmeli.supersimpledb import MurmeliDb
from murmeli.torclient import TorClient


class StartupWizard(QtWidgets.QMainWindow):
    '''Class to act as the main startup wizard using Qt'''

    def __init__(self, system, *args):
        '''Constructor'''
        QtWidgets.QMainWindow.__init__(*(self,) + args)
        self.system = self.ensure_minimal_system(system)
        self.murmeli_window = None

        title = self.get_text("startupwizard.title")
        self.setWindowTitle(title or "Cannot get texts")

        # main pane with the stack and the button panel
        mainpane = QtWidgets.QWidget(self)
        mainlayout = QtWidgets.QVBoxLayout()
        mainpane.setLayout(mainlayout)
        self.setCentralWidget(mainpane)

        i18n = self.system.get_component(System.COMPNAME_I18N)
        config = self.system.get_component(System.COMPNAME_CONFIG)
        self.card_stack = QtWidgets.QStackedWidget(mainpane)
        self.card_panels = [IntroPanel(i18n, config), DependenciesPanel(i18n),
                            PathsPanel(i18n, config), ServicesPanel(self.system),
                            KeygenPanel(self.system), FinishedPanel(self.system)]
        for card in self.card_panels:
            panel = card.get_panel()
            self.card_stack.addWidget(panel)
            card.redraw_navbuttons_signal.connect(self.redraw_buttons)

        # button panel at the bottom
        button_panel = QtWidgets.QFrame(self.card_stack)
        button_panel.setFrameStyle(QtWidgets.QFrame.Box + QtWidgets.QFrame.Sunken)
        self.back_button = QtWidgets.QPushButton(i18n.get_text("button.exit"))
        self.next_button = QtWidgets.QPushButton(i18n.get_text("button.next"))
        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(self.back_button)
        layout.addStretch(1)
        layout.addWidget(self.next_button)
        button_panel.setLayout(layout)

        self.back_button.clicked.connect(self.back_button_clicked)
        self.next_button.clicked.connect(self.next_button_clicked)

        mainlayout.addWidget(self.card_stack)
        mainlayout.addWidget(button_panel)
        self.next_button.setFocus()

    @staticmethod
    def ensure_minimal_system(system):
        '''Make sure that we have a minimal system to start the wizard'''
        minimal_system = system or System()
        # Add i18n
        if not minimal_system.has_component(System.COMPNAME_I18N):
            i18n = I18nManager(minimal_system)
            minimal_system.add_component(i18n)
        # Add config
        if not minimal_system.has_component(System.COMPNAME_CONFIG):
            config = Config(minimal_system)
            minimal_system.add_component(config)
        minimal_system.invoke_call(System.COMPNAME_I18N, "set_language")
        return minimal_system

    def back_button_clicked(self):
        '''Called when the 'Back' or 'Exit' buttons are pressed'''
        curr_index = self.card_stack.currentIndex()
        if curr_index == 0:
            # Back from the first card means exit
            self.system.stop()
            self.close()
        else:
            self.card_panels[curr_index].cancel()
            self.card_panels[curr_index-1].prepare()
            self.enable_buttons(self.card_panels[curr_index-1])
            self.card_stack.setCurrentIndex(curr_index - 1)

    def next_button_clicked(self):
        '''Called when the 'Next' or 'Finish' buttons are pressed'''
        curr_index = self.card_stack.currentIndex()
        curr_card = self.card_panels[curr_index]
        if curr_card.finish():
            # Card was successful, so we can go forward
            try:
                # prepare the coming tab, if necessary
                self.card_panels[curr_index + 1].prepare()
                self.card_panels[curr_index + 1].redraw_labels()
                self.card_stack.setCurrentIndex(curr_index + 1)
                self.enable_buttons(self.card_panels[curr_index + 1])
            except IndexError:  # we've gone past the end of the wizard, time to quit
                # Launch Murmeli
                print("Launching Murmeli now...")
                # close this wizard but keep Tor, Db running
                self.close()

    def enable_buttons(self, card):
        '''Ask the card what the button texts and enabled status should be'''
        back_key, next_key = card.get_button_keys()
        self.back_button.setText(self.get_text("button." + back_key))
        self.next_button.setText(self.get_text("button." + next_key))
        back_enabled, next_enabled = card.get_buttons_enabled()
        self.back_button.setEnabled(back_enabled)
        self.next_button.setEnabled(next_enabled)

    def get_text(self, text_key):
        '''Use the i18n to translate the given key'''
        return self.system.invoke_call(System.COMPNAME_I18N, "get_text", key=text_key)

    def redraw_buttons(self):
        '''Change the texts of the back/next buttons and enable them both'''
        curr_index = self.card_stack.currentIndex()
        curr_card = self.card_panels[curr_index]
        self.enable_buttons(curr_card)

    def finish(self):
        '''Close the window, close down the system'''
        if self.system:
            self.system.stop()


# ================WizardPanel===================

class WizardPanel(QtCore.QObject):
    '''Superclass of each of the panels in the wizard'''
    redraw_navbuttons_signal = QtCore.pyqtSignal()
    def __init__(self, i18n):
        QtCore.QObject.__init__(self)
        self.i18n = i18n
        self.labels = {}
    def get_panel(self):
        '''Override in each subclass to provide the panel to show'''
        return QtWidgets.QLabel("<i>TODO</i>")
    def prepare(self):
        '''Prepare to show this panel'''
        pass
    def finish(self):
        '''The current panel has been finished, save possible changes'''
        return True
    def cancel(self):
        '''The current panel has been cancelled, cancel whatever was done'''
        pass
    def get_text(self, text_key):
        '''Use the i18n to translate the given key'''
        return self.i18n.get_text(text_key) if self.i18n else text_key

    def _make_heading_label(self, token):
        '''Convenience method for making a bold label for each panel'''
        label = QtWidgets.QLabel(self.get_text(token))
        self._make_label_heading(label)
        return label

    def _make_label_heading(self, label):
        '''Convenience method for making an existing label bold for headings'''
        bold_font = label.font()
        bold_font.setWeight(QtGui.QFont.Bold)
        bold_font.setPointSize(bold_font.pointSize() + 1)
        label.setFont(bold_font)

    def get_button_keys(self):
        return ("back", "next")
    def get_buttons_enabled(self):
        return (True, True)

    def redraw_labels(self):
        '''Reset the texts for all labels if the language changes'''
        for label_key in list(self.labels.keys()):
            text_key = "startupwizard." + self.get_name() + "." + label_key
            self.labels[label_key].setText(self.get_text(text_key))


# ================Intro===================

class IntroPanel(WizardPanel):
    '''First panel for introduction with a logo'''
    def __init__(self, i18n, config):
        WizardPanel.__init__(self, i18n)
        self.config = config
        self.language_combo = None
    def get_name(self):
        return "intro"
    def get_panel(self):
        '''create the first panel, for introduction'''
        panel = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()
        # Make labels in advance
        self.labels = {}
        for label_name in ["heading", "description1", "description2", "description3"]:
            self.labels[label_name] = QtWidgets.QLabel()
        self._make_label_heading(self.labels["heading"])
        layout.addWidget(self.labels["heading"])
        self.labels["description1"].setWordWrap(True)
        layout.addWidget(self.labels["description1"])
        # language selection
        lang_frame = QtWidgets.QWidget()
        lang_layout = QtWidgets.QHBoxLayout()
        lang_frame.setLayout(lang_layout)
        self.language_combo = QtWidgets.QComboBox()
        self.language_combo.addItem("English")
        self.language_combo.addItem("Deutsch")
        self.language_combo.setCurrentIndex(0)
        self.language_combo.currentIndexChanged.connect(self.language_changed)
        lang_layout.addStretch(1)
        lang_layout.addWidget(self.language_combo)
        layout.addWidget(lang_frame)
        # image
        logoimage = QtWidgets.QLabel()
        logoimage.setPixmap(QtGui.QPixmap("images/intrologo.png"))
        logoimage.setAlignment(QtCore.Qt.AlignHCenter) # horizontally centred
        layout.addWidget(logoimage)
        self.labels["description2"].setWordWrap(True)
        layout.addWidget(self.labels["description2"])
        self.labels["description3"].setWordWrap(True)
        layout.addWidget(self.labels["description3"])
        panel.setLayout(layout)
        # fill in the texts
        self.redraw_labels()
        return panel

    def language_changed(self):
        '''React to a change in the language dropdown'''
        selected_lang = ["en", "de"][self.language_combo.currentIndex()]
        self.config.set_property(self.config.KEY_LANGUAGE, selected_lang)
        self.redraw_labels()
        self.redraw_navbuttons_signal.emit()

    def get_button_keys(self):
        '''exit button, not back'''
        return ("exit", "next")


# ================Dependencies===================

class DependenciesPanel(WizardPanel):
    '''Second panel for checking dependencies'''
    def __init__(self, i18n):
        WizardPanel.__init__(self, i18n)
        # some resources
        self.yes_pixmap = QtGui.QPixmap("images/tick-yes.png")
        self.no_pixmap = QtGui.QPixmap("images/tick-no.png")
        self.dependency_check_label = None
        self.dependency_labels = []
        self.all_found = False

    def get_name(self):
        return "dependencies"

    def get_panel(self):
        '''second panel, for dependencies'''
        panel = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()
        self.labels = {}
        for k in ["heading", "intro", "pyqt", "gnupg", "alsotor"]:
            self.labels[k] = QtWidgets.QLabel()
        self._make_label_heading(self.labels["heading"])
        layout.addWidget(self.labels["heading"])
        layout.addStretch(1)
        layout.addWidget(self.labels["intro"])
        depsbox = QtWidgets.QFrame(panel)
        sublayout = QtWidgets.QFormLayout()
        dep_keys = ['pyqt', 'gnupg']
        self.dependency_labels = [QtWidgets.QLabel() for k in dep_keys]
        for i, k in enumerate(dep_keys):
            sublayout.addRow(self.labels[k], self.dependency_labels[i])
            self.dependency_labels[i].depkey = k
        depsbox.setLayout(sublayout)
        sublayout.setFormAlignment(QtCore.Qt.AlignHCenter) # horizontally centred
        layout.addWidget(depsbox)
        layout.addSpacing(20)
        self.dependency_check_label = self._make_heading_label("")
        layout.addWidget(self.dependency_check_label)
        layout.addWidget(self.labels["alsotor"])
        layout.addStretch(1)
        panel.setLayout(layout)
        return panel

    def prepare(self):
        '''When going from the intro page to the dependencies page, this needs to be updated'''
        deps_found = {'pyqt':True}  # PyQt must be present, otherwise we wouldn't be here!
        self.all_found = True
        try:
            from gnupg import GPG
            deps_found["gnupg"] = True
        except ImportError:
            self.all_found = False

        # Update the ticks and crosses
        for label in self.dependency_labels:
            found = deps_found.get(label.depkey, False)
            label.setPixmap(self.yes_pixmap if found else self.no_pixmap)
            key = "startupwizard.dep.found" if found else "startupwizard.dep.notfound"
            label.setToolTip(self.get_text(key))

        # if not all dependencies are there, show the message
        key = "allfound" if self.all_found else "notallfound"
        self.dependency_check_label.setText(self.get_text("startupwizard.dependencies." + key))

    def get_buttons_enabled(self):
        return (True, self.all_found)


# ================Paths=====================

class PathsPanel(WizardPanel):
    '''Third panel for confirming or changing paths'''
    def __init__(self, i18n, config):
        WizardPanel.__init__(self, i18n)
        self.config = config
        self.data_dir_field = None
        self.tor_path_field = None
        self.gpg_path_field = None

    def get_name(self):
        return "paths"

    def get_panel(self):
        '''third panel, for paths'''
        panel = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()
        self.labels = {}
        for k in ["heading", "configfile", "datadir", "torexe", "gpgexe", "considerencryption"]:
            self.labels[k] = QtWidgets.QLabel()
        self._make_label_heading(self.labels["heading"])
        layout.addWidget(self.labels["heading"])
        filepathbox = QtWidgets.QFrame(panel)
        sublayout = QtWidgets.QFormLayout()
        sublayout.setSpacing(20)
        # Path to config file (read-only, can't be changed)
        sublayout.addRow(self.labels["configfile"], QtWidgets.QLabel(Config.CONFIG_FILE_PATH))
        # Path to data directory (input)
        datadir = self.config.get_property(Config.KEY_DATA_DIR)
        if not datadir:
            datadir = Config.DEFAULT_DATA_PATH
        self.data_dir_field = QtWidgets.QLineEdit(datadir)
        sublayout.addRow(self.labels["datadir"], self.data_dir_field)
        # Path to tor exe (input)
        self.tor_path_field = QtWidgets.QLineEdit("tor")
        sublayout.addRow(self.labels["torexe"], self.tor_path_field)
        # Path to gnupg exe (input)
        self.gpg_path_field = QtWidgets.QLineEdit("gpg")
        sublayout.addRow(self.labels["gpgexe"], self.gpg_path_field)
        # MAYBE: Could we check whether these paths exist, and guess alternative ones if not?
        # TODO: Browse buttons to select exes and directory
        filepathbox.setLayout(sublayout)
        sublayout.setFormAlignment(QtCore.Qt.AlignHCenter) # horizontally centred
        layout.addWidget(filepathbox)
        layout.addWidget(self.labels["considerencryption"])
        layout.addStretch(1)
        panel.setLayout(layout)
        return panel

    def finish(self):
        '''Called when leaving the paths page'''
        datadir = str(self.data_dir_field.text())
        self.config.set_property(Config.KEY_DATA_DIR, datadir)
        # Make sure all the directories exist, create them if not
        try:
            for direc in [self.config.get_database_dir(), self.config.get_web_cache_dir(), \
                          self.config.get_keyring_dir(), self.config.get_tor_dir()]:
                if not os.path.exists(direc):
                    os.makedirs(direc)
        except OSError as ose:
            print(ose)
            # Couldn't create one of the directories, so show error and stay on this panel
            QMessageBox.critical(None,
                                 self.get_text("gui.dialogtitle.error"),
                                 self.get_text("startupwizard.paths.failedtocreatedatadir"))
            return False
        # Also store selected paths to exes
        # TODO: Check the exes exist?
        self.config.set_property(Config.KEY_TOR_EXE, str(self.tor_path_field.text()))
        self.config.set_property(Config.KEY_GPG_EXE, str(self.gpg_path_field.text()))
        self.config.save()
        return True


# ================Services=====================

class ServicesPanel(WizardPanel):
    '''Wizard panel for the services page'''
    def __init__(self, system):
        WizardPanel.__init__(self, system.get_component(System.COMPNAME_I18N))
        self.system = system
        # some resources
        self.yes_pixmap = QtGui.QPixmap("images/tick-yes.png")
        self.no_pixmap = QtGui.QPixmap("images/tick-no.png")
        self.blank_pixmap = QtGui.QPixmap("images/tick-blank.png")
        self.services_check_label = None
        self.services_labels = []
        self.checks_done = False
        self.all_ok = False
        self.checker_thread = None

    def get_name(self):
        return "services"

    def get_panel(self):
        '''fourth panel, for services'''
        panel = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()
        self.labels = {}
        for k in ["heading", "intro", "database", "gpg", "tor", "abouttostart"]:
            self.labels[k] = QtWidgets.QLabel()
        self._make_label_heading(self.labels["heading"])
        layout.addWidget(self.labels["heading"])
        layout.addStretch(1)
        layout.addWidget(self.labels["intro"])
        servicesbox = QtWidgets.QFrame(panel)
        sublayout = QtWidgets.QFormLayout()
        services_keys = ['database', 'gpg', 'tor']
        self.services_labels = [QtWidgets.QLabel() for k in services_keys]
        for i, k in enumerate(services_keys):
            sublayout.addRow(self.labels[k], self.services_labels[i])
            self.services_labels[i].servicekey = k
            self.services_labels[i].setPixmap(self.blank_pixmap)
        servicesbox.setLayout(sublayout)
        sublayout.setFormAlignment(QtCore.Qt.AlignHCenter) # horizontally centred
        layout.addWidget(servicesbox)
        layout.addSpacing(10)
        layout.addWidget(self.labels["abouttostart"])
        layout.addSpacing(10)
        self.services_check_label = self._make_heading_label("")
        layout.addWidget(self.services_check_label)
        layout.addStretch(1)
        panel.setLayout(layout)
        return panel

    def get_buttons_enabled(self):
        '''disable navigation until checks done'''
        return (self.checks_done, self.all_ok)

    def prepare(self):
        '''Blank out the services tab and start the checking thread'''
        self.all_ok = False
        self.checks_done = False
        self.labels["abouttostart"].setVisible(True)
        # If we're coming back to this panel, remove the components again
        self.cancel()
        # Blank the ticks and crosses
        for label in self.services_labels:
            label.setPixmap(self.blank_pixmap)
        # start checking services
        self.checker_thread = ServiceStarterThread(self.system)
        # Connect signals and slots so we know what's happened
        self.checker_thread.finished.connect(self.finished_service_check)
        self.checker_thread.updated_signal.connect(self.updated_service_check)
        self.checker_thread.start()

    def updated_service_check(self):
        '''Called when service check has been updated (not yet completed) by the other thread'''
        services_keys = ['database', 'gpg', 'tor']
        for i, k in enumerate(services_keys):
            success = self.checker_thread.success_flags.get(k)
            self.services_labels[i].setPixmap(self.get_pixmap_for_success(success))

    def get_pixmap_for_success(self, success):
        '''Get the pixmap for the given success value'''
        if success is None:
            return self.blank_pixmap
        return self.yes_pixmap if success else self.no_pixmap

    def finished_service_check(self):
        '''Called when service check has been completed by the other thread'''
        self.updated_service_check()  # make sure all icons are updated
        self.checks_done = True
        self.all_ok = self.checker_thread.all_good()
        token = "startupwizard.services." + ("allstarted" if self.all_ok else "notallstarted")
        self.services_check_label.setText(self.get_text(token))
        self.labels["abouttostart"].setVisible(False)
        # emit signal back to controller
        self.redraw_navbuttons_signal.emit()

    def cancel(self):
        '''Coming back from services start - need to stop them'''
        for comp_name in [System.COMPNAME_DATABASE, System.COMPNAME_TRANSPORT]:
            self.system.remove_component(comp_name)


class ServiceStarterThread(QtCore.QThread):
    '''Separate thread for starting the services and reporting back'''
    updated_signal = QtCore.pyqtSignal()
    def __init__(self, system):
        QtCore.QThread.__init__(self)
        self.system = system
        self.success_flags = {}

    def run(self):
        '''Check each of the services in turn'''
        self.success_flags = {}
        # Database
        time.sleep(0.5)
        db_file_path = self.system.invoke_call(System.COMPNAME_CONFIG, "get_ss_database_file")
        database = MurmeliDb(self.system, db_file_path)
        self.system.add_component(database)
        self.success_flags['database'] = True
        database.save_to_file()
        self.updated_signal.emit()
        time.sleep(0.5)
        # Gnupg
        if not self.system.has_component(System.COMPNAME_CRYPTO):
            crypto = CryptoClient(self.system)
            self.system.add_component(crypto)
        gpg_version = self.system.invoke_call(System.COMPNAME_CRYPTO, "get_gpg_version")
        self.success_flags['gpg'] = True if gpg_version else False
        self.updated_signal.emit()
        time.sleep(1)
        # Tor
        if not self.system.has_component(System.COMPNAME_TRANSPORT):
            print("Need to create tor client")
            tor_dir = self.system.invoke_call(System.COMPNAME_CONFIG, "get_tor_dir")
            tor_path = self.system.invoke_call(System.COMPNAME_CONFIG, "get_property",
                                               key=Config.KEY_TOR_EXE)
            tor_client = TorClient(self.system, tor_dir, tor_path)
            self.system.add_component(tor_client)
        if self.system.invoke_call(System.COMPNAME_TRANSPORT, "is_started"):
            torid = self.system.invoke_call(System.COMPNAME_TRANSPORT, "get_own_torid")
            if torid:
                print("Started tor, our own id is: ", torid)
                self.success_flags['tor'] = True
            else:
                print("Failed to start tor")
                self.success_flags['tor'] = False
        else:
            print("startTor returned false :(")
            self.success_flags['tor'] = False

    def all_good(self):
        '''Check whether all have been started'''
        return self.success_flags.get('database', False) \
            and self.success_flags.get('gpg', False) \
            and self.success_flags.get('tor', False)


# ================Key generation=====================

class KeygenPanel(WizardPanel):
    '''Panel for generation of own keypair'''
    def __init__(self, system):
        WizardPanel.__init__(self, system.get_component(System.COMPNAME_I18N))
        self.system = system
        self.keypair_list_widget = None
        self.keygen_box = None
        self.keygen_param_boxes = None
        self.generate_button = None
        self.generate_progressbar = None
        self.private_keys = None
        self.keygen_thread = None

    def get_name(self):
        return "keygen"

    def get_panel(self):
        '''fifth panel, for generating or selecting keypair'''
        panel = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()
        self.labels = {}
        for k in ["heading", "introemptykeyring", "introsinglekey", "introselectkey",
                  "param.name", "param.email", "param.comment", "mighttakeawhile"]:
            self.labels[k] = QtWidgets.QLabel()
        self._make_label_heading(self.labels["heading"])
        layout.addWidget(self.labels["heading"])
        layout.addStretch(0.3)
        layout.addWidget(self.labels["introemptykeyring"])
        layout.addWidget(self.labels["introsinglekey"])
        layout.addWidget(self.labels["introselectkey"])
        # list of keypairs already in the keyring
        self.keypair_list_widget = QtWidgets.QListWidget()
        layout.addWidget(self.keypair_list_widget)
        # parameters for generation of new keypair
        self.keygen_box = QtWidgets.QFrame(panel)
        sublayout = QtWidgets.QFormLayout()
        self.keygen_param_boxes = {}
        for param in ['name', 'email', 'comment']:  # (no password)
            editbox = QtWidgets.QLineEdit()
            self.keygen_param_boxes[param] = editbox
            sublayout.addRow(self.labels["param." + param], editbox)
        self.keygen_box.setLayout(sublayout)
        sublayout.setFormAlignment(QtCore.Qt.AlignHCenter) # horizontally centred
        layout.addWidget(self.keygen_box)
        # 'Generate' button
        self.generate_button = QtWidgets.QPushButton(self.get_text("button.generate"))
        self.generate_button.clicked.connect(self.generate_clicked)
        layout.addWidget(self.generate_button)
        # Progress bar (actually more of an hourglass)
        self.generate_progressbar = QtWidgets.QProgressBar()
        self.generate_progressbar.setVisible(False)
        self.generate_progressbar.setMinimum(0)
        self.generate_progressbar.setMaximum(0)
        progress_panel = QtWidgets.QFrame()
        sublayout = QtWidgets.QHBoxLayout()
        sublayout.addStretch(0.4)
        sublayout.addWidget(self.generate_progressbar)
        sublayout.addStretch(0.4)
        progress_panel.setLayout(sublayout)
        layout.addWidget(progress_panel)
        # Label to say that it might take a minute or two
        layout.addWidget(self.labels["mighttakeawhile"])
        layout.addStretch(1)
        panel.setLayout(layout)
        return panel

    def prepare(self):
        '''Called before showing the keypair page'''
        self.private_keys = self.system.invoke_call(System.COMPNAME_CRYPTO, "get_keys",
                                                    private_keys=True)
        num_keys = len(self.private_keys)
        self.labels["introemptykeyring"].setVisible(num_keys == 0)
        self.labels["introsinglekey"].setVisible(num_keys == 1)
        self.labels["introselectkey"].setVisible(num_keys > 1)
        self.generate_progressbar.setVisible(False)
        self.labels["mighttakeawhile"].setVisible(False)
        self.keypair_list_widget.clear()
        for k in self.private_keys:
            name = k['uids']
            if isinstance(name, list):
                name = str(name[0])
            self.keypair_list_widget.addItem("%s - %s (%s)" % (k['keyid'], name, k['length']))
        self.keypair_list_widget.setVisible(num_keys > 0)
        self.keypair_list_widget.setCurrentRow(self.keypair_list_widget.count() - 1)
        # Hide generation option if we've got a key already
        self.keygen_box.setVisible(num_keys == 0)
        self.generate_button.setVisible(num_keys == 0)

    def finish(self):
        '''Finished the key generation / selection'''
        # Store key, name in the database for our own profile
        selected_key = self.private_keys[self.keypair_list_widget.currentRow()]
        ownid = self.system.invoke_call(System.COMPNAME_TRANSPORT, "get_own_torid")
        # See if a name was entered before, if so use that
        myname = self.keygen_param_boxes['name'].text()
        if not myname:
            # Extract the name from the string which comes back from the key
            # format is like "'Some Name (no comment) <no@email.com>'"
            myname = self.extract_name(selected_key['uids'])
        profile = {"name":myname, "keyid":selected_key['keyid'], "torid":ownid,
                   "status":"self", "ownprofile":True}
        # Store this in the database
        updated = self.system.invoke_call(System.COMPNAME_DATABASE, "add_or_update_profile",
                                          profile=profile)
        self.system.invoke_call(System.COMPNAME_DATABASE, "save_to_file")
        return updated

    @staticmethod
    def extract_name(gpg_name):
        '''Extract just the name from a GPG key identifier'''
        if isinstance(gpg_name, list):
            name = str(gpg_name[0])
        else:
            name = str(gpg_name)
        if name.startswith("'") and name.endswith("'"):
            name = name[1:-1]
        if "<" in name and ">" in name and "@" in name:
            reduced_name = re.sub("<.+@.+>", "", name)
            # Don't remove this bit if it would leave the result blank
            if reduced_name:
                name = reduced_name
        if "(" in name and ")" in name:
            name = re.sub(r"\(.+\)", "", name)
        return name.strip()

    def generate_clicked(self):
        '''Called when 'generate' button is clicked to make a new keypair'''
        self.generate_button.setEnabled(False)
        self.generate_progressbar.setVisible(True)
        self.labels["mighttakeawhile"].setVisible(True)
        # Get parameters out of form and substitute for blanks
        name = self.keygen_param_boxes['name'].text() or "no name"
        email = self.keygen_param_boxes['email'].text() or "no@email.com"
        comment = self.keygen_param_boxes['comment'].text() or "no comment"
        # Launch new keygen thread
        crypto = self.system.get_component(System.COMPNAME_CRYPTO)
        self.keygen_thread = KeyGenThread(crypto, name, email, comment)
        self.keygen_thread.finished.connect(self.finished_keygen)
        self.keygen_thread.start()

    def finished_keygen(self):
        '''React to finishing a key generation'''
        self.generate_button.setEnabled(True)
        # Update list with new key
        self.prepare()
        self.redraw_navbuttons_signal.emit()

    def get_buttons_enabled(self):
        return (True, self.keypair_list_widget.count() > 0)


class KeyGenThread(QtCore.QThread):
    '''Separate thread for calling the key generation and reporting back'''
    def __init__(self, crypto, name, email, comment):
        QtCore.QThread.__init__(self)
        self.crypto = crypto
        self.name = name
        self.email = email
        self.comment = comment
        self.keypair = None

    def run(self):
        '''Run the thread'''
        self.keypair = self.crypto.generate_key_pair(self.name, self.email, self.comment)

    def get_key(self):
        '''Get the generated key'''
        return self.keypair


# ================Finished=====================

class FinishedPanel(WizardPanel):
    '''Last panel, just to confirm that the wizard is finished'''
    def __init__(self, system):
        WizardPanel.__init__(self, system.get_component(System.COMPNAME_I18N))
        self.system = system
        self.yourid_label = None

    def get_name(self):
        return "finished"

    def get_panel(self):
        '''last panel, for confirmation that everything's complete'''
        panel = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()
        self.labels = {}
        for k in ["heading", "congrats", "nowstart"]:
            self.labels[k] = QtWidgets.QLabel()
        self._make_label_heading(self.labels["heading"])
        layout.addWidget(self.labels["heading"])
        layout.addStretch(1)
        layout.addWidget(self.labels["congrats"])
        layout.addWidget(self.labels["nowstart"])
        self.yourid_label = QtWidgets.QLabel()
        layout.addWidget(self.yourid_label)
        layout.addStretch(1)
        panel.setLayout(layout)
        return panel

    def prepare(self):
        '''Prepare the final panel'''
        torid = self.system.invoke_call(System.COMPNAME_TRANSPORT, "get_own_torid")
        text = self.get_text("startupwizard.finished.yourid") % torid
        self.yourid_label.setText(text)
        # TODO: If this is just a label, then it can't be selected and copied
        # - should it be a disabled text field instead?

    def get_button_keys(self):
        return ("back", "finish")

    def get_buttons_enabled(self):
        return (False, True)


# ==========================================

if __name__ == "__main__":
    # Get ready to launch a Qt GUI
    APP = QtWidgets.QApplication([])

    WIN = StartupWizard(None)
    WIN.show()

    APP.exec_()
