'''Message handlers for Murmeli'''

from murmeli.system import System, Component
from murmeli.config import Config
from murmeli.contactmgr import ContactManager
from murmeli import message
from murmeli import dbutils
from murmeli import inbox


class MessageHandler(Component):
    '''Abstract message handler'''

    def __init__(self, parent):
        Component.__init__(self, parent, System.COMPNAME_MSG_HANDLER)

    def receive(self, msg):
        '''Receive an incoming message'''
        if msg and isinstance(msg, message.Message):
            # Check if it's from a trusted sender
            if msg.sender_must_be_trusted:
                # TODO: Check sender
                pass
            if msg.msg_type == msg.TYPE_CONTACT_REQUEST:
                self.receive_contact_request(msg)
            elif msg.msg_type == msg.TYPE_CONTACT_RESPONSE:
                self.receive_contact_response(msg)
            elif msg.msg_type == msg.TYPE_STATUS_NOTIFY:
                self.receive_status_notify(msg)
            elif msg.msg_type == msg.TYPE_INFO_REQUEST:
                self.receive_info_request(msg)
            elif msg.msg_type == msg.TYPE_INFO_RESPONSE:
                self.receive_info_response(msg)
            elif msg.msg_type == msg.TYPE_FRIEND_REFERRAL:
                self.receive_friend_referral(msg)
            elif msg.msg_type == msg.TYPE_FRIENDREFER_REQUEST:
                self.receive_friend_refer_request(msg)
            elif msg.msg_type == msg.TYPE_REGULAR_MESSAGE:
                self.receive_regular_message(msg)
            elif msg.msg_type == msg.TYPE_RELAYED_MESSAGE:
                self.receive_relayed_message(msg)

    def receive_contact_request(self, msg):
        '''Receive a contact request'''
        pass

    def receive_contact_response(self, msg):
        '''Receive a contact response'''
        pass

    def receive_status_notify(self, msg):
        '''Receive a status notification'''
        # If it's a ping, reply with a pong
        if msg.get_field(msg.FIELD_PING) and msg.get_field(msg.FIELD_ONLINE):
            if not self.is_from_trusted_contact(msg):
                return
            # Create new pong for the sender and pass to outbox
            sender_of_ping = msg.get_field(msg.FIELD_SENDER_ID)
            pong = self._create_pong(sender_of_ping)
            dbutils.add_message_to_outbox(pong, self.get_component(System.COMPNAME_CRYPTO),
                                          self.get_component(System.COMPNAME_DATABASE))

    def _create_pong(self, recipient):
        '''Create a StatusNotify pong message for the given recipient'''
        pong = message.StatusNotifyMessage()
        pong.set_field(pong.FIELD_PING, 0)
        pong.recipients = [recipient]
        # Calculate profile hash and add to msg
        database = self.get_component(System.COMPNAME_DATABASE)
        own_hash = dbutils.calculate_hash(database.get_profile())
        pong.set_field(pong.FIELD_PROFILE_HASH, own_hash)
        return pong

    def receive_info_request(self, msg):
        '''Receive an info request'''
        pass
    def receive_info_response(self, msg):
        '''Receive an info response'''
        pass
    def receive_friend_referral(self, msg):
        '''Receive a friend referral'''
        pass
    def receive_friend_refer_request(self, msg):
        '''Receive a friend referral request'''
        pass
    def receive_regular_message(self, msg):
        '''Receive a regular message'''
        pass

    def receive_relayed_message(self, msg):
        '''Receive a relayed message for somebody else'''
        # TODO: Validate, then save in database
        pass

    def is_from_trusted_contact(self, msg):
        '''Return true if given message is from a contact with trusted status'''
        return self._get_sender_status(msg) in ['trusted', 'robot']

    def _get_sender_status(self, msg):
        '''Return status of the sender of the given message from the database'''
        sender_id = msg.get_field(msg.FIELD_SENDER_ID) if msg else None
        return self._get_contact_status(sender_id)

    def _get_contact_status(self, tor_id):
        '''Return status of the sender of the given message from the database'''
        if tor_id:
            profile = self.call_component(System.COMPNAME_DATABASE, "get_profile", torid=tor_id)
            if profile:
                return profile.get('status')
        return None


