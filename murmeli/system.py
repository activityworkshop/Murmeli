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

    def add_component(self, comp):
        '''Add the given component by its name'''
        assert comp.name
        assert comp.name not in self.components
        self.components[comp.name] = comp
        # start all components (also the ones already started!)
        for _, component in self.components.items():
            component.start()

    def get_component(self, name):
        '''Returns the component with the given name, if there is one'''
        assert name
        return self.components.get(name)

    def has_component(self, name):
        '''Returns true if there is already a component with the given name'''
        assert name
        return True if self.components.get(name) else False

    def remove_component(self, name):
        '''Remove the component with the given name, but don't complain if it's not there'''
        assert name
        if name in self.components:
            self.components[name].stop()
            self.components.pop(name)

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
        return None


class Component:
    '''Superclass of all components in the system'''
    def __init__(self, parent, name):
        self._parent = parent
        self.name = name
        self.started = False

    def start(self):
        '''Start this component'''
        if not self.started:
            self.started = self.checked_start()
            if self.started:
                print("Component '%s' starting..." % self.name)

    def checked_start(self):
        '''Called repeatedly until it returns True (child classes may rely on other components'''
        return True

    def stop(self):
        '''Stop this component'''
        print("Component '%s' stopping..." % self.name)
        self.started = False

    def get_component(self, comp_name):
        '''Get the specified component'''
        if self._parent:
            return self._parent.get_component(comp_name)
        return None

    def call_component(self, comp_name, call_name, **kwargs):
        '''Invoke a call on the specified component'''
        if self._parent:
            return self._parent.invoke_call(comp_name, call_name, **kwargs)
        return None

    def get_config_property(self, key):
        '''Convenience method for calling the config if available'''
        return self.call_component(System.COMPNAME_CONFIG, "get_property", key=key)
