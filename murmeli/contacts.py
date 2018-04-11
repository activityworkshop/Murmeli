'''Module to deal with the in-memory storage of the status of our contacts'''
import datetime
from murmeli.system import System, Component

class Contacts(Component):
    '''Class to manage the set of which of our contacts are currently online'''

    def __init__(self, parent):
        Component.__init__(self, parent, System.COMPNAME_CONTACTS)
        self._online_list = set()
        self._last_times = {}

    def set_online_status(self, tor_id, online):
        '''Set the online status to online or offline'''
        if online:
            self.come_online(tor_id)
        else:
            self.gone_offline(tor_id)

    def come_online(self, tor_id):
        '''The given tor id has announced it is online'''
        if not self.is_online(tor_id):
            self._last_times[tor_id] = datetime.datetime.now()
        self._online_list.add(tor_id)
        #print("Contacts just informed that", tor_id, "is online.  Set is now", self._online_list)

    def gone_offline(self, tor_id):
        '''The given tor id has announced it is offline (or we failed to send to it)'''
        if self.is_online(tor_id):
            self._online_list.remove(tor_id)
            self._last_times[tor_id] = datetime.datetime.now()
        #print("Contacts just informed that", tor_id, "is offline.  Set is now", self._online_list)

    def is_online(self, tor_id):
        '''Check whether the given tor id is currently online (as far as we know)'''
        #print("Contact list asked about", tor_id, ", answer is", (torId in self._online_list))
        return tor_id in self._online_list

    def last_seen(self, tor_id):
        '''Get the last time this contact went on- or offline'''
        return self._last_times.get(tor_id, None)
