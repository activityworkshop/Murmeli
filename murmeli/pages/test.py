'''Module for the test pageset, for diagnostics'''

from murmeli.pages.base import PageSet


class TestPageSet(PageSet):
    '''Example page server, used for testing and providing diagnostics'''
    def __init__(self, system):
        PageSet.__init__(self, system, "test")

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
        view.set_html(page)
