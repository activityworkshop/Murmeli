'''Messages and their types for Murmeli'''

from random import SystemRandom
import hashlib
import datetime
import json


class ByteChomper:
    '''Class for splitting up data strings according to different-sized fields'''
    def __init__(self, data):
        self.data = data if isinstance(data, bytes) else bytes()
        self.pos = 0

    def get_field(self, num_bytes):
        '''Extracts a series of bytes and returns them as a bytes sequence'''
        if not self.data:
            return bytes()
        field = self.data[self.pos : self.pos + num_bytes]
        self.pos += num_bytes
        return field

    def get_byte_value(self, num_bytes):
        '''Decode the series of bytes into a value, lowest byte first'''
        total = 0
        mult = 1
        for val in self.get_field(num_bytes):
            total += val * mult
            mult *= 256
        return total

    def get_string(self, num_bytes):
        '''Get the given number of bytes and turn into a string'''
        return self.get_field(num_bytes).decode('utf-8')

    def get_field_with_length(self, num_bytes):
        '''Use num_bytes to read the number of bytes to take for the field'''
        str_len = self.get_byte_value(num_bytes)
        return self.get_field(str_len)

    def get_string_with_length(self, num_bytes):
        '''Use num_bytes to read the string length, then take the string'''
        return self.get_field_with_length(num_bytes).decode('utf_8')

    def get_rest(self):
        '''Get the rest of the data'''
        return self.data[self.pos:] if self.data else None


