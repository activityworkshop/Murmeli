'''Module for the pages provided by the system'''

import re               # for regular expressions
import os.path
import shutil
import datetime
from PyQt5.QtWidgets import QFileDialog # for file selection (move somewhere else?)
from i18n import I18nManager
from config import Config
from dbinterface import DbI
from cryptoclient import CryptoClient
from contactmgr import ContactMaker
from pagetemplate import PageTemplate
from brainstorm import Brainstorm
from brainstormdata import Storm, Node
from compose import ComposeWindow
import message
from fingerprints import FingerprintChecker
from contacts import Contacts
from messageutils import MessageTree


class Bean:
	'''Class for interacting with page templates by adding properties'''
	pass


class PageServer:
	'''PageServer, containing several page sets'''
	def __init__(self):
		self.pageSets = {}
		self.addPageSet(DefaultPageSet())
		self.addPageSet(ContactsPageSet())
		self.addPageSet(MessagesPageSet())
		self.addPageSet(CalendarPageSet())
		self.addPageSet(SettingsPageSet())
		self.addPageSet(ComposePageSet())
		self.addPageSet(SpecialFunctions())
		self._openWindows = []

	def addPageSet(self, ps):
		self.pageSets[ps.getDomain()] = ps

	def servePage(self, view, url, params):
		domain, path = self.getDomainAndPath(url)
		# Do I need to intercept this to create a new window?
		if domain == "new":
			cw = ComposeWindow(I18nManager.getText("composemessage.title"))
			cw.setPageServer(self)
			cw.showPage("<html></html>")
			cw.navigateTo(path, params)
			# TODO: Remove the closed windows from the list
			self._openWindows.append(cw)
			return

		server = self.pageSets.get(domain)
		if not server: server = self.pageSets.get("")
		server.servePage(view, path, params)

	def getDomainAndPath(self, url):
		startpos = 1
		if url[0:15] == "http://murmeli/": startpos = 15
		slashpos = url.find("/", startpos)
		if slashpos < 0: return (url[startpos:], '/')
		return (url[startpos:slashpos], url[slashpos:])


