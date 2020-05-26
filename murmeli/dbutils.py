'''DbUtils for JSON conversion for Murmeli'''

import json    # for converting strings to and from json
import hashlib # for calculating checksums
import os      # for managing paths
import shutil  # for managing files
from murmeli import contactutils
from murmeli import imageutils
from murmeli.cryptoclient import CryptoError
from murmeli import message
from murmeli import inbox


class EncrypterShim:
    '''Adapter class to provide messages with an encrypter object'''

    def __init__(self, database, crypto, encrypt_key):
        self.database = database
        self.crypto = crypto
        self.encrypt_key = encrypt_key

    def encrypt(self, payload, enc_type):
        '''Encrypt the given message'''
        if enc_type == message.Message.ENCTYPE_NONE:
            return payload
        assert self.database
        # get own key from database for signing
        own_key = get_own_key_id(self.database)
        if enc_type == message.Message.ENCTYPE_ASYM:
            assert self.crypto
            return self.crypto.encrypt_and_sign(message=payload, recipient=self.encrypt_key,
                                                own_key=own_key)
        # Unsupported encryption type
        raise CryptoError()


def get_profile_as_string(profile):
    '''Return a string as a serialized representation of the given profile'''
    fields_to_copy = {}
    if profile:
        for key in profile.keys():
            if key not in ["status", "displayName", "ownprofile", "torid", "_id",
                           "keyid", "profilepicpath"]:
                fields_to_copy[key] = profile[key]
    return json.dumps(fields_to_copy)

def convert_string_to_dictionary(profile_string):
    '''Converts a profile string from an incoming message to a dictionary for update'''
    if isinstance(profile_string, str):
        try:
            result = json.loads(profile_string)
            if isinstance(result, dict):
                return result
        except ValueError:
            pass
    return None

def calculate_hash(db_row, used_fields=None):
    '''Return a hexadecimal string identifying the state of the database row, for comparison'''
    hasher = hashlib.md5()
    if db_row:
        for key in sorted(db_row.keys()):
            found_val = db_row[key]
            # ignore object ids and boolean flags
            if isinstance(found_val, str):
                if used_fields is not None:
                    used_fields[key] = found_val
                val_str = key + ":" + found_val
                hasher.update(val_str.encode('utf-8'))
    return hasher.hexdigest()

def export_all_avatars(database, outputdir):
    '''Export all the avatars for all contacts in the database to the given directory'''
    if not database:
        return
    for profile in database.get_profiles():
        outpath = os.path.join(outputdir, "avatar-" + profile.get('torid') + ".jpg")
        if not os.path.exists(outpath):
            # File doesn't exist, so get profilepic data
            picstr = profile.get("profilepic")
            if picstr:
                print("Debug: exportAvatar using bytes to", outpath)
                # Convert string to bytes and write to file
                pic_bytes = imageutils.string_to_bytes(picstr)
                if pic_bytes:
                    with open(outpath, "wb") as picfile:
                        picfile.write(pic_bytes)
            else:
                shutil.copy(os.path.join(outputdir, "avatar-none.jpg"), outpath)

def get_own_tor_id(database):
    '''Get our own tor id from the database'''
    own_profile = database.get_profile() if database else None
    return own_profile.get('torid') if own_profile else None

def get_own_key_id(database):
    '''Get our own key id from the database'''
    own_profile = database.get_profile() if database else None
    return own_profile.get('keyid') if own_profile else None

def user_id_from_key_id(database, key_id):
    '''Look for the key id in profiles and return the torid'''
    if database and key_id:
        for profile in database.get_profiles():
            if profile.get('keyid') == key_id:
                return profile.get('torid')
    return None

def create_profile(database, tor_id, in_profile, pic_output_path=None):
    '''Creates a new profile with the given torid, which should not yet exist.
       Also exports the avatar to the given output path'''
    in_profile['torid'] = tor_id
    if database:
        existing_profile = database.get_profile(tor_id)
        if existing_profile:
            if existing_profile.get("status") not in ["deleted", "requested", None]:
                print("Don't need to create profile, exists already!")
        if not database.add_or_update_profile(in_profile):
            print("FAILED to create profile, call failed!")
        if pic_output_path:
            _update_avatar(database, tor_id, pic_output_path)

