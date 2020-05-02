'''Module for the pages provided by the system'''

import os
import shutil
import re
from murmeli.pagetemplate import PageTemplate
from murmeli import dbutils


class Bean:
    '''Class for interacting with page templates by adding properties'''
    pass


class PageServer:
    '''PageServer, containing several page sets'''
    def __init__(self):
        self.page_sets = {}
        # keep track of the windows we have opened (so they're not garbage-collected)
        self.extra_windows = set()

    def add_page_set(self, pageset):
        '''Add a page set'''
        self.page_sets[pageset.domain] = pageset

    def serve_page(self, view, url, params):
        '''Serve the page associated with the given url and parameters'''
        domain, path = self.get_domain_and_path(url)
        page_set = self.page_sets.get(domain)
        if not page_set:
            page_set = self.page_sets.get("")
        if page_set:
            page_set.serve_page(view, path, params)

    @staticmethod
    def get_domain_and_path(url):
        '''Extract the domain and path from the given url'''
        stripped_url = url.strip() if url else ""
        if stripped_url.startswith("http://murmeli/"):
            stripped_url = stripped_url[15:]
        while stripped_url.startswith("/"):
            stripped_url = stripped_url[1:]
        slashpos = stripped_url.find("/")
        if slashpos < 0:
            return (stripped_url, '')
        return (stripped_url[:slashpos], stripped_url[slashpos + 1:])

    def get_page_title(self, path):
        '''Get the title of the specified page from one of the pagesets'''
        domain, subpath = self.get_domain_and_path(path)
        page_set = self.page_sets.get(domain)
        return page_set.get_page_title(subpath) if page_set else None


class MurmeliPageServer(PageServer):
    '''Page server used for Murmeli'''
    def __init__(self, system):
        PageServer.__init__(self)
        self.add_page_set(DefaultPageSet(system))
        self.add_page_set(ContactsPageSet(system))
        self.add_page_set(MessagesPageSet(system))
        self.add_page_set(SettingsPageSet(system))
        self.add_page_set(TestPageSet(system))


class PageSet:
    '''Superclass of all page sets'''
    def __init__(self, system, domain):
        self.system = system
        self.domain = domain
        self.std_head = ("<html><head>"
                         "<meta http-equiv=\"Content-Type\" content=\"text/html; charset=utf-8\">"
                         "<link href='file:///" + self.get_web_cache_dir() + "/default.css'"
                         " type='text/css' rel='stylesheet'>"
                         "</head>")

    def require_resource(self, resource):
        '''Require that the specified resource should be copied from web to the cache directory'''
        cache_dir = self.get_web_cache_dir()
        if cache_dir:
            os.makedirs(cache_dir, exist_ok=True)
            dest_path = os.path.join(cache_dir, resource)
            if not os.path.exists(dest_path):
                # dest file doesn't exist
                # (if it exists we assume it's still valid as these resources shouldn't change)
                source_path = os.path.join("web", resource)
                if os.path.exists(source_path):
                    shutil.copy(source_path, dest_path)
                else:
                    print("OUCH - failed to copy resource '%s' from web!" % resource)

    def get_web_cache_dir(self):
        '''Get the web cache directory from the config'''
        cache = None
        if self.system:
            cache = self.system.invoke_call(self.system.COMPNAME_CONFIG, "get_web_cache_dir")
        return cache or ""

    def require_resources(self, resources):
        '''Require a list of page resources such as images, css'''
        if isinstance(resources, list):
            for res in resources:
                self.require_resource(res)
        elif isinstance(resources, str):
            self.require_resource(resources)

    def build_page(self, params):
        '''General page-building method using a standard template
           and filling in the gaps using the given dictionary'''
        self.require_resource("default.css")
        return ''.join([self.std_head,
                        "<body>",
                        "<table border='0' width='100%%'>"
                        "<tr><td><div class='fancyheader'><p>%(pageTitle)s</p></div></td></tr>",
                        "<tr><td><div class='genericbox'>%(pageBody)s</div></td></tr>",
                        "<tr><td><div class='footer'>%(pageFooter)s</div></td></tr></table>",
                        "<div class='overlay' id='overlay' onclick='hideOverlay()'></div>",
                        "<div class='popuppanel' id='popup'>Here's the message</div>",
                        "</body></html>"]) % params

    def build_two_column_page(self, params):
        '''Build page using a two-column template with widths 1third, 2thirds'''
        self.require_resource("default.css")
        return ''.join([self.std_head,
                        "<body>",
                        "<table border='0' width='100%%'>"
                        "<tr><td colspan='2'>"
                        "<div class='fancyheader'><p>%(pageTitle)s</p></div></td></tr>",
                        "<tr valign='top'><td width='33%%'>"
                        "<div class='genericbox'>%(leftColumn)s</div></td>",
                        "<td width='67%%'><div class='genericbox'>%(rightColumn)s</div></td></tr>",
                        "<tr><td colspan='2'>"
                        "<div class='footer'>%(pageFooter)s</div></td></tr>"
                        "</table>",
                        "</body></html>"]) % params

    def i18n(self, key):
        '''Use the i18n component to translate the given key'''
        if self.system:
            return self.system.invoke_call(self.system.COMPNAME_I18N, "get_text", key=key)
        return None

    def get_all_i18n(self):
        '''Use the i18n component to get all the texts'''
        texts = None
        if self.system:
            texts = self.system.invoke_call(self.system.COMPNAME_I18N, "get_all_texts")
        return texts or {}

    def get_config(self):
        '''Get the config component, if any'''
        if self.system:
            return self.system.get_component(self.system.COMPNAME_CONFIG)
        return None

    @staticmethod
    def looks_like_userid(userid):
        '''Return true if the given string looks like a valid user id'''
        if userid and re.match("([a-zA-Z0-9]{16,56})$", userid):
            return True
        return False

    def get_page_title(self, _):
        '''Get the page title for any path by default'''
        return None


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