class PageSet:
	'''Superclass of all page servers'''
	def __init__(self, domain):
		self.domain = domain
		self.standardHead = "<html><head><meta http-equiv=\"Content-Type\" content=\"text/html; charset=utf-8\"><link href='file:///" + Config.getWebCacheDir() + "/default.css' type='text/css' rel='stylesheet'><script type='text/javascript'>function hideOverlay(){showLayer('overlay',false);showLayer('popup',false)} function showLayer(lname,show){document.getElementById(lname).style.visibility=(show?'visible':'hidden');} function showMessage(mess){document.getElementById('popup').innerHTML=mess; showLayer('overlay',true); showLayer('popup', true);}</script></head>"

	def getDomain(self):
		return self.domain

	def requirePageResource(self, resource):
		'''Require that the specified resource should be copied from web to the cache directory'''
		cacheDir = Config.getWebCacheDir()
		destPath = os.path.join(cacheDir, resource)
		if not os.path.exists(destPath):
			# dest doesn't exist (if it exists we assume it must still be valid as these resources shouldn't change)
			srcPath = os.path.join("web", resource)
			# TODO: This fails if destPath directory doesn't exist - eg if Config has become blank?
			if os.path.exists(srcPath):
				assert os.path.exists(cacheDir)
				shutil.copy(srcPath, destPath)
			else: print("OUCH - failed to copy resource '%s' from web!" % resource)

	def requirePageResources(self, resources):
		'''Require a list of page resources such as images, css'''
		if isinstance(resources, list):
			for res in resources:
				self.requirePageResource(res)
		elif isinstance(resources, str):
			self.requirePageResource(resources)

	def buildPage(self, params):
		'''General page-building method using a standard template
		   and filling in the gaps using the given dictionary'''
		self.requirePageResource("default.css")
		return ''.join([self.standardHead,
			"<body>",
			"<table border='0' width='100%%'><tr><td><div class='fancyheader'><p>%(pageTitle)s</p></div></td></tr>",
			"<tr><td><div class='genericbox'>%(pageBody)s</div></td></tr>",
			"<tr><td><div class='footer'>%(pageFooter)s</div></td></tr></table>",
			"<div class='overlay' id='overlay' onclick='hideOverlay()'></div>",
			"<div class='popuppanel' id='popup'>Here's the message</div>",
			"</body></html>"]) % params

	# General page-building method using a two-column template with widths 1third/2thirds
	def buildTwoColumnPage(self, params):
		self.requirePageResource("default.css")
		return ''.join([self.standardHead,
			"<body>",
			"<table border='0' width='100%%'><tr><td colspan='2'><div class='fancyheader'><p>%(pageTitle)s</p></div></td></tr>",
			"<tr valign='top'><td width='33%%'><div class='genericbox'>%(leftColumn)s</div></td>",
			"<td width='67%%'><div class='genericbox'>%(rightColumn)s</div></td></tr>",
			"<tr><td colspan='2'><div class='footer'>%(pageFooter)s</div></td></tr></table>",
			"<div class='overlay' id='overlay' onclick='hideOverlay()'></div>",
			"<div class='popuppanel' id='popup'>Here's the message</div>",
			"</body></html>"]) % params

	def makeLocalTimeString(self, tstamp):
		'''Convert a float (in UTC) to a string (in local timezone) for display'''
		if not tstamp:
			return ""
		try:
			sendTime = datetime.datetime.fromtimestamp(tstamp)
			# Check if it's today
			now = datetime.datetime.now()
			midnight = datetime.datetime(now.year, now.month, now.day, 0, 0, 0)
			if sendTime.timestamp() > midnight.timestamp():
				# today
				return "%02d:%02d" % (sendTime.hour, sendTime.minute)
			else:
				return "%d-%02d-%02d %02d:%02d" % (sendTime.year, sendTime.month, sendTime.day,
					sendTime.hour, sendTime.minute)
		except TypeError:
			print("Expected a float timestamp, found", type(tstamp), repr(tstamp))
		if isinstance(tstamp, str):
			return tstamp
		return ""


class DefaultPageSet(PageSet):
	'''Default page server, just for home page'''
	def __init__(self):
		PageSet.__init__(self, "")
		self.hometemplate = PageTemplate('home')

	def servePage(self, view, url, params):
		self.requirePageResource('avatar-none.jpg')
		contents = self.buildPage({'pageTitle' : "Murmeli",
			'pageBody' : self.hometemplate.getHtml(),
			'pageFooter' : "<p>Footer</p>"})
		view.setHtml(contents)


