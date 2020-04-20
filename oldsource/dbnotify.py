''' Classes to serve notifications about database events'''

class DbNotifierBase:
	'''Base for the notifiers'''
	def __init__(self):
		self.listeners = []
	def addListener(self, l):
		self.listeners.append(l)


class DbMessageNotifier(DbNotifierBase):
	'''Notifier reporting changes to messages in Inbox and Outbox'''
	_instance = None

	@staticmethod
	def getInstance():
		if not DbMessageNotifier._instance:
			DbMessageNotifier._instance = DbMessageNotifier()
		return DbMessageNotifier._instance

	def notify(self):
		'''Notify everybody that the contents of the inbox or outbox have changed'''
		print("DbMessageNotifier: notify called for", len(self.listeners), "listeners")
		for l in self.listeners:
			l.notifyMessagesChanged()


class DbResourceNotifier(DbNotifierBase):
	'''Notifier reporting changes to resources like avatar image files'''
	_instance = None

	@staticmethod
	def getInstance():
		if not DbResourceNotifier._instance:
			DbResourceNotifier._instance = DbResourceNotifier()
		return DbResourceNotifier._instance

	def notify(self, resourcePath):
		'''Notify everybody that the given resource has changed'''
		for l in self.listeners:
			l.notifyResourceChanged(resourcePath)
