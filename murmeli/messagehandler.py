'''Message handlers for Murmeli'''

import re
from murmeli.system import System, Component
from murmeli.config import Config
from murmeli.contactmgr import ContactManager
from murmeli import message
from murmeli import dbutils
from murmeli import inbox
from murmeli import pendingtable


class MessageHandler(Component):
    '''Abstract message handler'''

    def __init__(self, parent):
        Component.__init__(self, parent, System.COMPNAME_MSG_HANDLER)

    def receive(self, msg):
        '''Receive an incoming message'''
        if msg and isinstance(msg, message.Message):
            # Check if it's from a trusted sender
            if msg.sender_must_be_trusted:
                if not self.is_from_trusted_contact(msg):
                    print("Ignoring message from untrusted contact:", msg.get_sender_id())
                    return
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

    @staticmethod
    def receive_status_notify(msg):
        '''Receive a status notification'''
        _ = msg # by default do nothing, the sender now knows we're online

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

    @staticmethod
    def receive_regular_message(msg):
        '''Receive a regular message'''
        _ = msg

    def receive_relayed_message(self, msg):
        '''Receive a relayed message for somebody else'''
        sender_id = msg.get_sender_id() if msg else None
        database = self.get_component(System.COMPNAME_DATABASE)
        dbutils.add_relayed_message_to_outbox(msg, sender_id, database)

    def is_from_trusted_contact(self, msg):
        '''Return true if given message is from a contact with trusted status'''
        return self._get_sender_status(msg) in ['trusted', 'robot']

    def is_from_known_contact(self, msg):
        '''Return true if given message is from either trusted or untrusted contact'''
        return self._get_sender_status(msg) in ['trusted', 'untrusted', 'robot']

    def _get_sender_status(self, msg):
        '''Return status of the sender of the given message from the database'''
        sender_id = msg.get_sender_id() if msg else None
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

    def is_from_trusted_contact(self, msg):
        '''Return true if given message is from a contact with trusted status'''
        return self._get_sender_status(msg) in ['trusted', 'owner']

    def is_from_known_contact(self, msg):
        '''Return true if given message is from either trusted or untrusted contact'''
        return self.is_from_trusted_contact(msg)

    def receive_contact_request(self, msg):
        '''Receive a contact request'''
        # Compare incoming keyid with owner id in Config, ignore all others
        sender_keyid = msg.get_field(msg.FIELD_SENDER_KEY)
        owner_keyid = self.get_config_property(Config.KEY_ROBOT_OWNER_KEY)
        print("Contact request from key '%s', my owner has key '%s'" % (sender_keyid, owner_keyid))
        if sender_keyid == owner_keyid and sender_keyid:
            sender_id = msg.get_sender_id()
            print("Contact request from my owner with id '%s'" % sender_id)
            # Check if owner already set, if so then don't change it
            database = self.get_component(System.COMPNAME_DATABASE)
            if not database:
                return
            if not database.get_profiles_with_status(status="owner"):
                # update profile of owner with the murmeli id
                # NOTE: For conreq to robot, only the keyid is sent, not the whole key
                database.add_or_update_profile({"torid":sender_id, "status":"owner",
                                                "keyid":owner_keyid})
            # Send an automatic accept message
            resp = message.ContactAcceptMessage()
            resp.recipients = [sender_id]
            own_profile = database.get_profile()
            resp.set_field(resp.FIELD_MESSAGE, "I'm your robot")
            resp.set_field(resp.FIELD_SENDER_NAME, "Robot")
            own_keyid = own_profile.get('keyid')
            crypto = self.get_component(System.COMPNAME_CRYPTO)
            own_publickey = crypto.get_public_key(own_keyid) if crypto else None
            resp.set_field(resp.FIELD_SENDER_KEY, own_publickey)
            dbutils.add_message_to_outbox(resp, crypto, database)
            print("Contact response added to outbox")
        else:
            self.process_unknown_conreq(msg)

    @staticmethod
    def process_unknown_conreq(msg):
        '''Robot ignores contact requests if not from owner'''
        print("Contact request wasn't from our owner so I'll ignore it:", msg)

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

    def _get_owner_id(self):
        '''Get this robot's owner id from the database'''
        owner_profiles = self.call_component(System.COMPNAME_DATABASE,
                                             "get_profiles_with_status",
                                             status="owner")
        owner_profile = owner_profiles[0] if owner_profiles else None
        return owner_profile.get('torid') if owner_profile else None

    def _is_message_from_owner(self, msg):
        '''Return true if message is from this robot's owner'''
        owner_id = self._get_owner_id()
        return owner_id and owner_id == msg.get_sender_id()


