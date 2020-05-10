'''Module for the base pageset'''

import os
import shutil
import datetime
import re


class Bean:
    '''Class for interacting with page templates by adding properties'''
    def set(self, name, value):
        '''Set a property of the object'''
        self.__dict__[name] = value
    def __getattr__(self, name):
        return self.__dict__.get(name, '')


class PageSet:
    '''Superclass of all page sets'''
    def __init__(self, system, domain):
        self.system = system
        self.domain = domain
        self.std_head = ("<html><head>"
                         "<meta http-equiv=\"Content-Type\" content=\"text/html; charset=utf-8\">"
                         "<link href='file:///" + self.get_web_cache_dir() + "/default.css'"
                         " type='text/css' rel='stylesheet'>"
                         "<script type='text/javascript'>"
                         "function hideOverlay(){"
                         " showLayer('overlay',false);showLayer('popup',false)}"
                         " function showLayer(lname,show){"
                         " document.getElementById(lname).style.visibility="
                         "(show?'visible':'hidden');}"
                         " function showMessage(mess){"
                         " document.getElementById('popup').innerHTML=mess;"
                         " showLayer('overlay',true); showLayer('popup', true);}"
                         "</script></head>")

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
                        "<div class='overlay' id='overlay' onclick='hideOverlay()'></div>",
                        "<div class='popuppanel' id='popup'>Here's the message</div>",
                        "</body></html>"]) % params

    def make_local_time_string(self, tstamp):
        '''Convert a float (in UTC) to a string (in local timezone) for display'''
        if not tstamp:
            return ""
        try:
            send_time = datetime.datetime.fromtimestamp(tstamp)
            # Check if it's today
            now = datetime.datetime.now()
            midnight = datetime.datetime(now.year, now.month, now.day, 0, 0, 0)
            if send_time.timestamp() > midnight.timestamp():
                # today, just show time
                return "%02d:%02d" % (send_time.hour, send_time.minute)
            # Check if it's yesterday
            midnight -= datetime.timedelta(days=1)
            if send_time.timestamp() > midnight.timestamp():
                # yesterday, show 'Yesterday' and time
                return self.i18n("messages.sendtime.yesterday") + \
                       " %02d:%02d" % (send_time.hour, send_time.minute)
            # Not today or yesterday, show full date and time
            return "%d-%02d-%02d %02d:%02d" % (send_time.year, send_time.month, send_time.day,
                                               send_time.hour, send_time.minute)
        except TypeError:
            print("Expected a float timestamp, found", type(tstamp), repr(tstamp))
        if isinstance(tstamp, str):
            return tstamp
        return ""

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

    @staticmethod
    def get_page_title(_):
        '''Get the page title for any path by default'''
        return None
