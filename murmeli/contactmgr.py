'''Module for the management of contacts within Murmeli'''

from murmeli import contactutils
from murmeli import dbutils
from murmeli.message import ContactRequestMessage, ContactDenyMessage


class ContactManager:
    '''Class to manage contacts, like processing friend acceptance or rejection,
       working out which contacts are shared, etc'''

    def __init__(self, database, crypto):
        '''Constructor'''
        self._database = database
        self._crypto = crypto

    def handle_initiate(self, tor_id, display_name, intro_msg, robot=False):
        '''We have requested contact with another id, so we can set up
           this new contact's name with the right status'''
        own_torid = dbutils.get_own_tor_id(self._database)
        if not tor_id or tor_id == own_torid:
            return False
        allowed_status = ['robot'] if robot else ['deleted']
        new_status = 'reqrobot' if robot else 'requested'
        result = self._handle_initiate(tor_id, display_name, allowed_status, new_status)
        if result:
            if robot:
                dbutils.update_profile(self._database, own_torid, {'robot':tor_id})
                self._send_request_to_robot(tor_id)
            else:
                self._send_request(tor_id, intro_msg)
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
        # note: when requesting contact to a robot, only the keyid is sent, not the key
        outmsg.set_field(outmsg.FIELD_SENDER_KEY, own_keyid)
        outmsg.set_field(outmsg.FIELD_SENDER_ID, own_torid)
        outmsg.set_field(outmsg.FIELD_SENDER_NAME, own_torid)
        outmsg.recipients = [robot_id]
        dbutils.add_message_to_outbox(outmsg, self._crypto, self._database)

    def _send_request(self, friend_id, intro_msg):
        '''Send a contact request to the specified user'''
        own_profile = self._database.get_profile()
        own_keyid = own_profile.get('keyid')
        own_torid = own_profile.get('torid')
        outmsg = ContactRequestMessage()
        # note: when requesting contact to a regular user, the whole public key is sent
        own_publickey = self._crypto.get_public_key(own_keyid) if self._crypto else None
        outmsg.set_field(outmsg.FIELD_SENDER_KEY, own_publickey)
        outmsg.set_field(outmsg.FIELD_SENDER_ID, own_torid)
        outmsg.set_field(outmsg.FIELD_SENDER_NAME, own_profile['name'])
        outmsg.set_field(outmsg.FIELD_MESSAGE, intro_msg)
        outmsg.recipients = [friend_id]
        dbutils.add_message_to_outbox(outmsg, self._crypto, self._database)

    def handle_accept(self, tor_id):
        '''We want to accept a contact request, so we need to find the request(s),
           and use it/them to update our keyring and our database entry'''
        print("ContactMgr.handle_accept for id '%s'" % tor_id)

    def is_robot_id(self, tor_id):
        '''Return True if this tor_id is configured as our robot'''
        if not self._database:
            return False
        own_profile = self._database.get_profile(None)
        if not own_profile or own_profile.get('robot') != tor_id:
            return False
        # Now check other profile
        robot_status = dbutils.get_status(self._database, tor_id)
        return robot_status in ['robot', 'reqrobot']

    def handle_deny(self, tor_id):
        '''We want to deny a contact request - update database and send reply'''
        if not self._database:
            return
        # Delete all messages from this tor_id, from inbox and from pending
        dbutils.delete_messages_from_inbox(tor_id, self._database)
        # also construct and store response
        outmsg = ContactDenyMessage()
        outmsg.set_field(outmsg.FIELD_SENDER_ID, dbutils.get_own_tor_id(self._database))
        outmsg.recipients = [tor_id]
        dbutils.add_message_to_outbox(outmsg, None, self._database)

    def delete_contact(self, tor_id):
        '''Set the specified contact's status to deleted'''
        print("ContactManager: set status of '%s' to 'deleted'" % tor_id)
        dbutils.update_profile(self._database, tor_id, {'status':'deleted'})

    def handle_receive_accept(self, tor_id, name, key_str):
        '''We have requested contact with another id, and this has now been accepted.
           So we can import their public key into our keyring and update their status
           accordingly.'''
        key_id = self._crypto.import_public_key(key_str)
        print("Imported key into keyring, got id:", key_id)
        new_status = 'robot' if self.is_robot_id(tor_id) else "untrusted"
        profile = {'status':new_status, 'keyid':key_id, 'name':name}
        dbutils.update_profile(self._database, tor_id, profile)

    def handle_receive_deny(self, tor_id):
        '''We have requested contact with another id, but this has been denied.
           So we need to update their status accordingly'''
        self.delete_contact(tor_id)
        print("ContactMgr received contact refusal from %s" % tor_id)

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
