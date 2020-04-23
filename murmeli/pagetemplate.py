'''Page template class for Murmeli'''

from tempita import HTMLTemplate


class PageTemplate:
    '''Class to load a page template from file and i18n it, implementation using tempita'''

    # Constructor
    def __init__(self, pagename):
        lines = []
        if pagename:
            with open('web/' + pagename + '.tmplt', 'rb') as template_file:
                for line in template_file:
                    line = line.decode('utf-8')
                    if line:
                        lines.append(line[:-1])
        self.html = HTMLTemplate(''.join(lines))

    def set_template(self, template):
        '''For tests, allow to set template directly instead of from file'''
        self.html = HTMLTemplate(template)

    def get_html(self, tokens, params=None):
        '''Use the given dictionary (if any) to populate the template'''
        if params is None:
            params = {}
        params["langs"] = tokens
        return self.html.substitute(params)
