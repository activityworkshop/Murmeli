''''Testing of the page server'''

import unittest
from murmeli.pageserver import PageServer, MurmeliPageServer
from murmeli.system import System, Component


class FakeView:
    '''Class to fake the page view, will receive the html to display'''
    def __init__(self):
        self.html = None
    def set_html(self, html):
        '''Receive the html from the server'''
        self.html = html

class FakePageSet:
    '''Class to fake a page set without templates'''
    def __init__(self):
        self.response = None
        self.domain = "watermelon"
    def serve_page(self, view, path, params):
        '''Method called by page server to deliver a page'''
        self.response = "Watermelon: Url: '%s', params: '%s'" % (path, params)
        if view:
            view.set_html(self.response)
    def get_page_title(self, _):
        '''Get the page title'''
        return "wassermelone"


class PageServerTest(unittest.TestCase):
    '''Tests for the basics of the page server'''

    def test_missing_pagename(self):
        '''Check that accessing a missing pagename doesn't give exception'''
        server = PageServer()
        fake_view = FakeView()
        server.serve_page(fake_view, "/chicken.nugget/order", [])
        self.assertIsNone(fake_view.html, "no page served")

    def test_custom_pageset_called(self):
        '''Check that an added page set is properly called'''
        server = PageServer()
        page_set = FakePageSet()
        server.add_page_set(page_set)
        server.serve_page(None, "/watermelon/go.php", [])
        self.assertIsNotNone(page_set.response, "page_set called")
        self.assertTrue("Watermelon" in page_set.response, "watermelon delivered")

    def test_page_titles(self):
        '''Check that page titles are retrieved properly from pagesets'''
        server = PageServer()
        page_set = FakePageSet()
        server.add_page_set(page_set)
        self.assertIsNone(server.get_page_title("apricot/something.html"), "no title")
        title = server.get_page_title("watermelon/something.html")
        self.assertEqual("wassermelone", title, "correct title")

    def test_split_domain_empty(self):
        '''Check that splitting domain and path works for empty urls'''
        for url in [None, "", " ", "/", "//", "///", "http://murmeli/", "http://murmeli//"]:
            domain, path = PageServer.get_domain_and_path(url)
            self.assertEqual(domain, "", "empty domain from %s" % repr(url))
            self.assertEqual(path, "", "empty path from %s" % repr(url))

    def test_split_path_empty(self):
        '''Check that splitting domain and path works for urls with only a domain'''
        for url in ["firework", "/firework", " firework", "/firework/",
                    "http://murmeli/firework/", " http://murmeli//firework/ "]:
            domain, path = PageServer.get_domain_and_path(url)
            self.assertEqual(domain, "firework", "matching domain from %s" % repr(url))
            self.assertEqual(path, "", "empty path from %s" % repr(url))

    def test_split_domain_and_path(self):
        '''Check that splitting domain and path works for urls with both domain and path'''
        for url in ["firework/sparkler", "/firework/sparkler", " ///firework/sparkler"]:
            domain, path = PageServer.get_domain_and_path(url)
            self.assertEqual(domain, "firework", "matching domain from %s" % repr(url))
            self.assertEqual(path, "sparkler", "matching path from %s" % repr(url))

    def test_home_page(self):
        '''Check that home page works from default page set'''
        server = MurmeliPageServer(None)
        fake_view = FakeView()
        server.serve_page(fake_view, "/", [])
        self.assertTrue("fancyheader" in fake_view.html, "home page served")
        # There are no other pages so default is also used for unrecognised domains
        server.serve_page(fake_view, "/chicken.nugget/order", [])
        self.assertTrue("fancyheader" in fake_view.html, "home page served")

    def test_two_domains(self):
        '''Check that two added page sets are properly called'''
        server = MurmeliPageServer(None)
        page_set = FakePageSet()
        server.add_page_set(page_set)
        fake_view = FakeView()
        server.serve_page(fake_view, "/watermelon/go.php", [])
        self.assertTrue("Watermelon" in fake_view.html, "watermelon page served")
        server.serve_page(fake_view, "/", [])
        self.assertTrue("fancyheader" in fake_view.html, "home page served")
        self.assertFalse("Watermelon" in fake_view.html, "watermelon page not served")
        server.serve_page(fake_view, "/papaya/juice.html", [])
        self.assertTrue("fancyheader" in fake_view.html, "home page served for unknown domain")


class FakeI18n(Component):
    '''Fake internationalisation'''
    def __init__(self, parent):
        Component.__init__(self, parent, System.COMPNAME_I18N)

    def get_text(self, key):
        '''Get the i18n of the key if found, otherwise return the key'''
        _ = key
        return "ChickenChickenChicken"

    def get_all_texts(self):
        '''Not needed for these tests'''
        return None


class PoultryPageServerTest(unittest.TestCase):
    '''Tests for the i18n of the page server'''

    def test_home_page(self):
        '''Check that accessing the home page with a fake i18n gives chickens'''
        system = System()
        i18n = FakeI18n(system)
        system.add_component(i18n)
        server = MurmeliPageServer(system)
        # don't add the page server to the system, as it's not a component
        fake_view = FakeView()
        server.serve_page(fake_view, "/chicken/tikka/massala", [])
        self.assertTrue("ChickenChickenChicken" in fake_view.html, "wow that's a lot of chickens")


if __name__ == "__main__":
    unittest.main()
