'''Module for the pages provided  by the system'''

import re               # for regular expressions
import os.path
import shutil
import datetime
from PyQt4 import QtGui # for file selection
from i18n import I18nManager
from config import Config
from dbclient import DbClient
from contactmgr import ContactMaker
from pagetemplate import PageTemplate
import message
from fingerprints import FingerprintChecker
from contacts import Contacts


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
		self.addPageSet(SpecialFunctions())

	def addPageSet(self, ps):
		self.pageSets[ps.getDomain()] = ps

	def servePage(self, view, url, params):
		domain, path = self.getDomainAndPath(url)
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

	# TODO: Maybe some images need to be extracted from mongo to the web cache.
	def requirePageResource(self, resource):
		'''Require that the specified resource should be copied from web to the cache directory'''
		cacheDir = Config.getWebCacheDir()
		destPath = os.path.join(cacheDir, resource)
		if not os.path.exists(destPath):
			# dest doesn't exist (if it exists we assume it must still be valid as these resources shouldn't change)
			srcPath = os.path.join("web", resource)
			# TODO: This fails if destPath directory doesn't exist - eg if Config has become blank?
			if os.path.exists(srcPath):
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
			print("Expected a float timestamp, found", type(tstamp))
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
		DbClient.exportAvatars(Config.getWebCacheDir())
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
					DbClient.addMessageToOutbox(outmsg)
				else:
					print("Hmm, show an error message here?")
				# in any case, go back to contact list
				url = "/" + recipientid
				# ensure that picture is generated for new id
				DbClient.exportAvatars(Config.getWebCacheDir())
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
					DbClient.updateContact(userid, params)
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

		# If we haven't got any contents yet, then do a show details
		if not contents:
			# Show details for selected userid (or for self if userid is None)
			contents = self.generateListPage(doEdit=False, userid=userid, extraParams=pageParams)

		view.setHtml(contents)

	def generateAddPage(self):
		'''Build the form page for adding a new user, using the template'''
		bodytext = self.addtemplate.getHtml({"owntorid" : DbClient.getOwnTorId()})
		return self.buildPage({'pageTitle' : I18nManager.getText("contacts.title"),
			'pageBody' : bodytext,
			'pageFooter' : "<p>Footer</p>"})

	def generateFingerprintsPage(self, userid):
		'''Build the page for checking the fingerprints of the selected user'''
		# First, get the name of the user
		person = DbClient.getProfile(userid, False)
		dispName = person.get('displayName', '')
		fullName = person.get('name', '')
		if not dispName: dispName = fullName
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
		person = DbClient.getProfile(userid, False)
		ownFingerprint = CryptoClient.getFingerprint(DbClient.getOwnKeyId())
		usrFingerprint = CryptoClient.getFingerprint(person['keyid'])
		return FingerprintChecker(ownFingerprint, usrFingerprint)

	# Generate a page for listing all the contacts and showing the details of one of them
	def generateListPage(self, doEdit=False, userid=None, extraParams=None):
		self.requirePageResources(['avatar-none.jpg', 'status-self.png', 'status-requested.png', 'status-untrusted.png', 'status-trusted.png'])
		# List of contacts, and show details for the selected one (or self if userid=None)
		selectedprofile = DbClient.getProfile(userid)
		if selectedprofile is None:
			selectedprofile = DbClient.getProfile()
		userid = selectedprofile['torid']
		ownPage = userid == DbClient.getOwnTorId()

		# Build list of contacts
		userboxes = []
		for p in DbClient.getContactList():
			box = Bean()
			box.dispName = p['displayName']
			box.torid = p['torid']
			box.tilestyle = "contacttile" + ("selected" if p['torid'] == userid else "")
			box.status = p['status']
			box.isonline = Contacts.isOnline(box.torid)
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
		DbClient.exportAvatars(Config.getWebCacheDir())
		if url == "/send":
			print("send message of type '%(messageType)s' to id '%(sendTo)s'" % params)
		elif url.startswith("/delete/"):
			DbClient.deleteMessageFromInbox(params.get("msgId", ""))
		# Make dictionary to convert ids to names
		contactNames = {c['torid']:c['displayName'] for c in DbClient.getContactList()}
		unknownSender = I18nManager.getText("messages.sender.unknown")
		unknownRecpt = I18nManager.getText("messages.recpt.unknown")
		# Get contact requests, responses and mails from inbox
		conreqs = []
		conresps = []
		mails = []
		for m in DbClient.getInboxMessages():
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
					m['fromName'] = DbClient.getProfile(m['fromId'], True).get("displayName")
				elif not m.get('messageBody', False):
					m['messageBody'] = I18nManager.getText("messages.contactrequest.accepted")
				conresps.append(m)
			else:
				senderId = m.get('fromId', None)
				if not senderId and m.get('signatureKeyId', None):
					senderId = DbClient.findUserIdFromKeyId(m['signatureKeyId'])
				m['senderName'] = contactNames.get(senderId, unknownSender)
				m['sentTimeStr'] = self.makeLocalTimeString(m['timestamp'])
				# Split m['recipients'] by commas, and look up each id with contactNames
				recpts = m.get('recipients', '')
				if recpts:
					m['recipients'] = ", ".join([contactNames.get(i, unknownRecpt) for i in recpts.split(",")])
				else:
					m['recipients'] = unknownRecpt
				mails.append(m)
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
			DbClient.updateContactList(friendsseefriends)
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
		if url == "/selectfile":
			# Get home directory for file dialog
			homedir = os.path.expanduser("~/")
			# TODO: I18n for "open image" and "image files(*.jpg)"
			fname = QtGui.QFileDialog.getOpenFileName(view, "Open Image", homedir, "Image files (*.jpg)")
			if fname:
				view.page().mainFrame().evaluateJavaScript("updateProfilePic('" + fname + "');")