class Message:
    '''Superclass for all Messages'''

    TYPE_CONTACT_REQUEST = 1
    TYPE_CONTACT_RESPONSE = 2
    TYPE_STATUS_NOTIFY = 3
    TYPE_INFO_REQUEST = 5
    TYPE_INFO_RESPONSE = 6
    TYPE_FRIEND_REFERRAL = 7
    TYPE_FRIENDREFER_REQUEST = 8
    TYPE_REGULAR_MESSAGE = 20
    TYPE_RELAYED_MESSAGE = 21

    ENCTYPE_NONE = 0
    ENCTYPE_ASYM = 1
    # ENCTYPE_SYMM = 2
    ENCTYPE_RELAY = 3

    FIELD_SENDER_ID = "senderId"
    FIELD_SIGNATURE_KEYID = "signatureId"

    MAGIC_TOKEN = "murmeli"

    def __init__(self, enc_type, msg_type):
        self.enc_type = enc_type
        self.msg_type = msg_type
        self.should_be_queued = True   # Most should be queued, just certain subtypes not
        self.sender_must_be_trusted = True  # Most should only be accepted if sender is trusted
        self.original_payload = None # Perhaps the original payload is needed later
        self.should_be_relayed = False
        self.timestamp = None
        self.body = {}
        self.recipients = []
        self.version_number = None

    def set_field(self, key, value):
        '''Set the given field in the message'''
        self.body[key] = value

    def set_all_fields(self, dict_string):
        '''Set all fields in the message from the given dictionary serialization'''
        try:
            contents = json.loads(dict_string)
            if isinstance(contents, dict):
                for key, value in contents.items():
                    self.body[key] = value
        except TypeError:
            # TODO: Log this exception somewhere
            raise

    def get_field(self, key):
        '''Get the given field from the message'''
        return self.body.get(key)

    def get_sender_id(self):
        '''Get the sender id from the message'''
        return self.get_field(self.FIELD_SENDER_ID)

    @staticmethod
    def from_received_data(data, decrypter=None):
        '''Using the bytes received in the message, reconstruct it into a Message object'''
        chomper = ByteChomper(data)
        # Verify start token
        magic = chomper.get_string(len(Message.MAGIC_TOKEN))
        print("Start magic '%s'" % magic)
        if magic != Message.MAGIC_TOKEN:
            print("found '%s', expected '%s'" % (magic, Message.MAGIC_TOKEN))
            return None   # doesn't begin with magic
        checksum = chomper.get_field(16)
        print("Checksum '%s'" % checksum)
        if len(checksum) != 16:
            return None         # must be exactly 16 long
        enc_type = chomper.get_byte_value(1)
        print("Enc type '%s'" % enc_type)

        # Extract payload
        enc_payload = chomper.get_field_with_length(4)
        print("Payload '%s'" % repr(enc_payload))
        magic = chomper.get_string(len(Message.MAGIC_TOKEN))
        print("End magic '%s'" % magic)
        if magic != Message.MAGIC_TOKEN:
            return None   # no magic after the payload
        if chomper.get_rest():
            print("extra at the end?")
            return None   # spurious data at the end?

        # Check checksum
        calculated_check = Message.make_checksum(enc_payload)
        if calculated_check != checksum:
            return None        # checksum doesn't match

        if decrypter:
            payload, sig_id = decrypter.decrypt(enc_payload, enc_type)
        else:
            payload, sig_id = (enc_payload, None)

        msg = None
        if enc_type == Message.ENCTYPE_NONE:
            msg = UnencryptedMessage.from_received_payload(payload)
        elif enc_type == Message.ENCTYPE_ASYM:
            msg = AsymmetricMessage.from_received_payload(payload)
            if msg and (not sig_id or isinstance(msg, ContactAcceptMessage)):
                msg.original_payload = enc_payload
        elif enc_type == Message.ENCTYPE_RELAY:
            msg = RelayMessage.unpack_payload(payload, decrypter)
        if sig_id and enc_type in [Message.ENCTYPE_ASYM, Message.ENCTYPE_RELAY]:
            msg.set_field(msg.FIELD_SIGNATURE_KEYID, sig_id)
        return msg

    @staticmethod
    def from_encrypted_payload(data, decrypter):
        '''Using an encrypted payload stored from a message,
           reconstruct it into a Message object'''
        if decrypter:
            payload, sig_id = decrypter.decrypt(data, Message.ENCTYPE_ASYM)
            if sig_id:
                msg = AsymmetricMessage.from_received_payload(payload)
                msg.set_field(msg.FIELD_SIGNATURE_KEYID, sig_id)
                return msg
        return None

    def create_output(self, encrypter=None):
        '''Create the whole output packet from the internal fields'''
        payload = self.create_payload()
        if encrypter:
            payload = encrypter.encrypt(payload, self.enc_type)
        checksum = Message.make_checksum(payload)
        payload_size = len(payload)
        message_components = [Message.MAGIC_TOKEN,
                              checksum, # 16 bytes
                              bytes([self.enc_type]),
                              Message.encode_number_to_bytes(payload_size, 4),
                              payload,
                              Message.MAGIC_TOKEN]
        return Message.pack_bytes(message_components)

    def is_complete_for_sending(self):
        '''Check if all the required fields are non-empty for sending'''
        for field in self.get_required_body_fields():
            if not self.body.get(field):
                print("Message is missing field:", field)
                return False
        return True

    @staticmethod
    def make_checksum(payload):
        '''Make an md5 checksum of the payload'''
        return hashlib.md5(payload).digest()

    @staticmethod
    def encode_number_to_bytes(num, num_bytes=1):
        '''Pack the given number into a series of bytes'''
        res = bytearray()
        remainder = num
        for _ in range(num_bytes):
            res.append(remainder % 256)
            remainder = int(remainder/256)
        return res

    @staticmethod
    def pack_bytes(contents):
        '''Pack all the given contents into a single bytearray'''
        total = bytearray()
        for elem in contents:
            total += (elem.encode('utf-8') if isinstance(elem, str) else elem)
        return bytes(total)

    @staticmethod
    def make_current_timestamp():
        '''Make a timestamp float according to UTC'''
        return datetime.datetime.now(datetime.timezone.utc).timestamp()

    @staticmethod
    def timestamp_to_string(tstamp):
        '''Make a UTC timestamp string for sending from the given float'''
        send_time = datetime.datetime.fromtimestamp(tstamp, tz=datetime.timezone.utc)
        return "%d-%02d-%02d-%02d-%02d" % (send_time.year, send_time.month,
                                           send_time.day, send_time.hour, send_time.minute)

    @staticmethod
    def string_to_timestamp(timestr):
        '''Convert a timestamp in the string form 'YYYY-MM-DD-HH-MM' (in UTC) to a float'''
        try:
            (year, month, day, hour, minute) = [int(i) for i in timestr.split("-")]
            when = datetime.datetime(year, month, day, hour, minute, tzinfo=datetime.timezone.utc)
        except ValueError:
            print("Failed to parse timestamp '%s'" % timestr)
            when = datetime.datetime.now()
        except AttributeError:
            when = datetime.datetime.now()
        return when.timestamp()

    def get_body_fields(self):
        '''Get which fields should be packed in body'''
        return []

    def get_required_body_fields(self):
        '''Get which fields are necessary for the message to be valid'''
        return []

    def create_payload(self):
        '''Create the payload from the message contents (will be overridden)'''
        return bytes()

    def describe_message_type(self):
        '''Return a string describing the message type (for diagnostics only)'''
        typedescs = {self.TYPE_CONTACT_REQUEST:"contactrequest",
                     self.TYPE_CONTACT_RESPONSE:"contactresponse",
                     self.TYPE_STATUS_NOTIFY:"statusnotify",
                     self.TYPE_INFO_REQUEST:"inforequest",
                     self.TYPE_INFO_RESPONSE:"inforesponse",
                     self.TYPE_FRIEND_REFERRAL:"referral",
                     self.TYPE_FRIENDREFER_REQUEST:"referrequest",
                     self.TYPE_REGULAR_MESSAGE:"regular",
                     self.TYPE_RELAYED_MESSAGE:"relay"}
        return typedescs.get(self.msg_type)


