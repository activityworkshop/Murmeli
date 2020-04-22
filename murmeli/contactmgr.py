'''Module for the management of contacts within Murmeli'''

from murmeli import contactutils


class ContactManager:
    '''Class to manage contacts, like processing friend acceptance or rejection,
       working out which contacts are shared, etc'''

    def __init__(self, database, crypto):
        '''Constructor'''
        self._database = database
        self._crypto = crypto

    @staticmethod
    def get_contact_name_from_profile(profile, tor_id):
        '''If the given profile has a contact list, use it to look up the name
           for the given tor_id'''
        contact_str = profile.get("contactlist") if profile else None
        for contact_id, contact_name in contactutils.contacts_from_string(contact_str):
            if contact_id and contact_id == tor_id:
                return contact_name or contact_id
        # The name wasn't found, so just use the tor_id instead
        return tor_id
