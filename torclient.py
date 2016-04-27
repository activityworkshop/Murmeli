'''Murmeli, an encrypted communications platform by activityworkshop
   Based on Tor's hidden services and torchat_py
   Licensed to you under the GPL v2
   This file contains the interface with the tor network
   including building up the communications with tor,
   and managing the incoming and outgoing sockets.'''

import subprocess
import time
import socket
import threading
import os.path
import re
from config import Config
from message import Message


class TorClient:
	'''The main client for the Tor services.'''

	# Daemon referring to tor process
	_daemon = None
	# Single instance of client
	_torClient = None

	# Constructor
	def __init__(self):
		self.socketBroker = None

	@staticmethod
	def startTor():
		torexe = Config.getProperty(Config.KEY_TOR_EXE)
		rcfile = os.path.join(Config.getTorDir(), "torrc.txt")
		# Rewrite torrc with selected paths
		if not TorClient.writeTorrcFile(rcfile):
			return False

		# try to start tor
		started = False
		try:
			TorClient._daemon = subprocess.Popen([torexe, "-f", rcfile])
			print("started tor daemon!")
			started = True
			time.sleep(12)
		except:
			print("failed to start tor daemon - is it already running or did it just fail?")
			started = False
		if TorClient._torClient is None:
			TorClient._torClient = TorClient()
		if TorClient._torClient.socketBroker is not None:
			TorClient._torClient.socketBroker.close()
		TorClient._torClient.socketBroker = SocketBroker()
		return started

	@staticmethod
	def isStarted():
		return TorClient._torClient is not None

	@staticmethod
	def getOwnId():
		'''Get our own Torid from the hostname file'''
		# maybe the id hasn't been written yet, so we'll try a few times and wait
		for _ in range(10):
			try:
				hiddendir = os.path.join(Config.getTorDir(), "hidden_service")
				with open(os.path.join(hiddendir, "hostname"), "r") as hostfile:
					line = hostfile.read().rstrip()
				m = re.match("(.{16})\.onion$", line)
				if m: return m.group(1)
			except:
				time.sleep(1.5) # keep trying a few times more
		return None # dropped out of the loop, so the hostname isn't there yet


	@staticmethod
	def stopTor():
		if TorClient._daemon:
			print("Stopping tor")
			TorClient._daemon.terminate()
			TorClient._daemon = None
		else:
			print("Can't stop tor because we haven't got a handle on the process")

	@staticmethod
	def writeTorrcFile(rcfile):
		serviceFile = os.path.join(Config.getTorDir(), "hidden_service")
		datadir = os.path.join(Config.getTorDir(), "tor_data")
		# if file is already there, then we'll just overwrite it
		try:
			with open(rcfile, "w") as rc:
				rc.writelines(["# Configuration file for tor\n\n",
				  "SocksPort 11109\n",
				  "HiddenServiceDir " + serviceFile + "\n",
				  "HiddenServicePort 11009 127.0.0.1:11009\n",
				  "DataDirectory " + datadir + "\n"])
			return True
		except:
			return False # can't write file

##############################

class SocketBroker(threading.Thread):
	'''This class listens on the Tor port for incoming connection requests on our socket
	and starts a new thread for each accepted connection.  Connections should deal with
	only one message or command, and then be destroyed.'''

	# Constructor
	def __init__(self):
		print("Creating socketbroker")
		threading.Thread.__init__(self)
		self.socket = None
		self.running = False
		self.start()

	def run(self):
		'''Running in separate thread'''
		self.running = True
		# TODO: Get interface and port from config?  Or is it fixed?
		interface = "localhost"
		port = 11009
		try:
			self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
			self.socket.bind((interface, port))
		except Exception as e:
			print("Failed to open socket for listening!", e)
			return

		self.socket.listen(5)

		while self.running:
			try:
				print("Waiting for connection")
				conn, address = self.socket.accept()
				print("Accepted new connection from ", address, ", now start a new thread...")
				# Start new listener thread with this conn
				# (address is meaningless, just comes from proxy)
				listener = SocketListener(conn)
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


##############################

class SocketListener(threading.Thread):
	'''This class listens on the given connection obtained from our socket
	and starts a new thread to receive data on this connection.
	Connections should deal with only one message or command, and then be destroyed.'''

	def __init__(self, conn):
		'''Constructor'''
		threading.Thread.__init__(self)
		self.conn = conn
		self.running = False
		self.start()

	def run(self):
		'''Running in separate thread'''
		self.running = True
		print("I'm a socket listener, running in a separate thread now")
		received = "."
		msg = bytes()
		while received:
			received = self.conn.recv(1024)
			print("Got something" if received else "Got nothing!")
			if len(received) > 0:
				msg += received
			elif len(msg) > 0:
				m = Message.MessageFromReceivedData(msg)
				if m is None:
					print("Hang on, why is the incoming message None?")
					# Note: should reply with NACK, but this doesn't seem to work through the proxy
				else:
					print("Incoming message!  Sender was '%s'" % m.senderId)
					# TODO: Deal with this message object somehow
					# Note: should reply with ACK, but this doesn't seem to work through the proxy
		# close socket
		self.conn.close()
		print("closed connection, exiting listener thread")