class ParrotMessageHandler(RobotMessageHandler):
    '''Message handler subclass for parrot system'''

    def __init__(self, parent):
        RobotMessageHandler.__init__(self, parent)
        print("I'm a parrot message handler")

    def is_from_known_contact(self, msg):
        '''Return true if message is from a known contact'''
        return self._get_sender_status(msg) in ['owner', 'untrusted', 'trusted']

    def is_from_trusted_contact(self, msg):
        '''Return true if given message is from a contact with trusted status'''
        return self._get_sender_status(msg) == 'owner'

    def process_unknown_conreq(self, msg):
        '''Receive and automatically accept an unknown contact request'''
        sender_key = msg.get_field(msg.FIELD_SENDER_KEY)
        sender_id = msg.get_sender_id()
        print("Contact request from unknown sender with id '%s'" % sender_id)
        database = self.get_component(System.COMPNAME_DATABASE)
        crypto = self.get_component(System.COMPNAME_CRYPTO)
        # Use ContactManager to auto-accept and update db
        ContactManager(database, crypto).handle_accept(sender_id, "I'm a parrot", sender_key)
        # get key id from sender_id, compare with stored owner id
        sender_profile = database.get_profile(sender_id) if database else None
        sender_keyid = sender_profile.get("keyid") if sender_profile else None
        owner_keyid = self.get_config_property(Config.KEY_ROBOT_OWNER_KEY)
        if sender_keyid and sender_keyid == owner_keyid:
            database.add_or_update_profile({"torid":sender_id, 'status':'owner'})

    @staticmethod
    def receive_friend_referral(msg):
        '''Receive and ignore a friend referral'''
        _ = msg

    @staticmethod
    def receive_relayed_message(msg):
        '''Receive and ignore a relayed message for somebody else'''
        _ = msg

    def receive_regular_message(self, msg):
        '''Receive a regular message'''
        print("Parrot received regular message from:", msg.get_sender_id())
        if self.is_from_trusted_contact(msg):
            print("Received regular message from owner")
            forward_id, cropped_body = self._get_forward_id(msg.get_field(msg.FIELD_MSGBODY))
            if forward_id:
                print("Forwarding message from owner to '%s'" % forward_id)
                self._send_message(cropped_body, forward_id)
                return
        if self.is_from_known_contact(msg):
            recvd_body = msg.get_field(msg.FIELD_MSGBODY)
            if "Parrot: " in recvd_body[:13]:
                print("Already parroted, so ignoring this message.")
                return
            sender_id = msg.get_sender_id()
            self._send_message("Parrot: '%s'" % recvd_body[:100], sender_id)
            owner_id = self._get_owner_id()
            if sender_id != owner_id:
                self._send_message("Parrot (%s): '%s'" % (sender_id, recvd_body), owner_id)
        else:
            print("Regular message ignored because status=", self._get_sender_status(msg))

    def _send_message(self, msg_body, send_to):
        '''Send a regular message to the given id'''
        reply = message.RegularMessage()
        reply.set_field(reply.FIELD_RECIPIENTS, send_to)
        reply.set_field(reply.FIELD_MSGBODY, msg_body[:1000])
        reply.recipients = [send_to]
        crypto = self.get_component(System.COMPNAME_CRYPTO)
        database = self.get_component(System.COMPNAME_DATABASE)
        dbutils.add_message_to_outbox(reply, crypto, database)

    @staticmethod
    def _get_forward_id(msg_body):
        '''Extract a forwarding address from the message body, and also return the cropped body'''
        if msg_body and len(msg_body) > 58:
            bare_match = re.match("([a-zA-Z0-9]{56}): ", msg_body)
            if bare_match:
                return (bare_match.group(1), msg_body[58:])
            p_match = re.match("<p>([a-zA-Z0-9]{56}): ", msg_body)
            if p_match:
                return (p_match.group(1), "<p>" + msg_body[60:])
        return (None, msg_body)


