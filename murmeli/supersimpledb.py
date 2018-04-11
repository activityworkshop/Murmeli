'''Module for the database classes based on SuperSimpleDb'''

import json
import os.path
import threading
from murmeli.system import System, Component


class SuperSimpleDb:
    '''Holds a super-simple database as a dictionary in memory
       and allows read/write from a persistent file.
       The dictionary holds tables, stored by name, where each
       table is a list of dictionaries.
       Rows of the table (items in the list) can be added, modified
       or deleted, although deleting a row just sets the row to an
       empty dictionary rather than removing it from the list.
       The key of each row is then just the index of the item in the list.
       When loaded from file, the empty rows are then ignored.'''

    def __init__(self, file_path=None):
        '''Constructor.  If filePath is None, then there will be no file loading or saving.'''
        self.db = {}    # Database, holding a dictionary of lists
        self.file_path = file_path
        if file_path:
            self.load_from_file()

    def load_from_file(self):
        '''Load the database using the path given in the constructor'''
        if self.file_path and os.path.exists(self.file_path):
            with open(self.file_path, "r") as fp:
                self.db = json.load(fp)

    def save_to_file(self):
        '''Save the database back to the specified file'''
        if self.file_path:
            # Save the copy to file (overwriting what was there)
            with open(self.file_path, "w") as fp:
                json.dump(self.db, fp)

    def get_table(self, table_name):
        '''Get the table with the given name, and create it if necessary'''
        table = self.db.get(table_name, None)
        if table:
            return table
        # Table doesn't exist yet, so create it
        self.db[table_name] = []
        return self.db[table_name]

    def compress_table(self, table_name):
        '''Compress the specified table by removing the empty rows'''
        if self.db.get(table_name, None):
            self.db[table_name] = [m for m in self.get_table(table_name) if m]

    def delete_from_table(self, table_name, index):
        '''Returns True if specified row could be deleted, otherwise False'''
        table = self.db.get(table_name, None)
        index = int(index) if isinstance(index, str) else index
        if table and len(table) > index:
            table[index] = {}
            return True
        return False

    def get_num_tables(self):
        '''Only needed for testing'''
        return len(self.db)

    def find_in_table(self, table, criteria):
        '''Look in the given table (obtained from eg get_table) for rows
           matching the given criteria.  Criteria may include lists.'''
        results = []
        for item in table:
            row_matches = True
            # Loop through criteria, checking that all of them match this row
            for crit_key in criteria.keys():
                crit_val = criteria.get(crit_key, None)
                row_val = item.get(crit_key, None)
                if crit_val is None or crit_val == "":
                    if row_val:
                        row_matches = False
                elif isinstance(crit_val, int) or isinstance(crit_val, str):
                    if row_val != crit_val:
                        row_matches = False
                elif isinstance(crit_val, list):
                    if not row_val in crit_val:
                        row_matches = False
            if row_matches:
                results.append(item)

        return results


class Profile(dict):
    '''Wrapper class for profiles from the database'''
    def __init__(self, inDict):
        dict.__init__(self, inDict.copy())
    def __getitem__(self, key):
        val = dict.get(self, key, None)
        if not val and key == 'displayName':
            val = dict.get(self, 'name', None)
        if not val and key in ['displayName', 'name']:
            val = dict.get(self, 'torid', None)
        return val


