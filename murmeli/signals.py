'''Simple signal and timer functionality to remove dependency on Qt'''

import threading
import time

class Signal:
    '''A signal which can be connected to one or more listeners'''

    def __init__(self):
        self._listeners = []

    def clear(self):
        '''Clear all the listeners'''
        self._listeners.clear()

    def connect(self, listener):
        '''Connect this signal to an additional listener'''
        if listener:
            self._listeners.append(listener)

    def fire(self):
        '''Fire the signal to each of the listeners in turn'''
        for listener in self._listeners:
            listener()


class Timer:
    '''Calls a given method either repeatedly or after a given period'''
    def __init__(self, delay, target, repeated=True):
        self.delay = delay
        self.target = target
        self.repeated = repeated
        self.running = True
        threading.Thread(target=self.run).start()

    def run(self):
        '''Run in separate thread'''
        while self.running:
            time.sleep(self.delay)
            if self.running:
                self.target()
                self.running = self.running and self.repeated

    def stop(self):
        '''Stop the separate thread from running'''
        self.running = False