class RobotMessageHandler(MessageHandler):
    '''Message handler subclass for robot system'''

    def __init__(self, parent):
        MessageHandler.__init__(self, parent)

    def receive_contact_request(self, msg):
        '''Receive a contact request'''
        # Compare incoming keyid with owner id in Config, ignore all others
        sender_keyid = msg.get_field(msg.FIELD_SENDER_KEY)
        owner_keyid = self.get_config_property(Config.KEY_ROBOT_OWNER_KEY)
        print("Contact request was from '%s', my owner is '%s'" % (sender_keyid, owner_keyid))
        if sender_keyid == owner_keyid and sender_keyid:
            sender_id = msg.get_field(msg.FIELD_SENDER_ID)
            print("Contact request from my owner with id '%s'" % sender_id)
            # Check if owner already set, if so then don't change it
            database = self.get_component(System.COMPNAME_DATABASE)
            if not database:
                return
            crypto = self.get_component(System.COMPNAME_CRYPTO)
            if not database.get_profiles_with_status(status="owner"):
                # update db with SENDER_ID
                owner_profile = {"torid":sender_id, 'status':'owner', 'keyid':owner_keyid}
                # NOTE: For conreq to robot, only the keyid is sent, not the whole key
                database.add_or_update_profile(profile=owner_profile)
            # Send an automatic accept message
            resp = message.ContactAcceptMessage()
            resp.recipients = [sender_id]
            own_profile = database.get_profile()
            resp.set_field(resp.FIELD_MESSAGE, "I'm your robot")
            resp.set_field(resp.FIELD_SENDER_NAME, "Robot")
            own_keyid = own_profile.get('keyid')
            own_publickey = crypto.get_public_key(own_keyid) if crypto else None
            resp.set_field(resp.FIELD_SENDER_KEY, own_publickey)
            dbutils.add_message_to_outbox(resp, crypto, database)
            print("Contact response added to outbox")
        else:
            print("Contact request wasn't from our owner so I'll ignore it")

    def receive_friend_referral(self, msg):
        '''Receive a friend referral'''
        if self._is_message_from_owner(msg):
            print("Friend referral is from my owner so I'll process it")
            # Get referred friend out of message
            new_friend_id = msg.get_field(msg.FIELD_FRIEND_ID)
            new_friend_key = msg.get_field(msg.FIELD_FRIEND_KEY)
            # Add key to keyring and get keyid
            friend_keyid = self.call_component(System.COMPNAME_CRYPTO, "import_public_key",
                                               strkey=new_friend_key)
            if friend_keyid:
                # Update database
                profile = {'status':'trusted', 'keyid':friend_keyid}
                database = self.get_component(System.COMPNAME_DATABASE)
                dbutils.create_profile(database, new_friend_id, profile)

    def _is_message_from_owner(self, msg):
        '''Return true if message is from this robot's owner'''
        sender_id = msg.get_field(msg.FIELD_SENDER_ID)
        owner_profiles = self.call_component(System.COMPNAME_DATABASE,
                                             "get_profiles_with_status",
                                             status="owner")
        owner_profile = owner_profiles[0] if owner_profiles else None
        owner_id = owner_profile.get('torid') if owner_profile else None
        return owner_id and sender_id == owner_id


class RegularMessageHandler(MessageHandler):
    '''Message handler subclass for regular (human-based) system'''

    def __init__(self, parent):
        MessageHandler.__init__(self, parent)

    def receive_status_notify(self, msg):
        '''Receive a status notification'''
        # Reply to a ping with a pong
        MessageHandler.receive_status_notify(self, msg)
        # Update our list of who is online, offline
        sender_id = msg.get_field(msg.FIELD_SENDER_ID)
        is_online = msg.get_field(msg.FIELD_ONLINE)
        self.call_component(System.COMPNAME_CONTACTS, "set_online_status", tor_id=sender_id,
                            online=is_online)

    def receive_contact_request(self, msg):
        '''Receive a contact request'''
        # Maybe: check we haven't got this contact already
        # Check config to see whether we accept untrusted contact requests
        if self.call_component(System.COMPNAME_CONFIG, "get_property",
                               key=Config.KEY_ALLOW_FRIEND_REQUESTS):
            dbutils.add_message_to_inbox(msg, self.get_component(System.COMPNAME_DATABASE),
                                         inbox.MC_CONREQ_INCOMING)

    def receive_contact_response(self, msg):
        '''Receive a contact response (either accept or refuse)'''
        sender_id = msg.get_field(msg.FIELD_SENDER_ID)
        database = self.get_component(System.COMPNAME_DATABASE)
        if isinstance(msg, message.ContactDenyMessage):
            ContactManager(database, None).handle_receive_deny(sender_id)
            dbutils.add_message_to_inbox(msg, database, inbox.MC_CONRESP_REFUSAL)
        elif isinstance(msg, message.ContactAcceptMessage):
            print("  MessageHandler process Accept from '%s'" % sender_id)
            sender_status = dbutils.get_status(database, sender_id)
            if sender_status in ['pending', 'requested', 'reqrobot', 'untrusted']:
                sender_name = msg.get_field(msg.FIELD_SENDER_NAME) or sender_id
                key_str = msg.get_field(msg.FIELD_SENDER_KEY)
                crypto = self.get_component(System.COMPNAME_CRYPTO)
                manager = ContactManager(database, crypto)
                from_robot = manager.is_robot_id(sender_id)
                manager.handle_receive_accept(sender_id, sender_name, key_str)
                if from_robot:
                    print("Recognised accept from robot - need to check connections")
                else:
                    # Only add message to inbox if it's not from the robot
                    dbutils.add_message_to_inbox(msg, database, inbox.MC_CONRESP_ACCEPT)
            elif sender_status in [None, 'blocked', 'deleted']:
                print("Received a contact response but I didn't send them a request!")
        else:
            assert False

    def receive_info_request(self, msg):
        '''Receive an info request'''
        # TODO: Validate, then respond or discard
        pass

    def receive_info_response(self, msg):
        '''Receive an info response'''
        # TODO: Validate, then save in database
        pass

    def receive_friend_referral(self, msg):
        '''Receive a friend referral'''
        # TODO: Validate, then save in database
        pass

    def receive_friend_refer_request(self, msg):
        '''Receive a friend referral request'''
        # TODO: Validate, then save in database
        pass

    def receive_regular_message(self, msg):
        '''Receive a regular message'''
        # TODO: Validate, then save in database
        pass
