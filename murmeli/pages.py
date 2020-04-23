'''Module for the pages provided by the system'''

from murmeli.pagetemplate import PageTemplate


class PageServer:
    '''PageServer, containing several page sets'''
    def __init__(self):
        self.page_sets = {}
        # keep track of the windows we have opened (so they're not garbage-collected)
        self.extra_windows = set()

    def add_page_set(self, pageset):
        '''Add a page set'''
        self.page_sets[pageset.domain] = pageset

    def serve_page(self, view, url, params):
        '''Serve the page associated with the given url and parameters'''
        domain, path = self.get_domain_and_path(url)
        page_set = self.page_sets.get(domain)
        if not page_set:
            page_set = self.page_sets.get("")
        if page_set:
            page_set.serve_page(view, path, params)

    @staticmethod
    def get_domain_and_path(url):
        '''Extract the domain and path from the given url'''
        stripped_url = url.strip() if url else ""
        if stripped_url.startswith("http://murmeli/"):
            stripped_url = stripped_url[15:]
        while stripped_url.startswith("/"):
            stripped_url = stripped_url[1:]
        slashpos = stripped_url.find("/")
        if slashpos < 0:
            return (stripped_url, '')
        return (stripped_url[:slashpos], stripped_url[slashpos + 1:])

    def get_page_title(self, path):
        '''Get the title of the specified page from one of the pagesets'''
        domain, subpath = self.get_domain_and_path(path)
        page_set = self.page_sets.get(domain)
        return page_set.get_page_title(subpath) if page_set else None


class MurmeliPageServer(PageServer):
    '''Page server used for Murmeli'''
    def __init__(self, system):
        PageServer.__init__(self)
        self.add_page_set(DefaultPageSet(system))


class PageSet:
    '''Superclass of all page sets'''
    def __init__(self, system, domain):
        self.system = system
        self.domain = domain
        self.std_head = ("<html><head>"
                         "<meta http-equiv=\"Content-Type\" content=\"text/html; charset=utf-8\">"
                         "</script></head>")

    def build_page(self, params):
        '''General page-building method using a standard template
           and filling in the gaps using the given dictionary'''
        return ''.join([self.std_head,
                        "<body>",
                        "<table border='0' width='100%%'>"
                        "<tr><td><div class='fancyheader'><p>%(pageTitle)s</p></div></td></tr>",
                        "<tr><td><div class='genericbox'>%(pageBody)s</div></td></tr>",
                        "<tr><td><div class='footer'>%(pageFooter)s</div></td></tr></table>",
                        "<div class='overlay' id='overlay' onclick='hideOverlay()'></div>",
                        "<div class='popuppanel' id='popup'>Here's the message</div>",
                        "</body></html>"]) % params

    def get_page_title(self, _):
        '''Get the page title for any path by default'''
        return None


class DefaultPageSet(PageSet):
    '''Default page server, just for home page'''
    def __init__(self, system):
        PageSet.__init__(self, system, "")
        self.hometemplate = PageTemplate('home')

    def serve_page(self, view, url, params):
        '''Serve a page to the given view'''
        _ = (url, params)
        page_title = "home.title"
        contents = self.build_page({'pageTitle':page_title,
                                    'pageBody':self.hometemplate.get_html({}),
                                    'pageFooter':"<p>Footer</p>"})
        view.set_html(contents)
