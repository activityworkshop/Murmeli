'''Module for the messages pageset'''

from murmeli.pages.base import PageSet
from murmeli.pagetemplate import PageTemplate
from murmeli import dbutils
from murmeli.contactmgr import ContactManager
from murmeli.messageutils import MessageTree
from murmeli import inbox


class MessagesPageSet(PageSet):
    '''Messages page set, for showing list of messages etc'''
    def __init__(self, system):
        PageSet.__init__(self, system, "messages")
        self.messages_template = PageTemplate('messages')

    def serve_page(self, view, url, params):
        '''Serve a page to the given view'''
        print("Messages serving page", url, "params:", params)
        self.require_resources(['button-compose.png', 'default.css', 'avatar-none.jpg'])
        database = self.system.get_component(self.system.COMPNAME_DATABASE)
        dbutils.export_all_avatars(database, self.get_web_cache_dir())

        self._process_command(url, params)

        # Make dictionary to convert ids to names
        contact_names = {cont['torid']:cont['displayName'] for cont in database.get_profiles()}
        unknown_sender = self.i18n("messages.sender.unknown")
        unknown_recpt = self.i18n("messages.recpt.unknown")

        message_list = database.get_inbox() if database else []
        conreqs = []
        conresps = []
        mail_tree = MessageTree()
        for msg in message_list:
            if not msg or msg.get(inbox.FN_DELETED):
                continue
            timestamp = msg.get(inbox.FN_TIMESTAMP)
            msg[inbox.FN_SENT_TIME_STR] = self.make_local_time_string(timestamp)
            msg_type = msg.get(inbox.FN_MSG_TYPE)
            # Lookup sender name for display
            sender_id = msg.get(inbox.FN_FROM_ID)
            if not msg.get(inbox.FN_FROM_NAME):
                msg[inbox.FN_FROM_NAME] = contact_names.get(sender_id, unknown_sender)
            if msg_type in ["contactrequest", "contactrefer"]:
                conreqs.append(msg)
            elif msg_type == "contactresponse":
                msg[inbox.FN_MSG_BODY] = self.fix_conresp_body(msg.get(inbox.FN_MSG_BODY),
                                                               msg.get(inbox.FN_ACCEPTED))
                conresps.append(msg)
            elif msg_type == "normal":
                recpts = msg.get(inbox.FN_RECIPIENTS)
                if recpts:
                    reply_all = recpts.split(",")
                    recpt_name_list = [contact_names.get(i, unknown_recpt) for i in reply_all]
                    msg[inbox.FN_RECIPIENT_NAMES] = ", ".join(recpt_name_list)
                    reply_all.append(sender_id)
                    msg[inbox.FN_REPLY_ALL] = ",".join(reply_all)
                mail_tree.add_msg(msg)

        mails = mail_tree.build()
        num_msgs = len(conreqs) + len(conresps) + len(mails)
        bodytext = self.messages_template.get_html(self.get_all_i18n(),
                                                   {"contactrequests":conreqs,
                                                    "contactresponses":conresps,
                                                    "mails":mails, "nummessages":num_msgs,
                                                    "webcachedir":self.get_web_cache_dir()})
        contents = self.build_page({'pageTitle':self.i18n("messages.title"),
                                    'pageBody':bodytext,
                                    'pageFooter':"<p>Footer</p>"})
        view.set_html(contents)

    def _process_command(self, url, params):
        '''Process a command given by the url and params'''
        database = self.system.get_component(self.system.COMPNAME_DATABASE)
        if url == 'send':
            if params.get('messageType') == "contactresponse":
                if params.get('accept') == "1":
                    crypto = self.system.get_component(self.system.COMPNAME_CRYPTO)
                    ContactManager(database, crypto).handle_accept(params.get('sendTo'),
                                                                   params.get('messageBody'))
                else:
                    ContactManager(database, None).handle_deny(params.get('sendTo'))
        elif url == 'delete':
            msg_index = self.get_param_as_int(params, 'msgId')
            if msg_index >= 0 and not database.delete_from_inbox(msg_index):
                print("Delete of inbox message '%d' failed" % msg_index)

    def fix_conresp_body(self, msg_body, accepted):
        '''If a contact response message has a blank message body, replace it'''
        if msg_body:
            return msg_body
        suffix = "acceptednomessage" if accepted else "refused"
        return self.i18n("messages.contactrequest." + suffix)