class MurmeliDb(Component):
    '''Specialization of the SuperSimpleDb to handle Murmeli specifics'''
    db_write_lock = threading.Lock()

    TABLE_PROFILES = "profiles"
    TABLE_PENDING = "pendingcontacts"
    TABLE_OUTBOX = "outbox"
    TABLE_INBOX = "inbox"
    TABLE_ADMIN = "admin"

    def __init__(self, parent, file_path=None):
        '''Constructor.  If file_path is None, then there will be no file loading or saving.'''
        Component.__init__(self, parent, System.COMPNAME_DATABASE)
        self.db = SuperSimpleDb(file_path)
        with threading.Condition(self.db_write_lock):
            self.compress_table(MurmeliDb.TABLE_INBOX)
            self.compress_table(MurmeliDb.TABLE_OUTBOX)
            # TODO: Remove expired outbox messages?

    def compress_table(self, table_name):
        '''Compress the table and renumber the indexes'''
        self.db.compress_table(table_name)
        # assume our caller already has a write lock
        for i, r in enumerate(self.db.get_table(table_name)):
            if r and r.get("_id", None) != i:
                r['_id'] = i

    def get_inbox(self):
        '''Get a copy of the inbox'''
        return [m.copy() for m in self.db.get_table(MurmeliDb.TABLE_INBOX) if m]

    def get_profiles(self):
        '''Get all the (non-blank) profiles'''
        tab = self.db.get_table(MurmeliDb.TABLE_PROFILES)
        return [Profile(i) for i in tab if i]

    def get_profiles_with_status(self, status):
        '''Get all the profiles with the given status'''
        tab = self.db.get_table(MurmeliDb.TABLE_PROFILES)
        if isinstance(status, list):
            return [Profile(i) for i in tab if i and i.get("status", None) in status]
        elif status:
            return [Profile(i) for i in tab if i and i.get("status", None) == status]

    def get_profile(self, torid=None):
        '''Get the profile for the given torid'''
        if torid:
            for p in self.db.get_table(MurmeliDb.TABLE_PROFILES):
                if p and p.get("torid", None) == torid:
                    return Profile(p)
        else:
            # No id given, so get our own profile
            for p in self.db.get_table(MurmeliDb.TABLE_PROFILES):
                if p and p.get("status", None) == "self":
                    return Profile(p)
            print("%d rows in profiles table, but self not found?"
                  % len(self.db.get_table(MurmeliDb.TABLE_PROFILES)))

    def get_outbox(self):
        '''Get copies of all the messages in the outbox'''
        return [m.copy() for m in self.db.get_table(MurmeliDb.TABLE_OUTBOX) if m]

    def add_pending_contact(self, message):
        '''Add the given message to the pending contacts table
           (caller should have already checked that same hash
           isn't there in the table already)'''
        with threading.Condition(self.db_write_lock):
            self.db.get_table(MurmeliDb.TABLE_PENDING).append(message)

    def delete_from_pending_contacts(self, sender_id):
        '''Delete all the pending contact messages from the given senderId'''
        with threading.Condition(self.db_write_lock):
            for i, pc in enumerate(self.db.get_table(MurmeliDb.TABLE_PENDING)):
                if pc and pc.get("fromId", None) == sender_id:
                    self.db.delete_from_table(MurmeliDb.TABLE_PENDING, i)

    def get_pending_contact_messages(self):
        '''Get copies of all pending contact messages'''
        return [m.copy() for m in self.db.get_table(MurmeliDb.TABLE_PENDING) if m]

    def get_num_tables(self):
        '''Only needed for testing'''
        return self.db.get_num_tables()

    def add_message_to_inbox(self, msg):
        '''Append the given message to the inbox table'''
        with threading.Condition(self.db_write_lock):
            # Get current number in inbox, use this as index for msg
            inbox = self.db.get_table(MurmeliDb.TABLE_INBOX)
            msg['_id'] = len(inbox)
            inbox.append(msg)

    def delete_from_inbox(self, index):
        '''Delete the message at the given index from the inbox, return True on success'''
        with threading.Condition(self.db_write_lock):
            return self.db.delete_from_table(MurmeliDb.TABLE_INBOX, index)

    def update_inbox_message(self, index, props):
        '''Update the inbox message at the given index'''
        with threading.Condition(self.db_write_lock):
            inbox = self.db.get_table(MurmeliDb.TABLE_INBOX)
            if len(inbox) > index:
                row = inbox[index]
                if row:
                    row.update(props)
                    return True

    def add_message_to_outbox(self, msg):
        '''Append the given message to the outbox'''
        with threading.Condition(self.db_write_lock):
            # Get current number in outbox, use this as index for msg
            outbox = self.db.get_table(MurmeliDb.TABLE_OUTBOX)
            msg['_id'] = len(outbox)
            # TODO: Call system's encrypter for each of the recipients
            outbox.append(msg)

    def delete_from_outbox(self, index):
        '''Delete the message at the given index from the outbox, return True on success'''
        with threading.Condition(self.db_write_lock):
            return self.db.delete_from_table(MurmeliDb.TABLE_OUTBOX, index)

    def update_outbox_message(self, index, props):
        '''Update the outbox message at the given index'''
        with threading.Condition(self.db_write_lock):
            outbox = self.db.get_table(MurmeliDb.TABLE_OUTBOX)
            if len(outbox) > index:
                row = outbox[index]
                if row:
                    row.update(props)
                    return True

    def add_or_update_profile(self, prof):
        '''Either insert a new profile or update an existing one according to the id'''
        with threading.Condition(self.db_write_lock):
            tab = self.db.get_table(MurmeliDb.TABLE_PROFILES)
            new_id = prof.get("torid", None)
            if not new_id:
                return False
            for p in tab:
                if p.get("torid", None) == new_id:
                    p.update(prof)
                    return True
            tab.append(prof)
            return True

    def get_admin_value(self, key):
        '''Get the value of the given key, or None if not found'''
        tab = self.db.get_table(MurmeliDb.TABLE_ADMIN)
        first_row = tab[0] if tab else None
        if first_row:
            return first_row.get(key, None)

    def set_admin_value(self, key, value):
        '''Set the value of the given key'''
        tab = self.db.get_table(MurmeliDb.TABLE_ADMIN)
        first_row = tab[0] if tab else None
        if first_row:
            first_row[key] = value
        else:
            tab.append({key:value})

    def load_from_file(self):
        '''Load the database from file'''
        with threading.Condition(self.db_write_lock):
            self.db.load_from_file()

    def save_to_file(self):
        '''Save the database to file'''
        with threading.Condition(self.db_write_lock):
            self.db.save_to_file()

    def stop(self):
        '''Stop the database'''
        self.save_to_file()

    def find_in_table(self, table, criteria):
        '''Look in the given table (obtained from eg get_inbox) for rows
           matching the given criteria.  Criteria may include lists.'''
        return self.db.find_in_table(table, criteria)