class ContactsPageSet(PageSet):
	'''Contacts page server, for showing list of contacts etc'''
	def __init__(self):
		'''Constructor'''
		PageSet.__init__(self, "contacts")
		self.listtemplate = PageTemplate('contactlist')
		self.detailstemplate = PageTemplate('contactdetails')
		self.editowndetailstemplate = PageTemplate('editcontactself')
		self.editdetailstemplate = PageTemplate('editcontact')
		self.addtemplate = PageTemplate('addcontact')
		self.fingerprintstemplate = PageTemplate('fingerprints')

	def servePage(self, view, url, params):
		self.requirePageResources(['button-addperson.png', 'button-drawgraph.png', 'avatar-none.jpg'])
		DbI.exportAllAvatars(Config.getWebCacheDir())
		if url == "/add" or url == "/add/":
			contents = self.generateAddPage()
			view.setHtml(contents)
			return
		elif url == "/submitaddrequest":
			print("Submit add request!:", url)
			if len(params) > 0:
				# request to add a new friend
				recipientid  = params.get('murmeliid', '')
				dispname     = params.get('displayname', '')
				intromessage = params.get('intromessage', '')
				if len(recipientid) == 16:
					# TODO: How to react if: person already added (untrusted/trusted); request already sent (requested)
					# update the database accordingly
					ContactMaker.handleInitiate(recipientid, dispname)
					print("I should send an add request to '%s' now." % recipientid)
					outmsg = message.ContactRequestMessage(introMessage=intromessage)
					outmsg.recipients = [recipientid]
					DbI.addToOutbox(outmsg)
				else:
					print("Hmm, show an error message here?")
				# in any case, go back to contact list
				url = "/" + recipientid
				# ensure that picture is generated for new id
				DbI.exportAllAvatars(Config.getWebCacheDir())
		contents = None
		userid   = None
		pageParams = {}
		# Split url into components /userid/command
		command = [i for i in url.split("/") if i != ""]
		if len(command) > 0 and len(command[0]) == 16 and re.match("([a-zA-Z0-9]+)$", command[0]):
			userid = command[0]
			# check for command edit or submit-edit
			if len(command) == 2:
				if command[1] == "edit":
					contents = self.generateListPage(doEdit=True, userid=userid) # show edit fields
				elif command[1] == "submitedit":
					DbI.updateProfile(userid, params, Config.getWebCacheDir())
					# TODO: If we've updated our own details, can we trigger a broadcast?
					# don't generate contents, go back to details
				elif command[1] == "delete":
					ContactMaker.handleDeleteContact(userid)
					userid = None
				elif command[1] == "checkfingerprint":
					contents = self.generateFingerprintsPage(userid)
				elif command[1] == "checkedfingerprint":
					givenAnswer = int(params.get('answer', -1))
					fc = self._makeFingerprintChecker(userid)
					expectedAnswer = fc.getCorrectAnswer()
					if expectedAnswer == givenAnswer:
						ContactMaker.keyFingerprintChecked(userid)
						# Show page again
						contents = self.generateFingerprintsPage(userid)
					else:
						# Add a message to show when the list page is re-generated
						pageParams['fingerprint_check_failed'] = True
			elif len(command) == 3 and command[1] == "refer" and len(command[2]) == 16:
				intro = str(params.get('introMessage', ""))
				ContactMaker.sendReferralMessages(command[0], command[2], intro)
				pageParams['message_sent'] = True
				# go back to details page
			elif len(command) == 3 and command[1] == "requestrefer" and len(command[2]) == 16:
				intro = str(params.get('introMessage', ""))
				ContactMaker.sendReferRequestMessage(command[0], command[2], intro)
				pageParams['message_sent'] = True
				# go back to details page

		# If we haven't got any contents yet, then do a show details
		if not contents:
			# Show details for selected userid (or for self if userid is None)
			contents = self.generateListPage(doEdit=False, userid=userid, extraParams=pageParams)

		view.setHtml(contents)

	def generateAddPage(self):
		'''Build the form page for adding a new user, using the template'''
		bodytext = self.addtemplate.getHtml({"owntorid" : DbI.getOwnTorid()})
		return self.buildPage({'pageTitle' : I18nManager.getText("contacts.title"),
			'pageBody' : bodytext,
			'pageFooter' : "<p>Footer</p>"})

	def generateFingerprintsPage(self, userid):
		'''Build the page for checking the fingerprints of the selected user'''
		# First, get the name of the user
		person = DbI.getProfile(userid)
		dispName = person['displayName']
		fullName = person['name']
		if dispName != fullName:
			fullName = dispName + " (" + fullName + ")"
		fc = self._makeFingerprintChecker(userid)
		# check it's ok to generate
		status = person.get('status', '')
		if not fc.valid \
		  or status not in ['untrusted', 'trusted']:
			print("Not generating fingerprints page because status is", status)
			return None

		# Get one set of words for us and three sets for them
		printsAlreadyChecked = (person.get('status', '') == "trusted")
		bodytext = self.fingerprintstemplate.getHtml(
			{"mywords":fc.getCodeWords(True, 0, "en"), "theirwords0":fc.getCodeWords(False, 0, "en"),
			 "theirwords1":fc.getCodeWords(False, 1, "en"), "theirwords2":fc.getCodeWords(False, 2, "en"),
			 "fullname":fullName, "shortname":dispName, "userid":userid, "alreadychecked":printsAlreadyChecked})
		return self.buildPage({'pageTitle' : I18nManager.getText("contacts.title"),
			'pageBody' : bodytext,
			'pageFooter' : "<p>Footer</p>"})

	def _makeFingerprintChecker(self, userid):
		'''Use the given userid to make a FingerprintChecker between me and them'''
		person = DbI.getProfile(userid)
		ownFingerprint = CryptoClient.getFingerprint(DbI.getOwnKeyid())
		usrFingerprint = CryptoClient.getFingerprint(person['keyid'])
		return FingerprintChecker(ownFingerprint, usrFingerprint)

	# Generate a page for listing all the contacts and showing the details of one of them
	def generateListPage(self, doEdit=False, userid=None, extraParams=None):
		self.requirePageResources(['avatar-none.jpg', 'status-self.png', 'status-requested.png', 'status-untrusted.png',
			'status-trusted.png', 'status-pending.png'])
		# List of contacts, and show details for the selected one (or self if userid=None)
		selectedprofile = DbI.getProfile(userid)
		if not selectedprofile:
			selectedprofile = DbI.getProfile()
		userid = selectedprofile['torid']
		ownPage = userid == DbI.getOwnTorid()

		# Build list of contacts
		userboxes = []
		currTime = datetime.datetime.now()
		for p in DbI.getProfiles():
			box = Bean()
			box.dispName = p['displayName']
			box.torid = p['torid']
			box.tilestyle = "contacttile" + ("selected" if p['torid'] == userid else "")
			box.status = p['status']
			isonline = Contacts.instance().isOnline(box.torid)
			lastSeen = Contacts.instance().lastSeen(box.torid)
			lastSeenTime = str(lastSeen.timetz())[:5] if lastSeen and (currTime-lastSeen).total_seconds() < 18000 else None
			if lastSeenTime:
				box.lastSeen = I18nManager.getText("contacts.onlinesince" if isonline else "contacts.offlinesince") % lastSeenTime
			elif isonline:
				box.lastSeen = I18nManager.getText("contacts.online")
			else:
				box.lastSeen = None
			userboxes.append(box)

		# expand templates using current details
		lefttext = self.listtemplate.getHtml({'webcachedir' : Config.getWebCacheDir(), 'contacts' : userboxes})
		pageProps = {"webcachedir" : Config.getWebCacheDir(), 'person':selectedprofile}
		# Add extra parameters if necessary
		if extraParams:
			pageProps.update(extraParams)

		# See which contacts we have in common with this person
		(sharedContactIds, possIdsForThem, possIdsForMe, nameMap) = ContactMaker.getSharedAndPossibleContacts(userid)
		sharedContacts = self._makeIdAndNameBeanList(sharedContactIds, nameMap)
		pageProps.update({"sharedcontacts" : sharedContacts})
		possibleContacts = self._makeIdAndNameBeanList(possIdsForThem, nameMap)
		pageProps.update({"possiblecontactsforthem" : possibleContacts})
		possibleContacts = self._makeIdAndNameBeanList(possIdsForMe, nameMap)
		pageProps.update({"possiblecontactsforme" : possibleContacts})

		# Which template to use depends on whether we're just showing or also editing
		if doEdit:
			# Use two different details templates, one for self and one for others
			detailstemplate = self.editowndetailstemplate if ownPage else self.editdetailstemplate
			righttext = detailstemplate.getHtml(pageProps)
		else:
			detailstemplate = self.detailstemplate  # just show
			righttext = detailstemplate.getHtml(pageProps)

		contents = self.buildTwoColumnPage({'pageTitle' : I18nManager.getText("contacts.title"),
			'leftColumn' : lefttext,
			'rightColumn' : righttext,
			'pageFooter' : "<p>Footer</p>"})
		return contents

	def _makeIdAndNameBeanList(self, cids, nameMap):
		cList = []
		if cids:
			for cid in cids:
				c = Bean()
				c.torid = cid
				c.dispName = nameMap.get(cid, cid)
				cList.append(c)
		return cList


