'''Logging functionality in a window pane for Murmeli (with Qt)'''

from PyQt5.QtWidgets import QTextEdit
from PyQt5.QtCore import pyqtSignal
from murmeli import logger


class GuiLogSink(QTextEdit):
    '''Log sink, printing to a gui element in a Qt window'''

    updateSignal = pyqtSignal(str)

    def __init__(self, log_level=logger.LOGLEVEL_NORMAL):
        QTextEdit.__init__(self)
        self.setReadOnly(True)
        self.log_level = log_level
        self.updateSignal.connect(self._async_log)
        self.log("Murmeli", self.log_level)

    def log(self, logstr, log_level):
        '''Log the given string to the window'''
        if log_level >= self.log_level:
            self.updateSignal.emit(logstr)

    def _async_log(self, logstr):
        '''Add log to the window, but do it asynchronously in the gui thread'''
        self.append(logstr)