class UnencryptedMessage(Message):
    '''Superclass for both unencrypted message types'''

    def __init__(self, msg_type):
        Message.__init__(self, Message.ENCTYPE_NONE, msg_type)
        self.sender_must_be_trusted = False  # ok if sender unknown

    @staticmethod
    def from_received_payload(payload):
        '''Given the payload, construct an appropriate subtype'''
        if payload:
            msg = None
            msg_type = payload[0]
            msg_ver = payload[1]
            assert msg_ver == 1
            if msg_type == Message.TYPE_CONTACT_REQUEST:
                msg = ContactRequestMessage()
            elif msg_type == Message.TYPE_CONTACT_RESPONSE:
                msg = ContactDenyMessage()
            if msg:
                msg.version_number = msg_ver
                msg.set_all_fields(payload[2:].decode("utf-8"))
                # Unencrypted messages don't have timestamps, so we'll assign one on receipt
                msg.timestamp = msg.make_current_timestamp()
                return msg
        return None

    def create_payload(self):
        '''Create the payload from the message contents'''
        fields = {key:value for key, value in self.body.items() if key in self.get_body_fields()}
        contents = [
            bytes([self.msg_type]),
            bytes([1]),
            json.dumps(fields).encode("utf-8")]
        return Message.pack_bytes(contents)


class ContactRequestMessage(UnencryptedMessage):
    '''Message for requesting contact, which has to be unencrypted as we haven't got the
       recipient's public key yet'''

    FIELD_SENDER_NAME = "senderName"
    FIELD_MESSAGE = "message"
    FIELD_SENDER_KEY = "senderKey"

    def __init__(self):
        UnencryptedMessage.__init__(self, Message.TYPE_CONTACT_REQUEST)

    def get_body_fields(self):
        '''Get which fields should be packed in body'''
        return [self.FIELD_SENDER_NAME, self.FIELD_SENDER_ID, self.FIELD_MESSAGE,
                self.FIELD_SENDER_KEY]

    def get_required_body_fields(self):
        '''Get which fields are necessary for the message to be valid'''
        return [self.FIELD_SENDER_NAME, self.FIELD_SENDER_ID, self.FIELD_SENDER_KEY]


