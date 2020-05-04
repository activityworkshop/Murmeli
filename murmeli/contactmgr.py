'''Module for the management of contacts within Murmeli'''

from murmeli import contactutils
from murmeli import dbutils
from murmeli.message import ContactRequestMessage


class ContactManager:
    '''Class to manage contacts, like processing friend acceptance or rejection,
       working out which contacts are shared, etc'''

    def __init__(self, database, crypto):
        '''Constructor'''
        self._database = database
        self._crypto = crypto

    def handle_initiate(self, tor_id, display_name, robot=False):
        '''We have requested contact with another id, so we can set up
           this new contact's name with the right status'''
        own_torid = dbutils.get_own_tor_id(self._database)
        if not tor_id or tor_id == own_torid:
            return False
        allowed_status = ['robot'] if robot else ['deleted']
        new_status = 'reqrobot' if robot else 'requested'
        result = self._handle_initiate(tor_id, display_name, allowed_status, new_status)
        if robot and result:
            dbutils.update_profile(self._database, own_torid, {'robot':tor_id})
            self._send_request_to_robot(tor_id)
        return result

    def _handle_initiate(self, tor_id, display_name, allowed_status, new_status):
        '''We have requested contact with another id, so we can set up
           this new contact's name with a status of "requested"'''
        # If row already exists then get status (and name/displayname) and error with it
        if self._database:
            curr_status = dbutils.get_status(self._database, tor_id)
            if curr_status and curr_status != new_status and curr_status not in allowed_status:
                print("Initiate contact with '%s' but status is already '%s' ?"
                      % (tor_id, curr_status))
                return False
        # Add new row in db with id, name and new status
        if tor_id and tor_id != dbutils.get_own_tor_id(self._database):
            display_name = display_name or tor_id
            profile = {'displayName':display_name, 'name':display_name,
                       'status':new_status}
            dbutils.create_profile(self._database, tor_id, profile)
            return True
        return False

    def _send_request_to_robot(self, robot_id):
        '''Send a contact request to the given robot'''
        own_profile = self._database.get_profile()
        own_keyid = own_profile.get('keyid')
        own_torid = own_profile.get('torid')
        outmsg = ContactRequestMessage()
        outmsg.set_field(outmsg.FIELD_SENDER_KEY, own_keyid)
        outmsg.set_field(outmsg.FIELD_SENDER_ID, own_torid)
        outmsg.set_field(outmsg.FIELD_SENDER_NAME, own_torid)
        outmsg.recipients = [robot_id]
        dbutils.add_message_to_outbox(outmsg, self._crypto, self._database)

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
