'''Module for testing the logging to console and to file'''

import io
import os
import shutil
import unittest.mock
from murmeli import logger


class LoggingTest(unittest.TestCase):
    '''Tests for the logging'''

    @unittest.mock.patch('sys.stdout', new_callable=io.StringIO)
    def check_console(self, mock_stdout):
        '''Test logging to stdout'''
        log = logger.Logger(None)
        self.assertIsNotNone(log, "created Logger")
        log.add_sink(logger.PlainLogSink())
        log.log("banana")
        log.log("avocado", logger.LOGLEVEL_DEBUG)
        log.log("something normal", logger.LOGLEVEL_NORMAL)
        log.log("something bad", logger.LOGLEVEL_WARNING)
        self.assertEqual(mock_stdout.getvalue(), "Log: banana\nLog: something normal\nLog: something bad\n")

    def test_normal_print_logging(self):
        '''Test regular logging using print calls'''
        self.check_console()

    def test_logging_to_file(self):
        '''Test logging to single file'''
        logdir = os.path.join("test", "outputdata", "log")
        # Delete the log directory
        shutil.rmtree(logdir, ignore_errors=True)
        first_logfile = os.path.join("test", "outputdata", "log", "murmeli_001.log")
        self.assertFalse(os.path.exists(first_logfile), "log not there yet")
        # Make logger just for warnings
        log = logger.Logger(None)
        log.add_sink(logger.FileLogSink("test/outputdata/log", logger.LOGLEVEL_WARNING))
        # write log entries
        log.log("normal message")
        log.log("tiny debugging help", logger.LOGLEVEL_DEBUG)
        log.log("another normal message", logger.LOGLEVEL_NORMAL)
        log.log("warning about sharks", logger.LOGLEVEL_WARNING)
        log.log("warning about nettles", logger.LOGLEVEL_WARNING)
        # file should exist now
        self.assertTrue(os.path.exists(first_logfile), "log file created")

        with open(first_logfile, "r") as check_stream:
            all_log_lines = check_stream.readlines()

        self.assertFalse(any("normal" in line for line in all_log_lines), "no normals logged")
        self.assertFalse(any("debug" in line for line in all_log_lines), "no debugs logged")
        self.assertTrue(any("warning" in line for line in all_log_lines), "warnings logged")
        self.assertTrue(any("shark" in line for line in all_log_lines), "shark logged")
        self.assertTrue(any("nettle" in line for line in all_log_lines), "nettles logged")


if __name__ == "__main__":
    unittest.main()
