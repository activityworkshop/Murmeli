'''Module for the contacts pageset'''

from murmeli.pages.base import PageSet, Bean
from murmeli.pagetemplate import PageTemplate
from murmeli import dbutils
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

    def serve_page(self, view, url, params):
        '''Serve a page to the given view'''
        print("Contacts serving page", url)
        self.require_resources(['button-addperson.png', 'button-addrobot.png',
                                'button-drawgraph.png', 'avatar-none.jpg'])
        database = self.system.get_component(self.system.COMPNAME_DATABASE)
        crypto = self.system.get_component(self.system.COMPNAME_CRYPTO)
        dbutils.export_all_avatars(database, self.get_web_cache_dir())
        contents = None
        commands = self.interpret_commands(url)
        userid = commands[1] if len(commands) == 2 else None
        print("Commands:", commands, ", userid:", userid, ", params:", params)
        if commands[0] == "exportkey":
            own_keyid = dbutils.get_own_key_id(database)
            data_dir = self.get_config().get_data_dir()
            if cryptoutils.export_public_key(own_keyid, data_dir, crypto):
                print("Exported public key")
            else:
                print("FAILED to export public key")
            # TODO: Show javascript alert to confirm that export was done
            return
        if commands[0] == "add":
            contents = self.make_add_page()
        elif commands[0] == "submitadd":
            req_id = params.get('murmeliid') if params else None
            if req_id:
                disp_name = params.get('displayname', '') if params else None
                intro_msg = params.get('intromessage', '') if params else None
                if ContactManager(database, crypto).handle_initiate(req_id, disp_name, intro_msg):
                    print("Initiated contact")
        elif commands[0] == "addrobot":
            contents = self.make_add_robot_page()
        elif commands[0] == "submitaddrobot":
            req_id = params.get('murmeliid') if params else None
            if req_id:
                # initiate contact with robot
                if ContactManager(database, crypto).handle_initiate(req_id, "", "", True):
                    print("Initiated contact")
        elif commands[0] == "edit":
            contents = self.make_list_page(do_edit=True, userid=userid)
        elif commands[0] == "submitedit":
            dbutils.update_profile(self.system.get_component(self.system.COMPNAME_DATABASE),
                                   tor_id=userid, in_profile=params,
                                   pic_output_path=self.get_web_cache_dir())
        # If we haven't got any contents yet, then do a show details
        if not contents:
            contents = self.make_list_page(do_edit=False, userid=userid)
        view.set_html(contents)

    @staticmethod
    def interpret_commands(url):
        '''Take the url to make a list of command to execute and its parameters'''
        if url:
            command = [elem for elem in url.split("/") if elem]
            if command:
                if len(command) == 1:
                    if command[0] in ['add', 'submitadd', 'addrobot', 'submitaddrobot',
                                      'exportkey']:
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

    def make_list_page(self, do_edit=False, userid=None):
        '''Generate a page for listing all the contacts and showing the details of one of them'''
        self.require_resources(['status-self.png', 'status-requested.png', 'status-untrusted.png',
                                'status-trusted.png', 'status-pending.png', 'status-robot.png'])
        config = self.get_config()
        # Who are we showing?
        selectedprofile = self.system.invoke_call(self.system.COMPNAME_DATABASE, "get_profile",
                                                  torid=userid)
        ownprofile = self.system.invoke_call(self.system.COMPNAME_DATABASE, "get_profile",
                                             torid=None)
        if not selectedprofile:
            selectedprofile = ownprofile
        userid = selectedprofile['torid']
        own_page = userid == ownprofile['torid']

        # Build list of contacts
        userboxes = []
        database = self.system.get_component(self.system.COMPNAME_DATABASE)
        for profile in database.get_profiles():
            if profile['status'] in ['requested', 'untrusted', 'trusted', 'self']:
                box = Bean()
                box.set('disp_name', profile['displayName'])
                tor_id = profile['torid']
                box.set('torid', tor_id)
                tile_selected = profile['torid'] == userid
                box.set('tilestyle', "contacttile" + ("selected" if tile_selected else ""))
                box.set('status', profile['status'])
                box.set('last_seen', "")
                box.set('has_robot', dbutils.has_robot(database, tor_id))
                userboxes.append(box)
        # build list of contacts on left of page using these boxes
        tokens = self.get_all_i18n()
        lefttext = self.list_template.get_html(tokens, {'webcachedir':config.get_web_cache_dir(),
                                                        'contacts':userboxes})

        page_props = {"webcachedir":config.get_web_cache_dir(), 'person':selectedprofile}
        page_props["sharedcontacts"] = []
        page_props["posscontactsforthem"] = []
        page_props["posscontactsforme"] = []
        # Work out status of this contact's robot
        contacts = self.system.get_component(self.system.COMPNAME_CONTACTS)
        robot_status = dbutils.get_robot_status(database, userid, contacts)
        page_props['robotstatus'] = self.i18n("contacts.details.robotstatus." + robot_status)
        page_props['robotset'] = (robot_status != 'none')

        # Which template to use depends on whether we're just showing or also editing
        if do_edit:
            # Use two different details templates, one for self and one for others
            page_template = self.editowndetails_template if own_page else self.editdetails_template
        else:
            page_template = self.details_template
        righttext = page_template.get_html(tokens, page_props)


        # Put left side and right side together
        contents = self.build_two_column_page({'pageTitle':self.i18n("contacts.title"),
                                               'leftColumn':lefttext,
                                               'rightColumn':righttext,
                                               'pageFooter':"<p>Footer</p>"})
        return contents

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