class ContactDenyMessage(UnencryptedMessage):
    '''Message to deny a contact request - this can't be encrypted because we didn't
       accept their public key to our keyring, and in any case we've decided not to
       communicate with this person so we won't send a reason either.'''

    def __init__(self):
        UnencryptedMessage.__init__(self, Message.TYPE_CONTACT_RESPONSE)

    def get_body_fields(self):
        '''Get which fields should be packed in body'''
        return [self.FIELD_SENDER_ID]

    def get_required_body_fields(self):
        '''Get which fields are necessary for the message to be valid'''
        return [self.FIELD_SENDER_ID]


class AsymmetricMessage(Message):
    '''Superclass for all asymmetrically-encrypted message types'''

    def __init__(self, msg_type):
        Message.__init__(self, Message.ENCTYPE_ASYM, msg_type)
        self.should_be_relayed = True  # Most should be relayed

    @staticmethod
    def create_random_token():
        '''Create a random byte sequence to use as a repeating token'''
        randgen = SystemRandom()
        num_bytes = randgen.choice([3, 4, 5, 6])
        token = [randgen.randrange(255) + 1 for _ in range(num_bytes)]
        return bytearray(token)

    @staticmethod
    def from_received_payload(payload):
        '''Given the decrypted payload, construct an appropriate subtype'''
        if payload:
            msg = None
            msg_version = payload[0]
            print("msg version:", msg_version)
            # Separate fields of message into common ones and the type-specific payload
            msg_type, subpayload, timestr = AsymmetricMessage.strip_fields(payload[1:])
            print("msg type:", msg_type)
            if msg_type == Message.TYPE_CONTACT_RESPONSE:
                msg = ContactAcceptMessage()
            elif msg_type == Message.TYPE_STATUS_NOTIFY:
                msg = StatusNotifyMessage()
            elif msg_type == Message.TYPE_INFO_REQUEST:
                msg = InfoRequestMessage()
            elif msg_type == Message.TYPE_INFO_RESPONSE:
                msg = InfoResponseMessage()
            elif msg_type == Message.TYPE_REGULAR_MESSAGE:
                msg = RegularMessage()
            elif msg_type == Message.TYPE_FRIEND_REFERRAL:
                msg = ContactReferralMessage()
            elif msg_type == Message.TYPE_FRIENDREFER_REQUEST:
                msg = ContactReferRequestMessage()
            if msg:
                msg.timestamp = msg.string_to_timestamp(timestr)
                msg.version_number = msg_version
                msg.set_all_fields(subpayload.decode("utf-8"))
                return msg
        return None


    def create_payload(self):
        '''Create the payload from the message contents'''
        fields = {key:value for key, value in self.body.items() if key in self.get_body_fields()}
        token = AsymmetricMessage.create_random_token()
        if not self.timestamp:
            self.timestamp = Message.make_current_timestamp()
        msg_version = 1
        contents = [bytes([msg_version]),
                    token, Message.MAGIC_TOKEN, token,
                    bytes([self.msg_type]),
                    json.dumps(fields).encode("utf-8"),
                    Message.timestamp_to_string(self.timestamp)]
        return Message.pack_bytes(contents)

    @staticmethod
    def strip_fields(payload):
        '''Try to remove the random tokens from the start of the payload
           If successful, return a tuple containing the message type, payload and timestamp'''
        magic_token_len = len(Message.MAGIC_TOKEN)
        if payload:
            for toklen in [3, 4, 5, 6]:
                tok1 = payload[:toklen]
                mag1 = payload[toklen : toklen + magic_token_len]
                tok2 = payload[toklen + magic_token_len : 2*toklen + magic_token_len]
                if len(tok1) == toklen \
                  and tok1 == tok2 \
                  and mag1.decode('utf-8') == Message.MAGIC_TOKEN:
                    start_pos = 2*toklen + magic_token_len
                    # timestamp is always the last 16 bytes
                    timestamp = payload[-16:].decode("utf-8")
                    return (payload[start_pos], payload[start_pos+1:-16], timestamp)
        return ("", "", "")


