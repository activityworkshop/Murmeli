'''This module contains the classes for the main System and its components'''

class System:
    '''This is the main system, containing a dictionary of components identified by name.'''

    # Built-in component names
    COMPNAME_CONFIG = "comp.config"
    COMPNAME_TRANSPORT = "comp.transport"
    COMPNAME_DATABASE = "comp.database"
    COMPNAME_CRYPTO = "comp.crypto"
    COMPNAME_MSG_HANDLER = "comp.msghandler"
    COMPNAME_CONTACTS = "comp.contacts"
    COMPNAME_LOGGING = "comp.logging"
    COMPNAME_I18N = "comp.i18n"
    COMPNAME_GUI = "comp.gui"

    def __init__(self):
        self.components = {}

    def add_component(self, comp, name):
        '''Add the given component with the given name'''
        assert name
        assert name not in self.components
        self.components[name] = comp

    def start(self):
        '''Start all components after all have been loaded'''
        for _, comp in self.components.items():
            comp.start()

    def stop(self):
        '''Stop system and remove components'''
        for _, comp in self.components.items():
            comp.stop()
        self.components = {}

    def invoke_call(self, comp_name, call_name, **kwargs):
        '''Invoke a call on the specified component'''
        if comp_name in self.components:
            try:
                return getattr(self.components[comp_name], call_name)(**kwargs)
            except AttributeError:
                print("Failed to call method '%s' on '%s', not found" % (call_name, comp_name))
                raise
        else:
            print("Can't invoke %s, component %s not found" % (call_name, comp_name))


class Component:
    '''Superclass of all components in the system'''
    def __init__(self, parent, name):
        self._parent = parent
        self.name = name
        self.started = False
        if parent:
            parent.add_component(self, name)

    def start(self):
        '''Start this component'''
        print("Component '%s' starting..." % self.name)
        self.started = True

    def stop(self):
        '''Stop this component'''
        print("Component '%s' stopping..." % self.name)
        self.started = False

    def call_component(self, comp_name, call_name, **kwargs):
        '''Invoke a call on the specified component'''
        if self._parent:
            return self._parent.invoke_call(comp_name, call_name, **kwargs)

    def get_config_property(self, key):
        '''Convenience method for calling the config if available'''
        return self.call_component(System.COMPNAME_CONFIG, "get_property", key=key)
