'''Module for the messages pageset'''

from murmeli.pages.base import PageSet


class MessagesPageSet(PageSet):
    '''Messages page set, for showing list of messages etc'''
    def __init__(self, system):
        PageSet.__init__(self, system, "messages")

    def serve_page(self, view, url, params):
        '''Serve a page to the given view'''
        print("Messages serving page", url, "params:", params)
        page_title = self.i18n("messages.title") or "<messages>"
        page_body = "<p>Messages page: '%s'</p><p><a href='/'>[back]</a></p>" % url
        contents = self.build_page({'pageTitle':page_title,
                                    'pageBody':page_body,
                                    'pageFooter':"<p>Footer</p>"})
        view.set_html(contents)