class ContactsPageSet(PageSet):
    '''Contacts page server, for showing list of contacts etc'''
    def __init__(self, system):
        PageSet.__init__(self, system, "contacts")
        self.list_template = PageTemplate('contactlist')
        self.details_template = PageTemplate('contactdetails')

    def serve_page(self, view, url, params):
        '''Serve a page to the given view'''
        print("Contacts serving page", url)
        self.require_resources(['button-addperson.png', 'button-drawgraph.png',
                                'avatar-none.jpg'])
        database = self.system.get_component(self.system.COMPNAME_DATABASE)
        dbutils.export_all_avatars(database, self.get_web_cache_dir())
        commands = self.interpret_commands(url)
        userid = commands[1] if len(commands) == 2 else None
        print("Commands:", commands, ", userid:", userid, ", params:", params)
        contents = self.make_list_page(userid=userid)
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

    def make_list_page(self, userid=None):
        '''Generate a page for listing all the contacts and showing the details of one of them'''
        self.require_resources(['status-self.png', 'status-requested.png', 'status-untrusted.png',
                                'status-trusted.png', 'status-pending.png'])
        config = self.get_config()
        # Who are we showing?
        selectedprofile = self.system.invoke_call(self.system.COMPNAME_DATABASE, "get_profile",
                                                  torid=userid)
        ownprofile = self.system.invoke_call(self.system.COMPNAME_DATABASE, "get_profile",
                                             torid=None)
        if not selectedprofile:
            selectedprofile = ownprofile
        userid = selectedprofile['torid']

        # Build list of contacts
        userboxes = []
        database = self.system.get_component(self.system.COMPNAME_DATABASE)
        for profile in database.get_profiles():
            if profile['status'] in ['requested', 'untrusted', 'trusted', 'self']:
                box = Bean()
                box.disp_name = profile['displayName']
                tor_id = profile['torid']
                box.torid = tor_id
                box.tilestyle = "contacttile" + ("selected" if profile['torid'] == userid else "")
                box.status = profile['status']
                box.last_seen = ""
                userboxes.append(box)
        # build list of contacts on left of page using these boxes
        tokens = self.get_all_i18n()
        lefttext = self.list_template.get_html(tokens, {'webcachedir':config.get_web_cache_dir(),
                                                        'contacts':userboxes})

        page_props = {"webcachedir":config.get_web_cache_dir(), 'person':selectedprofile}
        page_props["sharedcontacts"] = []
        page_props["posscontactsforthem"] = []
        page_props["posscontactsforme"] = []
        righttext = self.details_template.get_html(tokens, page_props)


        # Put left side and right side together
        contents = self.build_two_column_page({'pageTitle':self.i18n("contacts.title"),
                                               'leftColumn':lefttext,
                                               'rightColumn':righttext,
                                               'pageFooter':"<p>Footer</p>"})
        return contents


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

class SettingsPageSet(PageSet):
    '''Settings page server, for showing and editing the current settings'''
    def __init__(self, system):
        PageSet.__init__(self, system, "settings")
        self.form_template = PageTemplate('settingsform')

    def serve_page(self, view, url, params):
        '''Serve a page to the given view'''
        print("Settings serving page '%s'" % url)
        print("params:", params)
        config = self.get_config()
        if not config:
            view.set_html("Error: Settings didn't find the config!")
            return
        if url == "edit":
            print("Edit settings")
            selected_lang = params.get('lang')
            if selected_lang and len(selected_lang) == 2:
                config.set_property(config.KEY_LANGUAGE, selected_lang)
            friendsseefriends = bool(params.get('friendsseefriends'))
            config.set_property(config.KEY_LET_FRIENDS_SEE_FRIENDS, friendsseefriends)
            allowfriendrequests = bool(params.get('allowfriendrequests'))
            config.set_property(config.KEY_ALLOW_FRIEND_REQUESTS, allowfriendrequests)
            # Save config to file in case it's changed
            config.save()
            contents = self.build_page({'pageTitle':self.i18n("settings.title"),
                                        'pageBody':"<p>Settings changed... should I go back"
                                                   + " to settings or back to home now?</p>"
                                                   + "<p>(<a href='/'>back</a>)</p>",
                                        'pageFooter':"<p>Footer</p>"})
        else:
            page_props = {"friendsseefriends" :
                          self.check_from_config(config, config.KEY_LET_FRIENDS_SEE_FRIENDS),
                          "allowfriendrequests" :
                          self.check_from_config(config, config.KEY_ALLOW_FRIEND_REQUESTS),
                          "showlogwindow" :
                          self.check_from_config(config, config.KEY_SHOW_LOG_WINDOW),
                          "language_en":"",
                          "language_de":""}
            page_props["language_" + config.get_property(config.KEY_LANGUAGE)] = "selected"
            tokens = self.get_all_i18n()
            contents = self.build_page({'pageTitle':self.i18n("settings.title"),
                                        'pageBody':self.form_template.get_html(tokens, page_props),
                                        'pageFooter':"<p>Footer</p>"})
        view.set_html(contents)

    @staticmethod
    def check_from_config(config, key):
        '''Get a string either "checked" or "" depending on the config flag'''
        return "checked" if config.get_property(key) else ""


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