def update_profile(database, tor_id, in_profile, pic_output_path=None, config=None):
    '''Updates the profile with the given torid, which should exist already.
       Also exports the avatar to the given output path if changed'''
    # If the profile pic path has changed, then we need to load the file
    given_picpath = in_profile.get('profilepicpath')
    pic_changed = False
    if given_picpath and os.path.exists(given_picpath):
        pic_changed = True
        # check if it's the same path as already stored
        stored_profile = database.get_profile(tor_id) if database else None
        if not stored_profile or stored_profile['profilepicpath'] != given_picpath:
            # file path has been given, so need to make a string from the bytes
            pic_bytes = imageutils.make_thumbnail_binary(given_picpath)
            in_profile['profilepic'] = imageutils.bytes_to_string(pic_bytes)
    elif in_profile.get('profilepic'):
        pic_changed = True
    in_profile['torid'] = tor_id
    if database:
        if not database.get_profile(tor_id) or not database.add_or_update_profile(in_profile):
            print("FAILED to update profile!")
    if pic_changed and pic_output_path:
        _update_avatar(database, tor_id, pic_output_path)
    if config and in_profile.get("status") in ["blocked", "deleted", "trusted"]:
        allow_friends_see_friends = config.get_property(config.KEY_LET_FRIENDS_SEE_FRIENDS)
        update_contact_list(database, allow_friends_see_friends)

def _update_avatar(database, user_id, output_dir):
    '''Update the avatar for the given user id'''
    picname = "avatar-%s.jpg" % user_id
    outpath = os.path.join(output_dir, picname)
    print("out path for update_avatar = ", outpath)
    try:
        os.remove(outpath)
    except (FileNotFoundError, TypeError):
        pass # it wasn't there anyway
    # We export pics for all the contacts but only the ones whose jpg doesn't exist already
    export_all_avatars(database, output_dir)

def update_contact_list(database, show_list):
    '''Depending on the setting, either clears the contact list from our own profile,
       or populates it based on the list of contacts in the database'''
    contact_list = []
    if show_list and database:
        # loop over trusted contacts
        for profile in database.get_profiles_with_status("trusted"):
            if profile['name']:
                contact_list.append((profile['torid'], profile['name']))
    database.add_or_update_profile({'torid':get_own_tor_id(database),
                                    'contactlist':contactutils.contacts_to_string(contact_list)})

def get_messageable_profiles(database):
    '''Return list of profiles to whom we can send a message'''
    if database:
        return [profile for profile in database.get_profiles_with_status(["trusted", "untrusted"])]
    return []

def has_friends(database):
    '''Return True if there is at least one trusted or untrusted friend'''
    return bool(get_messageable_profiles(database))

def get_status(database, tor_id):
    '''Return the status of the given tor_id'''
    profile = database.get_profile(tor_id) if database else None
    return profile.get('status') if profile else None

def is_trusted(database, tor_id):
    '''Return true if the given tor id is trusted'''
    return get_status(database, tor_id) == 'trusted'

def get_robot_status(database, tor_id, contacts):
    '''Return string describing robot status'''
    profile = database.get_profile(tor_id) if database else None
    robot_id = profile.get('robot') if profile else None
    if not robot_id:
        return "none"
    robot_profile = database.get_profile(robot_id)
    robot_status = robot_profile.get('status') if robot_profile else None
    result_key = "none"
    if robot_status == "reqrobot":
        result_key = "requested"
    elif robot_status == "robot":
        result_key = "enabled"
        if tor_id == get_own_tor_id(database) and contacts:
            result_key += (".online" if contacts.is_online(robot_id) else ".offline")
    return result_key

def has_robot(database, tor_id):
    '''Return True if the user with the given tor_id has a robot'''
    return get_robot_status(database, tor_id, None) == "enabled"

def add_message_to_inbox(msg, database, context):
    '''Unpack the given message and add it to the inbox according to the context.'''
    if msg and database:
        assert isinstance(msg, message.Message)
        # Make a dictionary using the given context
        db_row = inbox.create_row(msg, context)
        if db_row:
            # Calculate hash of message's type + body + timestamp + sender
            this_hash = calculate_hash({"type":db_row.get(inbox.FN_MSG_TYPE),
                                        "body":db_row.get(inbox.FN_MSG_BODY),
                                        "tstamp":db_row.get(inbox.FN_TIMESTAMP),
                                        "from":db_row.get(inbox.FN_FROM_ID)})
            # If hash is already in inbox, do nothing
            for found_msg in database.get_inbox():
                if found_msg and found_msg.get(inbox.FN_MSG_HASH) == this_hash:
                    print("Message already received, don't need it again!")
                    return
            # This is a new message
            db_row[inbox.FN_MSG_HASH] = this_hash
            database.add_row_to_inbox(db_row)