class ContactAcceptMessage(AsymmetricMessage):
    '''Message to reply to and accept a contact request, message is optional'''

    FIELD_SENDER_NAME = "senderName"
    FIELD_MESSAGE = "message"
    FIELD_SENDER_KEY = "senderKey"

    def __init__(self):
        AsymmetricMessage.__init__(self, Message.TYPE_CONTACT_RESPONSE)
        self.sender_must_be_trusted = False  # ok if sender unknown

    def get_body_fields(self):
        '''Get which fields should be packed in body'''
        return [self.FIELD_SENDER_NAME, self.FIELD_SENDER_ID, self.FIELD_MESSAGE,
                self.FIELD_SENDER_KEY]

    def get_required_body_fields(self):
        '''Get which fields are necessary for the message to be valid'''
        return [self.FIELD_SENDER_NAME, self.FIELD_SENDER_ID, self.FIELD_SENDER_KEY]


class StatusNotifyMessage(AsymmetricMessage):
    '''Message to send a notification of status, either coming online or about to go offline
       Includes a hash of the current profile for detection of changes'''

    FIELD_PING = "ping"
    FIELD_ONLINE = "online"
    FIELD_PROFILE_HASH = "profileHash"

    def __init__(self):
        AsymmetricMessage.__init__(self, Message.TYPE_STATUS_NOTIFY)
        self.should_be_relayed = False
        self.should_be_queued = False
        # set default values
        self.set_field(self.FIELD_PING, 1)
        self.set_field(self.FIELD_ONLINE, 1)
        self.set_field(self.FIELD_PROFILE_HASH, "")

    def get_body_fields(self):
        '''Get which fields should be packed in body'''
        return [self.FIELD_PING, self.FIELD_ONLINE, self.FIELD_PROFILE_HASH]

    @staticmethod
    def get_required_body_fields():
        '''Get which fields are necessary for the message to be valid'''
        return []


class InfoMessage(AsymmetricMessage):
    '''Superclass of the InfoRequest and InfoResponse message classes'''

    # shared fields for info request and info response
    FIELD_INFOTYPE = "infoType"
    INFO_PROFILE = 1

    def __init__(self, msg_type, info_type=INFO_PROFILE):
        AsymmetricMessage.__init__(self, msg_type)
        self.should_be_relayed = False
        self.should_be_queued = False
        self.set_field(self.FIELD_INFOTYPE, info_type)


class InfoRequestMessage(InfoMessage):
    '''An info request can be a request for a profile, or for a list of friends'''

    # Maybe other types of info request will be needed later?
    # Do we need another random token field just to bump up what is encrypted?

    def __init__(self, info_type=InfoMessage.INFO_PROFILE):
        InfoMessage.__init__(self, Message.TYPE_INFO_REQUEST, info_type)

    def get_body_fields(self):
        '''Get which fields should be packed in body'''
        return [self.FIELD_INFOTYPE]

    def get_required_body_fields(self):
        '''Get which fields are necessary for the message to be valid'''
        return [self.FIELD_INFOTYPE]

        # TODO: Should all such requests include a token broadcast by the status notify message?
        # This would allow confirmation that it's not a repeat of a recorded message.


class InfoResponseMessage(InfoMessage):
    '''An info response is sent to answer an info request, either returning a profile,
       or maybe something else'''

    FIELD_RESULT = "resultInfo"

    def __init__(self, info_type=InfoMessage.INFO_PROFILE):
        InfoMessage.__init__(self, Message.TYPE_INFO_RESPONSE, info_type)

    def get_body_fields(self):
        '''Get which fields should be packed in body'''
        return [self.FIELD_INFOTYPE, self.FIELD_RESULT]

    def get_required_body_fields(self):
        '''Get which fields are necessary for the message to be valid'''
        return [self.FIELD_INFOTYPE, self.FIELD_RESULT]


class RegularMessage(AsymmetricMessage):
    '''Class for a generic message to one or more contacts'''

    FIELD_MSGBODY = "messageBody"
    FIELD_REPLYHASH = "replyHash"
    FIELD_RECIPIENTS = "recipients"

    def __init__(self):
        AsymmetricMessage.__init__(self, Message.TYPE_REGULAR_MESSAGE)
        self.sender_must_be_trusted = False  # sender is allowed to be untrusted

    def get_body_fields(self):
        '''Get which fields should be packed in body'''
        return [self.FIELD_MSGBODY, self.FIELD_REPLYHASH, self.FIELD_RECIPIENTS]

    def get_required_body_fields(self):
        '''Get which fields are necessary for the message to be valid'''
        return [self.FIELD_MSGBODY, self.FIELD_RECIPIENTS]


