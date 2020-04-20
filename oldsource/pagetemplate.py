'''Page template class for Murmeli'''

from tempita import HTMLTemplate
from i18n import I18nManager


class PageTemplate:
	'''Class to load a page template from file and i18n it, implementation using tempita'''
	# Constructor
	def __init__(self, pagename):
		lines = []
		with open('web/' + pagename + '.tmplt', 'rb') as f:
			for l in f:
				l = l.decode('utf-8')
				if l:
					lines.append(l[:-1])
		self.html = HTMLTemplate(''.join(lines))

	def getHtml(self, params=None):
		'''Use the given dictionary (if any) to populate the template'''
		if params is None:
			params = {}
		params["langs"] = I18nManager.texts
		return self.html.substitute(params)
