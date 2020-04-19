'''Module for testing the gui notifiers'''

import unittest
import time
from murmeli import robot
from murmeli.guinotification import GuiNotifier


class RobotNotifierTest(unittest.TestCase):
    '''Tests for the robot notifier'''

    def test_robot_notifier(self):
        '''Test what happens when a notifier is instantiated and called'''
        notifier = robot.RobotNotifier(None)
        notifier.start()
        notifier.notify_gui(0)
        notifier.notify_gui(1)
        time.sleep(1) # Just to give time to see what the LEDs are doing
        notifier.stop()


class FakeGui:
    '''Spy to check that correct methods are called on the gui'''
    def __init__(self):
        self.received = set()
    def notify_gui(self, value):
        '''Receive a value through the notifier'''
        self.received.add(value)


class GuiNotifierTest(unittest.TestCase):
    '''Tests for the gui notifier'''

    def test_gui_notifier(self):
        '''Test what happens when a notifier is instantiated and called'''
        spy = FakeGui()
        notifier = GuiNotifier(None, spy)
        notifier.start()
        notifier.notify_gui(0)
        notifier.notify_gui(1)
        notifier.stop()
        self.assertEqual(spy.received, set([0, 1]), "both 0 and 1 received")


if __name__ == "__main__":
    unittest.main()
