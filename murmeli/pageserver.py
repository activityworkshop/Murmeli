'''Module for the pages provided by the system'''

from murmeli.pages.default import DefaultPageSet
from murmeli.pages.contacts import ContactsPageSet
from murmeli.pages.messages import MessagesPageSet
from murmeli.pages.settings import SettingsPageSet
from murmeli.pages.special import SpecialFunctions
from murmeli.pages.test import TestPageSet


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
        self.add_page_set(ContactsPageSet(system))
        self.add_page_set(MessagesPageSet(system))
        self.add_page_set(SettingsPageSet(system))
        self.add_page_set(SpecialFunctions(system))
        self.add_page_set(TestPageSet(system))
