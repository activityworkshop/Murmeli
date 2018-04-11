'''Message handlers for Murmeli'''

from murmeli.system import System, Component
from murmeli.config import Config
from murmeli import message


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
            # Create new pong for the sender and pass to outbox
            sender_of_ping = msg.get_field(msg.FIELD_SENDER_ID)
            pong = message.StatusNotifyMessage()
            pong.set_field(pong.FIELD_PING, 0)
            pong.recipients = [sender_of_ping]
            self.call_component(System.COMPNAME_DATABASE, "add_message_to_outbox", msg=pong)

    def receive_info_request(self, msg):
        '''Receive an info request'''
        pass
    def receive_info_response(self, msg):
        '''Receive an info response'''
        # TODO: Validate, then save in database
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


class RobotMessageHandler(MessageHandler):
    '''Message handler subclass for robot system'''

    def __init__(self, parent):
        MessageHandler.__init__(self, parent)

    def receive_contact_request(self, msg):
        '''Receive a contact request'''
        # Compare incoming keyid with owner id in Config, ignore all others
        sender_keyid = msg.get_field(msg.FIELD_SENDER_KEY)
        owner_keyid = self.get_config_property(Config.KEY_ROBOT_OWNER_KEY)
        if sender_keyid == owner_keyid:
            # TODO: Accept, update db with SENDER_ID, send response
            pass
    def receive_friend_referral(self, msg):
        '''Receive a friend referral'''
        # TODO: If it's from the robot's owner, accept automatically
        pass


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

