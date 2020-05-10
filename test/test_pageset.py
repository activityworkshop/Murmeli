''''Testing of the page set base functionality'''

import unittest
import datetime
from murmeli.pages.base import PageSet
from murmeli.system import System, Component


class FakeI18n(Component):
    '''Fake internationalisation'''
    def __init__(self, parent):
        Component.__init__(self, parent, System.COMPNAME_I18N)

    @staticmethod
    def get_text(key):
        '''Get the i18n of the key if found, otherwise return the key'''
        return key

    @staticmethod
    def get_all_texts():
        '''Not needed for these tests'''
        return None


class BasePageSetTest(unittest.TestCase):
    '''Tests for the base pageset'''

    def __init__(self, methodName='runTest'):
        unittest.TestCase.__init__(self, methodName)
        self.system = None

    def setUp(self):
        '''Get ready for tests'''
        self.system = System()
        i18n = FakeI18n(self.system)
        self.system.add_component(i18n)

    def tearDown(self):
        '''Clean up after tests'''
        self.system = None

    def test_empty_timestamps(self):
        '''Check that getting the timestamp string from an empty timestamp doesn't fail'''
        pageset = PageSet(self.system, "base")
        from_none = pageset.make_local_time_string(None)
        self.assertEqual("", from_none)
        from_empty = pageset.make_local_time_string("")
        self.assertEqual("", from_empty)
        from_self = pageset.make_local_time_string(self)
        self.assertEqual("", from_self)

    def test_nonempty_timestamps(self):
        '''Check that getting the timestamp string from strings and numbers succeeds'''
        pageset = PageSet(self.system, "base")
        from_number = pageset.make_local_time_string(1234567890.0)
        self.assertEqual('2009-02-14 00:31', from_number)
        from_string = pageset.make_local_time_string('something')
        self.assertEqual('something', from_string)

    def test_today_timestamps(self):
        '''Check that getting the timestamp string from today succeeds'''
        pageset = PageSet(self.system, "base")
        now = datetime.datetime.now()
        nine_thirty = datetime.datetime(now.year, now.month, now.day, 9, 30, 0)
        from_today = pageset.make_local_time_string(nine_thirty.timestamp())
        self.assertEqual('09:30', from_today)

    def test_yesterday_timestamps(self):
        '''Check that getting the timestamp string from yesterday succeeds'''
        pageset = PageSet(self.system, "base")
        now = datetime.datetime.now()
        threepm = datetime.datetime(now.year, now.month, now.day, 15, 0, 0)
        threepm -= datetime.timedelta(days=1)
        from_yesterday = pageset.make_local_time_string(threepm.timestamp())
        self.assertEqual('messages.sendtime.yesterday 15:00', from_yesterday)


if __name__ == "__main__":
    unittest.main()
