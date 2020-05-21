'''Module for the settings pageset'''

from murmeli.pages.base import PageSet
from murmeli.pagetemplate import PageTemplate
from murmeli import dbutils


class SettingsPageSet(PageSet):
    '''Settings page server, for showing and editing the current settings'''
    def __init__(self, system):
        PageSet.__init__(self, system, "settings")
        self.form_template = PageTemplate('settingsform')

    def serve_page(self, view, url, params):
        '''Serve a page to the given view'''
        config = self.get_config()
        if not config:
            view.set_html("Error: Settings didn't find the config!")
            return
        if url == "edit":
            selected_lang = params.get('lang')
            if selected_lang and len(selected_lang) == 2:
                config.set_property(config.KEY_LANGUAGE, selected_lang)
                # I18nManager will be triggered here because it listens to the Config
            friendsseefriends = bool(params.get('friendsseefriends'))
            fsf_before = config.get_property(config.KEY_LET_FRIENDS_SEE_FRIENDS)
            config.set_property(config.KEY_LET_FRIENDS_SEE_FRIENDS, friendsseefriends)
            # If Config has changed, may need to update own profile to include/hide friends info
            if friendsseefriends != fsf_before:
                self.update_contacts(friendsseefriends)
            showlogwindow = bool(params.get('showlogwindow'))
            config.set_property(config.KEY_SHOW_LOG_WINDOW, showlogwindow)
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

    def update_contacts(self, show_friends):
        '''Our contacts visibility has changed, so update our own profile accordingly'''
        database = self.system.get_component(self.system.COMPNAME_DATABASE)
        dbutils.update_contact_list(database, show_friends)
