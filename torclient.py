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


class TorClient:
	'''The main client for the Tor services.'''

	# Daemon referring to tor process
	_daemon = None

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
		return started


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

