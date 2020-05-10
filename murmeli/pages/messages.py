'''Module for the messages pageset'''

from murmeli.pages.base import PageSet
from murmeli.pagetemplate import PageTemplate
from murmeli import inbox


class MessagesPageSet(PageSet):
    '''Messages page set, for showing list of messages etc'''
    def __init__(self, system):
        PageSet.__init__(self, system, "messages")
        self.messages_template = PageTemplate('messages')

    def serve_page(self, view, url, params):
        '''Serve a page to the given view'''
        print("Messages serving page", url, "params:", params)
        database = self.system.get_component(self.system.COMPNAME_DATABASE)
        message_list = database.get_inbox() if database else []
        conreqs = []
        for msg in message_list:
            if not msg or msg.get(inbox.FN_DELETED):
                continue
            timestamp = msg.get(inbox.FN_TIMESTAMP)
            msg[inbox.FN_SENT_TIME_STR] = self.make_local_time_string(timestamp)
            if msg.get(inbox.FN_MSG_TYPE) == "contactrequest":
                conreqs.append(msg)
        num_msgs = len(conreqs)
        bodytext = self.messages_template.get_html(self.get_all_i18n(),
                                                   {"contactrequests":conreqs,
                                                    "contactresponses":[],
                                                    "mails":[], "nummessages":num_msgs,
                                                    "searchterm":'',
                                                    "webcachedir":self.get_web_cache_dir()})
        contents = self.build_page({'pageTitle':self.i18n("messages.title"),
                                    'pageBody':bodytext,
                                    'pageFooter':"<p>Footer</p>"})
        view.set_html(contents)
