'''Data structures, used only for the scrollbot'''

from datetime import datetime


class DataBuffer:
    '''Ring-buffer of 60 elements'''
    def __init__(self):
        self.buffer = [0] * 60

    def get_value(self, index):
        '''Get the value at the given index'''
        return self.buffer[index % 60]

    def set_value(self, index, value):
        '''Set the value at the given index'''
        self.buffer[index % 60] = value
        self.buffer[(index + 1) % 60] = 0

    def increment_value(self, index, inc):
        '''Add the given increment to the current value at the given index'''
        current_value = self.get_value(index)
        self.set_value(index, current_value + inc)

    def get_range(self, end_index, num_values):
        '''Get a range of values up to the given end_index'''
        result = []
        for index in range(num_values):
            result.append(self.get_value(end_index - num_values + index + 1))
        return result


class SendReceiveData:
    '''Class to hold data about the numbers of messages sent and received'''

    def __init__(self):
        self.send_data = DataBuffer()
        self.receive_data = DataBuffer()
        self._min_for_tests = None

    def _get_minute(self):
        '''Get the current minute value to use'''
        if self._min_for_tests is None:
            return datetime.now().minute
        return self._min_for_tests

    def add_message_received(self):
        '''One message has been received'''
        self.add_messages_received(1)

    def add_messages_received(self, num_msgs):
        '''One or more messages has been received'''
        minute = self._get_minute()
        self.receive_data.increment_value(minute, num_msgs)

    def add_message_sent(self):
        '''One message has been sent'''
        self.add_messages_sent(1)

    def add_messages_sent(self, num_sent):
        '''One or more messages has been sent'''
        minute = self._get_minute()
        self.send_data.increment_value(minute, num_sent)

    def get_data(self):
        '''Get both send and receive data as a tuple of lists'''
        minute = self._get_minute()
        num_values = 17
        return (self.send_data.get_range(minute, num_values),
                self.receive_data.get_range(minute, num_values))

    def set_minute_for_testing(self, minutes):
        '''For testing we don't want to be dependent on timing, so use fixed set values'''
        self._min_for_tests = minutes
