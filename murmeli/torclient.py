'''Module for the tor client'''

import os
import re
import time
import subprocess
import threading
import socket
import random
from murmeli.system import System, Component
from murmeli.message import Message
from murmeli.decrypter import DecrypterShim
from murmeli import guinotification


class TorClient(Component):
    '''Transport layer using Tor's hidden services'''

    def __init__(self, parent, file_path, tor_exe="tor"):
        Component.__init__(self, parent, System.COMPNAME_TRANSPORT)
        self.file_path = file_path
        self.tor_exe = tor_exe
        self.daemon = None
        self.socket_broker = None
        self.started = False

    def ignite_to_get_tor_id(self):
        '''Start tor, but only to get the tor id, then stop it again.
           Used only by setup / startupwizard when it doesn't actually
           need tor to run, it just needs to init everything.'''
        started = self.start_tor(start_socket_broker=False)
        result = (started, self.get_own_torid(started))
        self.stop_tor()
        return result


    @staticmethod
    def _write_torrc_file(tor_dir, rc_filename):
        service_dir = os.path.join(tor_dir, "hidden_service")
        data_dir = os.path.join(tor_dir, "tor_data")
        # if file is already there, then we'll just overwrite it
        try:
            with open(rc_filename, "w") as rc_file:
                rc_file.writelines(["# Configuration file for tor\n\n",
                                    "SocksPort 11109\n",
                                    "HiddenServiceDir " + service_dir + "\n",
                                    "HiddenServicePort 11009 127.0.0.1:11009\n",
                                    "DataDirectory " + data_dir + "\n"])
            return True
        except PermissionError:
            return False # can't write file

    def get_own_torid(self, is_started=True):
        '''Get our own Torid from the hostname file'''
        # maybe the id hasn't been written yet, so we'll try a few times and wait
        for _ in range(10):
            try:
                hostfile_path = os.path.join(self.file_path, "hidden_service", "hostname")
                with open(hostfile_path, "r") as hostfile:
                    line = hostfile.read().rstrip()
                address_match = re.match(r'(.{16,56})\.onion$', line)
                if address_match:
                    torid = address_match.group(1)
                    if len(torid) in [16, 56]:
                        return torid
            except Exception:
                if not is_started:
                    return None # no point in trying again if starting failed
                time.sleep(1.5) # keep trying a few times more
        return None # dropped out of the loop, so the hostname isn't there yet

    def start_tor(self, start_socket_broker=True):
        '''Start the tor process and attach a socket broker for listening'''
        if self.daemon or self.socket_broker:
            self.stop_tor()
        # Rewrite torrc with selected paths
        rc_file = os.path.join(self.file_path, "torrc.txt")
        if not self._write_torrc_file(self.file_path, rc_file):
            print("Failed to write rc file so failing start")
            return False

        # try to start tor
        started = False
        try:
            self.daemon = subprocess.Popen([self.tor_exe, "-f", rc_file])
            print("started tor daemon!")
            started = True
        except Exception as exc:
            print("failed to start tor daemon - is it already running or did it just fail?")
            print("Exception:", exc)
            started = False
        if start_socket_broker:
            self.socket_broker = SocketBroker(self)
        return started

    def stop_tor(self):
        '''Stop the tor exe and the socket broker'''
        if self.daemon:
            print("Stopping tor")
            self.daemon.terminate()
            self.daemon = None
            self.started = False
        else:
            print("Can't stop tor because we haven't got a handle on the process")
        if self.socket_broker:
            self.socket_broker.close()
            self.socket_broker = None

    def checked_start(self):
        '''Start the component'''
        return self.start_tor()

    def stop(self):
        '''Stop the component'''
        self.stop_tor()
        Component.stop(self)


###############################################################################