class MessagesPageSet(PageSet):
	'''Messages page server, for showing list of messages etc'''
	def __init__(self):
		PageSet.__init__(self, "messages")
		self.messagestemplate = PageTemplate('messages')

	def servePage(self, view, url, params):
		self.requirePageResources(['button-compose.png', 'default.css', 'jquery-3.1.1.js'])
		DbI.exportAllAvatars(Config.getWebCacheDir())

		messageList = None
		if url == "/send":
			print("send message of type '%(messageType)s' to id '%(sendTo)s'" % params)
			if params['messageType'] == "contactresponse":
				torId = params['sendTo']
				if params.get("accept", "0") == "1":
					ContactMaker.handleAccept(torId)
					# Make sure this new contact has an empty avatar
					DbI.exportAllAvatars(Config.getWebCacheDir())
					outmsg = message.ContactResponseMessage(message=params['messageBody'])
				else:
					ContactMaker.handleDeny(torId)
					outmsg = message.ContactDenyMessage()
				# Construct a ContactResponse message object for sending
				outmsg.recipients = [params['sendTo']]
				DbI.addToOutbox(outmsg)
		elif url.startswith("/delete/"):
			DbI.deleteFromInbox(params.get("msgId", ""))
		elif url in ["/search", "/search/"]:
			messageList = DbI.searchInboxMessages(params.get("searchTerm"))

		# Make dictionary to convert ids to names
		contactNames = {c['torid']:c['displayName'] for c in DbI.getProfiles()}
		unknownSender = I18nManager.getText("messages.sender.unknown")
		unknownRecpt = I18nManager.getText("messages.recpt.unknown")
		# Get contact requests, responses and mails from inbox
		conreqs = []
		conresps = []
		mailTree = MessageTree()
		if messageList is None:
			messageList = DbI.getInboxMessages()
		# TODO: Paging options?
		for m in messageList:
			if not m:
				continue
			m['msgId'] = str(m.get("_id", ""))
			if m['messageType'] == "contactrequest":
				conreqs.append(m)
			elif m['messageType'] == "contactrefer":
				senderId = m.get('fromId', None)
				m['senderName'] = contactNames.get(senderId, unknownSender)
				conreqs.append(m)
			elif m['messageType'] == "contactresponse":
				if not m.get('accepted', False):
					m['messageBody'] = I18nManager.getText("messages.contactrequest.refused")
					m['fromName'] = DbI.getProfile(m['fromId'])["displayName"]
				elif not m.get('messageBody', False):
					m['messageBody'] = I18nManager.getText("messages.contactrequest.accepted")
				conresps.append(m)
			else:
				senderId = m.get('fromId', None)
				if not senderId and m.get('signatureKeyId', None):
					senderId = DbI.findUserIdFromKeyId(m['signatureKeyId'])
				m['senderName'] = contactNames.get(senderId, unknownSender)
				m['sentTimeStr'] = self.makeLocalTimeString(m['timestamp'])
				# Split m['recipients'] by commas, and look up each id with contactNames
				recpts = m.get('recipients', '')
				if recpts:
					replyAll = recpts.split(",")
					m['recipients'] = ", ".join([contactNames.get(i, unknownRecpt) for i in replyAll])
					replyAll.append(senderId)
					m['replyAll'] = ",".join(replyAll)
				else:
					m['recipients'] = unknownRecpt
					m['replyAll'] = ""
				mailTree.addMsg(m)
		mails = mailTree.build()
		bodytext = self.messagestemplate.getHtml({"contactrequests":conreqs, "contactresponses":conresps,
			"mails":mails, "nummessages":len(conreqs)+len(conresps)+len(mails),
			"webcachedir" : Config.getWebCacheDir()})
		contents = self.buildPage({'pageTitle' : I18nManager.getText("messages.title"),
			'pageBody' : bodytext,
			'pageFooter' : "<p>Footer</p>"})
		view.setHtml(contents)


