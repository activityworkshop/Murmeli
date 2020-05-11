'''Module for the messages pageset'''

from murmeli.pages.base import PageSet
from murmeli.pagetemplate import PageTemplate
from murmeli.contactmgr import ContactManager
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

        if url == 'send':
            if params['messageType'] == "contactresponse":
                if params.get('accept') == "1":
                    crypto = self.system.get_component(self.system.COMPNAME_CRYPTO)
                    ContactManager(database, crypto).handle_accept(params.get('sendTo'),
                                                                   params.get('messageBody'))
                else:
                    ContactManager(database, None).handle_deny(params.get('sendTo'))

        message_list = database.get_inbox() if database else []
        conreqs = []
        conresps = []
        for msg in message_list:
            if not msg or msg.get(inbox.FN_DELETED):
                continue
            timestamp = msg.get(inbox.FN_TIMESTAMP)
            msg[inbox.FN_SENT_TIME_STR] = self.make_local_time_string(timestamp)
            msg_type = msg.get(inbox.FN_MSG_TYPE)
            if msg_type == "contactrequest":
                conreqs.append(msg)
            elif msg_type == "contactresponse":
                msg[inbox.FN_MSG_BODY] = self.fix_conresp_body(msg.get(inbox.FN_MSG_BODY),
                                                               msg.get(inbox.FN_ACCEPTED))
                conresps.append(msg)

        bodytext = self.messages_template.get_html(self.get_all_i18n(),
                                                   {"contactrequests":conreqs,
                                                    "contactresponses":conresps,
                                                    "mails":[],
                                                    "nummessages":len(conreqs) + len(conresps),
                                                    "searchterm":'',
                                                    "webcachedir":self.get_web_cache_dir()})
        contents = self.build_page({'pageTitle':self.i18n("messages.title"),
                                    'pageBody':bodytext,
                                    'pageFooter':"<p>Footer</p>"})
        view.set_html(contents)

    def fix_conresp_body(self, msg_body, accepted):
        '''If a contact response message has a blank message body, replace it'''
        if msg_body:
            return msg_body
        suffix = "acceptednomessage" if accepted else "refused"
        return self.i18n("messages.contactrequest." + suffix)
