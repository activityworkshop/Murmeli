#####################################
## Page template class for Murmeli ##
#####################################

from i18n import I18nManager
from config import Config
from tempita import HTMLTemplate

# Class to load a page template from file and i18n it
class PageTemplate:
	'''Implementation using tempita'''
	# Constructor
	def __init__(self, pagename):
		lines = []
		with open('web/' + pagename + '.tmplt', 'rb') as f:
			for l in f:
				l = l.decode('utf-8')
				if l:
					lines.append(l[:-1])
		self.html = HTMLTemplate(''.join(lines))

	def getHtml(self, params={}):
		'''Use the given dictionary to populate the template'''
		params["langs"] = I18nManager.texts
		return self.html.substitute(params)
