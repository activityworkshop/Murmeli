'''Gui Notification'''

from murmeli.system import System, Component


# Notification types
NOTIFY_SYSTEM_STARTING = 0
NOTIFY_TOR_CONNECTED = 1
NOTIFY_FRIEND_ONLINE = 2
NOTIFY_OUTBOX_FLUSHING = 3
NOTIFY_OUTBOX_FLUSHED = 4
NOTIFY_MSG_RECEIVING = 5
NOTIFY_MSG_RECEIVED = 6
NOTIFY_MSG_IN_INBOX = 7
NOTIFY_MSG_SENT = 8


class DefaultGuiNotifier(Component):
    '''Notifier component for system events when Gui is not actually available'''

    def __init__(self, parent):
        Component.__init__(self, parent, System.COMPNAME_GUI)
        print("Using a DefaultGuiNotifier for this headless system")

    def notify_gui(self, notify_type):
        '''Inform the gui that some event has occurred'''
        print("GUI notify:", notify_type)


class GuiNotifier(Component):
    '''Notifier component to inform GUI about system events'''

    def __init__(self, parent_system, gui):
        Component.__init__(self, parent_system, System.COMPNAME_GUI)
        self._gui = gui
        print("Using a GuiNotifier for this regular system")

    def notify_gui(self, notify_type):
        '''Inform the gui that some event has occurred'''
        if self._gui:
            self._gui.notify_gui(notify_type)
