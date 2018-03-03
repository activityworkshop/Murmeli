'''Plain logging functionality for Murmeli (without Qt)'''

import os
from murmeli.system import System, Component

LOGLEVEL_DEBUG, LOGLEVEL_NORMAL, LOGLEVEL_WARNING = (0, 1, 2)

class Logger(Component):
    '''Single logger component, which can have one or more sinks'''

    def __init__(self, parent):
        Component.__init__(self, parent, System.COMPNAME_LOGGING)
        self.sinks = []

    def add_sink(self, sink):
        '''Add the given sink to the list'''
        if sink and sink not in self.sinks:
            self.sinks.append(sink)

    def log(self, logstr, log_level=LOGLEVEL_NORMAL):
        '''Log the given string with the given level'''
        for sink in self.sinks:
            sink.log(logstr, log_level)


class PlainLogSink:
    '''Simple log sink, printing to the console'''
    def __init__(self, log_level=LOGLEVEL_NORMAL):
        self.log_level = log_level

    def log(self, logstr, log_level):
        '''Log the given string to the console'''
        if log_level >= self.log_level:
            print(logstr)


class FileLogSink:
    '''Log sink writing to a file'''
    def __init__(self, logpath, log_level=LOGLEVEL_NORMAL):
        self.log_level = log_level
        self.logfile = self.create_logfile(logpath)

    @staticmethod
    def create_logfile(logpath):
        '''Create a new logfile at the given path'''
        os.makedirs(name=logpath, exist_ok=True)
        file_num = 1
        while os.path.exists(FileLogSink.make_logfile_path(logpath, file_num)):
            file_num += 1
        return FileLogSink.make_logfile_path(logpath, file_num)

    @staticmethod
    def make_logfile_path(logpath, file_num):
        '''Make the name of the log file to write, given the number'''
        file_name = "murmeli_%03d.log" % file_num
        return os.path.join(logpath, file_name)

    def log(self, logstr, log_level):
        '''Log the given string to the file'''
        if log_level >= self.log_level and self.logfile:
            with open(self.logfile, "a") as logfile:
                logfile.write(logstr)
                logfile.write("\n")