def delete_messages_from_inbox(sender_id, database):
    '''Find all messages in the inbox from the given sender and delete them all'''
    if sender_id and database:
        for msg in database.get_inbox():
            if msg.get(inbox.FN_FROM_ID) == sender_id:
                database.delete_from_inbox(msg.get('_id'))

def find_inbox_message(database, find_criteria):
    '''Find any inbox messages matching the given critera and return True if any found'''
    for msg in database.get_inbox():
        if msg and not msg.get(inbox.FN_DELETED):
            all_found = True
            for key, val in find_criteria.items():
                if msg.get(key) != val:
                    all_found = False
            if all_found:
                return True
    return False


def mark_conreqs_as_replied(sender_id, database):
    '''Find all contact requests from the given sender and mark them as already replied'''
    if sender_id and database:
        for msg in database.get_inbox():
            conreq = msg.get(inbox.FN_MSG_TYPE) == "contactrequest" and \
              msg.get(inbox.FN_FROM_ID) == sender_id
            conref = msg.get(inbox.FN_MSG_TYPE) == "contactrefer" and \
              msg.get(inbox.FN_FRIEND_ID) == sender_id
            if conreq or conref:
                database.update_inbox_message(msg.get('_id'), {inbox.FN_REPLIED:True})

def add_message_to_outbox(msg, crypto, database, dont_relay=None):
    '''Unpack the given message and add it to the outbox.
       Note: this method takes a message object (with recipients and
       a create_output method), not just a dictionary of values.'''
    assert msg
    # Fill in sender id if not already present
    if not msg.get_field(msg.FIELD_SENDER_ID):
        own_profile = database.get_profile()
        msg.set_field(msg.FIELD_SENDER_ID, own_profile['torid'])
    if not msg.is_complete_for_sending():
        print("Message is not complete, cannot add to outbox:", msg)
        assert False
    if msg.recipients:
        # To whom can I relay this message?
        relays = set()
        if msg.should_be_relayed:
            relays = {profile['torid'] for profile in \
                      database.get_profiles_with_status(["trusted", "robot"])}
            relays.discard(dont_relay)

        for recpt in msg.recipients:
            if isinstance(msg, message.UnencryptedMessage):
                # If msg doesn't need encryption, then doesn't need a profile
                encrypt_key = "notneeded"
            else:
                prof = database.get_profile(torid=recpt)
                encrypt_key = prof.get("keyid") if prof else None

            if encrypt_key:
                try:
                    encrypter = EncrypterShim(database=database, crypto=crypto,
                                              encrypt_key=encrypt_key)
                    to_send = imageutils.bytes_to_string(msg.create_output(encrypter=encrypter))
                    if not to_send:
                        print("WARN: message to send is empty for enc type:", msg.enc_type)
                    database.add_row_to_outbox({"recipient":recpt,
                                                "relays":list(relays.difference({recpt})),
                                                "message":to_send,
                                                "queue":msg.should_be_queued,
                                                "encType":msg.enc_type,
                                                "msgType":msg.describe_message_type()})
                except CryptoError as exc:
                    print("CryptoError thrown: can't add message to Outbox!", exc)
            else:
                print("Profile for '%s' has no keyid so can't add message to outbox!" % recpt)

def add_relayed_message_to_outbox(msg, sender_id, database):
    '''Unpack the given relayed message and copy contents to the outbox.'''
    assert msg
    print("Relayed msg is of type:", type(msg))
    recipients = {profile['torid'] for profile in \
      database.get_profiles_with_status(["trusted", "owner"])}
    recipients.discard(sender_id)
    # convert output to string for storage
    to_send = imageutils.bytes_to_string(msg.create_output(encrypter=None))
    if not to_send:
        print("ERROR: Relayed message to send is empty for type", msg.enc_type)
    database.add_row_to_outbox({"recipientList":list(recipients),
                                "relays":[], "message":to_send,
                                "queue":True, "encType":msg.enc_type,
                                "msgType":msg.describe_message_type()})
