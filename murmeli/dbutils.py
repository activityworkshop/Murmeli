'''DbUtils for JSON conversion for Murmeli'''

import json    # for converting strings to and from json
import hashlib # for calculating checksums
import os      # for managing paths
import shutil  # for managing files
from murmeli import imageutils
from murmeli import message
from murmeli import inbox


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
        if in_profile.get("status") == "trusted":
            # TODO: Get friends-see-friends setting out of the config, use to update contact list
            pass

def update_profile(database, tor_id, in_profile, pic_output_path=None):
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

def get_messageable_profiles(database):
    '''Return list of profiles to whom we can send a message'''
    if database:
        return [profile for profile in database.get_profiles_with_status(["trusted", "untrusted"])]
    return []

def add_message_to_inbox(msg, database, context):
    '''Unpack the given message and add it to the inbox according to the context.'''
    if msg and database:
        assert isinstance(msg, message.Message)
        # Make a dictionary using the given context
        db_row = inbox.create_row(msg, context)
        database.add_row_to_inbox(db_row)

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
