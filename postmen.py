'''Module for the incoming and outgoing postmen, for handling the mail'''

import threading
import socks
from PyQt4 import QtCore # for timer
from dbinterface import DbI
from dbnotify import DbMessageNotifier
from message import StatusNotifyMessage
from contacts import Contacts
import imageutils


class OutgoingPostman(QtCore.QObject):
	'''This class is responsible for occasionally polling the outbox and (if possible)
	dealing with each of the messages in turn, sending them as appropriate'''

	flushSignal = QtCore.pyqtSignal()
	# Return codes
	RC_MESSAGE_SENT    = 1
	RC_MESSAGE_IGNORED = 2
	RC_MESSAGE_FAILED  = 3

	def __init__(self, parent):
		'''Constructor'''
		QtCore.QObject.__init__(self)
		self.parent = parent
		self._broadcasting = False
		self._flushing = False
		self.flushSignal.connect(self.flushOutbox)
		# Set up timers
		self.flushTimer = QtCore.QTimer()
		self.connect(self.flushTimer, QtCore.SIGNAL("timeout()"), self.flushOutbox)
		self.flushTimer.start(300000) # flush every 5 minutes
		self.broadcastTimer = QtCore.QTimer()
		self.connect(self.broadcastTimer, QtCore.SIGNAL("timeout()"), self.broadcastOnlineStatus)
		self.broadcastTimer.start(350000) # broadcast about every 5 minutes
		# Register myself as listener to the message notifier
		DbMessageNotifier.getInstance().addListener(self)
		# Trigger a broadcast after 30 seconds
		QtCore.QTimer.singleShot(30000, self.broadcastOnlineStatus)


	def notifyMessagesChanged(self):
		'''Called from Message notifier'''
		if not self._broadcasting:
			self.flushSignal.emit()

	def stop(self):
		'''Stop the timers, we're done'''
		self.flushTimer.stop()
		self.broadcastTimer.stop()

	def broadcastOnlineStatus(self):
		'''Queue a status notification message for each of our trusted contacts'''
		print("Outgoing postman is broadcasting the status...")
		self._broadcasting = True
		profileList = DbI.getTrustedProfiles()
		if profileList:
			msg = StatusNotifyMessage(online=True, ping=True, profileHash=None)
			msg.recipients = [c['torid'] for c in profileList]
			DbI.addToOutbox(msg)
		self._broadcasting = False
		self.flushSignal.emit()

	def flushOutbox(self):
		'''Trigger the flush in a separate thread so it doesn't block'''
		if not self._flushing:
			threading.Thread(target=self.flushOutboxInSeparateThread).start()

	def flushOutboxInSeparateThread(self):
		'''This can take quite a while to do the flush'''
		if self._flushing:
			return
		print("Outgoing postman is flushing the outbox...")
		self._flushing = True
		# Look in the outbox for messages
		messagesFound = 0
		messagesSent  = 0
		failedRecpts = set()
		for m in DbI.getOutboxMessages():
			if not m:
				continue	# message already deleted
			messagesFound += 1
			# Get recipient, timestamp, relays, message
			message = imageutils.stringToBytes(m['message'])
			sendTimestamp = m.get('timestamp', None) # not used yet
			# TODO: if the timestamp is too old, then either just delete the message (if it's not to be queued) or move to inbox

			# Some messages have a single recipient (and maybe relays), others only have a recipientList
			recipient = m.get('recipient', None)
			if recipient:
				sendSuccess = self.RC_MESSAGE_FAILED if recipient in failedRecpts else self.sendMessage(message, recipient)
				if sendSuccess == self.RC_MESSAGE_IGNORED:
					print("Dealt with message so I should delete it from the db:", m["_id"])
					DbI.deleteFromOutbox(m["_id"])
				elif sendSuccess == self.RC_MESSAGE_SENT:
					print("Sent message so I should delete it from the db:", m["_id"])
					DbI.deleteFromOutbox(m["_id"])
					messagesSent += 1
					testMsg = "Message sent, type was %s and recipient was %s" % (m.get("msgType", "unknown"), recipient)
					# TODO: Pass these values with the signal as an object, not a string
					self.emit(QtCore.SIGNAL("messageSent"), testMsg)
				elif not m.get('queue', False):
					print("I failed to send a message but it shouldn't be queued, deleting it")
					DbI.deleteFromOutbox(m["_id"])
					failedRecpts.add(recipient)
				else:
					print("I failed to send but I'll keep the message and try again later")
					failedRecpts.add(recipient)
			else:
				# There isn't a direct recipient, so let's hope there's a recipient list
				recipientList = m.get('recipientList', None)
				if recipientList:
					print("I've got a message to relay to: ", recipientList)
					failedRecipientsForThisMessage = set()
					# Try to send to each in the list
					for rRecipient in recipientList:
						if rRecipient in failedRecpts or self.sendMessage(message, rRecipient) == self.RC_MESSAGE_FAILED:
							# Couldn't send to this recipient
							failedRecipientsForThisMessage.add(rRecipient)
					if failedRecipientsForThisMessage:
						# Update m with the recipientList = failedRecipientsForThisMessage
						DbI.updateOutboxMessage(m["_id"], {"recipientList" : list(failedRecipientsForThisMessage)})
						print("I failed to send a relay to:", failedRecipientsForThisMessage)
					else:
						print("I managed to relay everything, now deleting relay message")
						DbI.deleteFromOutbox(m["_id"])
			# TODO: Wait inbetween sending to avoid overloading the network

		# TODO: Does the parent even need to know when a send has worked?
		if messagesSent > 0:
			self.parent.postmanKnock() # only once
		if messagesFound > 0:
			print("For %d found messages, I managed to send %d copies" % (messagesFound, messagesSent))
		# We tried to send a message to these recipients but failed - set them to be offline
		for r in failedRecpts:
			Contacts.instance().goneOffline(r)
		self._flushing = False

	def sendMessage(self, message, whoto):
		# Check status of recipient in profile
		profile = DbI.getProfile(whoto)
		status = profile['status'] if profile else "deleted"
		if status in ['deleted', 'blocked']:
			return self.RC_MESSAGE_IGNORED
		print("Trying to send message to '%s'" % whoto)
		if whoto is not None and len(whoto) == 16:
			try:
				s = socks.socksocket()
				s.setproxy(socks.PROXY_TYPE_SOCKS4, "localhost", 11109)
				s.connect((whoto + ".onion", 11009))
				numsent = s.send(message)
				s.close()
				if numsent != len(message):
					print("Oops - num bytes sent:", numsent, "but message has length:", len(message))
					# For really long messages, maybe need to chunk into 4k blocks or something?
				else:
					Contacts.instance().comeOnline(whoto)
					return self.RC_MESSAGE_SENT
			except Exception as e:
				print("Woah, that threw something:", e)
		print("Bailed from the send attempt, returning failure")
		return self.RC_MESSAGE_FAILED   # it didn't work


class IncomingPostman(threading.Thread):
	'''This class is responsible for dealing with inbox notifications and reacting to the
	messages that it finds in the inbox.
	(Does it actually need to do anything? Or just inform upwards if count>0 for the icon highlight?)'''
	def __init__(self, parent):
		threading.Thread.__init__(self)
		self.parent = parent
		self.somethingInInbox = False
		self.start()
		# Register myself as listener to the message notifier
		DbMessageNotifier.getInstance().addListener(self)

	# Running in separate thread
	def run(self):
		self.checkInbox()

	def stop(self):
		'''This thread doesn't poll so doesn't need to stop'''
		print("Stopping incoming postman")

	def notifyMessagesChanged(self):
		'''Called from Message notifier'''
		self.checkInbox()

	def checkInbox(self):
		'''Look in the inbox for messages'''
		messagesFound = len(DbI.getInboxMessages())
		self.somethingInInbox = (messagesFound > 0)
		self.parent.postmanKnock() # only once

	def isSomethingInInbox(self):
		'''Return True if there's something in the Inbox, otherwise False'''
		return self.somethingInInbox