class ContactReferralMessage(AsymmetricMessage):
    '''Class for a contact referral of a friend's friend'''

    FIELD_MSGBODY = "messageBody"
    FIELD_FRIEND_ID = "friendId"
    FIELD_FRIEND_NAME = "friendName"
    FIELD_FRIEND_KEY = "friendKey"
    FIELD_REFERRAL_TYPE = "referType"

    # Type of referral, as referrals of robots need to be handled differently
    REFERTYPE_NORMAL = ""
    REFERTYPE_ROBOT = "robot"
    REFERTYPE_REMOVEROBOT = "removerobot"


    def __init__(self):
        AsymmetricMessage.__init__(self, Message.TYPE_FRIEND_REFERRAL)

    def get_body_fields(self):
        '''Get which fields should be packed in body'''
        return [self.FIELD_REFERRAL_TYPE, self.FIELD_MSGBODY, self.FIELD_FRIEND_ID,
                self.FIELD_FRIEND_NAME, self.FIELD_FRIEND_KEY]

    def get_required_body_fields(self):
        '''Get which fields are necessary for the message to be valid'''
        return [self.FIELD_FRIEND_ID, self.FIELD_FRIEND_NAME, self.FIELD_FRIEND_KEY]

    def is_normal_referral(self):
        '''Return true if this is a normal referral, not a robot referral'''
        return not self.get_field(self.FIELD_REFERRAL_TYPE)

    def is_robot_referral(self):
        '''Return true if this is a referral of a robot from its owner'''
        return self.get_field(self.FIELD_REFERRAL_TYPE) == self.REFERTYPE_ROBOT

    def is_robot_removal(self):
        '''Return true if this is an instruction to remove a robot from its owner'''
        return self.get_field(self.FIELD_REFERRAL_TYPE) == self.REFERTYPE_REMOVEROBOT


class ContactReferRequestMessage(AsymmetricMessage):
    '''Class to request a contact referral from a friend'''

    FIELD_MSGBODY = "messageBody"
    FIELD_FRIEND_ID = "friendId"

    def __init__(self):
        AsymmetricMessage.__init__(self, Message.TYPE_FRIENDREFER_REQUEST)

    def get_body_fields(self):
        '''Get which fields should be packed in body'''
        return [self.FIELD_MSGBODY, self.FIELD_FRIEND_ID]

    def get_required_body_fields(self):
        '''Get which fields are necessary for the message to be valid'''
        return [self.FIELD_FRIEND_ID]


class RelayMessage(Message):
    '''A relay message is some (unknown) kind of binary message which we cannot decrypt
       but we can check the signature and relay it to our contacts'''

    def __init__(self):
        Message.__init__(self, Message.ENCTYPE_RELAY, Message.TYPE_RELAYED_MESSAGE)
        self.parcel = None
        self.received_bytes = None

    @staticmethod
    def wrap_outgoing_message(msg_bytes):
        '''Create a relay wrapper around an existing outgoing message'''
        relay_msg = RelayMessage()
        relay_msg.parcel = msg_bytes
        return relay_msg.create_output() if msg_bytes else None

    def create_payload(self):
        '''If we were given a parcel, then this is the payload we need'''
        assert self.parcel
        return self.parcel

    def create_output(self, encrypter=None):
        '''Override the regular header packing if we've got the wrapped message'''
        if self.received_bytes:
            return self.received_bytes
        return Message.create_output(self, encrypter)

    @staticmethod
    def unpack_payload(payload, crypto):
        '''Use the crypto object to unpack the given payload into a message'''
        if payload:
            msg_for_me = Message.from_received_data(payload, crypto)
            if msg_for_me:
                return msg_for_me
            # message isn't for me, but I can store a wrapped version
            msg = RelayMessage()
            msg.received_bytes = payload
            return msg
        return None
