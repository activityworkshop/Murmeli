from dbclient import DbClient
from dbnotify import DbMessageNotifier
from PyQt4 import QtCore # for timer
import threading


class OutgoingPostman(QtCore.QObject):
	'''This class is responsible for occasionally polling the outbox and (if possible)
	dealing with each of the messages in turn, sending them as appropriate'''

	flushSignal = QtCore.pyqtSignal()

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

	def flushOutbox(self):
		'''Trigger the flush in a separate thread so it doesn't block'''
		if not self._flushing:
			threading.Thread(target=self.flushOutboxInSeparateThread).start()

	def flushOutboxInSeparateThread(self):
		'''This can take quite a while to do the flush'''
		if self._flushing: return
		print("Outgoing postman is flushing the outbox...")


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
		# TODO: Also need to react when all the messages in the inbox have been deleted (or read)

	def checkInbox(self):
		'''Look in the inbox for messages'''
		messagesFound = 0
		for _ in DbClient.getInboxMessages():
			messagesFound += 1
			break
		self.somethingInInbox = (messagesFound > 0)
		self.parent.postmanKnock() # only once

	def isSomethingInInbox(self):
		'''Return True if there's something in the Inbox, otherwise False'''
		return self.somethingInInbox