class CalendarPageSet(PageSet):
	'''Calendar page server, for showing list of events, reminders etc'''
	def __init__(self):
		PageSet.__init__(self, "calendar")
		self.calendartemplate = PageTemplate('calendar')

	def servePage(self, view, url, params):
		contents = self.buildPage({'pageTitle' : I18nManager.getText("calendar.title"),
			'pageBody' : self.calendartemplate.getHtml(),
			'pageFooter' : "<p>Footer</p>"})
		view.setHtml(contents)
		# obviously this will do things with the url eventually too ;)


class SettingsPageSet(PageSet):
	'''Settings page server, for showing the current settings'''
	def __init__(self):
		PageSet.__init__(self, "settings")
		self.formtemplate = PageTemplate('settingsform')

	def servePage(self, view, url, params):
		if url == "/edit":
			selectedLang = params.get('lang', None)
			if selectedLang and len(selectedLang) == 2:
				Config.setProperty(Config.KEY_LANGUAGE, selectedLang)
				# I18nManager will be triggered here because it listens to the Config
			fsf = params.get('friendsseefriends', None)
			friendsseefriends = fsf is not None and len(fsf) > 0
			Config.setProperty(Config.KEY_ALLOW_FRIENDS_TO_SEE_FRIENDS, friendsseefriends)
			slw = params.get('showlogwindow', None)
			showlogwindow = slw is not None and len(slw) > 0
			Config.setProperty(Config.KEY_SHOW_LOG_WINDOW, showlogwindow)
			# If Config has changed, may need to update profile to include/hide friends info
			DbI.updateContactList(friendsseefriends)
			# When friends are notified next time, the profile's hash will be calculated and sent
			afw = params.get('allowfriendrequests', None)
			allowfriendrequests = afw is not None and len(afw) > 0
			Config.setProperty(Config.KEY_ALLOW_FRIEND_REQUESTS, allowfriendrequests)
			# Save config to file in case it's changed
			Config.save()
			contents = self.buildPage({'pageTitle' : I18nManager.getText("settings.title"),
				'pageBody' : "<p>Settings changed... should I go back to settings or back to home now?</p>",
				'pageFooter' : "<p>Footer</p>"})
			view.setHtml(contents)
		else:
			pageProps = {"friendsseefriends" : "checked" if Config.getProperty(Config.KEY_ALLOW_FRIENDS_TO_SEE_FRIENDS) else "",
				"allowfriendrequests" : "checked" if Config.getProperty(Config.KEY_ALLOW_FRIEND_REQUESTS) else "",
				"showlogwindow" : "checked" if Config.getProperty(Config.KEY_SHOW_LOG_WINDOW) else "",
				"language_en":"", "language_de":""}
			pageProps["language_" + Config.getProperty(Config.KEY_LANGUAGE)] = "selected"
			#print("body:", self.formtemplate.getHtml(pageProps))
			contents = self.buildPage({'pageTitle' : I18nManager.getText("settings.title"),
				'pageBody' : self.formtemplate.getHtml(pageProps),
				'pageFooter' : "<p>Footer</p>"})
			view.setHtml(contents)


