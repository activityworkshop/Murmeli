'''Module for the contacts pageset'''

from datetime import datetime
from murmeli.pages.base import PageSet, Bean
from murmeli.pagetemplate import PageTemplate
from murmeli import dbutils
from murmeli.fingerprints import FingerprintChecker
from murmeli.contactmgr import ContactManager
from murmeli import cryptoutils


class ContactsPageSet(PageSet):
    '''Contacts page server, for showing list of contacts etc'''
    def __init__(self, system):
        PageSet.__init__(self, system, "contacts")
        self.list_template = PageTemplate('contactlist')
        self.details_template = PageTemplate('contactdetails')
        self.editowndetails_template = PageTemplate('editcontactself')
        self.editdetails_template = PageTemplate('editcontact')
        self.add_template = PageTemplate('addcontact')
        self.addrobot_template = PageTemplate('addrobot')
        self.fingerprintstemplate = PageTemplate('fingerprints')

    def serve_page(self, view, url, params):
        '''Serve a page to the given view'''
        print("Contacts serving page", url)
        self.require_resources(['button-addperson.png', 'button-addrobot.png',
                                'button-removerobot.png',
                                'button-drawgraph.png', 'avatar-none.jpg'])
        database = self.system.get_component(self.system.COMPNAME_DATABASE)
        crypto = self.system.get_component(self.system.COMPNAME_CRYPTO)
        dbutils.export_all_avatars(database, self.get_web_cache_dir())
        commands = self.interpret_commands(url)
        if commands[0] == "exportkey":
            if self._export_key(crypto, database):
                view.page().runJavaScript("showMessage('%s')" % \
                  self.i18n('contacts.confirm.keyexported'))
            return

        contents, page_params, userid = self.make_page_contents(commands, params)
        # If we haven't got any contents yet, then do a show details
        contents = contents or self.make_list_page(do_edit=False, userid=userid,
                                                   extra_params=page_params)
        view.set_html(contents)

    def make_page_contents(self, commands, params):
        '''Make the page contents given the command and parameters'''
        userid = commands[1] if len(commands) == 2 else None
        database = self.system.get_component(self.system.COMPNAME_DATABASE)
        crypto = self.system.get_component(self.system.COMPNAME_CRYPTO)
        contents = None
        page_params = {}
        if commands[0] == "add":
            contents = self.make_add_page()
        elif commands[0] == "submitadd":
            req_id = params.get('murmeliid') if params else None
            if req_id:
                disp_name = params.get('displayname', '') if params else None
                intro_msg = params.get('intromessage', '') if params else None
                ContactManager(database, crypto).handle_initiate(req_id, disp_name, intro_msg)
                # ensure that avatar is exported for this new contact
                dbutils.export_all_avatars(database, self.get_web_cache_dir())
        elif commands[0] == "addrobot":
            contents = self.make_add_robot_page()
        elif commands[0] == "submitaddrobot":
            req_id = params.get('murmeliid') if params else None
            if req_id:
                ContactManager(database, crypto).handle_initiate(req_id, "", "", True)
        elif commands[0] == "removerobot":
            ContactManager(database, crypto).handle_robot_removal()
        elif commands[0] == "edit":
            contents = self.make_list_page(do_edit=True, userid=userid)
        elif commands[0] == "submitedit":
            assert not set(params.keys()).intersection(['status', 'keyid'])
            dbutils.update_profile(database, tor_id=userid, in_profile=params,
                                   pic_output_path=self.get_web_cache_dir())
        elif commands[0] == "checkfingerprint":
            contents = self.make_checkfinger_page(commands[1], params.get('lang'))
        elif commands[0] == "checkedfingerprint":
            given_answer = self.get_param_as_int(params, "answer", -1)
            fingers = self._make_fingerprint_checker(userid)
            # Compare with expected answer, generate appropriate page
            if given_answer == fingers.get_correct_answer():
                pending_referrals = []
                ContactManager(database, crypto, self.get_config()).key_fingerprint_checked( \
                  userid, pending_referrals)
                print("Pending referrals:", pending_referrals)
                for msg in pending_referrals:
                    self.system.invoke_call(self.system.COMPNAME_MSG_HANDLER, "receive", msg=msg)
                # Show page again
                contents = self.make_checkfinger_page(userid, params.get('lang'))
            else:
                page_params['fingerprint_check_failed'] = True
        elif commands[0] == "delete" and userid:
            ContactManager(database, None, self.get_config()).delete_contact(userid)
            userid = None
        elif commands[0] == "refer":
            intro = str(params.get('introMessage', ""))
            ContactManager(database, crypto).send_referral_messages(commands[1], commands[2],
                                                                    intro)
        return (contents, page_params, userid)

    def _export_key(self, crypto, database):
        '''Export our own public key to a file in our data directory'''
        own_keyid = dbutils.get_own_key_id(database)
        data_dir = self.get_config().get_data_dir()
        if cryptoutils.export_public_key(own_keyid, data_dir, crypto):
            print("Exported public key")
            return True
        print("FAILED to export public key")
        return False

    @staticmethod
    def interpret_commands(url):
        '''Take the url to make a list of command to execute and its parameters'''
        if url:
            command = [elem for elem in url.split("/") if elem]
            if command:
                if len(command) == 1:
                    if command[0] in ['add', 'submitadd', 'addrobot', 'submitaddrobot',
                                      'exportkey', 'removerobot']:
                        return command
                    if ContactsPageSet.looks_like_userid(command[0]):
                        return ['show', command[0]]
                elif len(command) == 2:
                    if ContactsPageSet.looks_like_userid(command[0]):
                        if command[1] in ['edit', 'submitedit', 'delete', 'checkfingerprint',
                                          'checkedfingerprint']:
                            return [command[1], command[0]]
                elif len(command) == 3:
                    if ContactsPageSet.looks_like_userid(command[0]) and \
                     ContactsPageSet.looks_like_userid(command[2]):
                        if command[1] in ['refer', 'requestrefer']:
                            return [command[1], command[0], command[2]]
        return ['show', None]

    def make_list_page(self, do_edit=False, userid=None, extra_params=None):
        '''Generate a page for listing all the contacts and showing the details of one of them'''
        self.require_resources(['status-self.png', 'status-requested.png', 'status-untrusted.png',
                                'status-trusted.png', 'status-robot.png'])
        # Who are we showing?
        selectedprofile = self.system.invoke_call(self.system.COMPNAME_DATABASE, "get_profile",
                                                  torid=userid)
        ownprofile = self.system.invoke_call(self.system.COMPNAME_DATABASE, "get_profile",
                                             torid=None)
        if not selectedprofile:
            selectedprofile = ownprofile
        userid = selectedprofile['torid']

        # Build list of contacts
        userboxes, has_friends = self._make_user_boxes(userid)
        # build left side of page using these boxes
        lefttext = self.list_template.get_html(self.get_all_i18n(),
                                               {'webcachedir':self.get_web_cache_dir(),
                                                'contacts':userboxes,
                                                'has_friends':has_friends})

        page_props = {"webcachedir":self.get_web_cache_dir(), 'person':selectedprofile}
        # Add extra parameters if necessary
        if extra_params:
            page_props.update(extra_params)
        # See which contacts we have in common with this person
        database = self.system.get_component(self.system.COMPNAME_DATABASE)
        shared_info = ContactManager(database, None).get_shared_possible_contacts(userid)
        page_props["sharedcontacts"] = self._make_id_name_bean_list(shared_info.get_shared_ids())
        page_props["posscontactsforthem"] = self._make_id_name_bean_list( \
          shared_info.get_ids_for_them())
        page_props["posscontactsforme"] = []
        # Work out status of this contact's robot
        robot_status = dbutils.get_robot_status(database, userid, \
          self.system.get_component(self.system.COMPNAME_CONTACTS))
        page_props['robotstatus'] = self.i18n("contacts.details.robotstatus." + robot_status)
        page_props['robotset'] = (robot_status != 'none')

        # Which template to use depends on whether we're just showing or also editing
        if do_edit:
            # Use two different details templates, one for self and one for others
            page_templ = self.editowndetails_template if userid == ownprofile['torid'] \
              else self.editdetails_template
        else:
            page_templ = self.details_template

        # Put left side and right side together
        return self.build_two_column_page({'pageTitle':self.i18n("contacts.title"),
                                           'leftColumn':lefttext,
                                           'rightColumn':page_templ.get_html(self.get_all_i18n(),
                                                                             page_props),
                                           'pageFooter':"<p>Footer</p>"})

    def _make_user_boxes(self, selected_id):
        '''Make a list of boxes for our contacts'''
        userboxes = []
        has_friends = False
        database = self.system.get_component(self.system.COMPNAME_DATABASE)
        for profile in database.get_profiles():
            if profile['status'] in ['requested', 'untrusted', 'trusted', 'self']:
                box = Bean()
                box.set('disp_name', profile['displayName'])
                tor_id = profile['torid']
                box.set('torid', tor_id)
                tile_selected = profile['torid'] == selected_id
                box.set('tilestyle', "contacttile" + ("selected" if tile_selected else ""))
                box.set('status', profile['status'])
                is_online = self.system.invoke_call(self.system.COMPNAME_CONTACTS,
                                                    "is_online", tor_id=tor_id)
                last_time = self.system.invoke_call(self.system.COMPNAME_CONTACTS,
                                                    "last_seen", tor_id=tor_id)
                box.set('last_seen', self._make_lastseen_string(is_online, last_time))
                box.set('has_robot', dbutils.has_robot(database, tor_id))
                userboxes.append(box)
                if profile['status'] in ['untrusted', 'trusted']:
                    has_friends = True
        return (userboxes, has_friends)

    @staticmethod
    def _make_id_name_bean_list(contact_list):
        '''Make a list of Bean objects for the given contact list'''
        con_list = []
        for cid, cname in contact_list:
            pair = Bean()
            pair.set('torid', cid)
            pair.set('disp_name', cname)
            con_list.append(pair)
        return con_list

    def _make_lastseen_string(self, online, last_time):
        '''Make a string describing the online / offline status'''
        curr_time = datetime.now()
        if last_time and (curr_time-last_time).total_seconds() < 18000:
            token = "contacts.onlinesince" if online else "contacts.offlinesince"
            return self.i18n(token) % str(last_time.timetz())[:5]
        if online:
            return self.i18n("contacts.online")
        return ""

    def make_add_page(self):
        '''Build the form page for adding a new contact, using the template'''
        own_profile = self.system.invoke_call(self.system.COMPNAME_DATABASE, "get_profile")
        own_tor_id = own_profile.get("torid") if own_profile else None
        tokens = self.get_all_i18n()
        bodytext = self.add_template.get_html(tokens, {"owntorid":own_tor_id or ""})
        return self.build_page({'pageTitle':self.i18n("contacts.title"),
                                'pageBody':bodytext,
                                'pageFooter':"<p>Footer</p>"})

    def make_add_robot_page(self):
        '''Build the form page for adding a new robot, using the template'''
        own_profile = self.system.invoke_call(self.system.COMPNAME_DATABASE, "get_profile") or {}
        own_tor_id = own_profile.get("torid")
        robot_id = own_profile.get("robotid")
        bodytext = self.addrobot_template.get_html(self.get_all_i18n(),
                                                   {"owntorid":own_tor_id or "",
                                                    "robotid":robot_id or ""})
        return self.build_page({'pageTitle':self.i18n("contacts.title"),
                                'pageBody':bodytext,
                                'pageFooter':"<p>Footer</p>"})

    def make_checkfinger_page(self, userid, lang):
        '''Generate a page for checking the fingerprint of the given user'''
        # First, get the name of the user
        person = self.system.invoke_call(self.system.COMPNAME_DATABASE, "get_profile",
                                         torid=userid)
        disp_name = person['displayName']
        full_name = person['name']
        if disp_name != full_name:
            full_name = "%s (%s)" % (disp_name, full_name)
        # check it's ok to generate
        status = person.get('status')
        if status not in ['untrusted', 'trusted']:
            print("Not generating fingerprints page because status is", status)
            return None
        fingers = self._make_fingerprint_checker(userid)
        page_params = {"mywords":fingers.get_code_words(True, 0, lang or "en"),
                       "theirwords0":fingers.get_code_words(False, 0, lang or "en"),
                       "theirwords1":fingers.get_code_words(False, 1, lang or "en"),
                       "theirwords2":fingers.get_code_words(False, 2, lang or "en"),
                       "fullname":full_name, "shortname":disp_name, "userid":userid,
                       "language_en":"", "language_de":"",
                       "alreadychecked":status == "trusted"}
        page_params["language_" + (lang or "en")] = "selected"
        body_text = self.fingerprintstemplate.get_html(self.get_all_i18n(), page_params)
        return self.build_page({'pageTitle':self.i18n("contacts.title"),
                                'pageBody':body_text,
                                'pageFooter':"<p>Footer</p>"})

    def _make_fingerprint_checker(self, userid):
        '''Use the given userid to make a FingerprintChecker between me and them'''
        own_profile = self.system.invoke_call(self.system.COMPNAME_DATABASE, "get_profile",
                                              torid=None)
        own_fingerprint = self.system.invoke_call(self.system.COMPNAME_CRYPTO, "get_fingerprint",
                                                  key_id=own_profile['keyid'])
        person = self.system.invoke_call(self.system.COMPNAME_DATABASE, "get_profile",
                                         torid=userid)
        other_fingerprint = self.system.invoke_call(self.system.COMPNAME_CRYPTO, "get_fingerprint",
                                                    key_id=person['keyid'])
        assert own_fingerprint and other_fingerprint
        return FingerprintChecker(own_fingerprint, other_fingerprint)
