'''Module for the test pageset, for diagnostics'''

from murmeli.pages.base import PageSet
from murmeli.pagetemplate import PageTemplate


class TestPageSet(PageSet):
    '''Example page server, used for testing and providing diagnostics'''
    def __init__(self, system):
        PageSet.__init__(self, system, "test")
        self.outbox_template = PageTemplate('showoutbox')
        self.contacts_template = PageTemplate('showcontacts')

    def serve_page(self, view, url, params):
        '''Serve a page to the given view'''
        print("URL= '%s', params='%s'" % (url, repr(params)))
        if url == "jquery":
            self.require_resource("jquery-3.5.0.slim.js")
            jsfile = "file:///" + self.get_web_cache_dir() + "/jquery-3.5.0.slim.js"
            page = "<html><head>" \
                   "<script src='" + jsfile + "'></script></head>" \
                   "<body><h2>jQuery</h2>" \
                   "<script>document.write('<p>Version: \"' + $.fn.jquery + '\"</p>');</script>" \
                   "<hr/></body></html>"
        elif url in ['showoutbox', 'deleteoutbox']:
            database = self.system.get_component(self.system.COMPNAME_DATABASE)
            if url == 'deleteoutbox':
                database.delete_all_from_outbox()
            mails = [msg for msg in database.get_outbox() if msg]
            page = self.outbox_template.get_html(self.get_all_i18n(),
                                                 {"mails":mails})
        elif url == 'showcontacts':
            database = self.system.get_component(self.system.COMPNAME_DATABASE)
            profiles = [prof for prof in database.get_profiles()]
            page = self.contacts_template.get_html(self.get_all_i18n(),
                                                   {"profiles":profiles})
        else:
            page = "<html><body><p>unknown page: '%s', params='%s'</p></body></html>" % \
                   (url, repr(params))

        view.set_html(page)