class SpecialFunctions(PageSet):
	'''Not delivering pages, but calling special Qt functions such as select file
	   or launching the wobbly network graph'''
	def __init__(self):
		PageSet.__init__(self, "special")

	def servePage(self, view, url, params):
		print("Special function:", url)
		if url == "/selectprofilepic":
			# Get home directory for file dialog
			homedir = os.path.expanduser("~/")
			fname = QFileDialog.getOpenFileName(view, I18nManager.getText("gui.dialogtitle.openimage"),
				homedir, I18nManager.getText("gui.fileselection.filetypes.jpg"))
			if fname:
				view.page().mainFrame().evaluateJavaScript("updateProfilePic('" + fname + "');")
		elif url == "/friendstorm":
			if not DbI.hasFriends():
				view.page().mainFrame().evaluateJavaScript("window.alert('No friends :(');")
				return
			# Launch a storm
			self.bs = Brainstorm(I18nManager.getText("contacts.storm.title"))
			self.bs.show()
			storm = Storm()
			# Build up Nodes and Edges using our contact list and if possible our friends' contact lists
			myTorId = DbI.getOwnTorid()
			friends = {}
			friendsOfFriends = {}
			for c in DbI.getMessageableProfiles():
				# print("Contact: id:'%s' name:'%s'" % (c['torid'], c['displayName']))
				nodeid = storm.getUnusedNodeId()
				torid = c['torid']
				friends[torid] = nodeid
				storm.addNode(Node(None, nodeid, c['displayName']))
				friendsOfFriends[torid] = c.get('contactlist', "")
			# Also add ourselves
			c = DbI.getProfile()
			nodeid = storm.getUnusedNodeId()
			friends[c['torid']] = nodeid
			storm.addNode(Node(None, nodeid, c['displayName']))
			# Add edges
			for torid in friends:
				if torid != myTorId:
					storm.addEdge(friends[torid], friends[myTorId])
			for torid in friendsOfFriends:
				if torid != myTorId:
					ffList = friendsOfFriends[torid]
					if ffList:
						for ff in ffList.split(","):
							if ff and len(ff) > 16:
								ffTorid = ff[:16]
								ffName = ff[16:]
								if ffTorid != myTorId:
									if not friends.get(ffTorid, None):
										# Friend's friend is not in the list yet - add it
										nodeid = storm.getUnusedNodeId()
										friends[ffTorid] = nodeid
										storm.addNode(Node(None, nodeid, ffName))
									# Add edge from torid to ffTorid
									storm.addEdge(friends[torid], friends[ffTorid])

			self.bs.setStorm(storm)


