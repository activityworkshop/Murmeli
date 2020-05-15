'''Module for the compose pageset'''

from murmeli.pages.base import PageSet, Bean
from murmeli.pagetemplate import PageTemplate
from murmeli import dbutils
from murmeli.message import RegularMessage
from murmeli import inbox


class ComposePageSet(PageSet):
    '''Functions for composing a new message'''
    def __init__(self, system):
        PageSet.__init__(self, system, "compose")
        self.compose_templ = PageTemplate('composemessage')
        self.closing_templ = PageTemplate('windowclosing')

    def get_page_title(self, path):
        '''Get the page title for the given path'''
        if path == "start":
            return self.i18n("messages.createnew")
        return None

    def serve_page(self, view, url, params):
        '''Serve a page to the given view'''
        if url == "start":
            self.require_resources(['default.css', 'jquery-3.5.0.slim.js'])
            database = self.system.get_component(self.system.COMPNAME_DATABASE)
            dbutils.export_all_avatars(database, self.get_web_cache_dir())
            parent_hash = params.get("reply")
            # Build list of contacts to whom we can send
            userboxes = []
            for profile in self.system.invoke_call(self.system.COMPNAME_DATABASE, "get_profiles"):
                if profile['status'] in ['untrusted', 'trusted']:
                    box = Bean()
                    box.set('disp_name', profile['displayName'])
                    box.set('torid', profile['torid'])
                    userboxes.append(box)
            page_params = {"contactlist":userboxes, "parenthash":parent_hash or "",
                           "webcachedir":self.get_web_cache_dir(),
                           "recipientids":params.get("sendto")}
            tokens = self.get_all_i18n()
            conts = self.build_page({'pageTitle':self.i18n("composemessage.title"),
                                     'pageBody':self.compose_templ.get_html(tokens, page_params),
                                     'pageFooter':"<p>Footer</p>"})
            view.set_html(conts)
            # If we've got no friends, then warn, can't send to anyone
            if not dbutils.has_friends(database):
                view.page().runJavaScript("window.alert('No friends :(');")
        elif url == "send":
            print("Compose pageset, called 'send'")
            msg_body = params.get('messagebody')
            if not msg_body:
                # TODO: throw an exception or just ignore?
                pass
            parent_hash = params.get("parenthash")
            recpts = params.get('sendto')
            # Make a corresponding message object and pass it on
            msg = RegularMessage()
            msg.set_field(msg.FIELD_RECIPIENTS, recpts)
            msg.set_field(msg.FIELD_MSGBODY, msg_body)
            msg.set_field(msg.FIELD_REPLYHASH, parent_hash)
            msg.recipients = recpts.split(",")
            print("Send this message:", type(msg))
            crypto = self.system.get_component(self.system.COMPNAME_CRYPTO)
            database = self.system.get_component(self.system.COMPNAME_DATABASE)
            dbutils.add_message_to_outbox(msg, crypto, database)
            # Save a copy of the sent message
            msg.set_field(msg.FIELD_SENDER_ID, dbutils.get_own_tor_id(database))
            dbutils.add_message_to_inbox(msg, database, inbox.MC_NORMAL_SENT)
            # Close window after successful send
            tokens = self.get_all_i18n()
            contents = self.build_page({'pageTitle':self.i18n("messages.title"),
                                        'pageBody':self.closing_templ.get_html(tokens),
                                        'pageFooter':"<p>Footer</p>"})
            view.set_html(contents)
