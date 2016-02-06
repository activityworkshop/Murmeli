from i18n import I18nManager
from config import Config
from pagetemplate import PageTemplate
import os.path

class PageServer:
	'''PageServer, containing several page sets'''
	def __init__(self):
		self.pageSets = {}
		self.addPageSet(DefaultPageSet())
		self.addPageSet(ContactsPageSet())
		self.addPageSet(MessagesPageSet())
		self.addPageSet(CalendarPageSet())
		self.addPageSet(SettingsPageSet())

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

# Superclass of all page servers
class PageSet:
	def __init__(self, domain):
		self.domain = domain
		self.standardHead = "<html><head><meta http-equiv=\"Content-Type\" content=\"text/html; charset=utf-8\"><link href='file://" + Config.getWebCacheDir() + "/default.css' type='text/css' rel='stylesheet'><script type='text/javascript'>function hideOverlay(){showLayer('overlay',false);showLayer('popup',false)} function showLayer(lname,show){document.getElementById(lname).style.visibility=(show?'visible':'hidden');} function showMessage(mess){document.getElementById('popup').innerHTML=mess; showLayer('overlay',true); showLayer('popup', true);}</script></head>"

	def getDomain(self): return self.domain

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

	# General page-building method using a standard template
	# and filling in the gaps using the given dictionary
	def buildPage(self, params):
		self.requirePageResource("default.css")
		return ''.join([self.standardHead,
			"<body>",
			"<table border='0' width='100%%'><tr><td><div class='fancyheader'><p>%(pageTitle)s</p></div></td></tr>",
			"<tr><td><div class='genericbox'>%(pageBody)s</div></td></tr>",
			"<tr><td><div class='footer'>%(pageFooter)s</div></td></tr></table>",
			"<div class='overlay' id='overlay' onclick='hideOverlay()'></div>",
			"<div class='popuppanel' id='popup'>Here's the message</div>",
			"</body></html>"]) % params


# Default page server, just for home page
class DefaultPageSet(PageSet):
	def __init__(self):
		PageSet.__init__(self, "")
		self.hometemplate = PageTemplate('home')

	def servePage(self, view, url, params):
		contents = self.buildPage({'pageTitle' : "Murmeli",
			'pageBody' : self.hometemplate.getHtml(),
			'pageFooter' : "<p>Footer</p>"})
		view.setHtml(contents)


# Contacts page server, for showing list of contacts etc
class ContactsPageSet(PageSet):
	# Constructor
	def __init__(self):
		PageSet.__init__(self, "contacts")
		self.listtemplate = PageTemplate('contactlist')

	def servePage(self, view, url, params):
		contents = self.buildPage({'pageTitle' : I18nManager.getText("contacts.title"),
			'pageBody' : self.listtemplate.getHtml(),
			'pageFooter' : "<p>Footer</p>"})
		view.setHtml(contents)


# Messages page server, for showing list of messages etc
class MessagesPageSet(PageSet):
	def __init__(self):
		PageSet.__init__(self, "messages")
		self.messagestemplate = PageTemplate('messages')

	def servePage(self, view, url, params):
		contents = self.buildPage({'pageTitle' : I18nManager.getText("messages.title"),
			'pageBody' : self.messagestemplate.getHtml(),
			'pageFooter' : "<p>Footer</p>"})
		view.setHtml(contents)


# Calendar page server, for showing list of events, reminders etc
class CalendarPageSet(PageSet):
	def __init__(self):
		PageSet.__init__(self, "calendar")
		self.calendartemplate = PageTemplate('calendar')

	def servePage(self, view, url, params):
		contents = self.buildPage({'pageTitle' : I18nManager.getText("calendar.title"),
			'pageBody' : self.calendartemplate.getHtml(),
			'pageFooter' : "<p>Footer</p>"})
		view.setHtml(contents)


# Settings page server, for showing the current settings
class SettingsPageSet(PageSet):
	def __init__(self):
		PageSet.__init__(self, "settings")
		self.formtemplate = PageTemplate('settingsform')

	def servePage(self, view, url, params):
		contents = self.buildPage({'pageTitle' : I18nManager.getText("settings.title"),
			'pageBody' : self.formtemplate.getHtml(),
			'pageFooter' : "<p>Footer</p>"})
		view.setHtml(contents)


