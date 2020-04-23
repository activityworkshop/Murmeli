'''Module for the management of contacts within Murmeli'''

from murmeli import contactutils
from murmeli import dbutils


class ContactManager:
    '''Class to manage contacts, like processing friend acceptance or rejection,
       working out which contacts are shared, etc'''

    def __init__(self, database, crypto):
        '''Constructor'''
        self._database = database
        self._crypto = crypto


    def get_shared_possible_contacts(self, tor_id):
        '''Check which contacts we share with the given torid
           and which ones we could recommend to each other'''
        name_map = {}
        our_contact_ids = set()
        trusted_contact_ids = set()
        their_contact_ids = set()
        # Get our id so we can exclude it from the sets
        my_tor_id = dbutils.get_own_tor_id(self._database)
        if tor_id == my_tor_id:
            return ([], [], [], {})
        # Find the contacts of the specified person
        selected_profile = self._database.get_profile(tor_id) if self._database else None
        selected_contacts = selected_profile.get('contactlist') if selected_profile else None
        for found_id, found_name in contactutils.contacts_from_string(selected_contacts):
            if found_id != my_tor_id:
                their_contact_ids.add(found_id)
                name_map[found_id] = found_name
        found_their_contacts = True if their_contact_ids else False
        # Now get information about our contacts
        for cont in dbutils.get_messageable_profiles(self._database):
            found_id = cont['torid']
            our_contact_ids.add(found_id)
            if cont.get('status') == 'trusted' and found_id != tor_id:
                trusted_contact_ids.add(found_id)
            name_map[found_id] = cont.get('displayName')
            # Should we check the contact information too?
            if not found_their_contacts:
                if self.is_contact_id_in_profile(cont, tor_id):
                    their_contact_ids.add(found_id)
        # Now we have three sets of torids: our contacts, our trusted contacts, and their contacts.
        shared_contact_ids = our_contact_ids.intersection(their_contact_ids) # might be empty
        # if the contact isn't trusted, then don't suggest anything
        if not selected_profile or selected_profile.get('status') != 'trusted':
            return (shared_contact_ids, [], [], name_map)
        suggestions_for_them = trusted_contact_ids.difference(their_contact_ids)
        possible_for_me = their_contact_ids.difference(our_contact_ids)
        # These sets may be empty, but we still return the map so we can look up names
        return (shared_contact_ids, suggestions_for_them, possible_for_me, name_map)

    @staticmethod
    def is_contact_id_in_profile(profile, tor_id):
        '''Return True if given tor_id appears in the profile's contactlist'''
        contact_str = profile.get("contactlist") if profile else None
        for contact_id, _ in contactutils.contacts_from_string(contact_str):
            if contact_id and contact_id == tor_id:
                return True
        return False
