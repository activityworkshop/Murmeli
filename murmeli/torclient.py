'''Module for the tor client'''

import os
import re
import time
import subprocess
from murmeli.system import System, Component


class TorClient(Component):
    '''Transport layer using Tor's hidden services'''

    def __init__(self, parent, file_path, tor_exe="tor"):
        Component.__init__(self, parent, System.COMPNAME_TRANSPORT)
        self.file_path = file_path
        self.tor_exe = tor_exe

    def ignite_to_get_tor_id(self):
        '''Start tor, but only to get the tor id, then stop it again.
           Used only by setup / startupwizard when it doesn't actually
           need tor to run, it just needs to init everything.'''
        # Rewrite torrc with selected paths
        rc_file = os.path.join(self.file_path, "torrc.txt")
        if not self._write_torrc_file(self.file_path, rc_file):
            print("Failed to write rc file, so aborting check")
            return (False, None)
        # try to start tor
        print("Starting tor")
        daemon = None
        try:
            daemon = subprocess.Popen([self.tor_exe, "-f", rc_file])
            started = True
        except Exception as e:
            print("Got exception:", e)
            started = False
        result = (started, self.get_own_torid(started))
        if daemon:
            print("Terminating daemon")
            daemon.terminate()
        return result


    @staticmethod
    def _write_torrc_file(tor_dir, rc_filename):
        service_dir = os.path.join(tor_dir, "hidden_service")
        data_dir = os.path.join(tor_dir, "tor_data")
        # if file is already there, then we'll just overwrite it
        try:
            with open(rc_filename, "w") as rc:
                rc.writelines(["# Configuration file for tor\n\n",
                               "SocksPort 11109\n",
                               "HiddenServiceDir " + service_dir + "\n",
                               "HiddenServicePort 11009 127.0.0.1:11009\n",
                               "DataDirectory " + data_dir + "\n"])
            return True
        except PermissionError:
            return False # can't write file

    def get_own_torid(self, is_started):
        '''Get our own Torid from the hostname file'''
        # maybe the id hasn't been written yet, so we'll try a few times and wait
        for _ in range(10):
            try:
                hostfile_path = os.path.join(self.file_path, "hidden_service", "hostname")
                with open(hostfile_path, "r") as hostfile:
                    line = hostfile.read().rstrip()
                address_match = re.match(r'(.{16})\.onion$', line)
                if address_match:
                    return address_match.group(1)
            except Exception as e:
                if not is_started:
                    return None # no point in trying again if starting failed
                time.sleep(1.5) # keep trying a few times more
        return None # dropped out of the loop, so the hostname isn't there yet

