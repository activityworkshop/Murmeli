'''Module for the management of contacts within Murmeli'''

from murmeli import contactutils
from murmeli import dbutils
from murmeli import inbox
from murmeli import pendingtable
from murmeli.message import Message, ContactRequestMessage, ContactAcceptMessage
from murmeli.message import ContactDenyMessage, ContactReferralMessage
from murmeli.decrypter import DecrypterShim


class SharedContacts:
    '''Class to hold info about shared and recommendable contacts'''
    def __init__(self):
        self.shared_ids = set()
        self.ids_for_them = set()
        self.ids_for_me = set()
        self.name_map = {}

    def get_shared_ids(self):
        '''Return a list of id and name tuples for contacts in common'''
        return [(cid, self.name_map.get(cid, cid)) for cid in self.shared_ids]

    def get_ids_for_them(self):
        '''Return a list of id and name tuples to recommend to them'''
        return [(cid, self.name_map.get(cid, cid)) for cid in self.ids_for_them]


class ContactManager:
    '''Class to manage contacts, like processing friend acceptance or rejection,
       working out which contacts are shared, etc'''

    def __init__(self, database, crypto, config=None):
        '''Constructor'''
        self._database = database
        self._crypto = crypto
        self._config = config

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

    def handle_accept(self, tor_id, reply_text, public_key=None):
        '''We want to accept a contact request, so we need to find the request(s),
           and use it/them to update our keyring and our database entry'''
        if not self._crypto:
            return
        print("ContactMgr.handle_accept for id '%s'" % tor_id)
        name, key_str = self.get_contact_request_details(tor_id)
        if public_key and not key_str:
            name, key_str = tor_id, public_key
        key_valid = key_str and len(key_str) > 20
        if key_valid:
            # Get this person's current status from the db, if available
            name = name or tor_id
            print("ContactMgr.handle_accept for name '%s' with key '%s'" % (name, key_str[:15]))
            status = dbutils.get_status(self._database, tor_id)
            # also create ContactAcceptMessage and add to outbox
            if status in [None, "requested", "deleted"]:
                # Import the found key into the keyring
                key_id = self._crypto.import_public_key(key_str)
                print("Imported key into keyring, got id:", key_id)
                is_direct = dbutils.find_inbox_message(self._database,
                                                       {inbox.FN_MSG_TYPE:"contactrequest",
                                                        inbox.FN_FROM_ID:tor_id})
                dbutils.create_profile(self._database, tor_id,
                                       {'displayName':name, 'name':name,
                                        'status':'untrusted' if is_direct else 'requested',
                                        'keyid':key_id})
                # send response
                own_profile = self._database.get_profile()
                own_publickey = self._crypto.get_public_key(own_profile.get('keyid'))
                outmsg = ContactAcceptMessage()
                outmsg.set_field(outmsg.FIELD_SENDER_KEY, own_publickey)
                outmsg.set_field(outmsg.FIELD_SENDER_NAME, own_profile['name'])
                outmsg.set_field(outmsg.FIELD_MESSAGE, reply_text or "")
                outmsg.recipients = [tor_id]
                dbutils.add_message_to_outbox(outmsg, self._crypto, self._database)
                # Maybe there is a pending contact response to deal with
                if not is_direct:
                    self.process_pending_contacts(tor_id)
            else:
                # status could be untrusted, or trusted
                print("Trying to handle an accept but status is already", status)
        # Mark all contact request messages from this id as 'replied'
        dbutils.mark_conreqs_as_replied(tor_id, self._database)

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

    def process_pending_contacts(self, tor_id):
        '''Perhaps some contact responses are pending, deal with them now'''
        print("Process pending contact accept responses from:", tor_id)
        found = False
        for resp in self._database.get_pending_contact_messages():
            if resp and resp.get(pendingtable.FN_FROM_ID) == tor_id:
                payload = resp.get(pendingtable.FN_PAYLOAD)
                msg = Message.from_encrypted_payload(payload, DecrypterShim(self._crypto))
                if msg and isinstance(msg, ContactAcceptMessage):
                    found = True
                    # Construct inbox message and pass to db
                    dbutils.add_message_to_inbox(msg, self._database,
                                                 inbox.MC_CONRESP_ALREADY_ACCEPTED)
        if found:
            print("Found pending contact accept from:", tor_id)
            dbutils.update_profile(self._database, tor_id, {'status':'untrusted'})
            # delete_from_pending_table
            self._database.delete_from_pending_table(tor_id)

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
        their_robot_id = dbutils.get_robot_id(self._database, tor_id)
        dbutils.update_profile(self._database, tor_id, {'status':'deleted'}, config=self._config)
        # If I have a robot, send disconnect message to robot
        my_robot_id = dbutils.get_robot_id(self._database, tor_id=None)
        if my_robot_id:
            self.send_robot_referral_messages(my_robot_id, tor_id, add=False)
        # If the friend had a robot, then delete that too
        if their_robot_id:
            dbutils.update_profile(self._database, their_robot_id, {'status':'deleted'})

    def handle_receive_accept(self, tor_id, name, key_str):
        '''We have requested contact with another id, and this has now been accepted.
           So we can import their public key into our keyring and update their status
           accordingly.'''
        key_id = self._crypto.import_public_key(key_str)
        print("Imported key into keyring, got id:", key_id)
        accept_from_robot = self.is_robot_id(tor_id)
        new_status = 'robot' if accept_from_robot else "untrusted"
        profile = {'status':new_status, 'keyid':key_id, 'name':name}
        dbutils.update_profile(self._database, tor_id, profile)
        # If accept_from_robot, send pairs of referral messages to everybody
        if accept_from_robot:
            for profile in self._database.get_profiles_with_status("trusted"):
                self.send_robot_referral_messages(tor_id, profile['torid'], add=True)

    def handle_receive_deny(self, tor_id):
        '''We have requested contact with another id, but this has been denied.
           So we need to update their status accordingly'''
        self.delete_contact(tor_id)
        print("ContactMgr received contact refusal from %s" % tor_id)

    def key_fingerprint_checked(self, tor_id):
        '''The fingerprint of this contact's key has been checked (over a separate channel)'''
        # Check that userid exists and that status is ok
        curr_status = dbutils.get_status(self._database, tor_id)
        if curr_status == "untrusted":
            dbutils.update_profile(self._database, tor_id, {'status':'trusted'},
                                   config=self._config)
        # If I have a robot, send pair of referral messages
        my_robot_id = dbutils.get_robot_id(self._database, tor_id=None)
        if my_robot_id:
            self.send_robot_referral_messages(my_robot_id, tor_id, add=True)

    def get_contact_request_details(self, tor_id):
        '''Use all received contact requests for the given id, and summarize name and public key'''
        found_names = set()
        found_keys = set()
        # Loop through all contact requests and contact refers for the given torid
        for msg in self._database.get_inbox():
            msg_type = msg.get(inbox.FN_MSG_TYPE) if msg else None
            if msg_type == "contactrequest" and msg.get(inbox.FN_FROM_ID) == tor_id:
                found_names.add(msg.get(inbox.FN_FROM_NAME))
                found_keys.add(msg.get(inbox.FN_PUBLIC_KEY))
            elif msg_type == "contactrefer" and msg.get(inbox.FN_FRIEND_ID) == tor_id:
                found_names.add(msg.get(inbox.FN_FRIEND_NAME))
                found_keys.add(msg.get(inbox.FN_PUBLIC_KEY))
        supplied_key = found_keys.pop() if len(found_keys) == 1 else None
        if supplied_key is None or len(supplied_key) < 80:
            return (None, None)  # key missing or too short
        supplied_name = found_names.pop() if len(found_names) == 1 else tor_id
        return (supplied_name, supplied_key)

    def get_shared_possible_contacts(self, tor_id):
        '''Check which contacts we share with the given torid
           and which ones we could recommend to each other'''
        shared_info = SharedContacts()
        our_contact_ids = set()
        trusted_contact_ids = set()
        their_contact_ids = set()
        # Get our id so we can exclude it from the sets
        my_tor_id = dbutils.get_own_tor_id(self._database)
        if tor_id == my_tor_id:
            return shared_info
        # Find the contacts of the specified person
        selected_profile = self._database.get_profile(tor_id) if self._database else None
        selected_contacts = selected_profile.get('contactlist') if selected_profile else None
        for found_id, found_name in contactutils.contacts_from_string(selected_contacts):
            if found_id != my_tor_id:
                their_contact_ids.add(found_id)
                shared_info.name_map[found_id] = found_name
        found_their_contacts = bool(their_contact_ids)
        # Now get information about our contacts
        for cont in dbutils.get_messageable_profiles(self._database):
            found_id = cont['torid']
            our_contact_ids.add(found_id)
            if cont.get('status') == 'trusted' and found_id != tor_id:
                trusted_contact_ids.add(found_id)
            shared_info.name_map[found_id] = cont.get('displayName')
            # Should we check the contact information too?
            if not found_their_contacts:
                if self.is_contact_id_in_profile(cont, tor_id):
                    their_contact_ids.add(found_id)
        # Now we have three sets of torids: our contacts, our trusted contacts, and their contacts.
        shared_info.shared_ids = our_contact_ids.intersection(their_contact_ids)
        # if the contact isn't trusted, then don't suggest anything
        if selected_profile and selected_profile.get('status') == 'trusted':
            shared_info.ids_for_them = trusted_contact_ids.difference(their_contact_ids)
            shared_info.ids_for_me = their_contact_ids.difference(our_contact_ids)
        return shared_info

    @staticmethod
    def is_contact_id_in_profile(profile, tor_id):
        '''Return True if given tor_id appears in the profile's contactlist'''
        contact_str = profile.get("contactlist") if profile else None
        for contact_id, _ in contactutils.contacts_from_string(contact_str):
            if contact_id and contact_id == tor_id:
                return True
        return False

    def send_referral_messages(self, friend_id1, friend_id2, intro):
        '''Send messages to both friends, to recommend they become friends with each other'''
        if not friend_id1 or not friend_id2 or friend_id1 == friend_id2:
            return
        if dbutils.get_status(self._database, friend_id1) != 'trusted':
            return
        if dbutils.get_status(self._database, friend_id2) != 'trusted':
            return
        self._send_referral_message(friend_id1, friend_id2, intro)
        self._send_referral_message(friend_id2, friend_id1, intro)

    def _send_referral_message(self, recipient_id, friend_id, intro, refer_type=None):
        '''Send a single referral message'''
        print("Send msg to '%s' referring '%s' with msg '%s' and type '%s'" % \
          (recipient_id, friend_id, intro, refer_type))
        outmsg = ContactReferralMessage()
        outmsg.set_field(outmsg.FIELD_MSGBODY, intro)
        outmsg.set_field(outmsg.FIELD_FRIEND_ID, friend_id)
        if refer_type:
            outmsg.set_field(outmsg.FIELD_REFERRAL_TYPE, refer_type)
        # Get name and key of friend_id from database
        profile = self._database.get_profile(friend_id)
        outmsg.set_field(outmsg.FIELD_FRIEND_NAME, profile.get('name'))
        key_str = self._crypto.get_public_key(profile.get('keyid'))
        outmsg.set_field(outmsg.FIELD_FRIEND_KEY, key_str)
        outmsg.recipients = [recipient_id]
        dbutils.add_message_to_outbox(outmsg, self._crypto, self._database, dont_relay=friend_id)

    def send_robot_referral_messages(self, robot_id, friend_id, add=True):
        '''Send message to friend, to ask them to add or remove our robot'''
        if not robot_id or not friend_id or robot_id == friend_id:
            return
        robot_status = dbutils.get_status(self._database, robot_id)
        friend_status = dbutils.get_status(self._database, friend_id)
        if robot_status != 'robot' or friend_status != 'trusted':
            return
        msg_type = ContactReferralMessage.REFERTYPE_ROBOT if add else \
                   ContactReferralMessage.REFERTYPE_REMOVEROBOT
        self._send_referral_message(friend_id, robot_id, "robot", msg_type)
        if add:
            self._send_referral_message(robot_id, friend_id, "robot", msg_type)