class RegularMessageHandler(MessageHandler):
    '''Message handler subclass for regular (human-based) system'''

    def __init__(self, parent):
        MessageHandler.__init__(self, parent)

    def receive_status_notify(self, msg):
        '''Receive a status notification'''
        # Update our list of who is online, offline
        sender_id = msg.get_sender_id()
        is_online = msg.get_field(msg.FIELD_ONLINE)
        self.call_component(System.COMPNAME_CONTACTS, "set_online_status", tor_id=sender_id,
                            online=is_online)
        database = self.get_component(System.COMPNAME_DATABASE)
        # If it's a ping, reply with a pong
        if msg.get_field(msg.FIELD_PING) and msg.get_field(msg.FIELD_ONLINE):
            if not self.is_from_trusted_contact(msg):
                return
            # Create new pong for the sender and pass to outbox
            pong = self._create_pong(database, sender_id)
            dbutils.add_message_to_outbox(pong, self.get_component(System.COMPNAME_CRYPTO),
                                          database)
        # Compare profile hash with stored one
        received_hash = msg.get_field(msg.FIELD_PROFILE_HASH)
        if received_hash and self.is_from_trusted_contact(msg):
            print("Got hash: '%s'" % received_hash)
            profile = database.get_profile(sender_id)
            if profile and profile.get('profileHash') != received_hash:
                print("Profile hash is different, need to send an InfoRequest")
                inforeq = message.InfoRequestMessage()
                inforeq.recipients = [sender_id]
                dbutils.add_message_to_outbox(inforeq,
                                              self.get_component(System.COMPNAME_CRYPTO),
                                              database)

    @staticmethod
    def _create_pong(database, recipient):
        '''Create a StatusNotify pong message for the given recipient'''
        pong = message.StatusNotifyMessage()
        pong.set_field(pong.FIELD_PING, 0)
        pong.recipients = [recipient]
        # Calculate profile hash and add to msg
        if dbutils.is_trusted(database, recipient):
            own_hash = dbutils.calculate_hash(database.get_profile())
            pong.set_field(pong.FIELD_PROFILE_HASH, own_hash)
        return pong

    def receive_contact_request(self, msg):
        '''Receive a contact request'''
        # Maybe: check we haven't got this contact already, or its status if we have
        # Check config to see whether we accept untrusted contact requests
        if self.call_component(System.COMPNAME_CONFIG, "get_property",
                               key=Config.KEY_ALLOW_FRIEND_REQUESTS):
            dbutils.add_message_to_inbox(msg, self.get_component(System.COMPNAME_DATABASE),
                                         inbox.MC_CONREQ_INCOMING)

    def receive_contact_response(self, msg):
        '''Receive a contact response (either accept or refuse)'''
        sender_id = msg.get_sender_id()
        database = self.get_component(System.COMPNAME_DATABASE)
        if isinstance(msg, message.ContactDenyMessage):
            ContactManager(database, None).handle_receive_deny(sender_id)
            dbutils.add_message_to_inbox(msg, database, inbox.MC_CONRESP_REFUSAL)
        elif isinstance(msg, message.ContactAcceptMessage):
            print("  MessageHandler process Accept from '%s'" % sender_id)
            sender_status = dbutils.get_status(database, sender_id)
            if sender_status in ['requested', 'reqrobot', 'untrusted']:
                sender_name = msg.get_field(msg.FIELD_SENDER_NAME) or sender_id
                key_str = msg.get_field(msg.FIELD_SENDER_KEY)
                crypto = self.get_component(System.COMPNAME_CRYPTO)
                manager = ContactManager(database, crypto)
                from_robot = manager.is_robot_id(sender_id)
                manager.handle_receive_accept(sender_id, sender_name, key_str)
                if not from_robot:
                    # Only add message to inbox if it's not from the robot
                    dbutils.add_message_to_inbox(msg, database, inbox.MC_CONRESP_ACCEPT)
            elif sender_status in [None, 'blocked', 'deleted']:
                print("Received a contact response but I didn't send them a request!")
                database.add_row_to_pending_table(pendingtable.create_row(msg))
        else:
            assert False

    def receive_info_request(self, msg):
        '''Receive an info request'''
        sender_id = msg.get_sender_id()
        database = self.get_component(System.COMPNAME_DATABASE)
        if dbutils.is_trusted(database, sender_id):
            print("Info request is from trusted sender, so should reply with info")
            self._send_info_response(database, self.get_component(System.COMPNAME_CRYPTO), msg)

    @staticmethod
    def _send_info_response(database, crypto, req_msg):
        '''Send an info response to the given info request message'''
        if req_msg.get_field(req_msg.FIELD_INFOTYPE) == req_msg.INFO_PROFILE:
            sender_id = req_msg.get_sender_id()
            print("Should send profile info to:", sender_id)
            outmsg = message.InfoResponseMessage()
            own_profile = database.get_profile() if database else {}
            own_profile['profileHash'] = dbutils.calculate_hash(own_profile)
            profile_string = dbutils.get_profile_as_string(own_profile)
            outmsg.set_field(outmsg.FIELD_RESULT, profile_string)
            outmsg.recipients = [sender_id]
            dbutils.add_message_to_outbox(outmsg, crypto, database)

    def receive_info_response(self, msg):
        '''Receive an info response'''
        print("RegularMessageHandler, Info response received!")
        if not self.is_from_trusted_contact(msg):
            return
        if msg.get_field(msg.FIELD_INFOTYPE) == msg.INFO_PROFILE:
            sender_id = msg.get_sender_id()
            in_profile = dbutils.convert_string_to_dictionary(msg.get_field(msg.FIELD_RESULT))
            database = self.get_component(System.COMPNAME_DATABASE)
            curr_profile = database.get_profile(sender_id)
            if in_profile and curr_profile:
                print("Updating profile with:", repr(in_profile.keys()))
                # Make sure that displayName in db has priority over incoming one
                in_profile['displayName'] = curr_profile.get('displayName')
                cache_dir = self.call_component(System.COMPNAME_CONFIG, "get_web_cache_dir")
                dbutils.update_profile(database, sender_id, in_profile, cache_dir)

    def receive_friend_referral(self, msg):
        '''Receive a friend referral'''
        print("Received friend referral")
        if not self.is_from_trusted_contact(msg):
            print("Received friend referral but sender wasn't trusted?!")
            return
        suggested_friendid = msg.get_field(msg.FIELD_FRIEND_ID)
        print("Received referral for '%s'" % suggested_friendid)
        current_status = self._get_contact_status(suggested_friendid)
        print("Current status of this contact is '%s'" % current_status)
        if msg.is_normal_referral():
            print("It's a regular friend referral")
            if current_status in [None, 'deleted', 'requested']:
                dbutils.add_message_to_inbox(msg, self.get_component(System.COMPNAME_DATABASE),
                                             inbox.MC_REFER_INCOMING)
        elif msg.is_robot_referral() and not current_status:
            print("My friend has referred their robot to me!")
        elif msg.is_robot_removal() and current_status == 'robot':
            print("My friend wants to remove their robot!")

    def receive_friend_refer_request(self, msg):
        '''Receive a friend referral request'''
        # TODO: Validate, then save in database
        pass

    def receive_regular_message(self, msg):
        '''Receive a regular message'''
        if self.is_from_known_contact(msg):
            # sender could be trusted or untrusted
            dbutils.add_message_to_inbox(msg, self.get_component(System.COMPNAME_DATABASE),
                                         inbox.MC_NORMAL_INCOMING)
