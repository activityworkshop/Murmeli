'''Module for the default pageset provided by the system'''

from murmeli.pages.base import PageSet
from murmeli.pagetemplate import PageTemplate


class DefaultPageSet(PageSet):
    '''Default page server, just for home page'''
    def __init__(self, system):
        PageSet.__init__(self, system, "")
        self.hometemplate = PageTemplate('home')

    def serve_page(self, view, url, params):
        '''Serve a page to the given view'''
        self.require_resource('avatar-none.jpg')
        _ = (url, params)
        page_title = self.i18n("home.title") or ""
        tokens = self.get_all_i18n()
        contents = self.build_page({'pageTitle':page_title,
                                    'pageBody':self.hometemplate.get_html(tokens),
                                    'pageFooter':"<p>Footer</p>"})
        view.set_html(contents)
