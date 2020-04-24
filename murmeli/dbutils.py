'''DbUtils for JSON conversion for Murmeli'''

import json    # for converting strings to and from json
import hashlib # for calculating checksums
from murmeli import imageutils


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

def get_own_tor_id(database):
    '''Get our own tor id from the database'''
    own_profile = database.get_profile() if database else None
    return own_profile.get('torid') if own_profile else None

def get_messageable_profiles(database):
    '''Return list of profiles to whom we can send a message'''
    if database:
        return [profile for profile in database.get_profiles_with_status(["trusted", "untrusted"])]
    return []

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
        for recpt in msg.recipients:
            to_send = imageutils.bytes_to_string(msg.create_output(encrypter=None))
            database.add_row_to_outbox({"recipient":recpt,
                                        "message":to_send,
                                        "queue":msg.should_be_queued,
                                        "encType":msg.enc_type})