class ComposePageSet(PageSet):
	'''Functions for composing a new message'''
	def __init__(self):
		PageSet.__init__(self, "compose")
		self.composetemplate = PageTemplate('composemessage')
		self.closingtemplate = PageTemplate('windowclosing')

	def servePage(self, view, url, params):
		print("Compose: %s, params %s" % (url, repr(params)))
		if url == "/start":
			self.requirePageResources(['default.css', 'jquery-3.1.1.js'])
			DbI.exportAllAvatars(Config.getWebCacheDir())
			parentHash = params.get("reply", None)
			recpts = params.get("sendto", None)
			# Build list of contacts to whom we can send
			userboxes = []
			for p in DbI.getMessageableProfiles():
				box = Bean()
				box.dispName = p['displayName']
				box.torid = p['torid']
				userboxes.append(box)
			pageParams = {"contactlist":userboxes, "parenthash" : parentHash if parentHash else "",
						 "webcachedir":Config.getWebCacheDir(), "recipientids":recpts}
			contents = self.buildPage({'pageTitle' : I18nManager.getText("composemessage.title"),
				'pageBody' : self.composetemplate.getHtml(pageParams),
				'pageFooter' : "<p>Footer</p>"})
			view.setHtml(contents)
			# If we've got no friends, then warn, can't send to anyone
			if not DbI.hasFriends():
				view.page().mainFrame().evaluateJavaScript("window.alert('No friends :(');")

		elif url == "/send":
			print("Submit new message with params:", params)
			msgBody = params['messagebody']  # TODO: check body isn't empty, throw an exception?
			parentHash = params.get("parenthash", None)
			recpts = params['sendto']
			# Make a corresponding message object and pass it on
			msg = message.RegularMessage(sendTo=recpts, messageBody=msgBody, replyToHash=parentHash)
			msg.recipients = recpts.split(",")
			DbI.addToOutbox(msg)
			# Save a copy of the sent message
			sentMessage = {"messageType":"normal", "fromId":DbI.getOwnTorid(),
				"messageBody":msgBody, "timestamp":msg.timestamp, "messageRead":True,
				"messageReplied":False, "recipients":recpts, "parentHash":parentHash}
			DbI.addToInbox(sentMessage)
			# Close window after successful send
			contents = self.buildPage({'pageTitle' : I18nManager.getText("messages.title"),
				'pageBody' : self.closingtemplate.getHtml(),
				'pageFooter' : "<p>Footer</p>"})
			view.setHtml(contents)