class SocketBroker(threading.Thread):
    '''This class listens on the Tor port for incoming connection requests on our socket
    and starts a new thread for each accepted connection.  Connections should deal with
    only one message or command, and then be destroyed.'''

    def __init__(self, parent):
        threading.Thread.__init__(self)
        self.parent = parent
        self.socket = None
        self.running = False
        self.setDaemon(True)
        self.start()

    def run(self):
        '''Running in separate thread'''
        self.running = True
        interface = "localhost"
        port = 11009

        # Try a few times to open the socket, we need to wait until tor has finished starting
        started = False
        attempts = 0
        while not started and attempts < 4:
            time.sleep(5)

            try:
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self.socket.bind((interface, port))
                print("Started tor and opened socket on attempt number", attempts)
                started = True
            except Exception as exc:
                print("Attempt", attempts, "- failed to open socket for listening!", exc)
                attempts += 1
        if not started:
            print("Failed after", attempts, "attempts to start the socket - tor failed to start?")
            return

        self.socket.listen(5)

        while self.running:
            try:
                print("Waiting for connection")
                conn, address = self.socket.accept()
                print("Accepted new connection from ", address, ", now start a new thread...")
                self.parent.call_component(System.COMPNAME_GUI, "notify_gui",
                                           notify_type=guinotification.NOTIFY_MSG_RECEIVING)
                # Start new listener thread with this conn
                # (address is meaningless, just comes from proxy)
                SocketListener(conn, self.parent)
                # Don't need to keep a handle on this as it'll start its own thread
            except:
                print("socket listener error, failed to accept connection!")
        print("Socket broker has finished accepting new connections, exiting thread")

    def close(self):
        '''Call from outside to cleanly close the thread and its socket'''
        self.running = False
        # TODO: Tell each of the socket listeners to close down too? (Most should be dead anyway)
        try:
            print("SocketBroker.close - closing the socket")
            self.socket.close()
            print("SocketBroker.close - closed the socket")
        except:
            print("SocketBroker.close - failed to close the socket")


###############################################################################

class SocketListener(threading.Thread):
    '''This class listens on the given connection obtained from our socket
    and starts a new thread to receive data on this connection.
    Connections should deal with only one message or command, and then be destroyed.'''

    def __init__(self, conn, component):
        '''Constructor'''
        threading.Thread.__init__(self)
        self.conn = conn
        self.component = component
        self.running = False
        self.start()

    def run(self):
        '''Running in separate thread'''
        self.running = True
        print("I'm a socket listener, running in a separate thread now")
        received = "."
        msg = bytes()
        is_http_req = False

        while received and not is_http_req:
            received = self.conn.recv(1024)
            print("Got something" if received else "Got nothing!")
            if received:
                is_http_req = not msg and self.looks_like_http(received)
                msg += received
                if is_http_req:
                    print("Got Http request: ", msg)
                    reply_to_send = "undergrowth (%d)" % random.Random().choice(range(10000))
                    self.conn.send(reply_to_send.encode("utf-8"))
            elif msg:
                crypto = self.component.get_component(System.COMPNAME_CRYPTO)
                received_msg = Message.from_received_data(msg, decrypter=DecrypterShim(crypto))
                if received_msg:
                    signature_keyid = received_msg.get_field(Message.FIELD_SIGNATURE_KEYID)
                    print("Incoming message!  Signature key:", signature_keyid)
                    print("Incoming message!  Sender was '%s'"
                          % received_msg.get_field(received_msg.FIELD_SENDER_ID))
                    logstr = "Received '%s' from '%s'" % (received_msg.describe_message_type(),
                                                          signature_keyid)
                    self.component.call_component(System.COMPNAME_LOGGING, "log", logstr=logstr)
                    # Pass to the system's message handler
                    self.component.call_component(System.COMPNAME_MSG_HANDLER, "receive",
                                                  msg=received_msg)
                else:
                    print("Hang on, why is the incoming message None?")
                # Note: should reply with ACK/NACK, but this doesn't work through the proxy
        # close socket
        self.conn.close()
        self.component.call_component(System.COMPNAME_GUI, "notify_gui",
                                      notify_type=guinotification.NOTIFY_MSG_RECEIVED)
        print("closed connection, exiting listener thread")

    @staticmethod
    def looks_like_http(data):
        '''Check if the given byte array looks like a HTTP request'''
        allowed_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ" \
                        "0123456789/_. \t".encode("utf-8")
        if not data or not isinstance(data, bytes) or len(data) < 5:
            return False
        if "GET".encode("utf-8") != data[:3]:
            return False
        for char in data:
            if char in "\r\n".encode("utf-8"):
                return True
            if char not in allowed_chars:
                return False
        return True
