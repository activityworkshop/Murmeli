'''Module for testing the data structures of the scrollbot'''

import unittest
from murmeli.scrollbotdata import DataBuffer, SendReceiveData


class DataBufferTest(unittest.TestCase):
    '''Tests for the databuffer'''

    def test_set(self):
        '''Test setting values'''
        buffer = DataBuffer()
        buffer.set_value(13, 4)
        buffer.set_value(22, -1)
        self.assertEqual(0, buffer.get_value(0), "empty value 0")
        self.assertEqual(4, buffer.get_value(13), "set value 4")
        self.assertEqual(-1, buffer.get_value(22), "set value -1")

    def test_set_next(self):
        '''Test effect on next index of setting values'''
        buffer = DataBuffer()
        buffer.set_value(13, 4)
        self.assertEqual(4, buffer.get_value(13), "set value 4")
        buffer.set_value(12, 3)
        self.assertEqual(3, buffer.get_value(12), "set value 3")
        self.assertEqual(0, buffer.get_value(13), "set value back to 0")

    def test_set_beyond(self):
        '''Test setting values with index beyond acceptable range'''
        buffer = DataBuffer()
        buffer.set_value(-1, 10)
        self.assertEqual(10, buffer.get_value(-1), "set value 10")
        self.assertEqual(10, buffer.get_value(59), "set value 10")
        buffer.set_value(60, 11)
        self.assertEqual(11, buffer.get_value(0), "set value 11")
        self.assertEqual(11, buffer.get_value(60), "set value 11")

    def test_increment(self):
        '''Test incrementing values'''
        buffer = DataBuffer()
        buffer.increment_value(19, 4)
        buffer.increment_value(19, 4)
        self.assertEqual(8, buffer.get_value(19), "incremented value 8")
        self.assertEqual(0, buffer.get_value(20), "still zero")

    def test_get_range(self):
        '''Test getting range of values'''
        buffer = DataBuffer()
        buffer.set_value(18, 2)
        buffer.set_value(20, 4)
        result = buffer.get_range(20, 5)
        self.assertEqual([0, 0, 2, 0, 4], result, "range matches")


class SendReceiveDataTest(unittest.TestCase):
    '''Tests for the send and receive data'''

    def test_empty(self):
        '''Test empty values'''
        data = SendReceiveData()
        data.set_minute_for_testing(4)
        send_values, receive_values = data.get_data()
        self.assertEqual(17, len(send_values), "17 send values")
        self.assertEqual(17, len(receive_values), "17 receive values")
        self.assertEqual(0, max(send_values), "all send values 0")
        self.assertEqual(0, max(receive_values), "all receive values 0")

    def test_set(self):
        '''Test setting values'''
        data = SendReceiveData()
        data.set_minute_for_testing(12)
        data.add_message_received()
        data.add_messages_sent(6)
        send_values, receive_values = data.get_data()
        self.assertEqual(17, len(send_values), "17 send values")
        self.assertEqual(17, len(receive_values), "17 receive values")
        self.assertEqual(6, max(send_values), "send values now non-zero")
        self.assertEqual(1, max(receive_values), "receive values now non-zero")
        self.assertEqual(6, send_values[-1], "last send value 6")
        self.assertEqual(1, receive_values[-1], "last receive value 1")

    def test_rollover(self):
        '''Test setting values over the 60-minute boundary'''
        data = SendReceiveData()
        data.set_minute_for_testing(58)
        data.add_message_received()
        data.add_messages_sent(2)
        data.set_minute_for_testing(60)
        data.add_message_received()
        data.add_messages_sent(1)
        data.set_minute_for_testing(1)
        data.add_messages_sent(2)
        data.set_minute_for_testing(2)
        data.add_message_received()
        data.set_minute_for_testing(3)
        send_values, receive_values = data.get_data()
        expected_sends = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2, 0, 1, 2, 0, 0]
        self.assertEqual(expected_sends, send_values, "send range matches")
        expected_receives = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 1, 0, 1, 0]
        self.assertEqual(expected_receives, receive_values, "received range matches")


if __name__ == "__main__":
    unittest.main()
